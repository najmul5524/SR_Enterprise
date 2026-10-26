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

@router.get("/farmer/{farmer_id}/active-batch")
async def get_farmer_active_batch(farmer_id: str):
    batches = db.get_batches(status="active", farmer_id=farmer_id)
    return JSONResponse({"status": "success", "batch": batches[0] if batches else None})

@router.post("/upload")
async def upload_image(file: UploadFile = File(...), folder: str = "general"):
    contents = await file.read()
    url = await upload_image_file(contents, file.filename, subfolder=folder)
    return JSONResponse({
        "status": "success",
        "url": url,
        "storage": "cloudinary" if is_cloudinary_active() else "local"
    })
