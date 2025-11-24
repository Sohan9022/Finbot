"""
bills.py  — Full-featured Bills / Invoices routes (clean rewrite)

Place this file at: /mnt/data/bills.py
Requires existing helpers:
 - core.ocr_processor.OCRProcessor
 - core.ocr_item_extractor.save_bill_and_items
 - core.category_learner.HybridCategoryLearner
 - core.database.DatabaseOperations
 - .auth.get_current_user_id
"""

import os
import sys
import io
import csv
import json
import tempfile
import logging
import time
from typing import Optional, List, Any, Dict
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from PIL import Image

# ensure project root for imports if running from different CWD
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from core.ocr_processor import OCRProcessor
from core.ocr_item_extractor import save_bill_and_items
from core.category_learner import HybridCategoryLearner
from core.database import DatabaseOperations
from .auth import get_current_user_id

router = APIRouter()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _response(success: bool, data: Any = None, message: str = "") -> Dict[str, Any]:
    payload: Dict[str, Any] = {"success": success}
    if data is not None:
        payload["data"] = data
    if message:
        payload["message"] = message
    return payload


class BillUpdate(BaseModel):
    amount: Optional[float] = None
    merchant: Optional[str] = None
    payment_status: Optional[str] = None
    notes: Optional[str] = None
    category: Optional[str] = None


class MarkAsPaidRequest(BaseModel):
    payment_date: Optional[str] = None
    payment_method: Optional[str] = None


def _ensure_json_serializable_raw(raw_text: Any) -> Optional[str]:
    if raw_text is None:
        return None
    if isinstance(raw_text, str):
        try:
            _ = json.loads(raw_text)
            return raw_text
        except Exception:
            return json.dumps(raw_text, ensure_ascii=False)
    try:
        return json.dumps(raw_text, ensure_ascii=False)
    except Exception:
        return str(raw_text)


def _to_float_safe(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


# -----------------------------
# Helper to create ocr_documents + document_categories and link to bills
# -----------------------------
def _create_ocr_doc_and_category_for_bill(bill_id: int, user_id: int, parsed: dict, predicted_category: Optional[str], ocr_conf: float = 0.0) -> Optional[int]:
    """
    Create an ocr_documents row (mirror of the bill) and a document_categories entry.
    Link the created doc id back to bills.document_id.
    Return doc_id or None on failure.
    """
    try:
        # prepare extracted_text: include parsed structure and raw_text if present
        raw_text = parsed.get("raw_text") or parsed.get("raw_lines") or parsed.get("extracted_text") or ""
        extracted_text = None
        if isinstance(raw_text, (list, dict)):
            extracted_text = json.dumps(raw_text, ensure_ascii=False)
        elif isinstance(raw_text, str) and raw_text.strip():
            extracted_text = raw_text
        else:
            # fallback to a JSON summary
            extracted_text = json.dumps(parsed, ensure_ascii=False)

        filename = f"bill_{bill_id}_{int(time.time())}.txt"
        file_path = f"bills/{filename}"

        # Save ocr_documents row
        doc_id = DatabaseOperations.save_ocr_document(
            filename=filename,
            file_path=file_path,
            extracted_text=extracted_text,
            confidence_score=float(ocr_conf or 0.0),
            processing_time=0.0,
            ocr_engine="bill_mirror",
            uploaded_by=user_id
        )

        if not doc_id:
            logger.warning("Failed to save ocr_documents for bill %s", bill_id)
            return None

        # Insert category record
        category_to_insert = predicted_category or parsed.get("category") or "Uncategorized"
        try:
            DatabaseOperations.insert_document_category(
                document_id=doc_id,
                category=category_to_insert,
                confidence=100.0 if category_to_insert != "Uncategorized" else 0.0,
                metadata={"source": "bill_upload", "bill_id": bill_id}
            )
        except Exception as e:
            logger.exception("Failed to insert document_categories for doc %s: %s", doc_id, e)

        # Link bill -> document_id
        try:
            DatabaseOperations.execute_query(
                "UPDATE bills SET document_id = %s WHERE id = %s",
                (doc_id, bill_id),
                fetch=False
            )
        except Exception as e:
            logger.exception("Failed to update bills.document_id for bill %s: %s", bill_id, e)

        return doc_id

    except Exception as e:
        logger.exception("create_ocr_doc_and_category_for_bill failed: %s", e)
        return None


# -----------------------------
# 1. UPLOAD
# -----------------------------
@router.post("/upload")
async def upload_bill(file: UploadFile = File(...), user_id: int = Depends(get_current_user_id)):
    tmp_path = None
    try:
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Empty file uploaded")
        if len(contents) > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large")

        suffix = os.path.splitext(file.filename)[1] or ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(contents)
            tmp.flush()
            tmp_path = tmp.name

        processor = OCRProcessor()

        ocr_text = ""
        ocr_conf = 0.0

        if file.filename.lower().endswith(".pdf"):
            images = processor.pdf_to_images(tmp_path)
            text_parts = []
            confs = []
            for img in images:
                r = processor.process_document(img)
                if r.get("success"):
                    text_parts.append(r.get("text", ""))
                    if r.get("confidence") is not None:
                        confs.append(r.get("confidence"))
            ocr_text = "\n".join(text_parts)
            ocr_conf = round(sum(confs) / len(confs), 2) if confs else 0.0
        else:
            img = Image.open(tmp_path).convert("RGB")
            r = processor.process_document(img)
            if not r.get("success"):
                raise HTTPException(status_code=400, detail="OCR failed")
            ocr_text = r.get("text", "")
            ocr_conf = r.get("confidence", 0.0)

        # Save via helper: returns save_result with bill_id
        save_res = save_bill_and_items(raw_text=ocr_text, uploaded_by=user_id)
        parsed = save_res.get("parsed", {}) or {}

        # Ensure we have the bill id (save_bill_and_items expected to return it)
        created_bill_id = None
        try:
            created_bill_id = save_res.get("save_result", {}).get("bill_id") or save_res.get("bill_id") or save_res.get("id")
        except Exception:
            created_bill_id = None

        # category suggestions
        learner = HybridCategoryLearner(user_id)
        try:
            suggestions = learner.suggest_category(text=ocr_text, merchant=parsed.get("merchant"), amount=parsed.get("amount")) or []
        except Exception:
            suggestions = []

        predicted_category = parsed.get("category") or (suggestions[0][0] if suggestions else None)

        # If we have a newly created bill, create ocr_documents mirror immediately (clean approach)
        doc_id = None
        if created_bill_id:
            doc_id = _create_ocr_doc_and_category_for_bill(created_bill_id, user_id, parsed, predicted_category, ocr_conf)

        return _response(True, {"parsed": parsed, "save_result": save_res, "suggestions": suggestions, "ocr_confidence": ocr_conf, "document_id": doc_id})

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("upload_bill failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


# -----------------------------
# 2. LIST BILLS
# -----------------------------
@router.get("/list")
async def list_bills(
    user_id: int = Depends(get_current_user_id),
    merchant: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = 0,
    sort: Optional[str] = Query("date_desc")
):
    base_q = """
        SELECT b.id, b.merchant_id, b.merchant_name, b.bill_date,
               b.total_amount AS amount, b.payment_status, b.due_date,
               COALESCE(dc.category, b.category, 'Uncategorized') AS category,
               b.created_at
        FROM bills b
        LEFT JOIN document_categories dc ON dc.document_id = b.document_id
        WHERE b.uploaded_by = %s
    """
    params = [user_id]

    if merchant:
        base_q += " AND b.merchant_name ILIKE %s"
        params.append(f"%{merchant}%")
    if date_from:
        base_q += " AND b.bill_date >= %s"
        params.append(date_from)
    if date_to:
        base_q += " AND b.bill_date <= %s"
        params.append(date_to)

    order_clause = {
        "date_asc": "b.bill_date ASC NULLS LAST",
        "date_desc": "b.bill_date DESC NULLS LAST",
        "amount_asc": "b.total_amount ASC NULLS LAST",
        "amount_desc": "b.total_amount DESC NULLS LAST"
    }.get(sort, "b.bill_date DESC")

    q = base_q + f" ORDER BY {order_clause} LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    bills = DatabaseOperations.execute_query(q, tuple(params)) or []

    count_q = "SELECT COUNT(*) AS total FROM bills WHERE uploaded_by = %s"
    count_params = [user_id]
    if merchant:
        count_q += " AND merchant_name ILIKE %s"
        count_params.append(f"%{merchant}%")
    total_res = DatabaseOperations.execute_query(count_q, tuple(count_params)) or [{"total": 0}]

    return _response(True, {"bills": bills, "total": int(total_res[0]["total"]), "limit": limit, "offset": offset})


# -----------------------------
# 3. GET BILL DETAIL (with items)
# -----------------------------
@router.get("/{bill_id}")
async def get_bill_detail(bill_id: int, user_id: int = Depends(get_current_user_id)):
    bill_q = """
        SELECT id, merchant_id, merchant_name, bill_date, total_amount AS amount,
               payment_status, due_date, raw_text, category, document_id, created_at
        FROM bills WHERE id = %s AND uploaded_by = %s
    """
    bill_res = DatabaseOperations.execute_query(bill_q, (bill_id, user_id))
    if not bill_res:
        raise HTTPException(status_code=404, detail="Bill not found")
    bill = bill_res[0]

    items = DatabaseOperations.execute_query(
        "SELECT id, product_name, qty, unit_price, line_total, raw_line, created_at FROM bill_items WHERE bill_id = %s ORDER BY id",
        (bill_id,)
    ) or []

    try:
        raw_lines = json.loads(bill.get("raw_text") or "[]")
    except Exception:
        raw_lines = bill.get("raw_text") or []

    # Also include linked document info if exists
    doc_info = None
    if bill.get("document_id"):
        doc = DatabaseOperations.execute_query("SELECT id, extracted_text, amount, payment_status, created_at FROM ocr_documents WHERE id = %s", (bill.get("document_id"),)) or []
        if doc:
            doc_info = doc[0]

    return _response(True, {"bill": bill, "items": items, "raw_lines": raw_lines, "document": doc_info})


# -----------------------------
# 4. SAVE-EDITED (create or update)
# -----------------------------
@router.post("/save-edited")
def save_edited(payload: dict, user_id: int = Depends(get_current_user_id)):
    try:
        bill_id = payload.get("bill_id")
        merchant_name = payload.get("merchant") or "Unknown"
        bill_date = payload.get("date")
        total = _to_float_safe(payload.get("total")) or 0.0
        items = payload.get("items") or []
        raw_text = payload.get("raw_text") or ""
        category = payload.get("category")

        raw_text_stored = _ensure_json_serializable_raw(raw_text)

        # Ensure merchant exists (simple upsert)
        m = DatabaseOperations.execute_query("SELECT id FROM merchants WHERE name = %s AND uploaded_by = %s", (merchant_name, user_id)) or []
        if m:
            merchant_id = m[0]["id"]
        else:
            res = DatabaseOperations.execute_query(
                "INSERT INTO merchants (name, metadata, uploaded_by, created_at) VALUES (%s, %s, %s, NOW()) RETURNING id",
                (merchant_name, json.dumps({}), user_id),
                fetch=True
            )
            merchant_id = res[0]["id"] if res else None

        if bill_id:
            # Update
            fields = []
            params = []
            fields.append("merchant_id = %s"); params.append(merchant_id)
            fields.append("merchant_name = %s"); params.append(merchant_name)
            fields.append("bill_date = %s"); params.append(bill_date)
            fields.append("total_amount = %s"); params.append(total)
            fields.append("raw_text = %s"); params.append(raw_text_stored)
            if category is not None:
                fields.append("category = %s"); params.append(category)

            params.extend([bill_id, user_id])
            q = f"UPDATE bills SET {', '.join(fields)} WHERE id = %s AND uploaded_by = %s"
            DatabaseOperations.execute_query(q, tuple(params), fetch=False)

            # Replace items
            DatabaseOperations.execute_query("DELETE FROM bill_items WHERE bill_id = %s", (bill_id,), fetch=False)
            for it in items:
                DatabaseOperations.execute_query(
                    "INSERT INTO bill_items (bill_id, product_name, qty, unit_price, line_total, raw_line, created_at) VALUES (%s, %s, %s, %s, %s, %s, NOW())",
                    (bill_id, it.get("product_name"), it.get("qty") or 0, it.get("unit_price") or 0, it.get("line_total") or 0, _ensure_json_serializable_raw(it.get("raw_line"))),
                    fetch=False
                )

            # Teach learner if category provided
            if category:
                try:
                    learner = HybridCategoryLearner(user_id)
                    b = DatabaseOperations.execute_query("SELECT raw_text, total_amount FROM bills WHERE id = %s", (bill_id,)) or []
                    raw_text_db = b[0].get("raw_text") if b else raw_text
                    amount_val = _to_float_safe(b[0].get("total_amount")) if b else total
                    learner.learn_from_input(category=category, text=str(raw_text_db), merchant=merchant_name, amount=amount_val)
                except Exception:
                    logger.exception("learn_from_input failed for edit")

            # Create or update ocr_documents mirror for this bill
            parsed = {"merchant": merchant_name, "amount": total, "date": bill_date, "raw_text": raw_text}
            try:
                # if a linked document exists, update its fields; else create new doc and link
                bill_row = DatabaseOperations.execute_query("SELECT document_id FROM bills WHERE id = %s", (bill_id,)) or []
                doc_id = bill_row[0].get("document_id") if bill_row and bill_row[0].get("document_id") else None
                if doc_id:
                    DatabaseOperations.execute_query(
                        "UPDATE ocr_documents SET extracted_text = %s, amount = %s, created_at = NOW() WHERE id = %s",
                        (json.dumps(parsed, ensure_ascii=False), total, doc_id),
                        fetch=False
                    )
                    # update category record if present
                    if category:
                        # update or insert doc category
                        exists = DatabaseOperations.execute_query("SELECT id FROM document_categories WHERE document_id = %s LIMIT 1", (doc_id,)) or []
                        if exists:
                            DatabaseOperations.execute_query(
                                "UPDATE document_categories SET category = %s, confidence = %s, metadata = COALESCE(metadata, '{}'::jsonb) || %s::jsonb WHERE document_id = %s",
                                (category, 100.0, json.dumps({"synced_from": "bills_edit"}), doc_id),
                                fetch=False
                            )
                        else:
                            DatabaseOperations.insert_document_category(doc_id, category, 100.0, {"synced_from": "bills_edit", "bill_id": bill_id})
                else:
                    # create fresh mirrored doc
                    _create_ocr_doc_and_category_for_bill(bill_id, user_id, parsed, category, ocr_conf=0.0)
            except Exception:
                logger.exception("save_edited:update doc mirror failed")

            return _response(True, {"bill_id": bill_id}, message="Bill updated")
        else:
            # Create new bill
            row = DatabaseOperations.execute_query(
                "INSERT INTO bills (merchant_id, merchant_name, bill_date, total_amount, raw_text, category, uploaded_by, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW()) RETURNING id",
                (merchant_id, merchant_name, bill_date, total, raw_text_stored, category, user_id),
                fetch=True
            )
            if not row:
                raise HTTPException(status_code=500, detail="Failed to create bill")
            new_bill_id = row[0]["id"]

            # Insert items
            for it in items:
                DatabaseOperations.execute_query(
                    "INSERT INTO bill_items (bill_id, product_name, qty, unit_price, line_total, raw_line, created_at) VALUES (%s, %s, %s, %s, %s, %s, NOW())",
                    (new_bill_id, it.get("product_name"), it.get("qty") or 0, it.get("unit_price") or 0, it.get("line_total") or 0, _ensure_json_serializable_raw(it.get("raw_line"))),
                    fetch=False
                )

            # Teach learner
            if category:
                try:
                    learner = HybridCategoryLearner(user_id)
                    learner.learn_from_input(category=category, text=str(raw_text), merchant=merchant_name, amount=total)
                except Exception:
                    logger.exception("learn_from_input failed for create")

            parsed = {"merchant": merchant_name, "amount": total, "date": bill_date, "raw_text": raw_text}
            try:
                _create_ocr_doc_and_category_for_bill(new_bill_id, user_id, parsed, category, ocr_conf=0.0)
            except Exception:
                logger.exception("save_edited:create doc mirror failed")

            return _response(True, {"bill_id": new_bill_id}, message="Bill created")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("save_edited failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# 5. UPDATE BILL (PUT)
# -----------------------------
@router.put("/{bill_id}")
async def update_bill(bill_id: int, payload: BillUpdate, user_id: int = Depends(get_current_user_id)):
    exists = DatabaseOperations.execute_query("SELECT id FROM bills WHERE id = %s AND uploaded_by = %s", (bill_id, user_id))
    if not exists:
        raise HTTPException(status_code=404, detail="Bill not found")

    fields = []
    params = []
    if payload.amount is not None:
        fields.append("total_amount = %s"); params.append(payload.amount)
    if payload.merchant is not None:
        fields.append("merchant_name = %s"); params.append(payload.merchant)
    if payload.payment_status is not None:
        fields.append("payment_status = %s"); params.append(payload.payment_status)
    if payload.notes is not None:
        fields.append("notes = %s"); params.append(payload.notes)
    if payload.category is not None:
        fields.append("category = %s"); params.append(payload.category)

    if fields:
        params.extend([bill_id, user_id])
        q = f"UPDATE bills SET {', '.join(fields)} WHERE id = %s AND uploaded_by = %s"
        DatabaseOperations.execute_query(q, tuple(params), fetch=False)

    if payload.category is not None:
        try:
            learner = HybridCategoryLearner(user_id)
            b = DatabaseOperations.execute_query("SELECT raw_text, total_amount FROM bills WHERE id = %s", (bill_id,)) or []
            raw_text = b[0].get("raw_text") if b else ""
            amount_val = _to_float_safe(b[0].get("total_amount")) if b else None
            learner.learn_from_input(category=payload.category, text=str(raw_text), merchant=payload.merchant or None, amount=amount_val)
        except Exception:
            logger.exception("learn_from_input failed on PUT update")

    # Sync to OCR doc (update mirrored doc)
    try:
        b = DatabaseOperations.execute_query("SELECT document_id, raw_text, total_amount FROM bills WHERE id = %s", (bill_id,)) or []
        if b and b[0].get("document_id"):
            doc_id = b[0].get("document_id")
            DatabaseOperations.execute_query(
                "UPDATE ocr_documents SET extracted_text = %s, amount = %s WHERE id = %s",
                (b[0].get("raw_text") or "", b[0].get("total_amount") or 0, doc_id),
                fetch=False
            )
            if payload.category is not None:
                exists = DatabaseOperations.execute_query("SELECT id FROM document_categories WHERE document_id = %s LIMIT 1", (doc_id,)) or []
                if exists:
                    DatabaseOperations.execute_query(
                        "UPDATE document_categories SET category = %s, confidence = %s, metadata = COALESCE(metadata, '{}'::jsonb) || %s::jsonb WHERE document_id = %s",
                        (payload.category, 100.0, json.dumps({"synced_from": "bills_put"}), doc_id),
                        fetch=False
                    )
                else:
                    DatabaseOperations.insert_document_category(doc_id, payload.category, 100.0, {"synced_from": "bills_put", "bill_id": bill_id})
    except Exception:
        logger.exception("update_bill: sync failed for bill %s", bill_id)

    updated = DatabaseOperations.execute_query(
        "SELECT id, merchant_id, merchant_name, bill_date, total_amount AS amount, payment_status, due_date, raw_text, category, document_id, created_at FROM bills WHERE id = %s AND uploaded_by = %s",
        (bill_id, user_id)
    ) or []

    return _response(True, {"bill": updated[0] if updated else None}, message="Bill updated successfully")


# -----------------------------
# 6. DELETE BILL
# -----------------------------
@router.delete("/{bill_id}")
async def delete_bill(bill_id: int, user_id: int = Depends(get_current_user_id)):
    exists = DatabaseOperations.execute_query("SELECT id, document_id FROM bills WHERE id = %s AND uploaded_by = %s", (bill_id, user_id)) or []
    if not exists:
        raise HTTPException(status_code=404, detail="Bill not found")

    doc_id = exists[0].get("document_id")
    DatabaseOperations.execute_query("DELETE FROM bill_items WHERE bill_id = %s", (bill_id,), fetch=False)
    DatabaseOperations.execute_query("DELETE FROM bills WHERE id = %s AND uploaded_by = %s", (bill_id, user_id), fetch=False)

    # Best-effort: remove document_categories and ocr_documents mirror if present and safe
    try:
        if doc_id:
            # remove category rows for that document (non-destructive for external analytics)
            DatabaseOperations.execute_query("DELETE FROM document_categories WHERE document_id = %s", (doc_id,), fetch=False)
            # optionally remove the mirrored document
            DatabaseOperations.execute_query("DELETE FROM ocr_documents WHERE id = %s", (doc_id,), fetch=False)
    except Exception:
        logger.exception("delete_bill: failed to clean mirrored doc %s", doc_id)

    return _response(True, message="Bill deleted successfully")


# -----------------------------
# 7. MARK AS PAID
# -----------------------------
@router.post("/{bill_id}/mark-paid")
async def mark_as_paid(bill_id: int, data: MarkAsPaidRequest, user_id: int = Depends(get_current_user_id)):
    exists = DatabaseOperations.execute_query("SELECT id, document_id FROM bills WHERE id = %s AND uploaded_by = %s", (bill_id, user_id)) or []
    if not exists:
        raise HTTPException(status_code=404, detail="Bill not found")

    payment_date = data.payment_date or datetime.utcnow().isoformat()
    DatabaseOperations.execute_query("UPDATE bills SET payment_status = 'paid', payment_date = %s WHERE id = %s AND uploaded_by = %s",
                                     (payment_date, bill_id, user_id), fetch=False)

    # Update mirrored OCR doc payment status
    try:
        doc_id = exists[0].get("document_id")
        if doc_id:
            DatabaseOperations.execute_query(
                "UPDATE ocr_documents SET payment_status = %s, payment_date = %s WHERE id = %s",
                ("paid", payment_date, doc_id),
                fetch=False
            )
            # also update document_categories metadata to include paid flag
            DatabaseOperations.execute_query(
                "UPDATE document_categories SET metadata = COALESCE(metadata, '{}'::jsonb) || %s::jsonb WHERE document_id = %s",
                (json.dumps({"payment_status": "paid", "payment_date": payment_date}), doc_id),
                fetch=False
            )
    except Exception:
        logger.exception("mark-as-paid: sync failed for bill %s", bill_id)

    updated = DatabaseOperations.execute_query(
        "SELECT id, merchant_id, merchant_name, bill_date, total_amount AS amount, payment_status, due_date, raw_text, category, document_id, created_at FROM bills WHERE id = %s AND uploaded_by = %s",
        (bill_id, user_id)
    ) or []

    return _response(True, {"bill": updated[0] if updated else None}, message="Bill marked as paid")


# -----------------------------
# 8. SEARCH
# -----------------------------
@router.get("/search")
async def search_bills(q: str = Query(..., min_length=1), user_id: int = Depends(get_current_user_id), limit: int = Query(50, ge=1, le=500)):
    qterm = f"%{q}%"
    bills = DatabaseOperations.execute_query("""
        SELECT id, merchant_name, total_amount AS amount, bill_date, payment_status, category, document_id, created_at
        FROM bills
        WHERE uploaded_by = %s AND (merchant_name ILIKE %s OR raw_text ILIKE %s)
        ORDER BY created_at DESC
        LIMIT %s
    """, (user_id, qterm, qterm, limit)) or []

    # attach items quickly
    items = DatabaseOperations.execute_query("SELECT bill_id, product_name, line_total FROM bill_items WHERE product_name ILIKE %s LIMIT 200", (qterm,)) or []
    item_map = {}
    for it in items:
        item_map.setdefault(it.get("bill_id"), []).append(it)
    for b in bills:
        b["items"] = item_map.get(b.get("id")) or []

    return _response(True, {"results": bills, "count": len(bills)})


# -----------------------------
# 9. EXPORT
# -----------------------------
@router.get("/export")
async def export_bills(format: str = Query("csv", regex="^(csv|json)$"), user_id: int = Depends(get_current_user_id),
                       merchant: Optional[str] = None, date_from: Optional[str] = None, date_to: Optional[str] = None):
    base_q = "SELECT id, merchant_name, total_amount AS amount, bill_date, payment_status, category, document_id, created_at FROM bills WHERE uploaded_by = %s"
    params = [user_id]
    if merchant:
        base_q += " AND merchant_name ILIKE %s"
        params.append(f"%{merchant}%")
    if date_from:
        base_q += " AND bill_date >= %s"
        params.append(date_from)
    if date_to:
        base_q += " AND bill_date <= %s"
        params.append(date_to)
    base_q += " ORDER BY created_at DESC"
    rows = DatabaseOperations.execute_query(base_q, tuple(params)) or []

    if not rows:
        raise HTTPException(status_code=404, detail="No bills to export")

    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        return StreamingResponse(iter([output.getvalue()]), media_type="text/csv",
                                 headers={"Content-Disposition": f"attachment; filename=bills_{datetime.utcnow().strftime('%Y%m%d')}.csv"})
    else:
        return _response(True, {"bills": rows, "exported_at": datetime.utcnow().isoformat(), "total": len(rows)})


# -----------------------------
# 10. REMINDERS
# -----------------------------
@router.get("/reminders")
async def reminders(days_ahead: int = Query(30, ge=1, le=365), user_id: int = Depends(get_current_user_id)):
    try:
        days = int(days_ahead)
    except Exception:
        days = 30
    query = """
        SELECT id, merchant_name, total_amount AS amount, bill_date, due_date, payment_status, category
        FROM bills
        WHERE uploaded_by = %s
          AND due_date IS NOT NULL
          AND due_date <= (NOW() + INTERVAL %s)
        ORDER BY due_date ASC
    """
    rows = DatabaseOperations.execute_query(query, (user_id, f"{days} days")) or []
    total_due = sum(float(r.get("amount") or 0) for r in rows) if rows else 0.0
    return _response(True, {"reminders": rows, "count": len(rows), "total_due": total_due, "days_ahead": days})


# -----------------------------
# 11. PARSE-ONLY
# -----------------------------
@router.post("/parse-only")
async def parse_only(file: UploadFile = File(...), user_id: int = Depends(get_current_user_id)):
    tmp_path = None
    try:
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Empty file")
        suffix = os.path.splitext(file.filename)[1] or ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(contents)
            tmp.flush()
            tmp_path = tmp.name

        processor = OCRProcessor()
        if file.filename.lower().endswith(".pdf"):
            images = processor.pdf_to_images(tmp_path)
            texts = []
            confs = []
            for img in images:
                r = processor.process_document(img)
                texts.append(r.get("text", ""))
                if r.get("confidence") is not None:
                    confs.append(r.get("confidence"))
            ocr_text = "\n".join(texts)
            ocr_conf = round(sum(confs) / len(confs), 2) if confs else 0.0
        else:
            img = Image.open(tmp_path).convert("RGB")
            r = processor.process_document(img)
            if not r.get("success"):
                raise HTTPException(status_code=400, detail="OCR failed")
            ocr_text = r.get("text", "")
            ocr_conf = r.get("confidence", 0.0)

        save_res = save_bill_and_items(raw_text=ocr_text, uploaded_by=user_id)
        parsed = save_res.get("parsed", {}) or {}
        parsed["raw_text"] = ocr_text
        parsed["ocr_confidence"] = ocr_conf

        return _response(True, data={"parsed": parsed})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("parse_only failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


# -----------------------------
# 12. BULK UPLOAD
# -----------------------------
@router.post("/bulk-upload")
async def bulk_upload(files: List[UploadFile] = File(...), user_id: int = Depends(get_current_user_id)):
    if len(files) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 files allowed")
    results = []
    processor = OCRProcessor()
    learner = HybridCategoryLearner(user_id)

    for file in files:
        tmp_path = None
        try:
            contents = await file.read()
            if not contents:
                results.append({"filename": file.filename, "success": False, "error": "Empty file"})
                continue
            suffix = os.path.splitext(file.filename)[1] or ".jpg"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(contents)
                tmp.flush()
                tmp_path = tmp.name

            if file.filename.lower().endswith(".pdf"):
                images = processor.pdf_to_images(tmp_path)
                texts = []
                confs = []
                for img in images:
                    r = processor.process_document(img)
                    texts.append(r.get("text", ""))
                    if r.get("confidence") is not None:
                        confs.append(r.get("confidence"))
                ocr_text = "\n".join(texts)
                ocr_conf = round(sum(confs) / len(confs), 2) if confs else 0.0
            else:
                img = Image.open(tmp_path).convert("RGB")
                r = processor.process_document(img)
                if not r.get("success"):
                    results.append({"filename": file.filename, "success": False, "error": "OCR failed"})
                    continue
                ocr_text = r.get("text", "")
                ocr_conf = r.get("confidence", 0.0)

            save_res = save_bill_and_items(raw_text=ocr_text, uploaded_by=user_id)
            parsed = save_res.get("parsed", {}) or {}
            try:
                suggestions = learner.suggest_category(text=ocr_text, merchant=parsed.get("merchant"), amount=parsed.get("amount")) or []
            except Exception:
                suggestions = []

            created_bill_id = save_res.get("save_result", {}).get("bill_id") or save_res.get("bill_id") or None
            predicted_category = parsed.get("category") or (suggestions[0][0] if suggestions else None)

            if created_bill_id:
                try:
                    _create_ocr_doc_and_category_for_bill(created_bill_id, user_id, parsed, predicted_category, ocr_conf=ocr_conf)
                except Exception:
                    logger.exception("bulk-upload: mirror create failed for bill %s", created_bill_id)

            results.append({"filename": file.filename, "success": True, "save_result": save_res, "parsed": parsed, "suggestions": suggestions[:3], "ocr_confidence": ocr_conf})
        except Exception as e:
            logger.exception("bulk-upload file error: %s", e)
            results.append({"filename": file.filename, "success": False, "error": str(e)})
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    return _response(True, data={"total": len(files), "successful": len([r for r in results if r.get("success")]), "failed": len([r for r in results if not r.get("success")]), "results": results})
