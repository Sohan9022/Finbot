
"""
conversational_assistant_fixed.py

Corrected ConversationalFinancialAssistant (Version B - fixed)
- _extract_category_from_text is correctly a method inside the class
- product name extraction regex hardened to avoid timestamps/dates
- consistent, production-friendly helpers retained
- Designed to be a drop-in replacement for the version B you selected
"""

from __future__ import annotations

import re
import json
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Any

# External project modules (existing in your repo)
try:
    from core.ocr_item_extractor import save_bill_and_items  # saves bills and bill_items.
    from core.database import DatabaseOperations                        # DB helpers.
    from core.category_learner import HybridCategoryLearner, BASE_CATEGORY_KNOWLEDGE  # learner.
    from core.ml_hybrid_categorizer import MLHybridCategorizer           # ML+hybrid wrapper.
    # NLU imports (optional)
    from core.nlu_classifier import load_pipeline, predict_intent
except Exception:
    # Allow running in contexts where package imports may not resolve.
    save_bill_and_items = None
    DatabaseOperations = None
    HybridCategoryLearner = None
    BASE_CATEGORY_KNOWLEDGE = {}
    MLHybridCategorizer = None
    load_pipeline = lambda: None
    predict_intent = lambda text, pipeline=None: {"intent": "unknown", "confidence": 0.0}


class ConversationalFinancialAssistant:
    def __init__(self, user_id: int):
        self.user_id = int(user_id)
        # instantiate learner if available
        try:
            self.learner = HybridCategoryLearner(self.user_id)
        except Exception:
            self.learner = None
        self.conversation_state: Dict[str, dict] = {}  # pending_transaction etc.
        # load local NLU pipeline (if trained)
        try:
            self.nlu_pipeline = load_pipeline()
        except Exception:
            self.nlu_pipeline = None

    # ----------------------------
    # Utilities
    # ----------------------------
    def _now_ts(self) -> datetime:
        # timezone-aware (UTC)
        return datetime.now(timezone.utc)

    def _safe_json_load(self, text: Optional[str]) -> dict:
        if not text:
            return {}
        try:
            return json.loads(text)
        except Exception:
            return {}

    def _float_or_zero(self, value) -> float:
        try:
            return float(value or 0)
        except Exception:
            return 0.0

    # ----------------------------
    # Confidence & Explainability
    # ----------------------------
    def compute_confidence(self, intent: dict, resp: dict) -> float:
        if isinstance(resp, dict) and resp.get("confidence") is not None:
            try:
                return float(resp.get("confidence"))
            except Exception:
                pass

        amt = intent.get("amount")
        cat = intent.get("category")
        pending = intent.get("pending_data") or self.conversation_state.get("pending_transaction")

        if amt and cat:
            base = 0.9
        elif amt and not cat:
            base = 0.55
        elif pending:
            base = 0.45
        else:
            base = 0.3

        if intent.get("merchant"):
            base += 0.03

        try:
            if self.learner:
                suggestions = self.learner.suggest_category(text=intent.get("note", ""), merchant=intent.get("merchant"))
                if suggestions and isinstance(suggestions, (list, tuple)) and len(suggestions) > 0:
                    top_score = suggestions[0][1] if isinstance(suggestions[0], (list, tuple)) and len(suggestions[0]) > 1 else None
                    if top_score:
                        top = float(top_score)
                        if top > 1.5:
                            top = top / 100.0
                        base = max(base, min(0.95, top))
        except Exception:
            pass

        return min(1.0, max(0.0, float(base)))

    def _explain_decision(self, intent: dict, saved_doc_id: Optional[int] = None) -> str:
        parts: List[str] = []
        amt = intent.get("amount")
        merchant = intent.get("merchant")
        category = intent.get("category")

        if amt:
            try:
                parts.append(f"Amount detected: ₹{float(amt):,.2f} (via regex)")
            except Exception:
                parts.append("Amount detected")
        if merchant:
            parts.append(f"Merchant: {merchant} (pattern match)")
        if category:
            parts.append(f"Predicted category: {category} (learner)")
        else:
            parts.append("Category: not provided — asked user to confirm")

        if saved_doc_id:
            parts.append(f"Saved as id: {saved_doc_id}")

        parts.append("Learner updated with input (if user confirmed).")
        return " • ".join(parts)

    # ----------------------------
    # Intent parsing & weak NLU
    # ----------------------------
    def parse_intent(self, message: str) -> dict:
        if not message:
            return {"action": "unknown"}

        raw = message.strip()
        # fallback heuristics if pipeline not loaded
        if not getattr(self, "nlu_pipeline", None):
            low = raw.lower()
            if any(k in low for k in ["how", "what", "show", "list", "which", "most", "top", "recent", "summary", "analyze", "help"]):
                return {"action": "query", "note": raw}
            # detect save-like phrases
            if re.search(r"\b(spent|paid|bought|saved|earned|made)\b", low) or re.search(r"\b\d+\b", low):
                # treat as a save transaction
                intent = {"action": "save_transaction", "type": "expense", "note": raw}
                amt = self._extract_amount(raw)
                if amt:
                    intent["amount"] = amt
                m = self._extract_merchant(raw)
                if m:
                    intent["merchant"] = m
                c = self._extract_category_from_text(raw)
                if c:
                    intent["category"] = c
                return intent
            return {"action": "unknown", "note": raw}

        pred = predict_intent(raw, pipeline=self.nlu_pipeline)
        label = pred.get("intent", "unknown")
        conf = pred.get("confidence", 0.0)

        map_to_action = {
            "expense_recording": ("save_transaction", "expense"),
            "income_recording": ("save_transaction", "income"),
            "saving_recording": ("save_transaction", "saving"),
            "spending_query": ("query", None),
            "product_frequency_query": ("query", None),
            "product_price_query": ("query", None),
            "top_expenses_query": ("query", None),
            "recent_transactions_query": ("query", None),
            "category_list_query": ("query", None),
            "analysis_query": ("analyze", None),
            "help": ("help", None),
            "unknown": ("unknown", None),
        }

        action, typ = map_to_action.get(label, ("unknown", None))

        intent = {
            "action": action,
            "type": typ,
            "amount": None,
            "category": None,
            "merchant": None,
            "note": raw,
            "nlu_label": label,
            "nlu_confidence": conf
        }

        if action == "save_transaction":
            amt = self._extract_amount(raw)
            if amt:
                intent["amount"] = amt
            m = self._extract_merchant(raw)
            if m:
                intent["merchant"] = m
            cat = self._extract_category_from_text(raw)
            if cat:
                intent["category"] = cat

        return intent

    def _extract_amount(self, text: str) -> Optional[float]:
        patterns = [
            r"₹\s*([\d,]+(?:\.\d+)?)",
            r"Rs\.?\s*([\d,]+(?:\.\d+)?)",
            r"rs\.?\s*([\d,]+(?:\.\d+)?)",
            r"rupees?\s*([\d,]+(?:\.\d+)?)",
            r"([\d,]+(?:\.\d+)?)\s*(?:rs|rupees|₹)\b",
            r"\b(?:spent|paid|save|saved|earned|made)\s+([\d,]+(?:\.\d+)?)\b",
            r"\b([\d,]+(?:\.\d+)?)\b",
        ]
        for pat in patterns:
            m = re.search(pat, text, flags=re.IGNORECASE)
            if m:
                num = m.group(1).replace(",", "")
                try:
                    val = float(num)
                    if val > 0:
                        return val
                except Exception:
                    continue
        return None

    def _extract_merchant(self, text: str) -> Optional[str]:
        m = re.search(r"\b(?:at|from|in|on)\s+([A-Za-z0-9&\.\-\'\s]{2,60})", text, flags=re.IGNORECASE)
        if m:
            merchant = m.group(1).strip().strip(".,!?")
            merchant = re.split(r"\b(?:for|spent|paid|rs|rupees|₹)\b", merchant, flags=re.IGNORECASE)[0].strip()
            return merchant or None
        return None

    def _extract_category_from_text(self, text: str) -> Optional[str]:
        """
        Extract category using:
         1) user-specific categories
         2) base knowledge (keyword map)
         3) MLHybridCategorizer fallback
        """
        text_lower = (text or "").lower()

        try:
            user_categories = self.learner.get_all_user_categories() or [] if self.learner else []
        except Exception:
            user_categories = []

        # 1) user categories (exact word boundary)
        for cat in user_categories:
            if not cat:
                continue
            cat_lower = cat.lower()
            if re.search(rf"\b{re.escape(cat_lower)}\b", text_lower):
                return cat

        # 2) base knowledge fallback
        for group, keywords in (BASE_CATEGORY_KNOWLEDGE or {}).items():
            for kw in keywords:
                if re.search(rf"\b{re.escape(kw.lower())}\b", text_lower):
                    return group

        # 3) hybrid ML fallback
        try:
            if MLHybridCategorizer:
                hybrid_ml = MLHybridCategorizer(self.user_id)
                result = hybrid_ml.suggest(item=text, location="", payment_method="")
                final_cat = result.get("final_category")
                if final_cat:
                    return final_cat
        except Exception:
            pass

        return None

    # ----------------------------
    # Save / Pending transaction handling
    # ----------------------------
    def save_transaction(self, intent: dict) -> dict:
        try:
            amount = intent.get("amount")
            if not amount or float(amount) <= 0:
                return {"success": False, "message": "❌ Please specify a valid amount. Example: 'Spent 499 on dining'."}

            # If no category, create pending and suggest
            if not intent.get("category"):
                suggestions = []
                try:
                    if self.learner:
                        suggestions = self.learner.suggest_category(text=intent.get("note", ""), merchant=intent.get("merchant"), amount=amount) or []
                except Exception:
                    suggestions = []

                if not suggestions and MLHybridCategorizer:
                    try:
                        hybrid_ml = MLHybridCategorizer(self.user_id)
                        ml_result = hybrid_ml.suggest(item=intent.get("note", ""), location="", payment_method="")
                        if ml_result.get("final_category"):
                            suggestions = [(ml_result["final_category"], ml_result.get("final_score", 0.75))]
                    except Exception:
                        pass

                top_suggestions = [s[0] if isinstance(s, (list, tuple)) else s for s in suggestions[:3]]
                suggestion_text = ("💡 Suggestions: " + ", ".join(top_suggestions)) if top_suggestions else ""

                pending = {
                    "type": intent.get("type") or "expense",
                    "amount": float(amount),
                    "merchant": intent.get("merchant"),
                    "note": intent.get("note"),
                    "suggestions": top_suggestions,
                    "created_at": self._now_ts().isoformat(),
                }
                self.conversation_state["pending_transaction"] = pending
                confidence = self.compute_confidence(intent, {"pending": True})
                return {
                    "success": False,
                    "message": f"📝 I noted ₹{float(amount):,.2f}. Which category should I assign? {suggestion_text}",
                    "needs_info": "category",
                    "suggestions": top_suggestions,
                    "pending": True,
                    "confidence": confidence,
                    "explanation": self._explain_decision(intent, saved_doc_id=None),
                }

            # We have category → prefer save as itemized bill
            out = self._save_chat_as_bill(intent)

            # fallback to legacy save if saving bill fails
            if not out.get("success"):
                out = self._save_to_database(intent)

            # determine saved id (bill_id or transaction_id)
            saved_id = None
            if out.get("save_result"):
                saved_id = out["save_result"].get("bill_id")
            elif out.get("transaction_id"):
                saved_id = out.get("transaction_id")

            conf = self.compute_confidence(intent, out)
            explanation = out.get("explanation") or self._explain_decision(intent, saved_doc_id=saved_id)
            out.update({"confidence": conf, "explanation": explanation})
            return out

        except Exception as e:
            return {"success": False, "message": f"❌ Error saving transaction: {str(e)}"}

    def complete_pending_transaction(self, user_response: str, pending_data: dict) -> dict:
        reply = (user_response or "").strip()
        detected = self._extract_category_from_text(reply)

        if detected:
            category = detected
        else:
            try:
                if MLHybridCategorizer:
                    hybrid_ml = MLHybridCategorizer(self.user_id)
                    res = hybrid_ml.suggest(item=reply, location="", payment_method="")
                    category = res.get("final_category") or reply.title()
                else:
                    category = reply.title()
            except Exception:
                category = reply.title()

        pending_data["category"] = category
        # Clear pending
        self.conversation_state.pop("pending_transaction", None)

        intent = {
            "type": pending_data.get("type", "expense"),
            "amount": pending_data.get("amount"),
            "merchant": pending_data.get("merchant"),
            "category": category,
            "note": pending_data.get("note") or "",
        }
        return self._save_to_database(intent)

    def _save_to_database(self, intent: dict) -> dict:
        try:
            transaction_type = intent.get("type", "expense")
            amount = float(intent.get("amount") or 0)
            if amount <= 0:
                return {"success": False, "message": "❌ Invalid amount."}
            category = intent.get("category") or "Uncategorized"
            merchant = intent.get("merchant") or "Chat Entry"
            note = intent.get("note") or ""
            ts = self._now_ts()
            timestamp = ts.strftime("%Y%m%d_%H%M%S")
            filename = f"chat_{transaction_type}_{timestamp}.txt"
            extracted_text = f"[{transaction_type.upper()}] {note}"

            if DatabaseOperations:
                doc_id = DatabaseOperations.save_ocr_document(
                    filename=filename,
                    file_path=f"manual_entries/{self.user_id}/{filename}",
                    extracted_text=extracted_text,
                    confidence_score=100.0,
                    processing_time=0.0,
                    ocr_engine="conversational_chat",
                    uploaded_by=self.user_id,
                )
            else:
                doc_id = None

            if not doc_id:
                # If DB helper not present, emulate an id for downstream flow (non-persistent)
                try:
                    doc_id = int(datetime.utcnow().timestamp())
                except Exception:
                    doc_id = None

            # Update amount and transaction type on the document (best-effort)
            try:
                if DatabaseOperations and doc_id:
                    DatabaseOperations.execute_query(
                        "UPDATE ocr_documents SET amount = %s, payment_status = 'paid', transaction_type = %s WHERE id = %s",
                        (amount, transaction_type, doc_id),
                        fetch=False,
                    )
            except Exception:
                pass

            # Insert category metadata via helper
            metadata = {
                "category": category,
                "merchant": merchant,
                "transaction_type": transaction_type,
                "transaction_date": ts.isoformat(),
                "payment_status": "paid",
                "notes": note,
                "manual_entry": True,
                "conversation_input": True,
                "source": "chat",
            }
            try:
                if DatabaseOperations and doc_id:
                    DatabaseOperations.insert_document_category(document_id=doc_id, category=category, confidence=100.0, metadata=metadata)
            except Exception:
                # best-effort; ignore
                pass

            # Teach learner (best-effort)
            try:
                if self.learner:
                    self.learner.learn_from_input(category=category, text=note, merchant=merchant, amount=amount)
            except Exception:
                pass

            emoji = {"saving": "💰", "expense": "💸", "income": "💵"}.get(transaction_type, "✅")
            response = f"""{emoji} **Saved Successfully!**

**Type:** {transaction_type.title()}
**Amount:** ₹{amount:,.2f}
**Category:** {category}
"""
            if merchant and merchant != "Chat Entry":
                response += f"**From:** {merchant}\n"

            response += f"\n✨ **AI learned:** Next time you say '{merchant}', I'll suggest '{category}'!"

            return {"success": True, "message": response, "transaction_id": int(doc_id) if doc_id else None, "updated_categories": [category]}

        except Exception as e:
            return {"success": False, "message": f"❌ Error saving to DB: {str(e)}"}

    def _save_chat_as_bill(self, intent: dict) -> dict:
        try:
            amount = float(intent.get("amount") or 0)
            if amount <= 0:
                return {"success": False, "message": "❌ Invalid amount."}

            merchant = intent.get("merchant") or ""
            note = intent.get("note") or ""
            product_name = None

            # Improved pattern: avoid capturing time-like or date-like strings.
            m = re.search(r"(?:on|for)\s+([A-Za-z][A-Za-z0-9\.\s\-&]{2,50})", note, flags=re.IGNORECASE)
            if m:
                candidate = m.group(1).strip()
                # ignore if candidate looks like a timestamp or date
                if not re.search(r"\b\d{1,2}[:/-]\d{1,2}\b", candidate) and not re.search(r"\b(?:am|pm|AM|PM)\b", candidate):
                    product_name = candidate
            elif intent.get("category"):
                product_name = intent.get("category")
            else:
                product_name = merchant or "Item"

            parsed = {
                "merchant": merchant or "Chat Entry",
                "date": self._now_ts().date().isoformat(),
                "total": amount,
                "items": [
                    {
                        "name": (product_name.title() if product_name else "Item"),
                        "qty": 1.0,
                        "unit_price": amount,
                        "line_total": amount,
                        "raw_line": note
                    }
                ],
                "raw_lines": [note]
            }

            if save_bill_and_items:
                save_res = save_bill_and_items(self.user_id, parsed)
            else:
                save_res = {"bill_id": None, "error": "save_bill_and_items not available"}

            if not save_res or not save_res.get("bill_id"):
                return {"success": False, "message": f"Failed to save as bill: {save_res}", "save_result": save_res}

            bill_id = save_res.get("bill_id")

            # Mirror into ocr_documents so dashboards & summaries include this chat-created bill.
            try:
                filename = f"bill_{bill_id}.json"
                file_path = f"bills/{self.user_id}/{bill_id}.json"
                extracted_text = json.dumps(parsed)

                if DatabaseOperations:
                    doc_id = DatabaseOperations.save_ocr_document(
                        filename=filename,
                        file_path=file_path,
                        extracted_text=extracted_text,
                        confidence_score=100.0,
                        processing_time=0.0,
                        ocr_engine="chat_bill_sync",
                        uploaded_by=self.user_id,
                    )
                else:
                    doc_id = None

                if doc_id:
                    try:
                        if DatabaseOperations:
                            DatabaseOperations.execute_query(
                                "UPDATE ocr_documents SET amount = %s, payment_status = 'paid', transaction_type = %s WHERE id = %s",
                                (amount, intent.get("type", "expense"), doc_id),
                                fetch=False,
                            )
                    except Exception:
                        pass

                    category = intent.get("category") or "Uncategorized"
                    metadata = {
                        "merchant": merchant,
                        "bill_id": bill_id,
                        "notes": note,
                        "source": "chat_bill",
                        "transaction_type": intent.get("type", "expense"),
                        "transaction_date": self._now_ts().isoformat()
                    }
                    try:
                        if DatabaseOperations:
                            DatabaseOperations.insert_document_category(document_id=doc_id, category=category, confidence=100.0, metadata=metadata)
                    except Exception:
                        pass

                    try:
                        if self.learner:
                            self.learner.learn_from_input(category=category, text=note, merchant=merchant, amount=amount)
                    except Exception:
                        pass

                    save_res["mirrored_doc_id"] = doc_id

            except Exception as e:
                save_res["mirror_error"] = str(e)

            return {"success": True, "message": f"Saved as bill (id: {bill_id})", "save_result": save_res}

        except Exception as e:
            return {"success": False, "message": f"Error saving bill: {str(e)}"}

    # ----------------------------
    # Query handlers (selected subset)
    # ----------------------------
    def _query_items_sum(self, product_query: str, start: Optional[str] = None, end: Optional[str] = None) -> dict:
        q = """
            SELECT COALESCE(SUM(bi.qty), 0) as total_qty, COALESCE(SUM(bi.line_total), 0) as total_spent
            FROM bill_items bi
            LEFT JOIN bills b ON bi.bill_id = b.id
            WHERE b.uploaded_by = %s AND bi.product_name ILIKE %s
        """
        params: List[Any] = [self.user_id, f"%{product_query}%"]
        if start:
            q += " AND b.bill_date >= %s"
            params.append(start)
        if end:
            q += " AND b.bill_date <= %s"
            params.append(end)
        try:
            res = DatabaseOperations.execute_query(q, tuple(params)) or []
            if res:
                return res[0]
        except Exception:
            pass

        q2 = """
            SELECT COUNT(*) as total_qty, COALESCE(SUM(amount), 0) as total_spent
            FROM ocr_documents
            WHERE uploaded_by = %s AND extracted_text ILIKE %s
        """
        try:
            res2 = DatabaseOperations.execute_query(q2, (self.user_id, f"%{product_query}%")) or []
            return res2[0] if res2 else {"total_qty": 0, "total_spent": 0}
        except Exception:
            return {"total_qty": 0, "total_spent": 0}

    def _date_filter_for_query(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        t = (text or "").lower()
        now = self._now_ts()
        start = end = None
        if "today" in t:
            start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_dt = start_dt + timedelta(days=1)
            start, end = start_dt.isoformat(), end_dt.isoformat()
        elif "this month" in t:
            start_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if start_dt.month == 12:
                next_month = start_dt.replace(year=start_dt.year + 1, month=1)
            else:
                next_month = start_dt.replace(month=start_dt.month + 1)
            start, end = start_dt.isoformat(), next_month.isoformat()
        elif "last month" in t:
            first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if first_of_this_month.month == 1:
                first_of_last_month = first_of_this_month.replace(year=first_of_this_month.year - 1, month=12)
            else:
                first_of_last_month = first_of_this_month.replace(month=first_of_this_month.month - 1)
            start, end = first_of_last_month.isoformat(), first_of_this_month.isoformat()
        return start, end

    def handle_spending_query(self, question: str) -> dict:
        category = self._extract_category_from_text(question)
        start_iso, end_iso = self._date_filter_for_query(question)

        if category:
            query = """
                SELECT 
                    SUM(ocr.amount) as total,
                    COUNT(*) as count,
                    AVG(ocr.amount) as average
                FROM ocr_documents ocr
                LEFT JOIN document_categories dc ON ocr.id = dc.document_id
                WHERE ocr.uploaded_by = %s AND dc.category = %s AND ocr.transaction_type = 'expense'
            """
            params: List[Any] = [self.user_id, category]
            if start_iso and end_iso:
                query += " AND ocr.created_at >= %s AND ocr.created_at < %s"
                params += [start_iso, end_iso]

            result = DatabaseOperations.execute_query(query, tuple(params)) or []
            if result and result[0] and result[0].get("total"):
                total = self._float_or_zero(result[0].get("total"))
                count = int(result[0].get("count") or 0)
                avg = self._float_or_zero(result[0].get("average"))
                return {
                    "success": True,
                    "message": f"""💰 **{category} Spending:**\n\n**Total:** ₹{total:,.2f}\n**Transactions:** {count}\n**Average:** ₹{avg:,.2f} per transaction\n\n📊 You've spent ₹{total:,.2f} on {category}."""
                }
            else:
                return {"success": True, "message": f"No expense records found for **{category}**."}
        else:
            return self.get_total_summary()

    def handle_savings_query(self, question: str) -> dict:
        query = """
            SELECT SUM(amount) as total, COUNT(*) as count
            FROM ocr_documents
            WHERE uploaded_by = %s AND transaction_type = 'saving'
        """
        result = DatabaseOperations.execute_query(query, (self.user_id,)) or []
        if result and result[0] and result[0].get("total"):
            total = self._float_or_zero(result[0].get("total"))
            count = int(result[0].get("count") or 0)
            return {
                "success": True,
                "message": f"""💰 **Savings Summary:**\n\n**Total Saved:** ₹{total:,.2f}\n**Savings Events:** {count}\n\n🎯 Keep it up!"""
            }
        else:
            return {"success": True, "message": "No savings recorded yet. Try: 'Saved 200 today'."}

    def get_category_list(self) -> dict:
        try:
            categories = self.learner.get_all_user_categories() or [] if self.learner else []
        except Exception:
            categories = []
        try:
            stats = self.learner.get_category_stats() or {} if self.learner else {}
        except Exception:
            stats = {}

        if not categories:
            return {"success": True, "message": "No categories learned yet. Add some expenses or upload bills."}

        query = """
            SELECT 
                dc.category,
                COUNT(*) as count,
                SUM(ocr.amount) as total
            FROM ocr_documents ocr
            LEFT JOIN document_categories dc ON ocr.id = dc.document_id
            WHERE ocr.uploaded_by = %s AND dc.category IS NOT NULL
            GROUP BY dc.category
            ORDER BY total DESC
        """
        results = DatabaseOperations.execute_query(query, (self.user_id,)) or []
        message = f"📚 **Your Categories ({len(categories)}):**\n\n"

        if results:
            for row in results:
                cat = row.get("category") or "Uncategorized"
                count = int(row.get("count") or 0)
                total = self._float_or_zero(row.get("total"))
                message += f"• **{cat}**: ₹{total:,.0f} ({count} transactions)\n"

        if stats and isinstance(stats, dict) and stats.get("semantic_groups"):
            message += f"\n🎯 **AI Groupings:**\n"
            for group, cats in stats["semantic_groups"].items():
                message += f"• {group}: {', '.join(cats)}\n"

        return {"success": True, "message": message}

    def get_total_summary(self) -> dict:
        try:
            q1 = """
                SELECT transaction_type, COALESCE(SUM(amount),0) as total, COUNT(*) as count
                FROM ocr_documents
                WHERE uploaded_by = %s
                GROUP BY transaction_type
            """
            res1 = DatabaseOperations.execute_query(q1, (self.user_id,)) or []

            totals = {"expense": 0.0, "income": 0.0, "saving": 0.0}
            counts = {"expense": 0, "income": 0, "saving": 0}

            for row in res1:
                ttype = (row.get("transaction_type") or "").lower()
                total = self._float_or_zero(row.get("total"))
                count = int(row.get("count") or 0)
                if ttype in totals:
                    totals[ttype] += total
                    counts[ttype] += count

            try:
                q2 = """
                    SELECT COALESCE(SUM(total),0) as total
                    FROM bills
                    WHERE uploaded_by = %s
                """
                res2 = DatabaseOperations.execute_query(q2, (self.user_id,)) or []
                bill_total = float(res2[0].get("total") or 0) if res2 else 0
                totals["expense"] += bill_total
            except Exception:
                pass

            total_expense = totals["expense"]
            total_income = totals["income"]
            total_saving = totals["saving"]
            net_flow = total_income - total_expense

            if total_expense + total_income + total_saving == 0:
                return {"success": True, "message": "No financial data yet. Start by telling me: 'Spent 499 on dining'."}

            cat_query = """
                SELECT dc.category, SUM(ocr.amount) as total, COUNT(*) as count
                FROM ocr_documents ocr
                LEFT JOIN document_categories dc ON ocr.id = dc.document_id
                WHERE ocr.uploaded_by = %s AND dc.category IS NOT NULL AND ocr.transaction_type = 'expense'
                GROUP BY dc.category
                ORDER BY total DESC
                LIMIT 5
            """
            top_cats = DatabaseOperations.execute_query(cat_query, (self.user_id,)) or []

            message = f"""📊 **Complete Financial Summary:**\n\n**Total Expenses:** ₹{total_expense:,.2f}\n**Total Income:** ₹{total_income:,.2f}\n**Total Savings:** ₹{total_saving:,.2f}\n**Net Flow (Income - Expenses):** ₹{net_flow:,.2f}\n\n"""
            if top_cats:
                message += "**Top 5 Expense Categories:**\n"
                for i, row in enumerate(top_cats, 1):
                    cat = row.get("category") or "Uncategorized"
                    cat_total = self._float_or_zero(row.get("total"))
                    percentage = (cat_total / total_expense * 100) if total_expense else 0
                    message += f"{i}. **{cat}**: ₹{cat_total:,.0f} ({percentage:.1f}%)\n"

            return {"success": True, "message": message}

        except Exception as e:
            return {"success": False, "message": f"❌ Error building summary: {str(e)}"}

    def get_top_expenses(self) -> dict:
        query = """
            SELECT ocr.amount, dc.category, ocr.created_at, ocr.filename
            FROM ocr_documents ocr
            LEFT JOIN document_categories dc ON ocr.id = dc.document_id
            WHERE ocr.uploaded_by = %s
            ORDER BY ocr.amount DESC
            LIMIT 10
        """
        results = DatabaseOperations.execute_query(query, (self.user_id,)) or []
        if not results:
            return {"success": True, "message": "No expenses recorded yet."}

        message = "💸 **Top 10 Expenses:**\n\n"
        for i, row in enumerate(results, 1):
            amount = self._float_or_zero(row.get("amount"))
            cat = row.get("category") or "Uncategorized"
            created_at = row.get("created_at")
            try:
                if isinstance(created_at, str):
                    date_str = created_at.split("T")[0]
                else:
                    date_str = created_at.strftime("%Y-%m-%d")
            except Exception:
                date_str = "unknown date"
            message += f"{i}. ₹{amount:,.2f} - {cat} ({date_str})\n"
        return {"success": True, "message": message}

    def get_recent_transactions(self) -> dict:
        query = """
            SELECT ocr.amount, dc.category, ocr.created_at, dc.metadata
            FROM ocr_documents ocr
            LEFT JOIN document_categories dc ON ocr.id = dc.document_id
            WHERE ocr.uploaded_by = %s
            ORDER BY ocr.created_at DESC
            LIMIT 10
        """
        results = DatabaseOperations.execute_query(query, (self.user_id,)) or []
        if not results:
            return {"success": True, "message": "No transactions yet."}

        message = "📋 **Recent Transactions:**\n\n"
        for row in results:
            amount = self._float_or_zero(row.get("amount"))
            cat = row.get("category") or "Uncategorized"
            created_at = row.get("created_at")
            try:
                if isinstance(created_at, str):
                    date_str = datetime.fromisoformat(created_at).strftime("%b %d, %Y")
                else:
                    date_str = created_at.strftime("%b %d, %Y")
            except Exception:
                date_str = "unknown date"

            merchant = ""
            metadata = self._safe_json_load(row.get("metadata"))
            if metadata.get("merchant"):
                merchant = f" at {metadata.get('merchant')}"

            message += f"• ₹{amount:,.2f} - {cat}{merchant} ({date_str})\n"

        return {"success": True, "message": message}

    def smart_category_query(self, question: str) -> dict:
        category = self._extract_category_from_text(question)
        if category:
            return self.handle_spending_query(f"How much on {category}")
        return self.get_total_summary()

    # ----------------------------
    # Analysis & insights
    # ----------------------------
    def handle_analysis(self, request: str) -> dict:
        query = """
            SELECT dc.category, ocr.amount, ocr.created_at
            FROM ocr_documents ocr
            LEFT JOIN document_categories dc ON ocr.id = dc.document_id
            WHERE ocr.uploaded_by = %s AND dc.category IS NOT NULL
            ORDER BY ocr.created_at DESC
        """
        results = DatabaseOperations.execute_query(query, (self.user_id,)) or []
        if not results:
            return {"success": True, "message": "Not enough data for analysis yet."}

        category_totals = defaultdict(float)
        monthly_totals = defaultdict(float)
        for row in results:
            cat = row.get("category") or "Uncategorized"
            amount = self._float_or_zero(row.get("amount"))
            created_at = row.get("created_at")
            try:
                if isinstance(created_at, str):
                    month = created_at[:7]
                else:
                    month = created_at.strftime("%Y-%m")
            except Exception:
                month = "unknown"
            category_totals[cat] += amount
            monthly_totals[month] += amount

        total_spending = sum(category_totals.values())
        if total_spending == 0:
            return {"success": True, "message": "No spend data found for analysis."}

        top_category = max(category_totals.items(), key=lambda x: x[1])
        avg_monthly = sum(monthly_totals.values()) / (len(monthly_totals) or 1)

        message = f"""📈 **Financial Analysis & Insights:**\n\n**Total Analyzed:** ₹{total_spending:,.2f}\n**Top Spending Category:** {top_category[0]} (₹{top_category[1]:,.2f})\n**Average Monthly:** ₹{avg_monthly:,.2f}\n\n**Insights:**\n"""
        top_3 = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:3]
        for i, (cat, amount) in enumerate(top_3, 1):
            percentage = (amount / total_spending) * 100
            message += f"{i}. **{cat}**: {percentage:.1f}% of spending\n"

        message += f"\n💡 **Recommendations:**\n"
        if top_category[1] / total_spending > 0.4:
            message += f"• Consider reducing spending on {top_category[0]}\n"
        message += "• Track daily expenses for better insights\n"
        message += "• Set category-wise budgets\n"

        return {"success": True, "message": message}

def show_help(self) -> dict:
    try:
        user_categories = self.learner.get_all_user_categories() or [] if self.learner else []
    except Exception:
        user_categories = []

    categories_text = (
        f"\n**Your categories:** {', '.join(user_categories[:10])}"
        if user_categories else ""
    )

    return {
        "success": True,
        "message": f"""
**💬 What I Can Do:**

**💸 Track Expenses:**
• "Spent 499 on dining"
• "Bought coffee for 150 at Starbucks"
• "Paid 800 for electricity"

**💰 Log Savings:**
• "Saved 200 today"
• "Put aside 1000 this month"

**💵 Record Income:**
• "Made 5000 profit from freelancing"
• "Earned 10000 this month"

**❓ Ask Questions:**
• "How much did I spend on food?"
• "Show my top expenses"
• "Give me a summary"
• "What are my categories?"
• "Show recent transactions"

**📊 Get Analysis:**
• "Analyze my spending"
• "Give me insights"
• "Show trends"

Just talk naturally!{categories_text}
""",
    }


    # ----------------------------
    # Main handler
    # ----------------------------
    def handle_conversation(self, message: str) -> dict:
        if not message or not message.strip():
            return {"success": False, "message": "Please say something! 😊"}

        intent = self.parse_intent(message)
        act = intent.get("action")

        if act == "save_transaction":
            return self.save_transaction(intent)
        elif act == "complete_pending":
            pending = intent.get("pending_data")
            user_resp = intent.get("user_response")
            if not pending:
                return {"success": False, "message": "No pending transaction found."}
            return self.complete_pending_transaction(user_resp, pending)
        elif act == "query":
            return self.handle_query_with_intent(message, intent)
        elif act == "summary":
            return self.get_total_summary()
        elif act == "analyze":
            return self.handle_analysis(message)
        elif act == "help":
            return self.show_help()
        else:
            return {
                "success": True,
                "message": """I didn't quite understand that. Try one of these:

💸 "Spent 499 on dining"
💸 "Bought coffee for 150 at Starbucks"
❓ "How much did I spend on food?"
📊 "Give me a summary"
Type "help" for the full list of commands.
""",
            }

    def handle_query_with_intent(self, question: str, intent: dict) -> dict:
        q = (question or "").strip()
        q_lower = q.lower()
        nlu_label = intent.get("nlu_label")

        # product frequency
        if nlu_label == "product_frequency_query" or ("how many" in q_lower or "how often" in q_lower or ("most" in q_lower and "buy" in q_lower)):
            m = re.search(r"(?:buy|bought|purchase|purchased)\s+(?:of\s+)?([\w\s]+)", q_lower)
            prod = None
            if m:
                prod = m.group(1).strip()
                prod = re.split(r"\b(this|last|this month|today|yesterday|in|at|from)\b", prod)[0].strip()
            start, end = self._date_filter_for_query(q)
            if prod:
                res = self._query_items_sum(prod, start, end)
                qty = float(res.get("total_qty") or 0)
                spent = float(res.get("total_spent") or 0)
                return {"success": True, "message": f"You purchased *{prod}* {int(qty)} times (₹{spent:,.2f} total) in the selected period."}
            else:
                qsql = """
                    SELECT bi.product_name, COALESCE(SUM(bi.qty),0) as qty
                    FROM bill_items bi
                    LEFT JOIN bills b ON bi.bill_id = b.id
                    WHERE b.uploaded_by = %s
                    GROUP BY bi.product_name
                    ORDER BY qty DESC
                    LIMIT 10
                """
                results = DatabaseOperations.execute_query(qsql, (self.user_id,)) or []
                if results:
                    text = "Top products by quantity:\n" + "\n".join([f"{r.get('product_name')} - {int(r.get('qty'))}" for r in results])
                    return {"success": True, "message": text}
                return {"success": True, "message": "No product history found."}

        # product price query
        if nlu_label == "product_price_query" or any(tok in q_lower for tok in ["expensive", "priciest", "highest price", "highest cost"]):
            qsql = """
                SELECT bi.product_name, bi.line_total
                FROM bill_items bi
                LEFT JOIN bills b ON bi.bill_id = b.id
                WHERE b.uploaded_by = %s
                ORDER BY bi.line_total DESC
                LIMIT 10
            """
            results = DatabaseOperations.execute_query(qsql, (self.user_id,)) or []
            if results:
                text = "Most expensive items:\n" + "\n".join([f"{r.get('product_name')} - ₹{float(r.get('line_total')):,.2f}" for r in results])
                return {"success": True, "message": text}
            return self.get_top_expenses()

        # spending queries
        if nlu_label == "spending_query" or any(tok in q_lower for tok in ["spent", "spend", "spending", "how much on", "how much did i spend"]):
            return self.handle_spending_query(q)

        # top expenses
        if nlu_label == "top_expenses_query" or any(tok in q_lower for tok in ["top expenses", "top 10", "biggest expenses", "largest expenses"]):
            return self.get_top_expenses()

        # recent transactions
        if nlu_label == "recent_transactions_query" or any(tok in q_lower for tok in ["recent", "latest", "yesterday", "last"]):
            return self.get_recent_transactions()

        # categories
        if nlu_label == "category_list_query" or "category" in q_lower or "categories" in q_lower:
            return self.get_category_list()

        # analysis
        if nlu_label == "analysis_query" or any(tok in q_lower for tok in ["analyze", "insight", "trend", "compare", "pattern"]):
            return self.handle_analysis(q)

        # help
        if nlu_label == "help" or any(tok in q_lower for tok in ["help", "what can you do", "commands"]):
            return self.show_help()

        return self.smart_category_query(q)

# End of file
