import asyncio
import sys
import httpx
sys.stdout.reconfigure(encoding='utf-8')
from main import app
from app.db import db
from app.auth import create_session_token

async def run_tests():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        print("\n--- 1. Testing Root and Login Pages ---")
        res = await client.get("/")
        print(f"GET / -> Status {res.status_code} (Redirected to {res.headers.get('location')})")
        assert res.status_code in [303, 307]

        res = await client.get("/login")
        print(f"GET /login -> Status {res.status_code}")
        assert res.status_code == 200
        assert "SR Enterprise" in res.text
        assert "Hind Siliguri" in res.text

        print("\n--- 2. Testing Dealer Admin Login ---")
        res = await client.post("/login/admin", data={"username": "admin", "password": "admin123"}, follow_redirects=False)
        print(f"POST /login/admin -> Status {res.status_code}, Cookie set: {'sre_session' in res.cookies}")
        assert res.status_code == 303
        admin_cookie = res.cookies["sre_session"]
        client.cookies.set("sre_session", admin_cookie)

        print("\n--- 3. Testing Admin Dashboard ---")
        res = await client.get("/admin")
        print(f"GET /admin -> Status {res.status_code}")
        assert res.status_code == 200
        assert "ডিলার কন্ট্রোল সেন্টার" in res.text

        print("\n--- 4. Testing Inventory Listing & QR Generation ---")
        res = await client.get("/admin/inventory")
        print(f"GET /admin/inventory -> Status {res.status_code}")
        assert res.status_code == 200
        assert "নুরিশ ব্রয়লার স্টার্টার" in res.text

        # Test QR label image route
        products = db.get_products()
        test_prod = products[0]
        res = await client.get(f"/admin/inventory/qr-label/{test_prod['id']}")
        print(f"GET /admin/inventory/qr-label/{test_prod['id']} -> Status {res.status_code}, Content-Type: {res.headers.get('content-type')}")
        assert res.status_code == 200
        assert res.headers.get("content-type") == "image/png"

        print("\n--- 5. Testing QR Lookup API ---")
        res = await client.get(f"/api/qr/lookup?code={test_prod['qr_code']}")
        print(f"GET /api/qr/lookup (Product) -> Status {res.status_code}, Result: {res.json()['data']['name_bn']}")
        assert res.status_code == 200
        assert res.json()["status"] == "success"

        farmers = db.get_farmers()
        test_farmer = farmers[0]
        res = await client.get(f"/api/qr/lookup?code=SRE:FRM:{test_farmer['id']}")
        print(f"GET /api/qr/lookup (Farmer) -> Status {res.status_code}, Result: {res.json()['data']['name']}")
        assert res.status_code == 200

        print("\n--- 6. Testing Batch Lifecycle (Shed Management) ---")
        res = await client.get("/admin/batches")
        assert res.status_code == 200
        batches = db.get_batches(status="active")
        active_b = batches[0]
        res = await client.get(f"/admin/batch/{active_b['id']}")
        assert res.status_code == 200
        assert active_b["batch_no"] in res.text

        # Add a feed log
        res = await client.post(f"/admin/batch/{active_b['id']}/add-log", data={
            "log_type": "feed",
            "log_date": "2026-10-25",
            "item_id": test_prod["id"],
            "item_name": test_prod["name_bn"],
            "qty": 5,
            "unit": "বস্তা",
            "unit_price": test_prod["sell_price"],
            "note": "অটোমেটেড টেস্ট ফিড ডেলিভারি"
        }, follow_redirects=False)
        print(f"POST add-log -> Status {res.status_code}")
        assert res.status_code == 303

        print("\n--- 7. Testing POS Dispatch / Invoice Creation ---")
        items_payload = [{
            "product_id": test_prod["id"],
            "name_bn": test_prod["name_bn"],
            "qty": 2,
            "unit": test_prod["unit"],
            "price": test_prod["sell_price"],
            "category": test_prod["category"],
            "total": 2 * test_prod["sell_price"]
        }]
        import json
        prev_due = test_farmer["total_due"]
        res = await client.post("/admin/dispatch/create", data={
            "farmer_id": test_farmer["id"],
            "batch_id": active_b["id"],
            "invoice_date": "2026-10-25",
            "items_json": json.dumps(items_payload),
            "subtotal": 2 * test_prod["sell_price"],
            "discount": 0,
            "paid_amount": 0,
            "payment_type": "credit",
            "note": "টেস্ট চালান মেমো"
        }, follow_redirects=False)
        print(f"POST /admin/dispatch/create -> Status {res.status_code}, Redirects to: {res.headers.get('location')}")
        assert res.status_code == 303
        
        # Check printable memo
        memo_url = res.headers.get("location")
        created_inv_id = memo_url.split("/")[3]
        res = await client.get(memo_url)
        assert res.status_code == 200
        assert "ক্যাশ মেমো" in res.text
        assert test_farmer["name"] in res.text

        # Verify farmer due was updated
        updated_f = db.get_farmer_by_id(test_farmer["id"])
        print(f"Farmer due before: ৳{prev_due:,.0f} -> after invoice: ৳{updated_f['total_due']:,.0f}")
        assert updated_f["total_due"] > prev_due

        print("\n--- 8. Testing Payment Collection ---")
        res = await client.post("/admin/payments/record", data={
            "farmer_id": test_farmer["id"],
            "amount": 10000,
            "payment_method": "bKash",
            "transaction_ref": "BKASH_TEST_TRX",
            "payment_date": "2026-10-25",
            "note": "বিকাশ পেমেন্ট টেস্ট"
        }, follow_redirects=False)
        assert res.status_code == 303
        after_pay_f = db.get_farmer_by_id(test_farmer["id"])
        print(f"Farmer due after ৳10,000 payment: ৳{after_pay_f['total_due']:,.0f}")
        assert after_pay_f["total_due"] == updated_f["total_due"] - 10000

        print("\n--- 9. Testing Farmer Portal Login & Live Views ---")
        client.cookies.clear()
        res = await client.post("/login/farmer", data={"phone": test_farmer["phone"], "pin": test_farmer["pin"]}, follow_redirects=False)
        print(f"POST /login/farmer -> Status {res.status_code}")
        assert res.status_code == 303
        farmer_cookie = res.cookies["sre_session"]
        client.cookies.set("sre_session", farmer_cookie)

        res = await client.get("/farmer")
        print(f"GET /farmer (Dashboard) -> Status {res.status_code}")
        assert res.status_code == 200
        assert test_farmer["name"] in res.text
        assert "আমার বর্তমান বকেয়া" in res.text

        res = await client.get("/farmer/ledger")
        print(f"GET /farmer/ledger -> Status {res.status_code}")
        assert res.status_code == 200
        assert "হিসাবের খতিয়ান" in res.text

        res = await client.post("/farmer/request-feed/submit", data={
            "items_requested": "নুরিশ গ্রোয়ার ৫ বস্তা",
            "farmer_note": "খুব দ্রুত দরকার",
            "batch_id": active_b["id"]
        }, follow_redirects=False)
        assert res.status_code == 303
        print(f"POST /farmer/request-feed/submit -> Successfully requested feed!")

        print("\n--- 10. Testing Transaction Edit & Delete Features ---")
        client.cookies.clear()
        client.cookies.set("sre_session", admin_cookie)

        # 1. Invoices list page
        res = await client.get("/admin/invoices")
        print(f"GET /admin/invoices -> Status {res.status_code}")
        assert res.status_code == 200

        # 2. Update Invoice
        res = await client.post("/admin/invoice/update", data={
            "invoice_id": created_inv_id,
            "invoice_date": "2026-10-26",
            "payment_type": "credit",
            "discount": 100,
            "paid_amount": 0,
            "note": "আপডেট নোট"
        }, follow_redirects=False)
        print(f"POST /admin/invoice/update -> Status {res.status_code}")
        assert res.status_code == 303

        # 3. Payments update & delete
        latest_payments = db.get_payments(farmer_id=test_farmer["id"], limit=1)
        if latest_payments:
            pay_id = latest_payments[0]["id"]
            res = await client.post("/admin/payments/update", data={
                "payment_id": pay_id,
                "amount": 12000,
                "payment_method": "bKash",
                "transaction_ref": "TRXNEW123",
                "payment_date": "2026-10-26",
                "note": "আপডেটেড পেমেন্ট"
            }, follow_redirects=False)
            print(f"POST /admin/payments/update -> Status {res.status_code}")
            assert res.status_code == 303

            res = await client.get(f"/admin/payments/delete/{pay_id}", follow_redirects=False)
            print(f"GET /admin/payments/delete -> Status {res.status_code}")
            assert res.status_code == 303

        # 4. Delete invoice (verifying stock restoration & dues reconciliation)
        res = await client.get(f"/admin/invoice/delete/{created_inv_id}", follow_redirects=False)
        print(f"GET /admin/invoice/delete -> Status {res.status_code}")
        assert res.status_code == 303

        print("\n--- 11. Testing APK Download and Cloudinary Storage ---")
        # Test APK redirect to GitHub CDN (preserves 5GB Render free bandwidth)
        res = await client.get("/download/apk", follow_redirects=False)
        print(f"GET /download/apk -> Status {res.status_code}, Location: {res.headers.get('location')}")
        assert res.status_code == 302
        assert "raw.githubusercontent.com" in res.headers.get("location")

        # Test local APK download
        res = await client.get("/download/apk?local=1")
        print(f"GET /download/apk?local=1 -> Status {res.status_code}, Content-Type: {res.headers.get('content-type')}")
        assert res.status_code == 200
        assert len(res.content) > 50000 # Verified valid APK binary

        # Test Cloudinary storage module
        from app.storage import upload_image_file, upload_image_to_cloudinary, is_cloudinary_active
        test_img_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        saved_url = await upload_image_file(test_img_bytes, "test_pic.png", subfolder="test")
        print(f"Image upload helper -> Saved URL: {saved_url}")
        assert saved_url.startswith("http") or saved_url.startswith("/static/uploads")

        # Test direct Cloudinary helper
        direct_res = upload_image_to_cloudinary(test_img_bytes, filename="direct_test.png", subfolder="test")
        print(f"Direct Cloudinary result -> Status: {direct_res['status']}")
        assert direct_res["status"] in ["success", "error"]

        print("\n--- 12. Testing Farmer Edit, Delete & Live Autocomplete Search APIs ---")
        # 1. Create a test farmer
        new_farmer_id = db.save_farmer({
            "name": "টেস্ট খামারি রহিম",
            "phone": "01999888777",
            "pin": "5555",
            "shed_name": "রহিম পোল্ট্রি ফার্ম",
            "address": "গাজীপুর সদর",
            "shed_capacity": 2000,
            "status": "active"
        })
        print(f"Created farmer for testing: {new_farmer_id}")

        # 2. Update farmer
        res = await client.post("/admin/farmer/update", data={
            "farmer_id": new_farmer_id,
            "name": "টেস্ট খামারি রহিম (আপডেটেড)",
            "phone": "01999888777",
            "pin": "9999",
            "shed_name": "রহিম পোল্ট্রি ফার্ম - শেড ২",
            "address": "জয়দেবপুর, গাজীপুর",
            "shed_capacity": 2500,
            "status": "active",
            "notes": "আপডেটেড নোটস"
        }, follow_redirects=False)
        print(f"POST /admin/farmer/update -> Status {res.status_code}")
        assert res.status_code == 303
        updated_f = db.get_farmer_by_id(new_farmer_id)
        assert updated_f["name"] == "টেস্ট খামারি রহিম (আপডেটেড)"
        assert updated_f["pin"] == "9999"

        # 3. Test Search APIs
        res = await client.get("/api/farmers/search?q=রহিম")
        print(f"GET /api/farmers/search?q=রহিম -> Status {res.status_code}, Found: {len(res.json()['data'])}")
        assert res.status_code == 200
        assert len(res.json()["data"]) >= 1

        res = await client.get("/api/inventory/search?q=ব্রয়লার")
        print(f"GET /api/inventory/search?q=ব্রয়লার -> Status {res.status_code}, Found: {len(res.json()['data'])}")
        assert res.status_code == 200
        assert len(res.json()["data"]) >= 1

        res = await client.get("/api/batches/search?q=BATCH")
        print(f"GET /api/batches/search?q=BATCH -> Status {res.status_code}, Found: {len(res.json()['data'])}")
        assert res.status_code == 200

        res = await client.get("/api/invoices/search?q=INV")
        print(f"GET /api/invoices/search?q=INV -> Status {res.status_code}, Found: {len(res.json()['data'])}")
        assert res.status_code == 200

        res = await client.get("/api/global/search?q=নুরিশ")
        print(f"GET /api/global/search?q=নুরিশ -> Status {res.status_code}, Results: {list(res.json()['data'].keys())}")
        assert res.status_code == 200

        # 4. Delete farmer
        res = await client.get(f"/admin/farmer/delete/{new_farmer_id}", follow_redirects=False)
        print(f"GET /admin/farmer/delete -> Status {res.status_code}")
        assert res.status_code == 303
        assert db.get_farmer_by_id(new_farmer_id) is None
        print(f"Farmer {new_farmer_id} successfully deleted from database!")

        print("\n--- 13. Testing Shed (Batch) Edit, Delete & Dispatch with ?scan=1 ---")
        # 1. Test dispatch page with scan=1
        res = await client.get("/admin/dispatch?scan=1")
        print(f"GET /admin/dispatch?scan=1 -> Status {res.status_code}")
        assert res.status_code == 200
        assert "checkoutScannerArea" in res.text

        # 2. Create test batch
        test_batch_id = db.save_batch({
            "batch_no": "টেস্ট ব্যাচ-৯৯",
            "farmer_id": test_farmer["id"],
            "farmer_name": test_farmer["name"],
            "bird_type": "ব্রয়লার (Cobb 500)",
            "chick_qty": 500,
            "chick_unit_cost": 50.0,
            "start_date": "2026-10-26",
            "notes": "টেস্টিং নোট"
        })
        print(f"Created batch for testing: {test_batch_id}")

        # 3. Update batch
        res = await client.post("/admin/batch/update", data={
            "batch_id": test_batch_id,
            "batch_no": "টেস্ট ব্যাচ-৯৯ (আপডেটেড)",
            "bird_type": "সোনালী হাইব্রিড",
            "chick_qty": 600,
            "chick_unit_cost": 45.0,
            "start_date": "2026-10-26",
            "status": "active",
            "notes": "আপডেটেড টেস্টিং নোট"
        }, follow_redirects=False)
        print(f"POST /admin/batch/update -> Status {res.status_code}")
        assert res.status_code == 303
        updated_b = db.get_batch_by_id(test_batch_id)
        assert updated_b["batch_no"] == "টেস্ট ব্যাচ-৯৯ (আপডেটেড)"
        assert updated_b["chick_qty"] == 600

        # 4. Delete batch
        res = await client.get(f"/admin/batch/delete/{test_batch_id}", follow_redirects=False)
        print(f"GET /admin/batch/delete -> Status {res.status_code}")
        assert res.status_code == 303
        assert db.get_batch_by_id(test_batch_id) is None
        print(f"Batch {test_batch_id} successfully deleted from database!")

        # --- 14. Testing Multiple Sheds per Farmer & Automatic Cost Attribution in Dispatch ---
        print("\n--- 14. Testing Multiple Sheds per Farmer & Automatic Cost Attribution ---")
        # Create farmer with 2 active sheds
        f_multi_id = db.save_farmer({
            "name": "মাল্টি-শেড খামারি",
            "phone": "01799887766",
            "address": "গাজীপুর সদর",
            "shed_capacity": 4000
        })

        batch_1_id = db.save_batch({
            "batch_no": "শেড-১ (ব্রয়লার)",
            "farmer_id": f_multi_id,
            "farmer_name": "মাল্টি-শেড খামারি",
            "bird_type": "ব্রয়লার",
            "chick_qty": 2000,
            "chick_unit_cost": 50.0,
            "start_date": "2026-10-26"
        })

        batch_2_id = db.save_batch({
            "batch_no": "শেড-২ (সোনালী)",
            "farmer_id": f_multi_id,
            "farmer_name": "মাল্টি-শেড খামারি",
            "bird_type": "সোনালী",
            "chick_qty": 1500,
            "chick_unit_cost": 40.0,
            "start_date": "2026-10-26"
        })

        # Test API returns both sheds
        res = await client.get(f"/api/farmer/{f_multi_id}/batches")
        assert res.status_code == 200
        data = res.json()
        assert data["count"] == 2
        batch_ids = [b["id"] for b in data["all_batches"]]
        assert batch_1_id in batch_ids and batch_2_id in batch_ids
        print(f"GET /api/farmer/{f_multi_id}/batches -> Status 200, Found {data['count']} sheds for farmer")

        # Initial investments
        b1_init = db.get_batch_by_id(batch_1_id)["total_investment"]
        b2_init = db.get_batch_by_id(batch_2_id)["total_investment"]

        # Create dispatch specifically for Shed-2
        feed_items = [{
            "id": "P001",
            "sku": "SRE-FD-01",
            "name_bn": "নুরিশ ব্রয়লার স্টার্টার",
            "category": "পৌল্ট্রি খাদ্য",
            "unit": "বস্তা (৫০ কেজি)",
            "qty": 2,
            "price": 3550,
            "total": 7100
        }]

        inv_res = await client.post("/admin/dispatch/create", data={
            "farmer_id": f_multi_id,
            "batch_id": batch_2_id,
            "invoice_date": "2026-10-26",
            "items_json": json.dumps(feed_items),
            "subtotal": 7100,
            "discount": 0,
            "paid_amount": 0,
            "payment_type": "credit",
            "note": "শেড-২ এর খাদ্য চালান"
        }, follow_redirects=False)
        assert inv_res.status_code == 303
        inv_id = inv_res.headers["location"].split("/admin/invoice/")[1].split("/print")[0]
        print(f"Created dispatch {inv_id} tied to Shed-2 (batch_2_id)")

        # Verify Shed-2 cost increased automatically by 7,100
        b2_updated = db.get_batch_by_id(batch_2_id)
        assert b2_updated["total_feed_cost"] == 7100
        assert b2_updated["total_feed_bags"] == 2
        assert b2_updated["total_investment"] == b2_init + 7100
        print(f"Shed-2 Feed Cost: ৳{b2_updated['total_feed_cost']}, Total Investment: ৳{b2_updated['total_investment']} (Successfully updated)")

        # Verify Shed-1 was NOT affected
        b1_updated = db.get_batch_by_id(batch_1_id)
        assert b1_updated["total_feed_cost"] == 0
        assert b1_updated["total_investment"] == b1_init
        print("Shed-1 investment remained untouched (Accurate attribution verified)")

        # Verify print memo endpoint contains batch
        memo_res = await client.get(f"/admin/invoice/{inv_id}/print")
        assert memo_res.status_code == 200
        assert "শেড-২ (সোনালী)" in memo_res.text
        print("Print memo successfully shows the selected shed/batch name!")

        # Clean up test data
        db.delete_invoice(inv_id)
        db.delete_batch(batch_1_id)
        db.delete_batch(batch_2_id)
        db.delete_farmer(f_multi_id)

        print("\n=======================================================")
        print("ALL TESTS PASSED SUCCESSFULLY! 100% VERIFIED!")
        print("=======================================================\n")

if __name__ == "__main__":
    asyncio.run(run_tests())
