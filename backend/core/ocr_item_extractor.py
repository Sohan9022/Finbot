
# core/ocr_item_extractor.py
"""
Final patched OCR item extractor/save pipeline.

Key changes in this final version:
 - Saves to ocr_documents (preferred) and also creates a bills row (so UI/listing works)
 - Inserts items into bill_items using bill_id (no document_id fallback)
 - Defensive: it will continue even if optional columns/tables are missing
 - When updating ocr_documents, it will attempt merchant_id update but ignore failures (so you may still want to run DB migration to add merchant_id)
 - Redacts sensitive info before saving
"""

import re
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from core.database import DatabaseOperations

# -----------------------------
# Helpers: detection & redaction
# -----------------------------


def is_upi_id(text: str) -> bool:
    if not text:
        return False
    t = text.strip()
    return "@" in t and len(t.split("@")[0]) > 1 and len(t.split("@")[-1]) <= 20


def looks_like_email(text: str) -> bool:
    return bool(re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text))


def redact_sensitive(text: str) -> str:
    if not text:
        return text
    s = text
    # mask emails & upi-like tokens
    s = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[REDACTED_EMAIL]", s)
    s = re.sub(r"\b[A-Za-z0-9._%+-]{1,}@[A-Za-z0-9.-]{1,}\b", "[REDACTED_EMAIL]", s)
    # mask long digit sequences (UTR, account numbers, long card sequences)
    s = re.sub(r"\b\d{6,}\b", "[REDACTED_NUMBER]", s)
    # mask phone-like sequences (loose)
    s = re.sub(r"(?:(?:\+?\d{1,3}[-\s.]*)?(?:\d{10,13}))", "[REDACTED_PHONE]", s)
    # normalize whitespace
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


# -----------------------------
# Payment app/mode/direction
# -----------------------------


def detect_payment_app(text: str) -> Optional[str]:
    t = (text or "").lower()
    if "phonepe" in t or "u transaction successful" in t or "powered by phonepe" in t:
        return "PhonePe"
    if "gpay" in t or "google pay" in t or "sent to gpay" in t:
        return "Google Pay"
    if "paytm" in t:
        return "Paytm"
    if "yono" in t and "sbi" in t:
        return "SBI"
    if "icici" in t and ("imobile" in t or "imps" in t):
        return "ICICI"
    if "@ok" in t or "@ybl" in t or "@upi" in t or "@paytm" in t:
        return "UPI Transfer"
    return None


def detect_payment_mode(text: str) -> Optional[str]:
    t = (text or "").lower()
    if any(k in t for k in ["upi", "gpay", "phonepe", "paytm"]):
        return "UPI"
    if any(k in t for k in ["imps", "imps txn", "instant payment"]):
        return "IMPS"
    if any(k in t for k in ["neft", "rtgs"]):
        return "NEFT/RTGS"
    if any(k in t for k in ["card", "visa", "mastercard", "debit card", "credit card"]):
        return "CARD"
    if any(k in t for k in ["wallet", "paytm wallet", "phonepe wallet"]):
        return "WALLET"
    if any(k in t for k in ["bank", "account", "beneficiary"]):
        return "BANK_TRANSFER"
    return None


def detect_direction(text: str) -> Optional[str]:
    t = (text or "").lower()
    if any(p in t for p in ["sent to", "paid to", "debited from", "you paid", "you sent"]):
        return "Sent"
    if any(p in t for p in ["received from", "credited", "you received", "was credited"]):
        return "Received"
    return None


# -----------------------------
# Merchant extraction
# -----------------------------


def extract_merchant_from_upi_lines(lines: List[str]) -> Optional[str]:
    for i, ln in enumerate(lines):
        if "paid to" in ln.lower() or ln.lower().strip().startswith("paid"):
            candidates = []
            for nxt in lines[i + 1:i + 5]:
                clean = nxt.strip()
                if not clean:
                    continue
                low = clean.lower()
                if any(k in low for k in ["transaction", "successful", "utr", "paid", "payment", "powered by"]):
                    continue
                if is_upi_id(clean) or looks_like_email(clean):
                    continue
                if re.fullmatch(r"[\d\W]+", clean):
                    continue
                filtered = re.sub(r"[^A-Za-z0-9\s\.,&()/-]", "", clean).strip()
                if filtered:
                    candidates.append(filtered)
            if candidates:
                merged = " ".join(candidates[:2]).strip()
                return merged.upper()
    return None


def fallback_merchant_from_lines(lines: List[str]) -> Optional[str]:
    for ln in lines[:6]:
        clean = ln.strip()
        if not clean:
            continue
        if is_upi_id(clean) or looks_like_email(clean):
            continue
        low = clean.lower()
        if any(k in low for k in ["transaction", "successful", "payment", "paid", "banking name"]):
            continue
        if any(ch.isalpha() for ch in clean) and len(clean) >= 3:
            filtered = re.sub(r"[^A-Za-z0-9\s\.,&()/-]", "", clean).strip()
            if filtered:
                return filtered.upper()
    return None


# -----------------------------
# Amount / Date
# -----------------------------


def extract_amount(text: str) -> Optional[float]:
    if not text:
        return None
    patterns = [
        r"(?:grand total|grand|net amount|amount payable|amount|total|paid|payment|debited|credited)[\s:\-–]*₹?\s*([\d,]+(?:\.\d{1,2})?)",
        r"₹\s*([\d,]+(?:\.\d{1,2})?)",
        r"Rs\.?\s*([\d,]+(?:\.\d{1,2})?)",
    ]
    amounts = []
    for p in patterns:
        for m in re.finditer(p, text, flags=re.IGNORECASE):
            s = m.group(1).replace(",", "")
            try:
                v = float(s)
                if 0 < v < 10_000_000:
                    amounts.append((v, m.start()))
            except:
                continue
    if not amounts:
        for m in re.finditer(r"₹?\s*([\d,]{1,3}(?:,\d{3})*(?:\.\d{1,2})?)", text):
            s = m.group(1).replace(",", "")
            try:
                v = float(s)
                if 0 < v < 10_000_000:
                    amounts.append((v, m.start()))
            except:
                continue
    if not amounts:
        return None
    # prefer amount near keywords
    keyword_positions = []
    for kw in ["total", "grand", "net amount", "amount payable", "paid", "debited"]:
        for m in re.finditer(rf"\b{re.escape(kw)}\b", text, flags=re.IGNORECASE):
            keyword_positions.append(m.start())
    if keyword_positions:
        best = None
        best_dist = None
        for v, pos in amounts:
            dist = min(abs(pos - kp) for kp in keyword_positions)
            if best is None or dist < best_dist:
                best = v
                best_dist = dist
        if best is not None:
            return float(best)
    amounts_sorted = sorted(amounts, key=lambda x: x[0], reverse=True)
    return float(amounts_sorted[0][0])


def extract_date(text: str) -> Optional[str]:
    if not text:
        return None
    patterns = [
        r"(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
        r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
        r"(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?,?\s*\d{2,4})",
        r"(?:date|txn date|transaction date|bill date)[\s:\-]*([0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4})",
    ]
    for p in patterns:
        m = re.search(p, text, flags=re.IGNORECASE)
        if m:
            raw = m.group(1).replace(",", "").strip()
            parsed = _parse_date_flex(raw)
            if parsed:
                return parsed
    return None


def _parse_date_flex(date_str: str) -> Optional[str]:
    date_str = date_str.strip()
    fmts = [
        "%d-%m-%Y", "%d/%m/%Y", "%d-%m-%y", "%d/%m/%y",
        "%Y-%m-%d", "%Y/%m/%d",
        "%d %b %Y", "%d %B %Y"
    ]
    from datetime import datetime as _dt
    for f in fmts:
        try:
            d = _dt.strptime(date_str, f)
            return d.date().isoformat()
        except Exception:
            continue
    try:
        d = _dt.fromisoformat(date_str)
        return d.date().isoformat()
    except Exception:
        return None


# -----------------------------
# Lightweight item parser (used if advanced parser not provided)
# -----------------------------


PRICE_RE = r"(?:₹\s*|Rs\.?\s*)?([\d,]+(?:\.\d{1,2})?)"
QUANTITY_RE = r"(\d+(?:\.\d+)?)\s*(?:x|X|qty|pcs|pc|nos|no)?\b"
IGNORE_ROW_KEYWORDS = [
    "subtotal", "gst", "tax", "total tax", "cgst", "sgst", "discount", "savings", "round off",
    "service charge", "delivery charge", "payment", "order total", "grand total", "total payable"
]


def looks_like_price_token(token: str) -> bool:
    return bool(re.search(PRICE_RE, token))


def parse_price_from_token(token: str) -> Optional[float]:
    if not token:
        return None
    m = re.search(PRICE_RE, token)
    if not m:
        return None
    s = m.group(1).replace(",", "")
    try:
        return float(s)
    except:
        return None


def parse_items_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Simplified parser for line-items. For complex invoices, you can swap
    in an advanced parser. This function returns a best-effort list of items.
    """
    if not text:
        return []
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines() if ln.strip()]
    items = []
    for ln in lines:
        low = ln.lower()
        if any(k in low for k in IGNORE_ROW_KEYWORDS):
            continue
        # try to find a trailing price
        tokens = ln.split()
        if not tokens:
            continue
        # find last token that looks like price
        line_total = None
        for j in range(len(tokens)-1, -1, -1):
            if looks_like_price_token(tokens[j]):
                line_total = parse_price_from_token(tokens[j])
                desc = " ".join(tokens[:j]).strip()
                break
        if line_total is None:
            continue
        # qty detection
        qty = None
        m_qty = re.search(QUANTITY_RE, ln, flags=re.IGNORECASE)
        if m_qty:
            try:
                qty = float(m_qty.group(1))
            except:
                qty = None
        items.append({
            "description": desc,
            "quantity": qty,
            "unit_price": None,
            "line_total": line_total,
            "raw_line": ln
        })
    return items


# -----------------------------
# Final save function (writes to both ocr_documents and bills + bill_items)
# -----------------------------


def save_bill_and_items(
    raw_text: str,
    items: Optional[List[Dict[str, Any]]] = None,
    merchant_name: Optional[str] = None,
    merchant_id: Optional[int] = None,
    bill_date: Optional[str] = None,
    total_amount: Optional[float] = None,
    uploaded_by: Optional[int] = None,
    filename: Optional[str] = None,
    file_path: Optional[str] = None,
    ocr_engine: str = "tesseract",
    confidence_score: float = 0.0,
    processing_time: float = 0.0,
) -> Dict[str, Any]:
    """
    Save OCR document & also create a bills row + bill_items (using bill_id).
    Defensive: failures in optional tables won't block the main save.
    """
    try:
        items = items or []
        now = datetime.utcnow()

        lines = [ln.strip() for ln in (raw_text or "").splitlines() if ln.strip()]

        # merchant detection
        merchant = None
        if merchant_name:
            merchant = merchant_name.strip().upper()
            if is_upi_id(merchant) or looks_like_email(merchant):
                merchant = None
        if not merchant:
            merchant = extract_merchant_from_upi_lines(lines)
        if not merchant:
            merchant = fallback_merchant_from_lines(lines)

        payment_app = detect_payment_app(raw_text)
        payment_mode = detect_payment_mode(raw_text)
        direction = detect_direction(raw_text)

        amount = total_amount if total_amount is not None else extract_amount(raw_text)
        detected_date = bill_date or extract_date(raw_text)

        parsed_items = items if items else parse_items_from_text(raw_text)

        sanitized_text = redact_sensitive(raw_text)

        if not filename:
            ts = now.strftime("%Y%m%d_%H%M%S")
            filename = f"ocr_doc_{ts}.txt"
        if not file_path:
            file_path = f"uploads/{uploaded_by or 'anon'}/{filename}"

        # 1) save to ocr_documents
        doc_id = None
        try:
            doc_id = DatabaseOperations.save_ocr_document(
                filename=filename,
                file_path=file_path,
                extracted_text=sanitized_text,
                confidence_score=float(confidence_score or 0.0),
                processing_time=float(processing_time or 0.0),
                ocr_engine=ocr_engine,
                uploaded_by=uploaded_by,
            )
        except Exception:
            doc_id = None

        if not doc_id:
            insert_q = """
                INSERT INTO ocr_documents
                (filename, file_path, extracted_text, confidence_score, processing_time, ocr_engine, uploaded_by, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                RETURNING id
            """
            res = DatabaseOperations.execute_query(
                insert_q,
                (filename, file_path, sanitized_text, confidence_score, processing_time, ocr_engine, uploaded_by),
                fetch=True,
            )
            doc_id = int(res[0]["id"]) if res else None

        if not doc_id:
            return {"success": False, "message": "Failed to save OCR document."}

        # 2) create bills row (best-effort)
        bill_id = None
        try:
            raw_lines_json = json.dumps([ln for ln in lines])
            cleaned_merchant_name = merchant if merchant else (merchant_name or None)
            bill_insert_q = """
                INSERT INTO bills (merchant_id, merchant_name, bill_date, total_amount, raw_text, uploaded_by, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                RETURNING id
            """
            resb = DatabaseOperations.execute_query(
                bill_insert_q,
                (merchant_id, cleaned_merchant_name, detected_date, amount, raw_lines_json, uploaded_by),
                fetch=True,
            )
            if resb:
                bill_id = int(resb[0].get("id"))
        except Exception:
            bill_id = None

        # 3) update ocr_documents structured fields (amount, bill_date, merchant_id) — ignore errors
        try:
            upd_parts = []
            upd_params = []
            if amount is not None:
                upd_parts.append("amount = %s")
                upd_params.append(amount)
            if detected_date:
                upd_parts.append("bill_date = %s")
                upd_params.append(detected_date)
            # merchant linking attempt
            merchant_row_id = merchant_id
            if merchant:
                try:
                    r = DatabaseOperations.execute_query(
                        "SELECT id FROM merchants WHERE LOWER(name) = LOWER(%s) LIMIT 1", (merchant,), fetch=True
                    )
                    if r:
                        merchant_row_id = int(r[0]["id"])
                    else:
                        DatabaseOperations.execute_query(
                            "INSERT INTO merchants (name, created_at) VALUES (%s, NOW())", (merchant,), fetch=False
                        )
                        r2 = DatabaseOperations.execute_query(
                            "SELECT id FROM merchants WHERE LOWER(name) = LOWER(%s) LIMIT 1", (merchant,), fetch=True
                        )
                        if r2:
                            merchant_row_id = int(r2[0]["id"])
                except Exception:
                    merchant_row_id = merchant_row_id
            if merchant_row_id:
                upd_parts.append("merchant_id = %s")
                upd_params.append(merchant_row_id)

            if upd_parts:
                upd_q = "UPDATE ocr_documents SET " + ", ".join(upd_parts) + " WHERE id = %s"
                upd_params.append(doc_id)
                try:
                    DatabaseOperations.execute_query(upd_q, tuple(upd_params), fetch=False)
                except Exception:
                    # likely merchant_id column missing — ignore
                    pass
        except Exception:
            pass

        # 4) insert parsed items into bill_items using bill_id
        items_saved = 0
        if parsed_items and bill_id:
            for it in parsed_items:
                desc = it.get("description") or it.get("name") or ""
                qty = it.get("quantity") or it.get("qty") or None
                unit_price = it.get("unit_price") or it.get("price") or None
                line_total = it.get("line_total") or it.get("total") or None
                raw_line = it.get("raw_line") or None
                try:
                    DatabaseOperations.execute_query(
                        "INSERT INTO bill_items (bill_id, product_name, qty, unit_price, line_total, raw_line, created_at) VALUES (%s, %s, %s, %s, %s, %s, NOW())",
                        (bill_id, desc, qty, unit_price, line_total, raw_line),
                        fetch=False,
                    )
                    items_saved += 1
                except Exception:
                    continue

        # 5) save document_categories metadata
        metadata = {
            "merchant": merchant,
            "merchant_id": merchant_row_id if 'merchant_row_id' in locals() else merchant_id,
            "bill_date": detected_date,
            "total_amount": amount,
            "payment_app": payment_app,
            "payment_mode": payment_mode,
            "direction": direction,
            "items_saved": items_saved,
            "uploaded_by": uploaded_by,
            "saved_to_bills": bool(bill_id),
            "saved_to_ocr_documents": True
        }
        try:
            DatabaseOperations.insert_document_category(document_id=doc_id, category="Uncategorized", confidence=0.0, metadata=metadata)
        except Exception:
            try:
                DatabaseOperations.execute_query(
                    "INSERT INTO document_categories (document_id, category, confidence, metadata, created_at) VALUES (%s, %s, %s, %s, NOW())",
                    (doc_id, "Uncategorized", 0.0, json.dumps(metadata)),
                    fetch=False,
                )
            except Exception:
                pass

        return {
            "success": True,
            "document_id": doc_id,
            "bill_id": bill_id,
            "items_saved": items_saved,
            "parsed": {
                "merchant": merchant,
                "merchant_id": merchant_row_id if 'merchant_row_id' in locals() else None,
                "amount": amount,
                "bill_date": detected_date,
                "payment_app": payment_app,
                "payment_mode": payment_mode,
                "direction": direction,
                "items_count": len(parsed_items),
            },
            "message": "Saved OCR document and (when available) created bills row + items."
        }

    except Exception as e:
        return {"success": False, "message": f"Exception in save_bill_and_items: {e}"}
