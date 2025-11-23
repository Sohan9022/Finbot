# conversational_assistant.py
"""
Complete Conversational Financial Assistant (merged & cleaned)

- single canonical save_transaction (no duplicates)
- compute_confidence + _explain_decision kept
- pending transaction handling retained
- timezone-aware timestamps
- safe DB writes via DatabaseOperations
- returns consistent response structure for ChatService compatibility
"""

import re
import json
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Any
from core.ocr_item_extractor import save_bill_and_items  # add to imports

from core.database import DatabaseOperations
from core.category_learner import HybridCategoryLearner, BASE_CATEGORY_KNOWLEDGE
from core.ml_hybrid_categorizer import MLHybridCategorizer


class ConversationalFinancialAssistant:
    def __init__(self, user_id: int):
        self.user_id = int(user_id)
        self.learner = HybridCategoryLearner(self.user_id)
        # conversation_state can hold pending transactions etc.
        self.conversation_state: Dict[str, dict] = {}

    def _query_items_sum(self, product_query: str, start=None, end=None):
        """
        Returns total qty and spend for a product (supports partial match).
    """
        q = """
            SELECT SUM(bi.qty) as total_qty, SUM(bi.line_total) as total_spent
            FROM bill_items bi
            LEFT JOIN bills b ON bi.bill_id = b.id
            WHERE b.uploaded_by = %s AND bi.product_name ILIKE %s
            """
        params = [self.user_id, f"%{product_query}%"]
        if start:
            q += " AND b.bill_date >= %s"
            params.append(start)
        if end:
            q += " AND b.bill_date <= %s"
            params.append(end)
        res = DatabaseOperations.execute_query(q, tuple(params)) or []
        return res[0] if res else {"total_qty": 0, "total_spent": 0}

    
    

    # ----------------------------
    # Utilities
    # ----------------------------
    def _now_ts(self) -> datetime:
        # timezone-aware timestamp (UTC). Convert to local if needed before display.
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

    def compute_confidence(self, intent: dict, resp: dict) -> float:
        """
        Heuristic confidence (0..1).
        Uses amount, category, merchant, learner suggestions.
        """
        # if assistant already returned explicit confidence, use it
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
            suggestions = self.learner.suggest_category(text=intent.get("note", ""), merchant=intent.get("merchant"))
            if suggestions and isinstance(suggestions, (list, tuple)) and len(suggestions) > 0:
                top_score = suggestions[0][1] if isinstance(suggestions[0], (list, tuple)) and len(suggestions[0]) > 1 else None
                if top_score:
                    base = max(base, min(0.95, float(top_score)))
        except Exception:
            pass

        return min(1.0, max(0.0, float(base)))

    def _explain_decision(self, intent: dict, saved_doc_id: Optional[int] = None) -> str:
        """Short explainability text used by UI. Keep concise."""
        parts = []
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
            parts.append(f"Predicted category: {category} (user / learner knowledge)")
        else:
            parts.append("Category: not provided — asked user to confirm")

        if saved_doc_id:
            parts.append(f"Saved as document id: {saved_doc_id}")

        parts.append("Learner updated with input (if user confirmed).")
        return " • ".join(parts)

    # ----------------------------
    # Intent parsing & weak NLU
    # ----------------------------
    def parse_intent(self, message: str) -> dict:
        """
        Parse intent and extract fields.
        Uses original message (not lowercased) for currency regex so symbols aren't lost.
        """
        if not message:
            return {"action": "unknown"}

        raw = message.strip()
        message_lower = raw.lower()

        intent = {
            "action": None,
            "type": None,  # 'expense'|'income'|'saving'
            "amount": None,
            "category": None,
            "merchant": None,
            "note": raw,
        }

        # Action detection
        expense_words = ["spent", "spend", "bought", "purchased", "paid", "buy", "order", "ordered", "spent on"]
        saving_words = ["save", "saved", "saving", "put aside", "set aside"]
        income_words = ["profit", "earned", "made", "income", "received", "got paid", "salary", "paid me"]

        # Summaries / queries / analysis / help
        if any(w in message_lower for w in ["summary", "overview", "breakdown"]):
            intent["action"] = "summary"
            return intent

        if any(w in message_lower for w in ["analyze", "insight", "trend", "compare", "pattern"]):
            intent["action"] = "analyze"
            return intent

        if any(w in message_lower for w in ["help", "what can you do", "commands"]):
            intent["action"] = "help"
            return intent
        # Query detection (questions) — priority check
        query_phrases = ["how much", "how many", "show", "what", "tell me", "list", "where", "when", "which"]
        if any(phrase in message_lower for phrase in query_phrases):
            # treat as query — return immediately so questions aren't misclassified as saves
            intent["action"] = "query"
            return intent

        # If user replying to a pending transaction
        if "pending_transaction" in self.conversation_state:
            intent["action"] = "complete_pending"
            intent["pending_data"] = self.conversation_state["pending_transaction"]
            intent["user_response"] = raw
            return intent

        # Save actions
        if any(w in message_lower for w in expense_words):
            intent["action"] = "save_transaction"
            intent["type"] = "expense"
        elif any(w in message_lower for w in saving_words):
            intent["action"] = "save_transaction"
            intent["type"] = "saving"
        elif any(w in message_lower for w in income_words):
            intent["action"] = "save_transaction"
            intent["type"] = "income"
        else:
            # fallback if words exist or bare number
            if re.search(r"\b(spent|paid|bought|saved|earned)\b", message_lower) or re.search(r"\b\d+\b", message_lower):
                intent["action"] = "save_transaction"
                if "save" in message_lower or "saved" in message_lower:
                    intent["type"] = "saving"
                elif any(w in message_lower for w in income_words):
                    intent["type"] = "income"
                else:
                    intent["type"] = "expense"
            else:
                intent["action"] = "unknown"
                return intent

        # Extract amount using original text (keep currency symbols)
        amount = self._extract_amount(raw)
        if amount is not None:
            intent["amount"] = amount

        # Merchant extraction
        merchant = self._extract_merchant(raw)
        if merchant:
            intent["merchant"] = merchant

        # Category extraction with word boundaries
        cat = self._extract_category_from_text(raw)
        if cat:
            intent["category"] = cat

        return intent

    def _extract_amount(self, text: str) -> Optional[float]:
        # Try several amount patterns on original text (not lowercased)
        patterns = [
            r"₹\s*([\d,]+(?:\.\d+)?)",
            r"Rs\.?\s*([\d,]+(?:\.\d+)?)",
            r"rs\.?\s*([\d,]+(?:\.\d+)?)",
            r"rupees?\s*([\d,]+(?:\.\d+)?)",
            r"([\d,]+(?:\.\d+)?)\s*(?:rs|rupees|₹)\b",
            r"\b(?:spent|paid|save|saved|earned|made)\s+([\d,]+(?:\.\d+)?)\b",
            r"\b([\d,]+(?:\.\d+)?)\b",  # last resort: any bare number
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
        # Look for "at <merchant>" or "from <merchant>" or "in <merchant>" or "on <merchant>"
        m = re.search(r"\b(?:at|from|in|on)\s+([A-Za-z0-9&\.\-\'\s]{2,40})", text, flags=re.IGNORECASE)
        if m:
            merchant = m.group(1).strip().strip(".,!?")
            # Stop at common delimiters / prepositions
            merchant = re.split(r"\b(?:for|spent|paid|rs|rupees|₹)\b", merchant, flags=re.IGNORECASE)[0].strip()
            return merchant if merchant else None
        return None

def _extract_category_from_text(self, text: str) -> Optional[str]:
    """
    Extract category from natural language text using:
    1. User-defined categories (best)
    2. Base knowledge fallback
    3. Hybrid + MLHybridCategorizer (final fallback)
    """

    text_lower = text.lower()
    user_categories = self.learner.get_all_user_categories() or []

    # ----------------------------------------------------
    # 1. User-specific category detection
    # ----------------------------------------------------
    for cat in user_categories:
        cat_lower = cat.lower()
        if re.search(rf"\b{re.escape(cat_lower)}\b", text_lower):
            return cat

    # ----------------------------------------------------
    # 2. Base knowledge fallback
    # ----------------------------------------------------
    for group, keywords in BASE_CATEGORY_KNOWLEDGE.items():
        for kw in keywords:
            if re.search(rf"\b{re.escape(kw.lower())}\b", text_lower):
                return group

    # ----------------------------------------------------
    # 3. ML + Hybrid Combined (fallback)
    # ----------------------------------------------------
    try:
        hybrid_ml = MLHybridCategorizer(self.user_id)
        result = hybrid_ml.suggest(
            item=text,
            location="",
            payment_method=""
        )
        final_cat = result.get("final_category")
        if final_cat:
            return final_cat

    except Exception as e:
        print("MLHybridCategorizer error:", e)

    return None


    # ----------------------------
    # Save / Pending transaction handling (single, canonical)
    # ----------------------------
    def save_transaction(self, intent: dict) -> dict:
        """
        Save transaction from intent. If category missing, save pending and ask user.
        Return a dict with consistent keys:
        { success: bool, message: str, needs_info?: 'category', suggestions?: [...], pending?: bool,
          confidence?: float, explanation?: str, transaction_id?: int, updated_categories?: [...] }
        """
        try:
            amount = intent.get("amount")
            if not amount or amount <= 0:
                return {"success": False, "message": "❌ Please specify a valid amount. Example: 'Spent 499 on dining'."}

            # If category missing, ask for it and offer suggestions
            if not intent.get("category"):
                suggestions = []
                try:
                    suggestions = self.learner.suggest_category(text=intent.get("note", ""), merchant=intent.get("merchant"), amount=amount) or []
                except Exception:
                    suggestions = []

                
                if not suggestions:
                    try:
                        hybrid_ml = MLHybridCategorizer(self.user_id)
                        ml_result = hybrid_ml.suggest(
                            item=intent.get("note", ""),
                            location="",
                            payment_method=""
                        )
                        if ml_result.get("final_category"):
                            suggestions = [(ml_result["final_category"], 0.75)]
                    except Exception:
                        pass


                
                top_suggestions = [s[0] if isinstance(s, (list, tuple)) else s for s in suggestions[:3]]
                suggestion_text = ("💡 Suggestions: " + ", ".join(top_suggestions)) if top_suggestions else ""
                # store pending
                pending = {
                    "type": intent.get("type") or "expense",
                    "amount": amount,
                    "merchant": intent.get("merchant"),
                    "note": intent.get("note"),
                    "suggestions": top_suggestions,
                    "created_at": self._now_ts().isoformat(),
                }
                self.conversation_state["pending_transaction"] = pending
                confidence = self.compute_confidence(intent, {"pending": True})
                return {
                    "success": False,
                    "message": f"📝 I noted ₹{amount:,.2f}. Which category should I assign? {suggestion_text}",
                    "needs_info": "category",
                    "suggestions": top_suggestions,
                    "pending": True,
                    "confidence": confidence,
                    "explanation": self._explain_decision(intent, saved_doc_id=None),
                }

            # we have category → save as itemized bill
            out = self._save_chat_as_bill(intent)

            # fallback to legacy save if needed
            if not out.get("success"):
                out = self._save_to_database(intent)

      # determine saved id (new bills or legacy)
            saved_id = None
            if out.get("save_result"):
                saved_id = out["save_result"].get("bill_id")
            elif out.get("transaction_id"):
                saved_id = out["transaction_id"]
            
             # compute confidence
            conf = self.compute_confidence(intent, out)

      # explanation (uses bill_id when available)
            explanation = self._explain_decision(intent, saved_doc_id=saved_id)

            out.update({
         "confidence": conf,
         "explanation": explanation
      })

            return out


        except Exception as e:
            return {"success": False, "message": f"❌ Error saving transaction: {str(e)}"}

    def complete_pending_transaction(self, user_response: str, pending_data: dict) -> dict:
        """
        Complete pending transaction: user_response may be category name or 'merchant: name' style.
        We'll be permissive: try to detect a known category in the reply; otherwise treat reply as category string.
        """
        reply = (user_response or "").strip()
        detected = self._extract_category_from_text(reply) or None

        if detected:
            category = detected
        else:
    # try ML understanding of user's reply
            try:
                hybrid_ml = MLHybridCategorizer(self.user_id)
                res = hybrid_ml.suggest(
                    item=reply,
                    location="",
                    payment_method=""
        )
                if res.get("final_category"):
                    category = res["final_category"]
                else:
                    category = reply.title()
            except:
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
        """
        Save the transaction into DB using DatabaseOperations helpers.
        Returns dict with success/message/transaction_id/updated_categories.
        """
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

            doc_id = DatabaseOperations.save_ocr_document(
                filename=filename,
                file_path=f"manual_entries/{self.user_id}/{filename}",
                extracted_text=extracted_text,
                confidence_score=100,
                processing_time=0,
                ocr_engine="conversational_chat",
                uploaded_by=self.user_id,
            )
            if not doc_id:
                return {"success": False, "message": "❌ Failed to save document."}

            # Update amount, payment_status, and transaction_type on document
            DatabaseOperations.execute_query(
                "UPDATE ocr_documents SET amount = %s, payment_status = 'paid', transaction_type = %s WHERE id = %s",
                (amount, transaction_type, doc_id),
                fetch=False,
            )

            # Insert category metadata
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

            DatabaseOperations.execute_query(
                """
                INSERT INTO document_categories (document_id, category, confidence, metadata)
                VALUES (%s, %s, %s, %s)
                """,
                (doc_id, category, 100, json.dumps(metadata)),
                fetch=False,
            )

            # Teach the learner (best-effort)
            try:
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

            return {"success": True, "message": response, "transaction_id": doc_id, "updated_categories": [category]}

        except Exception as e:
            return {"success": False, "message": f"❌ Error saving to DB: {str(e)}"}

    
def _save_chat_as_bill(self, intent: dict) -> dict:
    """
    Convert a chat 'save_transaction' intent into a single-item bill and persist it.
    Returns the same dict shape as save_transaction currently expects.
    """
    try:
        amount = float(intent.get("amount") or 0)
        if amount <= 0:
            return {"success": False, "message": "❌ Invalid amount."}

        merchant = intent.get("merchant") or ""
        note = intent.get("note") or ""

        # Try to extract a short product name from note, fallback to category or 'Item'
        product_name = None
        # Example patterns: "spent 64 on milk", "bought milk for 64"
        m = re.search(r"(?:on|for)\s+([A-Za-z0-9\.\s\-&]{2,50})", note, flags=re.IGNORECASE)
        if m:
            product_name = m.group(1).strip()
        elif intent.get("category"):
            product_name = intent.get("category")
        else:
            # fallback: use merchant or generic
            product_name = merchant or "Item"

        parsed = {
            "merchant": merchant or "Chat Entry",
            "date": datetime.now().date().isoformat(),
            "total": amount,
            "items": [
                {
                    "name": product_name.title(),
                    "qty": 1.0,
                    "unit_price": amount,
                    "line_total": amount,
                    "raw_line": note
                }
            ],
            "raw_lines": [note]
        }

        save_res = save_bill_and_items(self.user_id, parsed)

        return {"success": True, "message": f"Saved as bill (id: {save_res.get('bill_id')})", "save_result": save_res}
    except Exception as e:
        return {"success": False, "message": f"Error saving bill: {str(e)}"}


    # ----------------------------
    # Query handlers
    # ----------------------------
    def handle_query(self, question: str) -> dict:
        q = (question or "").strip()
        q_lower = q.lower()

        # in handle_query or an extended router for chat:
        if "how many" in q_lower or "how much" in q_lower:
        # try product match
            m = re.search(r"how many ([\w\s]+) (?:did i|have i|were )", q_lower)
            if m:
                prod = m.group(1).strip()
      # use date filter
                start, end = self._date_filter_for_query(q)
                res = self._query_items_sum(prod, start, end)
                qty = float(res.get("total_qty") or 0)
                spent = float(res.get("total_spent") or 0)
                return {"success": True, "message": f"You purchased {qty} units of {prod} (₹{spent:,.2f} total) in the selected period."}

        # Specific category list
        if "category" in q_lower or "categories" in q_lower:
            return self.get_category_list()

        # Spending queries
        if any(tok in q_lower for tok in ["spent", "spend", "spending", "how much on", "how much did i spend"]):
            return self.handle_spending_query(q)

        # Savings queries
        if any(tok in q_lower for tok in ["saved", "saving", "savings"]):
            return self.handle_savings_query(q)

        # Top or most
        if "top" in q_lower or "most" in q_lower:
            return self.get_top_expenses()

        # Recent or latest
        if "recent" in q_lower or "latest" in q_lower:
            return self.get_recent_transactions()

        # Total/all/everything
        if "total" in q_lower or q_lower in ["give me a summary", "summary", "show me a summary"]:
            return self.get_total_summary()

        # Fallback: smart category query
        return self.smart_category_query(q)

    def _date_filter_for_query(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Return (start_iso, end_iso) or (None, None).
        Handles "today", "this month", "last month".
        """
        t = text.lower()
        now = self._now_ts()
        start = end = None

        if "today" in t:
            start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_dt = start_dt + timedelta(days=1)
            start, end = start_dt.isoformat(), end_dt.isoformat()
        elif "this month" in t or re.search(r"\bthis month\b", t):
            start_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # next month start:
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
        """
        If a category is mentioned, return category-specific spending; otherwise return total summary.
        Recognizes optional date filters (today, this month, last month).
        """
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
            params = [self.user_id, category]
            if start_iso and end_iso:
                query += " AND ocr.created_at >= %s AND ocr.created_at < %s"
                params += [start_iso, end_iso]

            result = DatabaseOperations.execute_query(query, tuple(params))
            if result and result[0] and result[0].get("total"):
                total = self._float_or_zero(result[0].get("total"))
                count = int(result[0].get("count") or 0)
                avg = self._float_or_zero(result[0].get("average"))
                return {
                    "success": True,
                    "message": f"""💰 **{category} Spending:**

**Total:** ₹{total:,.2f}
**Transactions:** {count}
**Average:** ₹{avg:,.2f} per transaction

📊 You've spent ₹{total:,.2f} on {category}."""
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
        result = DatabaseOperations.execute_query(query, (self.user_id,))
        if result and result[0] and result[0].get("total"):
            total = self._float_or_zero(result[0].get("total"))
            count = int(result[0].get("count") or 0)
            return {
                "success": True,
                "message": f"""💰 **Savings Summary:**

**Total Saved:** ₹{total:,.2f}
**Savings Events:** {count}

🎯 Keep it up!"""
            }
        else:
            return {"success": True, "message": "No savings recorded yet. Try: 'Saved 200 today'."}

    def get_category_list(self) -> dict:
        categories = self.learner.get_all_user_categories() or []
        stats = self.learner.get_category_stats() or {}

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
        results = DatabaseOperations.execute_query(query, (self.user_id,))
        message = f"📚 **Your Categories ({len(categories)}):**\n\n"

        if results:
            for row in results:
                cat = row.get("category") or "Uncategorized"
                count = int(row.get("count") or 0)
                total = self._float_or_zero(row.get("total"))
                message += f"• **{cat}**: ₹{total:,.0f} ({count} transactions)\n"

        if stats.get("semantic_groups"):
            message += f"\n🎯 **AI Groupings:**\n"
            for group, cats in stats["semantic_groups"].items():
                message += f"• {group}: {', '.join(cats)}\n"

        return {"success": True, "message": message}

    def get_total_summary(self) -> dict:
        """
        Return totals for expenses, income, savings, and net flow + top categories.
        """
        query = """
            SELECT transaction_type, SUM(amount) as total, COUNT(*) as count, AVG(amount) as average
            FROM ocr_documents
            WHERE uploaded_by = %s
            GROUP BY transaction_type
        """
        results = DatabaseOperations.execute_query(query, (self.user_id,))

        totals = {"expense": 0.0, "income": 0.0, "saving": 0.0}
        counts = {"expense": 0, "income": 0, "saving": 0}

        if results:
            for row in results:
                ttype = (row.get("transaction_type") or "").lower()
                total = self._float_or_zero(row.get("total"))
                count = int(row.get("count") or 0)
                if ttype in totals:
                    totals[ttype] = total
                    counts[ttype] = count

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
        top_cats = DatabaseOperations.execute_query(cat_query, (self.user_id,))

        message = f"""📊 **Complete Financial Summary:**

**Total Expenses:** ₹{total_expense:,.2f}
**Total Income:** ₹{total_income:,.2f}
**Total Savings:** ₹{total_saving:,.2f}
**Net Flow (Income - Expenses):** ₹{net_flow:,.2f}

"""
        if top_cats:
            message += "**Top 5 Expense Categories:**\n"
            for i, row in enumerate(top_cats, 1):
                cat = row.get("category") or "Uncategorized"
                cat_total = self._float_or_zero(row.get("total"))
                percentage = (cat_total / total_expense * 100) if total_expense else 0
                message += f"{i}. **{cat}**: ₹{cat_total:,.0f} ({percentage:.1f}%)\n"

        return {"success": True, "message": message}

    def get_top_expenses(self) -> dict:
        query = """
            SELECT ocr.amount, dc.category, ocr.created_at, ocr.filename
            FROM ocr_documents ocr
            LEFT JOIN document_categories dc ON ocr.id = dc.document_id
            WHERE ocr.uploaded_by = %s
            ORDER BY ocr.amount DESC
            LIMIT 10
        """
        results = DatabaseOperations.execute_query(query, (self.user_id,))
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
        results = DatabaseOperations.execute_query(query, (self.user_id,))
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
        results = DatabaseOperations.execute_query(query, (self.user_id,))
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

        message = f"""📈 **Financial Analysis & Insights:**

**Total Analyzed:** ₹{total_spending:,.2f}
**Top Spending Category:** {top_category[0]} (₹{top_category[1]:,.2f})
**Average Monthly:** ₹{avg_monthly:,.2f}

**Insights:**
"""
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

    # ----------------------------
    # Help
    # ----------------------------
    def show_help(self) -> dict:
        user_categories = self.learner.get_all_user_categories() or []
        categories_text = f"\n**Your categories:** {', '.join(user_categories[:10])}" if user_categories else ""
        return {
            "success": True,
            "message": f"""**💬 What I Can Do:**

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
            return self.handle_query(message)
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
