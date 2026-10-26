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
    farmer = db.get_farmer_by_id(user["farmer_id"])
    ctx = {
        "current_path": request.url.path,
        "user": user,
        "farmer": farmer,
        "shop": db.get_settings(),
        "is_mobile_app": is_mobile_app_client(request),
    }
    if extra:
        ctx.update(extra)
    return ctx

def render_farmer_template(request: Request, name: str, extra: dict = None):
    return templates.TemplateResponse(request=request, name=name, context=farmer_context(request, extra))

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def farmer_dashboard(request: Request):
    user = get_current_user(request)
    farmer = db.get_farmer_by_id(user["farmer_id"])
    if not farmer:
        return RedirectResponse(url="/logout", status_code=303)

    batches = db.get_batches(farmer_id=farmer["id"])
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

    recent_logs = []
    if active_batch:
        recent_logs = db.get_batch_logs(active_batch["id"])[-8:]

    recent_invoices = db.get_invoices(farmer_id=farmer["id"], limit=5)
    farmer_qr = generate_qr_data_url(f"SRE:FRM:{farmer['id']}")

    return render_farmer_template(request, "farmer/dashboard.html", {
        "farmer": farmer,
        "active_batch": active_batch,
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
            "details": f"{len(inv.get('items', []))} টি পণ্য মালামাল",
            "amount": inv["net_total"],
            "ref_id": inv["id"]
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
async def request_feed_page(request: Request, success: Optional[str] = None):
    user = get_current_user(request)
    farmer = db.get_farmer_by_id(user["farmer_id"])
    batches = db.get_batches(status="active", farmer_id=farmer["id"])
    active_batch = batches[0] if batches else None
    products = db.get_products()
    my_requests = db.get_feed_requests(farmer_id=farmer["id"])

    return render_farmer_template(request, "farmer/request_feed.html", {
        "farmer": farmer,
        "active_batch": active_batch,
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
