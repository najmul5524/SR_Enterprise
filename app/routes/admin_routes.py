import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Request, Form, UploadFile, File, Depends, HTTPException, Query, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.db import db
from app.auth import require_admin, get_current_user, is_mobile_app_client
from app.storage import upload_image_file, is_cloudinary_active
from app.qr_service import generate_qr_data_url, generate_product_label_image, generate_qr_image_bytes

router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])
templates = Jinja2Templates(directory=str(settings.BASE_DIR / "templates"))

# Context processor helper for base templates
def admin_context(request: Request, extra: dict = None) -> dict:
    unread_notifs = db.get_unread_notification_count(recipient_role="admin")
    admin_notifs = db.get_notifications(recipient_role="admin", limit=10)
    ctx = {
        "current_path": request.url.path,
        "user": get_current_user(request),
        "shop": db.get_settings(),
        "is_cloudinary": is_cloudinary_active(),
        "is_firebase": db.is_firebase_active(),
        "is_mobile_app": is_mobile_app_client(request),
        "now_date": datetime.now().strftime("%Y-%m-%d"),
        "pending_requests_count": unread_notifs,
        "pending_requests": admin_notifs,
    }
    if extra:
        ctx.update(extra)
    return ctx

def render_template(request: Request, name: str, extra: dict = None):
    return templates.TemplateResponse(request=request, name=name, context=admin_context(request, extra))

@router.get("/api/notifications")
async def get_admin_notifications_api():
    unread_count = db.get_unread_notification_count(recipient_role="admin")
    notifs = db.get_notifications(recipient_role="admin", limit=15)
    return {
        "count": unread_count,
        "notifications": notifs,
        "requests": notifs
    }

@router.post("/api/notifications/{notif_id}/read")
async def mark_admin_notif_read_api(notif_id: str):
    db.mark_notification_as_read(notif_id, recipient_role="admin")
    unread = db.get_unread_notification_count(recipient_role="admin")
    return {"status": "success", "count": unread}

@router.post("/api/notifications/mark-all-read")
async def mark_all_admin_notifs_read_api():
    db.mark_all_notifications_as_read(recipient_role="admin")
    return {"status": "success", "count": 0}

# ==================== DASHBOARD ====================
@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    stats = db.get_dashboard_stats()
    active_batches = db.get_batches(status="active")
    
    # Calculate days for each active batch
    today = datetime.now().date()
    for b in active_batches:
        try:
            start_d = datetime.strptime(b["start_date"], "%Y-%m-%d").date()
            b["age_days"] = max(0, (today - start_d).days)
        except Exception:
            b["age_days"] = 0

    recent_invoices = db.get_invoices(limit=15)
    low_stock_products = db.get_products(low_stock_only=True)
    recent_payments = db.get_payments(limit=5)
    feed_requests = db.get_feed_requests(status="pending")

    # Detailed data for KPI modals (Requirement 8)
    all_farmers = db.get_farmers()
    farmers_with_dues = []
    for f in all_farmers:
        f_sheds = db.get_batches(farmer_id=f["id"])
        f["sheds"] = f_sheds
        shed_names = [s["batch_no"] for s in f_sheds if s.get("status") == "active"]
        if not shed_names and f_sheds:
            shed_names = [s["batch_no"] for s in f_sheds]
        f["active_sheds_names"] = ", ".join(shed_names) if shed_names else (f.get("shed_name") or "শেড ১")
        if f.get("total_due", 0) > 0 or len(f_sheds) > 0:
            farmers_with_dues.append(f)
    farmers_with_dues.sort(key=lambda x: x.get("total_due", 0), reverse=True)

    today_str = datetime.now().strftime("%Y-%m-%d")
    all_today_invoices = db.get_invoices(limit=50)
    today_invoices = [inv for inv in all_today_invoices if str(inv.get("invoice_date", "")).startswith(today_str)]

    return render_template(request, "admin/dashboard.html", {
        "stats": stats,
        "active_batches": active_batches,
        "recent_invoices": recent_invoices,
        "low_stock_products": low_stock_products,
        "recent_payments": recent_payments,
        "pending_requests_count": len(feed_requests),
        "farmers_with_dues": farmers_with_dues,
        "today_invoices": today_invoices,
    })

# ==================== INVENTORY ====================
@router.get("/inventory", response_class=HTMLResponse)
async def inventory_page(request: Request, category: str = None, low_stock: bool = False):
    products = db.get_products(category=category, low_stock_only=low_stock)
    return render_template(request, "admin/inventory.html", {
        "products": products,
        "selected_category": category or "",
        "low_stock_filter": low_stock,
        "total_items": len(products),
    })

@router.post("/inventory/save")
async def save_product(
    request: Request,
    id: Optional[str] = Form(None),
    sku: Optional[str] = Form(None),
    name_bn: str = Form(...),
    name: Optional[str] = Form(""),
    category: str = Form(...),
    unit: str = Form(...),
    buy_price: float = Form(0),
    sell_price: float = Form(0),
    stock: float = Form(0),
    alert_qty: float = Form(10),
    description: Optional[str] = Form(""),
    image_file: Optional[UploadFile] = File(None)
):
    image_url = ""
    if image_file and image_file.filename:
        content = await image_file.read()
        if content:
            image_url = await upload_image_file(content, image_file.filename, subfolder="products")

    product_data = {
        "name_bn": name_bn.strip(),
        "name": (name or name_bn).strip(),
        "category": category,
        "unit": unit,
        "buy_price": buy_price,
        "sell_price": sell_price,
        "stock": stock,
        "alert_qty": alert_qty,
        "description": description or "",
    }
    if id:
        product_data["id"] = id
    if sku and sku.strip():
        product_data["sku"] = sku.strip()
    if image_url:
        product_data["image_url"] = image_url

    db.save_product(product_data)
    return RedirectResponse(url="/admin/inventory", status_code=303)

@router.post("/inventory/stock-adjust")
async def stock_adjust(product_id: str = Form(...), delta_qty: float = Form(...)):
    db.adjust_stock(product_id, delta_qty)
    return RedirectResponse(url="/admin/inventory", status_code=303)

@router.get("/inventory/delete/{product_id}")
async def delete_product(product_id: str):
    db.delete_product(product_id)
    return RedirectResponse(url="/admin/inventory", status_code=303)

@router.get("/inventory/qr-image/{product_id}")
async def product_qr_image(product_id: str):
    product = db.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    qr_data = product.get("sku") or product.get("qr_code") or product["id"]
    img_bytes = generate_qr_image_bytes(qr_data)
    return Response(content=img_bytes, media_type="image/png")

@router.get("/inventory/qr-label/{product_id}")
async def product_qr_label(product_id: str):
    product = db.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Encode QR code with product SKU number
    qr_data = product.get("sku") or product.get("qr_code") or product["id"]
    img_bytes = generate_product_label_image(
        product_name=product.get("name_bn") or product.get("name"),
        sku=product.get("sku", ""),
        price=product.get("sell_price", 0),
        qr_data=qr_data
    )
    return Response(content=img_bytes, media_type="image/png")

# ==================== QR SCANNER ====================
@router.get("/scanner", response_class=HTMLResponse)
async def qr_scanner_page(request: Request):
    return render_template(request, "admin/qr_scanner.html")

# ==================== FARMERS ====================
@router.get("/farmers", response_class=HTMLResponse)
async def farmers_page(request: Request, q: Optional[str] = None):
    farmers = db.get_farmers(search=q)
    # Check active batches for each farmer
    for f in farmers:
        active = db.get_batches(status="active", farmer_id=f["id"])
        f["active_batch"] = active[0] if active else None

    return render_template(request, "admin/farmers.html", {
        "farmers": farmers,
        "search_query": q or "",
    })

@router.post("/farmers/save")
async def save_farmer(
    request: Request,
    id: Optional[str] = Form(None),
    name: str = Form(...),
    phone: str = Form(...),
    pin: Optional[str] = Form("1234"),
    shed_name: Optional[str] = Form(""),
    address: Optional[str] = Form(""),
    shed_capacity: int = Form(1000),
    notes: Optional[str] = Form(""),
    image_file: Optional[UploadFile] = File(None)
):
    image_url = ""
    if image_file and image_file.filename:
        content = await image_file.read()
        if content:
            image_url = await upload_image_file(content, image_file.filename, subfolder="farmers")

    data = {
        "name": name.strip(),
        "phone": phone.strip(),
        "pin": pin.strip() if pin else "1234",
        "shed_name": (shed_name or f"{name}-এর শেড").strip(),
        "address": address or "",
        "shed_capacity": shed_capacity,
        "notes": notes or "",
    }
    if id:
        data["id"] = id
    if image_url:
        data["image_url"] = image_url

    farmer_id = db.save_farmer(data)
    return RedirectResponse(url=f"/admin/farmer/{farmer_id}", status_code=303)

@router.post("/farmer/update")
async def update_farmer_handler(
    request: Request,
    farmer_id: str = Form(...),
    name: str = Form(...),
    phone: str = Form(...),
    pin: Optional[str] = Form("1234"),
    shed_name: Optional[str] = Form(""),
    address: Optional[str] = Form(""),
    shed_capacity: int = Form(1000),
    status: Optional[str] = Form("active"),
    notes: Optional[str] = Form(""),
    image_file: Optional[UploadFile] = File(None)
):
    existing = db.get_farmer_by_id(farmer_id)
    if not existing:
        raise HTTPException(status_code=404, detail="খামারি খুঁজে পাওয়া যায়নি")

    image_url = ""
    if image_file and image_file.filename:
        content = await image_file.read()
        if content:
            image_url = await upload_image_file(content, image_file.filename, subfolder="farmers")

    data = {
        "id": farmer_id,
        "name": name.strip(),
        "phone": phone.strip(),
        "pin": pin.strip() if pin else existing.get("pin", "1234"),
        "shed_name": (shed_name or existing.get("shed_name") or f"{name}-এর শেড").strip(),
        "address": address.strip() if address else existing.get("address", ""),
        "shed_capacity": shed_capacity,
        "status": status.strip() if status else "active",
        "notes": notes.strip() if notes else "",
    }
    if image_url:
        data["image_url"] = image_url

    db.save_farmer(data)
    return RedirectResponse(url=f"/admin/farmer/{farmer_id}", status_code=303)

@router.get("/farmer/delete/{farmer_id}")
@router.post("/farmer/delete/{farmer_id}")
async def delete_farmer_handler(request: Request, farmer_id: str):
    farmer = db.get_farmer_by_id(farmer_id)
    if not farmer:
        raise HTTPException(status_code=404, detail="খামারি খুঁজে পাওয়া যায়নি")
    
    db.delete_farmer(farmer_id)
    return RedirectResponse(url="/admin/farmers?deleted=1", status_code=303)

@router.get("/farmer/{farmer_id}", response_class=HTMLResponse)
async def farmer_detail(request: Request, farmer_id: str):
    farmer = db.get_farmer_by_id(farmer_id)
    if not farmer:
        raise HTTPException(status_code=404, detail="খামারি খুঁজে পাওয়া যায়নি")

    batches = db.get_batches(farmer_id=farmer_id)
    active_batch = None
    for b in batches:
        if b["status"] == "active":
            active_batch = b
            try:
                start_d = datetime.strptime(b["start_date"], "%Y-%m-%d").date()
                b["age_days"] = max(0, (datetime.now().date() - start_d).days)
            except Exception:
                b["age_days"] = 0
            break

    invoices = db.get_invoices(farmer_id=farmer_id, limit=30)
    payments = db.get_payments(farmer_id=farmer_id, limit=30)
    farmer_qr_url = generate_qr_data_url(f"SRE:FRM:{farmer['id']}")

    return render_template(request, "admin/farmer_detail.html", {
        "farmer": farmer,
        "active_batch": active_batch,
        "batches": batches,
        "invoices": invoices,
        "payments": payments,
        "farmer_qr_url": farmer_qr_url,
    })

# ==================== BATCHES (SHED LIFE-CYCLE) ====================
@router.get("/batches", response_class=HTMLResponse)
async def batches_page(request: Request, status: Optional[str] = None):
    batches = db.get_batches(status=status)
    today = datetime.now().date()
    for b in batches:
        try:
            start_d = datetime.strptime(b["start_date"], "%Y-%m-%d").date()
            b["age_days"] = max(0, (today - start_d).days)
        except Exception:
            b["age_days"] = 0

    farmers = db.get_farmers()
    return render_template(request, "admin/batches.html", {
        "batches": batches,
        "status_filter": status or "all",
        "farmers": farmers,
    })

@router.post("/batch/new")
async def create_new_batch(
    farmer_id: str = Form(...),
    batch_no: str = Form(...),
    bird_type: str = Form(...),
    chick_qty: int = Form(...),
    chick_unit_cost: float = Form(...),
    start_date: str = Form(...),
    notes: Optional[str] = Form("")
):
    farmer = db.get_farmer_by_id(farmer_id)
    if not farmer:
        raise HTTPException(status_code=400, detail="Invalid farmer")

    batch_data = {
        "batch_no": batch_no.strip(),
        "farmer_id": farmer["id"],
        "farmer_name": farmer["name"],
        "bird_type": bird_type,
        "chick_qty": chick_qty,
        "chick_unit_cost": chick_unit_cost,
        "start_date": start_date or datetime.now().strftime("%Y-%m-%d"),
        "notes": notes or ""
    }
    batch_id = db.save_batch(batch_data)
    return RedirectResponse(url=f"/admin/batch/{batch_id}", status_code=303)

@router.post("/batch/update")
async def update_batch_route(
    request: Request,
    batch_id: str = Form(...),
    batch_no: str = Form(...),
    bird_type: str = Form("ব্রয়লার"),
    chick_qty: int = Form(1000),
    chick_unit_cost: float = Form(50.0),
    start_date: str = Form(...),
    status: str = Form("active"),
    notes: Optional[str] = Form("")
):
    db.update_batch(batch_id, {
        "batch_no": batch_no.strip(),
        "bird_type": bird_type.strip(),
        "chick_qty": chick_qty,
        "chick_unit_cost": chick_unit_cost,
        "start_date": start_date.strip(),
        "status": status.strip(),
        "notes": notes.strip() if notes else ""
    })
    return RedirectResponse(url=f"/admin/batch/{batch_id}", status_code=303)

@router.get("/batch/delete/{batch_id}")
@router.post("/batch/delete/{batch_id}")
async def delete_batch_route(request: Request, batch_id: str):
    db.delete_batch(batch_id)
    return RedirectResponse(url="/admin/batches?deleted=1", status_code=303)

@router.get("/batch/{batch_id}", response_class=HTMLResponse)
async def batch_detail(request: Request, batch_id: str):
    batch = db.get_batch_by_id(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="ব্যাচ খুঁজে পাওয়া যায়নি")

    farmer = db.get_farmer_by_id(batch["farmer_id"])
    logs = db.get_batch_logs(batch_id)
    
    # Calculate age
    try:
        start_d = datetime.strptime(batch["start_date"], "%Y-%m-%d").date()
        batch["age_days"] = max(0, (datetime.now().date() - start_d).days)
    except Exception:
        batch["age_days"] = 0

    products = db.get_products()
    batch_qr_url = generate_qr_data_url(f"SRE:BAT:{batch['id']}")
    batch_payments = db.get_payments(batch_id=batch_id)

    return render_template(request, "admin/batch_detail.html", {
        "batch": batch,
        "farmer": farmer,
        "logs": logs,
        "products": products,
        "batch_qr_url": batch_qr_url,
        "batch_payments": batch_payments,
    })

@router.post("/batch/{batch_id}/add-log")
async def add_batch_log(
    batch_id: str,
    log_type: str = Form(...),
    log_date: str = Form(...),
    item_id: Optional[str] = Form(None),
    item_name: str = Form(...),
    qty: float = Form(0),
    unit: Optional[str] = Form(""),
    unit_price: float = Form(0),
    note: Optional[str] = Form("")
):
    batch = db.get_batch_by_id(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    log_data = {
        "batch_id": batch_id,
        "farmer_id": batch["farmer_id"],
        "log_type": log_type,
        "log_date": log_date or datetime.now().strftime("%Y-%m-%d"),
        "item_id": item_id or "",
        "item_name": item_name.strip(),
        "qty": qty,
        "unit": unit or "",
        "unit_price": unit_price,
        "total_amount": qty * unit_price if log_type != "mortality" else 0,
        "note": note or "",
    }
    db.add_batch_log(log_data)
    return RedirectResponse(url=f"/admin/batch/{batch_id}", status_code=303)

@router.post("/batch/{batch_id}/settle")
async def settle_batch(
    batch_id: str,
    harvest_date: str = Form(...),
    birds_sold: int = Form(...),
    total_weight_kg: float = Form(...),
    rate_per_kg: float = Form(...)
):
    settlement = {
        "harvest_date": harvest_date,
        "birds_sold": birds_sold,
        "total_weight_kg": total_weight_kg,
        "rate_per_kg": rate_per_kg,
    }
    db.close_and_settle_batch(batch_id, settlement)
    return RedirectResponse(url=f"/admin/batch/{batch_id}?settled=true", status_code=303)

# ==================== DISPATCH / BILLING (POS) ====================
@router.get("/dispatch", response_class=HTMLResponse)
async def dispatch_page(
    request: Request,
    farmer_id: Optional[str] = None,
    batch_id: Optional[str] = None,
    add_item: Optional[str] = None,
    feed_request_id: Optional[str] = None
):
    farmers = db.get_farmers()
    products = db.get_products()
    
    feed_req = db.get_feed_request_by_id(feed_request_id) if feed_request_id else None
    if feed_req:
        if not farmer_id:
            farmer_id = feed_req.get("farmer_id")
        if not batch_id:
            batch_id = feed_req.get("batch_id")

    selected_farmer = db.get_farmer_by_id(farmer_id) if farmer_id else None
    farmer_batches = []
    active_batch = None
    if selected_farmer:
        all_batches = db.get_batches(farmer_id=selected_farmer["id"])
        farmer_batches = all_batches
        if batch_id:
            for b in all_batches:
                if b["id"] == batch_id:
                    active_batch = b
                    break
        if not active_batch:
            active_batches = [b for b in all_batches if b.get("status") == "active"]
            active_batch = active_batches[0] if active_batches else (all_batches[0] if all_batches else None)

    initial_product = db.get_product_by_id(add_item) if add_item else None

    return render_template(request, "admin/dispatch.html", {
        "farmers": farmers,
        "products": products,
        "selected_farmer": selected_farmer,
        "farmer_batches": farmer_batches,
        "active_batch": active_batch,
        "initial_product": initial_product,
        "feed_request_id": feed_request_id,
        "feed_request": feed_req,
    })

@router.post("/dispatch/create")
async def create_dispatch(
    request: Request,
    customer_type: str = Form("farmer"),
    farmer_id: Optional[str] = Form(None),
    customer_name: Optional[str] = Form(""),
    customer_phone: Optional[str] = Form(""),
    batch_id: Optional[str] = Form(None),
    invoice_date: str = Form(...),
    items_json: str = Form(...),
    subtotal: float = Form(0),
    discount: float = Form(0),
    paid_amount: float = Form(0),
    payment_type: str = Form("credit"),
    note: Optional[str] = Form(""),
    feed_request_id: Optional[str] = Form(None),
    receipt_file: Optional[UploadFile] = File(None)
):
    if customer_type == "retail" or not farmer_id or farmer_id in ("WALK_IN", "RETAIL"):
        final_farmer_id = "WALK_IN"
        c_name = (customer_name or "").strip() or "সাধারণ ক্রেতা (খুচরা)"
        c_phone = (customer_phone or "").strip()
        if c_phone:
            final_farmer_name = f"{c_name} ({c_phone})"
        else:
            final_farmer_name = c_name
        final_batch_id = ""
    else:
        farmer = db.get_farmer_by_id(farmer_id)
        if not farmer:
            raise HTTPException(status_code=400, detail="Invalid farmer")
        final_farmer_id = farmer["id"]
        final_farmer_name = farmer["name"]
        final_batch_id = batch_id or ""

    items = []
    try:
        items = json.loads(items_json)
    except Exception:
        items = []

    receipt_url = ""
    if receipt_file and receipt_file.filename:
        content = await receipt_file.read()
        if content:
            receipt_url = await upload_image_file(content, receipt_file.filename, subfolder="invoices")

    net_total = max(0.0, subtotal - discount)
    if payment_type == "cash":
        paid_amount = net_total
        due_amount = 0.0
    elif payment_type == "credit":
        paid_amount = 0.0
        due_amount = net_total
    else:
        paid_amount = min(net_total, max(0.0, paid_amount))
        due_amount = max(0.0, net_total - paid_amount)

    invoice_data = {
        "farmer_id": final_farmer_id,
        "farmer_name": final_farmer_name,
        "batch_id": final_batch_id,
        "items": items,
        "subtotal": subtotal,
        "discount": discount,
        "net_total": net_total,
        "paid_amount": paid_amount,
        "due_amount": due_amount,
        "payment_type": payment_type,
        "invoice_date": invoice_date,
        "note": note or "",
        "receipt_image_url": receipt_url
    }
    inv_id = db.create_invoice(invoice_data)

    # Requirement 3: Automatically mark feed request as approved upon creating dispatch
    if feed_request_id:
        db.update_feed_request_status(feed_request_id, "approved")
    elif final_farmer_id not in ("WALK_IN", "RETAIL", "COUNTER_SALE", "GENERAL_CUSTOMER", ""):
        pending_reqs = db.get_feed_requests(farmer_id=final_farmer_id, status="pending")
        for pr in pending_reqs:
            if not final_batch_id or pr.get("batch_id") == final_batch_id:
                db.update_feed_request_status(pr["id"], "approved")
                break

    return RedirectResponse(url=f"/admin/invoice/{inv_id}/print", status_code=303)

@router.get("/invoice/{invoice_id}/print", response_class=HTMLResponse)
async def print_invoice(request: Request, invoice_id: str):
    invoice = db.get_invoice_by_id(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="চালান খুঁজে পাওয়া যায়নি")

    farmer = db.get_farmer_by_id(invoice["farmer_id"]) if (invoice.get("farmer_id") and invoice["farmer_id"] != "WALK_IN") else None
    batch = db.get_batch_by_id(invoice["batch_id"]) if invoice.get("batch_id") else None
    qr_url = generate_qr_data_url(f"SRE:INV:{invoice['invoice_no']}")

    return render_template(request, "admin/print_memo.html", {
        "invoice": invoice,
        "farmer": farmer,
        "batch": batch,
        "qr_url": qr_url,
    })

@router.get("/invoices", response_class=HTMLResponse)
async def invoices_list_page(request: Request, q: Optional[str] = None):
    invoices = db.get_invoices(limit=100)
    if q:
        q_clean = q.strip().lower()
        invoices = [inv for inv in invoices if q_clean in inv.get("invoice_no", "").lower() or q_clean in inv.get("farmer_name", "").lower()]
    return render_template(request, "admin/invoices.html", {
        "invoices": invoices,
        "search_query": q or ""
    })

@router.post("/invoice/update")
async def update_invoice_route(
    invoice_id: str = Form(...),
    invoice_date: str = Form(...),
    payment_type: str = Form("credit"),
    discount: float = Form(0),
    paid_amount: float = Form(0),
    note: Optional[str] = Form(""),
    redirect_to: Optional[str] = Form(None),
    items_json: Optional[str] = Form(None),
    receipt_file: Optional[UploadFile] = File(None)
):
    inv = db.get_invoice_by_id(invoice_id)
    if inv:
        subtotal = float(inv.get("subtotal", 0))
        update_data = {
            "invoice_date": invoice_date,
            "payment_type": payment_type,
            "subtotal": subtotal,
            "discount": discount,
            "net_total": subtotal - discount,
            "paid_amount": paid_amount,
            "note": note or ""
        }
        # Edited line items -> full stock / shed / farmer-due re-reconcile
        if items_json:
            try:
                parsed = json.loads(items_json)
                if isinstance(parsed, list) and parsed:
                    clean = []
                    for it in parsed:
                        qty = float(it.get("qty", 0) or 0)
                        price = float(it.get("price", 0) or 0)
                        if qty <= 0:
                            continue
                        it["qty"] = qty
                        it["price"] = price
                        it["total"] = qty * price
                        clean.append(it)
                    if clean:
                        update_data["items"] = clean
            except Exception:
                pass
        if receipt_file and receipt_file.filename:
            content = await receipt_file.read()
            if content:
                uploaded_url = await upload_image_file(content, receipt_file.filename, subfolder="invoices")
                if uploaded_url:
                    update_data["receipt_image_url"] = uploaded_url
        db.update_invoice(invoice_id, update_data)
    return RedirectResponse(url=redirect_to or "/admin/invoices", status_code=303)

@router.get("/invoice/delete/{invoice_id}")
async def delete_invoice_route(invoice_id: str, redirect_to: Optional[str] = None):
    db.delete_invoice(invoice_id)
    return RedirectResponse(url=redirect_to or "/admin/invoices", status_code=303)

@router.post("/batch/log/update")
async def update_batch_log_route(
    log_id: str = Form(...),
    batch_id: str = Form(...),
    log_date: str = Form(...),
    log_type: str = Form(...),
    item_name: str = Form(...),
    qty: float = Form(0),
    unit: str = Form(""),
    unit_price: float = Form(0),
    note: Optional[str] = Form("")
):
    db.update_batch_log(log_id, {
        "log_date": log_date,
        "log_type": log_type,
        "item_name": item_name,
        "qty": qty,
        "unit": unit,
        "unit_price": unit_price,
        "note": note or ""
    })
    return RedirectResponse(url=f"/admin/batch/{batch_id}", status_code=303)

@router.get("/batch/log/delete/{log_id}")
async def delete_batch_log_route(log_id: str, batch_id: str):
    db.delete_batch_log(log_id)
    return RedirectResponse(url=f"/admin/batch/{batch_id}", status_code=303)

# ==================== PAYMENTS ====================
@router.get("/payments", response_class=HTMLResponse)
async def payments_page(request: Request, farmer_id: Optional[str] = None):
    farmers = db.get_farmers()
    payments = db.get_payments(farmer_id=farmer_id, limit=100)
    selected_farmer = db.get_farmer_by_id(farmer_id) if farmer_id else None
    all_batches = db.get_batches()

    return render_template(request, "admin/payments.html", {
        "farmers": farmers,
        "payments": payments,
        "selected_farmer": selected_farmer,
        "batches": all_batches,
    })

@router.post("/payments/record")
async def record_payment(
    farmer_id: str = Form(...),
    amount: float = Form(...),
    payment_method: str = Form("cash"),
    transaction_ref: Optional[str] = Form(""),
    payment_date: str = Form(...),
    batch_id: Optional[str] = Form(None),
    note: Optional[str] = Form(""),
    redirect_to: Optional[str] = Form(None),
    voucher_file: Optional[UploadFile] = File(None)
):
    farmer = db.get_farmer_by_id(farmer_id)
    if not farmer:
        raise HTTPException(status_code=400, detail="Invalid farmer")

    clean_batch_id = (batch_id or "").strip()
    if clean_batch_id:
        b_check = db.get_batch_by_id(clean_batch_id)
        if not b_check:
            clean_batch_id = ""

    voucher_url = ""
    if voucher_file and voucher_file.filename:
        content = await voucher_file.read()
        if content:
            voucher_url = await upload_image_file(content, voucher_file.filename, subfolder="payments")

    payment_data = {
        "farmer_id": farmer["id"],
        "farmer_name": farmer["name"],
        "batch_id": clean_batch_id,
        "amount": amount,
        "payment_method": payment_method,
        "transaction_ref": transaction_ref or "",
        "voucher_image_url": voucher_url,
        "payment_date": payment_date,
        "note": note or "",
    }
    db.record_payment(payment_data)

    if redirect_to:
        return RedirectResponse(url=redirect_to, status_code=303)
    if clean_batch_id:
        return RedirectResponse(url=f"/admin/batch/{clean_batch_id}", status_code=303)
    return RedirectResponse(url=f"/admin/farmer/{farmer['id']}", status_code=303)

@router.post("/payments/update")
async def update_payment_route(
    payment_id: str = Form(...),
    amount: float = Form(...),
    payment_method: str = Form("cash"),
    transaction_ref: Optional[str] = Form(""),
    payment_date: str = Form(...),
    batch_id: Optional[str] = Form(None),
    note: Optional[str] = Form(""),
    redirect_to: Optional[str] = Form(None)
):
    clean_batch_id = (batch_id or "").strip()
    db.update_payment(payment_id, {
        "batch_id": clean_batch_id,
        "amount": amount,
        "payment_method": payment_method,
        "transaction_ref": transaction_ref or "",
        "payment_date": payment_date,
        "note": note or ""
    })
    return RedirectResponse(url=redirect_to or "/admin/payments", status_code=303)

@router.get("/payments/delete/{payment_id}")
async def delete_payment_route(payment_id: str, redirect_to: Optional[str] = None):
    db.delete_payment(payment_id)
    return RedirectResponse(url=redirect_to or "/admin/payments", status_code=303)

# ==================== FEED REQUESTS ====================
@router.get("/feed-requests", response_class=HTMLResponse)
async def feed_requests_page(request: Request):
    requests_list = db.get_feed_requests()
    return render_template(request, "admin/feed_requests.html", {
        "feed_requests": requests_list
    })

@router.post("/feed-requests/{req_id}/status")
async def update_request_status(req_id: str, status: str = Form(...)):
    db.update_feed_request_status(req_id, status)
    return RedirectResponse(url="/admin/feed-requests", status_code=303)

# ==================== SETTINGS & INTEGRATIONS ====================
@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, msg: Optional[str] = None, pwd_msg: Optional[str] = None, pwd_error: Optional[str] = None):
    return render_template(request, "admin/settings.html", {
        "msg": msg,
        "pwd_msg": pwd_msg,
        "pwd_error": pwd_error
    })

@router.post("/settings/save")
async def save_settings(
    shop_name: str = Form(...),
    owner_name: str = Form(...),
    phone: str = Form(...),
    alt_phone: Optional[str] = Form(""),
    address: str = Form(...),
    bkash_merchant: Optional[str] = Form(""),
    nagad_personal: Optional[str] = Form(""),
    bank_info: Optional[str] = Form("")
):
    settings_dict = {
        "shop_name": shop_name.strip(),
        "owner_name": owner_name.strip(),
        "phone": phone.strip(),
        "alt_phone": alt_phone.strip() if alt_phone else "",
        "address": address.strip(),
        "bkash_merchant": bkash_merchant.strip() if bkash_merchant else "",
        "nagad_personal": nagad_personal.strip() if nagad_personal else "",
        "bank_info": bank_info.strip() if bank_info else ""
    }
    db.update_settings(settings_dict)
    return RedirectResponse(url="/admin/settings?msg=তথ্য+সফলভাবে+সংরক্ষণ+হয়েছে", status_code=303)

@router.post("/settings/change-password")
async def change_admin_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    shop_settings = db.get_settings()
    active_password = shop_settings.get("admin_password") or settings.ADMIN_PASSWORD

    if current_password.strip() != active_password:
        return RedirectResponse(url="/admin/settings?pwd_error=বর্তমান+পাসওয়ার্ডটি+সঠিক+নয়!", status_code=303)

    if new_password != confirm_password:
        return RedirectResponse(url="/admin/settings?pwd_error=নতুন+পাসওয়ার্ড+এবং+নিশ্চিতকরণ+পাসওয়ার্ড+মেলেনি!", status_code=303)

    if len(new_password.strip()) < 4:
        return RedirectResponse(url="/admin/settings?pwd_error=নতুন+পাসওয়ার্ড+কমপক্ষে+৪+অক্ষরের+হতে+হবে!", status_code=303)

    db.update_settings({"admin_password": new_password.strip()})

    try:
        env_path = settings.BASE_DIR / ".env"
        if env_path.exists():
            content = env_path.read_text(encoding="utf-8")
            if "ADMIN_PASSWORD=" in content:
                import re
                new_content = re.sub(r'ADMIN_PASSWORD=.*', f'ADMIN_PASSWORD={new_password.strip()}', content)
                env_path.write_text(new_content, encoding="utf-8")
            else:
                env_path.write_text(content.strip() + f"\nADMIN_PASSWORD={new_password.strip()}\n", encoding="utf-8")
    except Exception as e:
        print(f"[SETTINGS] Could not write .env: {e}")

    return RedirectResponse(url="/admin/settings?pwd_msg=অ্যাডমিন+পাসওয়ার্ড+সফলভাবে+পরিবর্তন+করা+হয়েছে!", status_code=303)

@router.post("/settings/firebase-backup")
async def trigger_firebase_backup():
    if not db.is_firebase_active():
        return RedirectResponse(url="/admin/settings?pwd_error=Firebase+সংযুক্ত+নেই!+Render-এ+FIREBASE_CREDENTIALS_BASE64+অথবা+FIREBASE_CREDENTIALS+সেট+করুন।", status_code=303)
    res = db.backup_all_to_firebase()
    if res.get("status") == "success":
        return RedirectResponse(url="/admin/settings?msg=Firebase+ক্লাউডে+সমস্ত+ডাটা+সফলভাবে+ম্যানুয়ালি+ব্যাকআপ+করা+হয়েছে!", status_code=303)
    else:
        err = res.get("message", "ক্লাউড ব্যাকআপে সমস্যা হয়েছে")
        return RedirectResponse(url=f"/admin/settings?pwd_error=ব্যাকআপ+ব্যর্থ:+{err}", status_code=303)

@router.post("/settings/firebase-restore")
async def trigger_firebase_restore():
    if not db.is_firebase_active():
        return RedirectResponse(url="/admin/settings?pwd_error=Firebase+সংযুক্ত+নেই!+Render-এ+FIREBASE_CREDENTIALS_BASE64+অথবা+FIREBASE_CREDENTIALS+সেট+করুন।", status_code=303)
    res = db.restore_all_from_firebase()
    if res.get("status") == "success":
        return RedirectResponse(url="/admin/settings?msg=Firebase+ক্লাউড+থেকে+সমস্ত+ডাটা+সফলভাবে+রিস্টোর+করা+হয়েছে!", status_code=303)
    else:
        err = res.get("message", "ক্লাউড রিস্টোরে সমস্যা হয়েছে")
        return RedirectResponse(url=f"/admin/settings?pwd_error=রিস্টোর+ব্যর্থ:+{err}", status_code=303)


# ==================== EXPENSES (বিবিধ ও অন্যান্য খরচ) ====================
@router.get("/expenses", response_class=HTMLResponse)
async def expenses_page(
    request: Request,
    category: Optional[str] = None,
    q: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    expenses = db.get_expenses(start_date=start_date, end_date=end_date, category=category, search=q)
    summary = db.get_expenses_summary()
    return render_template(request, "admin/expenses.html", {
        "expenses": expenses,
        "summary": summary,
        "selected_category": category or "all",
        "search_query": q or "",
        "start_date": start_date or "",
        "end_date": end_date or "",
    })

@router.post("/expenses/save")
async def save_expense_handler(
    request: Request,
    id: Optional[str] = Form(None),
    category: str = Form(...),
    amount: float = Form(...),
    expense_date: Optional[str] = Form(None),
    payment_method: str = Form("cash"),
    note: Optional[str] = Form("")
):
    data = {
        "category": category.strip(),
        "amount": max(0.0, float(amount)),
        "expense_date": expense_date or datetime.now().strftime("%Y-%m-%d"),
        "payment_method": payment_method,
        "note": (note or "").strip(),
    }
    if id:
        data["id"] = id
    db.save_expense(data)
    return RedirectResponse(url="/admin/expenses?saved=1", status_code=303)

@router.get("/expenses/delete/{expense_id}")
@router.post("/expenses/delete/{expense_id}")
async def delete_expense_handler(request: Request, expense_id: str):
    db.delete_expense(expense_id)
    return RedirectResponse(url="/admin/expenses?deleted=1", status_code=303)
