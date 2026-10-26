from fastapi import APIRouter, Request, Query, UploadFile, File
from fastapi.responses import JSONResponse
from app.db import db
from app.storage import upload_image_file, is_cloudinary_active

router = APIRouter(prefix="/api")

@router.get("/qr/lookup")
async def qr_lookup(code: str = Query(...)):
    raw = code.strip()
    
    # 1. Direct search in products by SKU or ID (Case-insensitive)
    prod = db.get_product_by_id(raw)
    if prod:
        return JSONResponse({"status": "success", "type": "product", "data": prod})

    # 2. Check if format has prefix SRE:PRD:<id>:<sku>
    if raw.startswith("SRE:PRD:"):
        parts = raw.split(":")
        for part in parts[2:]:
            product = db.get_product_by_id(part)
            if product:
                return JSONResponse({"status": "success", "type": "product", "data": product})
            
    # 3. Check if format is SRE:FRM:<id>
    elif raw.startswith("SRE:FRM:"):
        parts = raw.split(":")
        farmer_id = parts[2] if len(parts) > 2 else raw
        farmer = db.get_farmer_by_id(farmer_id)
        if farmer:
            batches = db.get_batches(status="active", farmer_id=farmer["id"])
            active_batch = batches[0] if batches else None
            return JSONResponse({
                "status": "success",
                "type": "farmer",
                "data": farmer,
                "active_batch": active_batch
            })

    # 4. Direct search in farmers by ID or phone
    farmer = db.get_farmer_by_id(raw) or db.get_farmer_by_phone(raw)
    if farmer:
        batches = db.get_batches(status="active", farmer_id=farmer["id"])
        active_batch = batches[0] if batches else None
        return JSONResponse({
            "status": "success",
            "type": "farmer",
            "data": farmer,
            "active_batch": active_batch
        })

    return JSONResponse({"status": "not_found", "message": "কোন তথ্য পাওয়া যায়নি"}, status_code=404)

@router.get("/inventory/search")
async def search_inventory(q: str = Query("")):
    products = db.get_products()
    term = q.strip().lower()
    if term:
        results = [
            p for p in products
            if term in p.get("name_bn", "").lower()
            or term in p.get("name", "").lower()
            or term in p.get("sku", "").lower()
            or term in p.get("category", "").lower()
        ]
    else:
        results = products[:20]
    return JSONResponse({"status": "success", "data": results})

@router.get("/farmers/search")
async def search_farmers(q: str = Query("")):
    farmers = db.get_farmers()
    term = q.strip().lower()
    if term:
        results = [
            f for f in farmers
            if term in f.get("name", "").lower()
            or term in f.get("phone", "").lower()
            or term in f.get("shed_name", "").lower()
            or term in f.get("address", "").lower()
        ]
    else:
        results = farmers[:20]
    return JSONResponse({"status": "success", "data": results})

@router.get("/batches/search")
async def search_batches(q: str = Query("")):
    batches = db.get_batches()
    term = q.strip().lower()
    if term:
        results = [
            b for b in batches
            if term in b.get("batch_no", "").lower()
            or term in b.get("farmer_name", "").lower()
            or term in b.get("bird_type", "").lower()
        ]
    else:
        results = batches[:20]
    return JSONResponse({"status": "success", "data": results})

@router.get("/invoices/search")
async def search_invoices(q: str = Query("")):
    invoices = db.get_invoices(limit=100)
    term = q.strip().lower()
    if term:
        results = [
            inv for inv in invoices
            if term in inv.get("invoice_no", "").lower()
            or term in inv.get("farmer_name", "").lower()
        ]
    else:
        results = invoices[:20]
    return JSONResponse({"status": "success", "data": results})

@router.get("/global/search")
async def global_search(q: str = Query("")):
    term = q.strip().lower()
    if not term:
        return JSONResponse({"status": "success", "data": {"products": [], "farmers": [], "batches": [], "invoices": []}})
    
    products = [p for p in db.get_products() if term in p.get("name_bn", "").lower() or term in p.get("sku", "").lower()][:5]
    farmers = [f for f in db.get_farmers() if term in f.get("name", "").lower() or term in f.get("phone", "").lower()][:5]
    batches = [b for b in db.get_batches() if term in b.get("batch_no", "").lower() or term in b.get("farmer_name", "").lower()][:5]
    invoices = [inv for inv in db.get_invoices(limit=50) if term in inv.get("invoice_no", "").lower() or term in inv.get("farmer_name", "").lower()][:5]
    
    return JSONResponse({
        "status": "success",
        "data": {
            "products": products,
            "farmers": farmers,
            "batches": batches,
            "invoices": invoices
        }
    })

@router.get("/farmer/{farmer_id}/batches")
@router.get("/farmer/{farmer_id}/active-batch")
async def get_farmer_batches(farmer_id: str):
    all_batches = db.get_batches(farmer_id=farmer_id)
    active_batches = [b for b in all_batches if b.get("status") == "active"]
    return JSONResponse({
        "status": "success",
        "batch": active_batches[0] if active_batches else (all_batches[0] if all_batches else None),
        "batches": active_batches,
        "all_batches": all_batches,
        "count": len(all_batches)
    })

@router.post("/upload")
async def upload_image(file: UploadFile = File(...), folder: str = "general"):
    contents = await file.read()
    url = await upload_image_file(contents, file.filename, subfolder=folder)
    return JSONResponse({
        "status": "success",
        "url": url,
        "storage": "cloudinary" if is_cloudinary_active() else "local"
    })
