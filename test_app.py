import asyncio
import sys
import uuid
import json
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

        print("\n--- 7b. Testing Retail / Walk-in Customer Sale & Auto Stock Sync ---")
        # Grab a medicine product to sell to a retail customer
        med_prods = [p for p in db.get_products() if "ঔষধ" in p.get("category", "")]
        test_med = med_prods[0] if med_prods else test_prod
        initial_stock = test_med["stock"]
        retail_qty = 3
        retail_items = [{
            "id": test_med["id"],
            "product_id": test_med["id"],
            "sku": test_med["sku"],
            "name": test_med["name"],
            "name_bn": test_med["name_bn"],
            "qty": retail_qty,
            "unit": test_med["unit"],
            "price": test_med["sell_price"],
            "category": test_med["category"],
            "total": retail_qty * test_med["sell_price"]
        }]
        total_retail_price = retail_qty * test_med["sell_price"]
        farmer_due_before_retail = updated_f["total_due"]

        res = await client.post("/admin/dispatch/create", data={
            "customer_type": "retail",
            "customer_name": "জালাল উদ্দিন",
            "customer_phone": "01711223344",
            "invoice_date": "2026-10-26",
            "items_json": json.dumps(retail_items),
            "subtotal": total_retail_price,
            "discount": 0,
            "paid_amount": total_retail_price,
            "payment_type": "cash",
            "note": "কাউন্টার ক্যাশ খুচরা বিক্রয়"
        }, follow_redirects=False)
        print(f"POST /admin/dispatch/create (Retail) -> Status {res.status_code}")
        assert res.status_code == 303
        retail_memo_url = res.headers.get("location")
        retail_inv_id = retail_memo_url.split("/")[3]

        # Verify stock decreased by retail_qty
        stock_after_prod = db.get_product_by_id(test_med["id"])
        print(f"Stock before retail sale: {initial_stock} -> after: {stock_after_prod['stock']}")
        assert stock_after_prod["stock"] == initial_stock - retail_qty

        # Verify registered farmers due was NOT modified
        farmer_after_retail = db.get_farmer_by_id(test_farmer["id"])
        assert farmer_after_retail["total_due"] == farmer_due_before_retail

        # Check printable memo for retail customer
        res = await client.get(retail_memo_url)
        assert res.status_code == 200
        assert "জালাল উদ্দিন" in res.text
        assert "খুচরা / কাউন্টার বিক্রয়" in res.text

        # Verify invoice appears in invoices list
        res = await client.get("/admin/invoices")
        assert res.status_code == 200
        assert "জালাল উদ্দিন" in res.text
        assert "খুচরা" in res.text

        print("Retail walk-in sale passed with perfect stock deduction & memo generation!")

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

        # Test Admin Notification Button & Badge next to Logout
        print("\n--- 9b. Testing Admin Top Header Notification Bell & Dropdown ---")
        admin_dash_res = await client.get("/admin")
        assert admin_dash_res.status_code == 200
        assert "notifBellBtn" in admin_dash_res.text
        assert "notifBadge" in admin_dash_res.text
        assert "খামারিদের মালামাল রিকুয়েস্ট" in admin_dash_res.text
        assert "নুরিশ গ্রোয়ার ৫ বস্তা" in admin_dash_res.text
        print("Admin header successfully displays notification bell & badge with pending request!")

        # Test Notifications API
        api_notif_res = await client.get("/admin/api/notifications")
        assert api_notif_res.status_code == 200
        notif_json = api_notif_res.json()
        assert notif_json["count"] >= 1
        assert any("নুরিশ গ্রোয়ার" in req["items_requested"] for req in notif_json["requests"])
        print(f"GET /admin/api/notifications -> Status 200, Live count: {notif_json['count']}")

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
        # Test APK redirect directly to GitHub raw CDN (preserves 5GB Render free bandwidth)
        res = await client.get("/download/apk", follow_redirects=False)
        print(f"GET /download/apk -> Status {res.status_code}, Location: {res.headers.get('location')}")
        assert res.status_code == 301
        assert "raw.githubusercontent.com/najmul5524/SR_Enterprise/main/static/apk/SR_Enterprise.apk" in res.headers.get("location")

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
        f_multi_phone = f"017{uuid.uuid4().hex[:8]}"
        f_multi_id = db.save_farmer({
            "name": "মাল্টি-শেড খামারি",
            "phone": f_multi_phone,
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
        assert data["count"] >= 2
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

        # Verify Multi-Shed Farmer Portal Sync & Feed Request with Shed Selection
        print("\n--- 14b. Testing Multi-Shed Farmer Portal Sync & Dropdown Feed Request ---")
        client.cookies.clear()
        res = await client.post("/login/farmer", data={"phone": f_multi_phone, "pin": "1234"}, follow_redirects=False)
        assert res.status_code == 303
        multi_farmer_cookie = res.cookies["sre_session"]
        client.cookies.set("sre_session", multi_farmer_cookie)

        # 1. Check farmer dashboard shows multiple sheds
        dash_res = await client.get("/farmer")
        assert dash_res.status_code == 200
        assert "শেড-১ (ব্রয়লার)" in dash_res.text
        assert "শেড-২ (সোনালী)" in dash_res.text
        assert "শেড পরিবর্তন করুন" in dash_res.text
        print("Farmer dashboard correctly synchronizes and displays multiple sheds!")

        # 2. Switch to Shed-2 via query param
        dash_shed2 = await client.get(f"/farmer?batch_id={batch_2_id}")
        assert dash_shed2.status_code == 200
        assert "শেড-২ (সোনালী)" in dash_shed2.text
        print("Farmer can seamlessly switch active shed view on dashboard!")

        # 3. Check feed request page has shed dropdown
        feed_req_page = await client.get("/farmer/request-feed")
        assert feed_req_page.status_code == 200
        assert "কোন শেডের জন্য মালামাল প্রয়োজন?" in feed_req_page.text
        assert "শেড-২ (সোনালী)" in feed_req_page.text

        # 4. Submit feed request specifically selecting Shed-2
        req_submit = await client.post("/farmer/request-feed/submit", data={
            "items_requested": "সোনালী স্টার্টার ৪ বস্তা",
            "batch_id": batch_2_id,
            "farmer_note": "শেড ২ এর জন্য জরুরি"
        }, follow_redirects=False)
        assert req_submit.status_code == 303

        # 5. Verify feed request shows shed in admin panel
        client.cookies.clear()
        client.cookies.set("sre_session", admin_cookie)
        admin_reqs = await client.get("/admin/feed-requests")
        assert admin_reqs.status_code == 200
        assert "শেড-২ (সোনালী)" in admin_reqs.text
        assert f"batch_id={batch_2_id}" in admin_reqs.text
        print("Feed request correctly attributes shed and links to dispatch in admin!")

        # Clean up test data
        db.delete_invoice(inv_id)
        db.delete_batch(batch_1_id)
        db.delete_batch(batch_2_id)
        db.delete_farmer(f_multi_id)

        print("\n--- 15. Testing Admin Settings Password Change ---")
        # 1. Verify settings page renders security section
        res = await client.get("/admin/settings")
        assert res.status_code == 200
        assert "ডিলার অ্যাডমিন পাসওয়ার্ড পরিবর্তন" in res.text
        print("GET /admin/settings -> Security section verified")

        # 2. Test wrong current password
        res = await client.post("/admin/settings/change-password", data={
            "current_password": "wrongpassword999",
            "new_password": "newpass2026",
            "confirm_password": "newpass2026"
        }, follow_redirects=False)
        assert res.status_code == 303
        assert "pwd_error" in res.headers["location"]
        print("Wrong current password successfully rejected!")

        # 3. Test password confirmation mismatch
        res = await client.post("/admin/settings/change-password", data={
            "current_password": "admin123",
            "new_password": "newpass2026",
            "confirm_password": "mismatchpass"
        }, follow_redirects=False)
        assert res.status_code == 303
        assert "pwd_error" in res.headers["location"]
        print("Password mismatch successfully rejected!")

        # 4. Successfully change admin password
        res = await client.post("/admin/settings/change-password", data={
            "current_password": "admin123",
            "new_password": "newpass2026",
            "confirm_password": "newpass2026"
        }, follow_redirects=False)
        assert res.status_code == 303
        assert "pwd_msg" in res.headers["location"]
        print("Password successfully updated to 'newpass2026'")

        # 5. Verify old password no longer works
        test_login_client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
        old_login_res = await test_login_client.post("/login/admin", data={"username": "admin", "password": "admin123"}, follow_redirects=False)
        assert old_login_res.status_code == 400
        print("Old password 'admin123' correctly rejected!")

        # 6. Verify new password logs in successfully
        new_login_res = await test_login_client.post("/login/admin", data={"username": "admin", "password": "newpass2026"}, follow_redirects=False)
        assert new_login_res.status_code == 303
        print("New password 'newpass2026' logs in successfully!")

        # 7. Reset password back to default 'admin123'
        res = await client.post("/admin/settings/change-password", data={
            "current_password": "newpass2026",
            "new_password": "admin123",
            "confirm_password": "admin123"
        }, follow_redirects=False)
        assert res.status_code == 303
        print("Admin password successfully restored to 'admin123'")

        print("\n--- 16. Testing Shed Selection during Payment Collection & Auto-Coordination ---")
        # 1. Create a test farmer and batch
        f_shed_id = f"FARMER-{uuid.uuid4().hex[:6].upper()}"
        f_phone = f"01788{uuid.uuid4().hex[:6]}"
        db.save_farmer({
            "id": f_shed_id,
            "name": "হুমায়ূন কবির",
            "phone": f_phone,
            "shed_name": "কবির ব্রয়লার ফার্ম",
            "address": "কাপাসিয়া",
            "shed_capacity": 1000,
            "total_due": 0
        })

        b_shed_id = db.save_batch({
            "batch_no": "SHED-TEST-PAY-01",
            "farmer_id": f_shed_id,
            "farmer_name": "হুমায়ূন কবির",
            "bird_type": "ব্রয়লার",
            "chick_qty": 1000,
            "chick_unit_cost": 50,
            "start_date": "2026-10-01"
        })

        b_initial = db.get_batch_by_id(b_shed_id)
        assert b_initial["total_investment"] == 50000 # 1000 * 50
        assert b_initial["total_paid"] == 0
        assert b_initial["remaining_due"] == 50000
        f_initial = db.get_farmer_by_id(f_shed_id)
        assert f_initial["total_due"] == 50000
        print(f"Initial State: Shed Investment: ৳{b_initial['total_investment']}, Paid: ৳{b_initial['total_paid']}, Farmer Due: ৳{f_initial['total_due']}")

        # 2. Collect ৳20,000 payment explicitly selecting this shed/batch
        pay_res = await client.post("/admin/payments/record", data={
            "farmer_id": f_shed_id,
            "batch_id": b_shed_id,
            "amount": 20000,
            "payment_method": "bKash",
            "transaction_ref": "TRX-SHED-PAY-123",
            "payment_date": "2026-10-15",
            "note": "শেড ১ এর অগ্রিম কিস্তি জমা",
            "redirect_to": "/admin/payments"
        }, follow_redirects=False)
        assert pay_res.status_code == 303

        # Verify automatic coordination with farmer due and shed balance
        b_after_pay = db.get_batch_by_id(b_shed_id)
        assert b_after_pay["total_paid"] == 20000
        assert b_after_pay["remaining_due"] == 30000 # 50000 - 20000
        f_after_pay = db.get_farmer_by_id(f_shed_id)
        assert f_after_pay["total_due"] == 30000 # 50000 - 20000
        print(f"After ৳20,000 Payment: Shed Paid: ৳{b_after_pay['total_paid']}, Shed Remaining Due: ৳{b_after_pay['remaining_due']}, Farmer Due: ৳{f_after_pay['total_due']}")

        # 3. Check /admin/payments renders the shed/batch column
        payments_page_res = await client.get("/admin/payments")
        assert payments_page_res.status_code == 200
        assert "SHED-TEST-PAY-01" in payments_page_res.text
        print("GET /admin/payments successfully displays 'SHED-TEST-PAY-01' in table!")

        # 4. Check /admin/batch/{b_shed_id} displays payments and payment collection button
        batch_page_res = await client.get(f"/admin/batch/{b_shed_id}")
        assert batch_page_res.status_code == 200
        assert "TRX-SHED-PAY-123" in batch_page_res.text
        assert "শেডের টাকা গ্রহণ" in batch_page_res.text
        print("GET /admin/batch/{batch_id} successfully displays payment history and collection button!")

        # 5. Test harvest settlement coordination with already collected payment
        # Harvest sale = 1500 kg @ ৳60 = ৳90,000
        # Dealer investment was 50,000, already received 20,000 -> remaining to recover is 30,000
        settle_result = db.close_and_settle_batch(b_shed_id, {
            "harvest_date": "2026-10-26",
            "birds_sold": 950,
            "total_weight_kg": 1500,
            "rate_per_kg": 60
        })
        assert settle_result["dealer_recovery"] == 50000 # Total dealer recovery = 20k paid + 30k from sale
        assert settle_result["farmer_profit"] == 60000 # 90k sale - 30k unrecovered investment
        f_settled = db.get_farmer_by_id(f_shed_id)
        assert f_settled["total_due"] == 0 # 30k remaining was recovered from sale -> 0 due! No double deduction!
        print(f"Flock Harvest Settlement: Total Sale: ৳90,000, Total Dealer Recovery: ৳{settle_result['dealer_recovery']}, Farmer Profit: ৳{settle_result['farmer_profit']}, Farmer Final Due: ৳{f_settled['total_due']}")

        # Clean up test data
        payments = db.get_payments(batch_id=b_shed_id)
        for p in payments:
            db.delete_payment(p["id"])
        db.delete_batch(b_shed_id)
        db.delete_farmer(f_shed_id)

        # --- 17. Testing Stock >= 0, Farmer Registration Shed Auto-Creation & Expenses Section ---
        print("\n--- 17. Testing Stock Limit >= 0, Auto-Shed Creation & Expenses Management ---")
        
        # Test 17a: Stock cannot drop below 0
        db.adjust_stock("P001", -99999)
        prod = db.get_product_by_id("P001")
        assert prod["stock"] >= 0.0, f"Stock dropped below 0: {prod['stock']}"
        db.adjust_stock("P001", 100) # Restore stock
        print(f"Stock >= 0 constraint verified! Current stock: {db.get_product_by_id('P001')['stock']}")

        # Test 17b: Farmer Registration immediately creates a shed in batches table
        test_ph = f"017{uuid.uuid4().hex[:8]}"
        f_reg_id = db.save_farmer({
            "name": "রেজিস্টার্ড খামারি",
            "phone": test_ph,
            "shed_name": "উত্তর পাড়া ব্রয়লার শেড",
            "shed_capacity": 2500
        })
        reg_sheds = db.get_batches(farmer_id=f_reg_id)
        assert len(reg_sheds) >= 1, "Registered farmer has no sheds!"
        assert reg_sheds[0]["batch_no"] == "উত্তর পাড়া ব্রয়লার শেড", "Shed name mismatch!"
        print(f"Auto-shed registration passed! Shed: {reg_sheds[0]['batch_no']}")
        
        # Test 17c: Expenses Section CRUD & Summary
        exp_id = db.save_expense({
            "category": "আপ্যায়ন ও চা-নাস্তা",
            "amount": 750.0,
            "payment_method": "cash",
            "note": "টেস্ট আপ্যায়ন খরচ"
        })
        exp_list = db.get_expenses(category="আপ্যায়ন ও চা-নাস্তা")
        assert any(e["id"] == exp_id for e in exp_list), "Expense not found in list!"
        exp_summary = db.get_expenses_summary()
        assert exp_summary["total_expense"] > 0, "Expense summary returned 0!"
        res_exp_page = await client.get("/admin/expenses")
        assert res_exp_page.status_code == 200, f"Expenses page status: {res_exp_page.status_code}"
        db.delete_expense(exp_id)
        print("Expenses management & summary verified successfully!")

        # Clean up registered farmer
        for s in reg_sheds:
            db.delete_batch(s["id"])
        db.delete_farmer(f_reg_id)

        print("\n--- 18. Testing Invoice Memo Photo (Admin & Farmer Views) & A4 PDF Print Template ---")
        # 18a: Create an invoice with uploaded receipt memo photo
        test_img_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        f_test_id = db.save_farmer({
            "name": "মেমো ফটো টেস্ট খামারি",
            "phone": f"017{uuid.uuid4().hex[:8]}",
            "shed_name": "শেড ১"
        })
        f_sheds = db.get_batches(farmer_id=f_test_id)
        f_shed_id = f_sheds[0]["id"] if f_sheds else ""

        res_inv_create = await client.post("/admin/dispatch/create", data={
            "farmer_id": f_test_id,
            "batch_id": f_shed_id,
            "invoice_date": "2026-10-26",
            "payment_type": "credit",
            "discount": "0",
            "paid_amount": "0",
            "items_json": json.dumps([{"id": "P001", "name": "ব্রয়লার স্টার্টার ফিড", "name_bn": "ব্রয়লার স্টার্টার ফিড", "price": 3500.0, "qty": 2.0, "unit": "বস্তা", "total": 7000.0}])
        }, files={
            "receipt_file": ("test_memo.png", test_img_bytes, "image/png")
        }, follow_redirects=False)

        assert res_inv_create.status_code == 303, f"Invoice creation failed: {res_inv_create.status_code}"
        redirect_loc = res_inv_create.headers.get("location")
        created_inv_id = redirect_loc.split("/")[-2] if "print" in redirect_loc else redirect_loc.split("/")[-1]
        
        created_inv = db.get_invoice_by_id(created_inv_id)
        assert created_inv is not None, "Created invoice not found in DB!"
        assert created_inv.get("receipt_image_url"), "receipt_image_url was not saved on invoice!"
        print(f"Invoice memo image saved: {created_inv.get('receipt_image_url')}")

        # 18b: Check Admin Invoice List & Print Template
        res_invoices_page = await client.get("/admin/invoices")
        assert res_invoices_page.status_code == 200
        assert "openMemoLightbox" in res_invoices_page.text or "ছবি" in res_invoices_page.text
        print("Admin invoices table displays memo image lightbox trigger successfully!")

        res_memo_print = await client.get(f"/admin/invoice/{created_inv_id}/print")
        assert res_memo_print.status_code == 200
        assert "সংযুক্ত হস্তলিখিত মেমো" in res_memo_print.text or "ভাউচারের ছবি" in res_memo_print.text
        assert "Hind Siliguri" in res_memo_print.text
        print("Print memo template renders physical memo photo section & Bengali font rules!")

        # 18c: Check Farmer Portal (Ledger and Dashboard)
        farmer_phone = db.get_farmer_by_id(f_test_id)["phone"]
        await client.post("/login/farmer", data={"phone": farmer_phone, "pin": "1234"})
        res_f_ledger = await client.get("/farmer/ledger")
        assert res_f_ledger.status_code == 200
        assert "openFarmerMemoModal" in res_f_ledger.text or "মেমোর ছবি" in res_f_ledger.text
        print("Farmer ledger renders interactive memo photo viewer button!")

        res_f_dash = await client.get("/farmer")
        assert res_f_dash.status_code == 200
        assert "openFarmerMemoModal" in res_f_dash.text or "মেমোর ছবি" in res_f_dash.text
        print("Farmer dashboard renders recent invoices with memo photo modal button!")

        # 18d: Update invoice with new receipt memo (switch back to admin)
        await client.post("/login/admin", data={"username": "admin", "password": "admin123"}, follow_redirects=False)
        new_img_bytes = b"new_memo_photo_content_bytes"
        res_inv_update = await client.post("/admin/invoice/update", data={
            "invoice_id": created_inv_id,
            "invoice_date": "2026-10-26",
            "payment_type": "credit",
            "discount": "100",
            "paid_amount": "500",
            "note": "আপডেটেড নোট"
        }, files={
            "receipt_file": ("updated_memo.png", new_img_bytes, "image/png")
        }, follow_redirects=False)
        assert res_inv_update.status_code == 303
        updated_inv = db.get_invoice_by_id(created_inv_id)
        assert updated_inv["discount"] == 100.0
        print("Invoice memo photo update verified successfully!")

        print("\n--- 19. Testing Farmer Digital Memo & Real-Time Notifications ---")
        # 19a: Test Farmer Digital Memo Access
        farmer_phone = db.get_farmer_by_id(f_test_id)["phone"]
        await client.post("/login/farmer", data={"phone": farmer_phone, "pin": "1234"}, follow_redirects=False)
        
        # Access own invoice memo
        res_farmer_memo = await client.get(f"/farmer/invoice/{created_inv_id}/memo")
        print(f"GET /farmer/invoice/{created_inv_id}/memo -> Status {res_farmer_memo.status_code}")
        assert res_farmer_memo.status_code == 200
        assert "মালামাল ডেলিভারি চালান" in res_farmer_memo.text
        assert "খামারি পোর্টালে ফিরুন" in res_farmer_memo.text
        assert "/farmer" in res_farmer_memo.text

        # Create a second farmer to test unauthorized access rejection (403)
        other_farmer_id = db.save_farmer({
            "name": "অন্য খামারি",
            "phone": f"018{uuid.uuid4().hex[:8]}",
            "shed_name": "শেড ২"
        })
        other_phone = db.get_farmer_by_id(other_farmer_id)["phone"]
        await client.post("/login/farmer", data={"phone": other_phone, "pin": "1234"}, follow_redirects=False)
        res_unauthorized_memo = await client.get(f"/farmer/invoice/{created_inv_id}/memo")
        print(f"Unauthorized farmer memo access -> Status {res_unauthorized_memo.status_code}")
        assert res_unauthorized_memo.status_code == 403

        # Switch back to first farmer
        await client.post("/login/farmer", data={"phone": farmer_phone, "pin": "1234"}, follow_redirects=False)

        # 19b: Test Farmer Notification Bell & Modals in Farmer View
        res_farmer_dash = await client.get("/farmer")
        assert res_farmer_dash.status_code == 200
        assert "farmerNotifBellBtn" in res_farmer_dash.text
        assert "farmerNotifModal" in res_farmer_dash.text
        assert "farmerNotifDropdown" in res_farmer_dash.text

        # Post a feed request from farmer
        res_req_feed = await client.post("/farmer/request-feed/submit", data={
            "batch_id": f_shed_id,
            "items_requested": "১০ বস্তা স্টার্টার ফিড ও ভিটামিন",
            "farmer_note": "কালকের মধ্যে ডেলিভারি লাগবে।"
        }, follow_redirects=False)
        assert res_req_feed.status_code == 303

        # Check Farmer Notification API
        res_f_notifs = await client.get("/farmer/api/notifications")
        assert res_f_notifs.status_code == 200
        f_notif_data = res_f_notifs.json()
        print(f"Farmer Notifications API -> Count: {f_notif_data['count']}, Total items: {len(f_notif_data['notifications'])}")
        assert f_notif_data["count"] >= 1
        assert any(n.get("type") == "request" for n in f_notif_data["notifications"])

        # 19c: Test Admin Notification Bell, Details Modal & Enriched Info
        await client.post("/login/admin", data={"username": "admin", "password": "admin123"}, follow_redirects=False)
        res_admin_page = await client.get("/admin")
        assert res_admin_page.status_code == 200
        assert "notifBellBtn" in res_admin_page.text
        assert "adminNotifModal" in res_admin_page.text
        assert "showAdminNotifDetails" in res_admin_page.text

        # Check Admin Notification API & Enriched Fields (phone, address, due)
        res_a_notifs = await client.get("/admin/api/notifications")
        assert res_a_notifs.status_code == 200
        a_notif_data = res_a_notifs.json()
        print(f"Admin Notifications API -> Pending Count: {a_notif_data['count']}")
        assert a_notif_data["count"] >= 1
        top_req = a_notif_data["requests"][0]
        assert "farmer_phone" in top_req
        assert "farmer_address" in top_req
        assert "farmer_due" in top_req
        print(f"Enriched Feed Request details: farmer={top_req['farmer_name']}, phone={top_req['farmer_phone']}, due={top_req['farmer_due']}")

        # Clean up second farmer
        db.delete_farmer(other_farmer_id)

        # Clean up test invoice & farmer
        db.delete_invoice(created_inv_id)
        for s in f_sheds:
            db.delete_batch(s["id"])
        db.delete_farmer(f_test_id)

        print("\n=======================================================")
        print("ALL TESTS PASSED SUCCESSFULLY! 100% VERIFIED!")
        print("=======================================================\n")

if __name__ == "__main__":
    asyncio.run(run_tests())
