from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.db import db
from app.auth import require_farmer, get_current_user, is_mobile_app_client
from app.qr_service import generate_qr_data_url

router = APIRouter(prefix="/farmer", dependencies=[Depends(require_farmer)])
templates = Jinja2Templates(directory=str(settings.BASE_DIR / "templates"))

def farmer_context(request: Request, extra: dict = None) -> dict:
    user = get_current_user(request)
    fid = user.get("farmer_id") if user else None
    farmer = db.get_farmer_by_id(fid) if fid else None
    
    unread_count = db.get_unread_notification_count(recipient_role="farmer", recipient_id=fid) if fid else 0
    farmer_notifs = db.get_notifications(recipient_role="farmer", recipient_id=fid, limit=10) if fid else []
    
    ctx = {
        "current_path": request.url.path,
        "user": user,
        "farmer": farmer,
        "shop": db.get_settings(),
        "is_mobile_app": is_mobile_app_client(request),
        "farmer_requests": farmer_notifs,
        "farmer_notif_count": unread_count,
    }
    if extra:
        ctx.update(extra)
    return ctx

def render_farmer_template(request: Request, name: str, extra: dict = None):
    return templates.TemplateResponse(request=request, name=name, context=farmer_context(request, extra))

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def farmer_dashboard(request: Request, batch_id: Optional[str] = None):
    user = get_current_user(request)
    farmer = db.get_farmer_by_id(user["farmer_id"])
    if not farmer:
        return RedirectResponse(url="/logout", status_code=303)

    batches = db.get_batches(farmer_id=farmer["id"])
    for b in batches:
        try:
            start_d = datetime.strptime(b["start_date"], "%Y-%m-%d").date()
            b["age_days"] = max(0, (datetime.now().date() - start_d).days)
        except Exception:
            b["age_days"] = 0

    active_batches = [b for b in batches if b.get("status") == "active"]
    
    selected_batch = None
    if batch_id:
        for b in batches:
            if b["id"] == batch_id:
                selected_batch = b
                break
    if not selected_batch:
        selected_batch = active_batches[0] if active_batches else (batches[0] if batches else None)

    recent_logs = []
    if selected_batch:
        recent_logs = db.get_batch_logs(selected_batch["id"])[-8:]

    recent_invoices = db.get_invoices(farmer_id=farmer["id"], limit=5)
    farmer_qr = generate_qr_data_url(f"SRE:FRM:{farmer['id']}")

    return render_farmer_template(request, "farmer/dashboard.html", {
        "farmer": farmer,
        "batches": batches,
        "active_batches": active_batches,
        "active_batch": selected_batch,
        "selected_batch": selected_batch,
        "recent_logs": recent_logs,
        "recent_invoices": recent_invoices,
        "farmer_qr": farmer_qr,
    })

@router.get("/ledger", response_class=HTMLResponse)
async def farmer_ledger(request: Request):
    user = get_current_user(request)
    farmer = db.get_farmer_by_id(user["farmer_id"])
    invoices = db.get_invoices(farmer_id=farmer["id"], limit=100)
    payments = db.get_payments(farmer_id=farmer["id"], limit=100)

    # Combine into unified chronological ledger statement
    ledger_entries = []
    for inv in invoices:
        ledger_entries.append({
            "date": inv["invoice_date"],
            "type": "debit", # Maalamal / Expense
            "title": f"চালান #{inv['invoice_no']}",
            "invoice_no": inv["invoice_no"],
            "details": f"{len(inv.get('items', []))} টি পণ্য মালামাল",
            "amount": inv["net_total"],
            "ref_id": inv["id"],
            "receipt_image_url": inv.get("receipt_image_url"),
            "items": inv.get("items", []),
            "note": inv.get("note")
        })
    for p in payments:
        shed_info = f" • শেড: {p.get('batch_no')}" if p.get("batch_no") else ""
        ledger_entries.append({
            "date": p["payment_date"],
            "type": "credit", # Payment / Jama
            "title": f"জমা পরিশোধ ({p.get('payment_method','ক্যাশ')})",
            "details": f"রশিদ #{p['receipt_no']}{shed_info} - {p.get('note', '')}",
            "amount": p["amount"],
            "ref_id": p["id"],
            "voucher": p.get("voucher_image_url")
        })

    # Sort chronological descending
    ledger_entries.sort(key=lambda x: x["date"], reverse=True)

    return render_farmer_template(request, "farmer/ledger.html", {
        "farmer": farmer,
        "ledger_entries": ledger_entries,
        "invoices": invoices,
        "payments": payments,
    })

@router.get("/request-feed", response_class=HTMLResponse)
async def request_feed_page(request: Request, batch_id: Optional[str] = None, success: Optional[str] = None):
    user = get_current_user(request)
    farmer = db.get_farmer_by_id(user["farmer_id"])
    batches = db.get_batches(farmer_id=farmer["id"])
    for b in batches:
        try:
            start_d = datetime.strptime(b["start_date"], "%Y-%m-%d").date()
            b["age_days"] = max(0, (datetime.now().date() - start_d).days)
        except Exception:
            b["age_days"] = 0

    active_batches = [b for b in batches if b.get("status") == "active"]
    selected_batch_id = batch_id or (active_batches[0]["id"] if active_batches else (batches[0]["id"] if batches else ""))
    products = db.get_products()
    my_requests = db.get_feed_requests(farmer_id=farmer["id"])

    return render_farmer_template(request, "farmer/request_feed.html", {
        "farmer": farmer,
        "batches": batches,
        "active_batches": active_batches,
        "selected_batch_id": selected_batch_id,
        "active_batch": active_batches[0] if active_batches else None,
        "products": products,
        "my_requests": my_requests,
        "success": success
    })

@router.post("/request-feed/submit")
async def submit_feed_request(
    request: Request,
    items_requested: str = Form(...),
    farmer_note: Optional[str] = Form(""),
    batch_id: Optional[str] = Form(None)
):
    user = get_current_user(request)
    farmer = db.get_farmer_by_id(user["farmer_id"])
    
    req_data = {
        "farmer_id": farmer["id"],
        "farmer_name": farmer["name"],
        "batch_id": batch_id or "",
        "items_requested": items_requested.strip(),
        "farmer_note": farmer_note or "",
    }
    db.create_feed_request(req_data)
    return RedirectResponse(url="/farmer/request-feed?success=১", status_code=303)

@router.get("/invoice/{invoice_id}/memo", response_class=HTMLResponse)
async def farmer_view_invoice_memo(request: Request, invoice_id: str):
    user = get_current_user(request)
    invoice = db.get_invoice_by_id(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="চালান খুঁজে পাওয়া যায়নি")

    if str(invoice.get("farmer_id")) != str(user.get("farmer_id")):
        raise HTTPException(status_code=403, detail="এই চালানটি দেখার অনুমতি আপনার অ্যাকাউন্টে নেই")

    farmer = db.get_farmer_by_id(invoice["farmer_id"])
    batch = db.get_batch_by_id(invoice["batch_id"]) if invoice.get("batch_id") else None
    qr_url = generate_qr_data_url(f"SRE:INV:{invoice['invoice_no']}")

    return render_farmer_template(request, "admin/print_memo.html", {
        "invoice": invoice,
        "farmer": farmer,
        "batch": batch,
        "qr_url": qr_url,
        "is_farmer": True,
        "back_url": "/farmer"
    })

@router.get("/api/notifications")
async def farmer_notifications_api(request: Request):
    user = get_current_user(request)
    if not user or not user.get("farmer_id"):
        return {"count": 0, "notifications": []}

    fid = user["farmer_id"]
    unread_count = db.get_unread_notification_count(recipient_role="farmer", recipient_id=fid)
    notifs = db.get_notifications(recipient_role="farmer", recipient_id=fid, limit=15)
    
    formatted = []
    for n in notifs:
        st_text = "অনুমোদিত হয়েছে" if n.get("req_status") == "approved" else ("বাতিল" if n.get("req_status") == "rejected" else ("ডিলারের অপেক্ষমান" if n.get("req_status") == "pending" else "ডেলিভারি সম্পন্ন"))
        notif_type = "request" if n.get("type") in ("feed_request", "request") else n.get("type", "general")
        formatted.append({
            "id": n["id"],
            "type": notif_type,
            "title": n["title"],
            "details": n.get("items_requested") or n.get("message") or "",
            "note": n.get("farmer_note", ""),
            "status": n.get("req_status") or n.get("status", ""),
            "status_text": st_text,
            "shed": n.get("batch_no", ""),
            "date": n.get("created_at", ""),
            "is_read": n.get("is_read", 0),
            "ref_id": n.get("ref_id", ""),
            "link_url": n.get("link_url", "")
        })

    return {
        "count": unread_count,
        "notifications": formatted
    }

@router.post("/api/notifications/{notif_id}/read")
async def mark_farmer_notif_read_api(request: Request, notif_id: str):
    user = get_current_user(request)
    fid = user.get("farmer_id") if user else None
    if fid:
        db.mark_notification_as_read(notif_id, recipient_role="farmer", recipient_id=fid)
        unread = db.get_unread_notification_count(recipient_role="farmer", recipient_id=fid)
        return {"status": "success", "count": unread}
    return {"status": "error", "count": 0}

@router.post("/api/notifications/mark-all-read")
async def mark_all_farmer_notifs_read_api(request: Request):
    user = get_current_user(request)
    fid = user.get("farmer_id") if user else None
    if fid:
        db.mark_all_notifications_as_read(recipient_role="farmer", recipient_id=fid)
    return {"status": "success", "count": 0}
