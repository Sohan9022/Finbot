"""
Hybrid Category Learner
Learns categories from:
- OCR text
- Merchant names
- User selections
- Amount patterns
- Base keywords

Used by:
- BillCategorizer
- ConversationalFinancialAssistant
- Bills API
"""

from typing import List, Dict, Optional, Tuple
import json
import os


# ------------------------------------------------------------
# BASE KNOWLEDGE (default categories + keywords)
# ------------------------------------------------------------
BASE_CATEGORY_KNOWLEDGE = {
    "Food": ["food", "restaurant", "dining", "meal", "pizza", "burger", "cafe", "swiggy", "zomato"],
    "Groceries": ["grocery", "supermarket", "dmart", "market", "mart", "provision"],
    "Fuel": ["petrol", "diesel", "fuel", "hp", "ioc", "bpcl"],
    "Shopping": ["shopping", "clothes", "fashion", "store", "mall", "lifestyle", "myntra", "ajio"],
    "Bills": ["electricity", "bill", "water", "postpaid", "prepaid", "mobile", "broadband", "wifi"],
    "Health": ["medical", "chemist", "pharmacy", "hospital", "clinic", "medicine"],
    "Travel": ["ola", "uber", "bus", "train", "flight", "travel"],
    "Entertainment": ["movie", "cinema", "pvr", "inox", "entertainment"],
    "Subscriptions": ["subscription", "netflix", "amazon prime", "spotify"],
    "Others": []
}


# ------------------------------------------------------------
# Hybrid Learner Class
# ------------------------------------------------------------
class HybridCategoryLearner:

    def __init__(self, user_id: int):
        self.user_id = int(user_id)
        self.model_dir = "models"
        os.makedirs(self.model_dir, exist_ok=True)

        self.model_file = os.path.join(self.model_dir, f"user_{self.user_id}_categories.json")
        self.user_memory = self._load_user_memory()

    # --------------------------------------------------------
    # LOAD + SAVE USER LEARNINGS
    # --------------------------------------------------------
    def _load_user_memory(self) -> Dict:
        if os.path.exists(self.model_file):
            try:
                with open(self.model_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_user_memory(self):
        try:
            with open(self.model_file, "w", encoding="utf-8") as f:
                json.dump(self.user_memory, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # --------------------------------------------------------
    # PUBLIC METHODS
    # --------------------------------------------------------
    def learn_from_input(
        self,
        category: str,
        text: Optional[str] = None,
        merchant: Optional[str] = None,
        amount: Optional[float] = None,
        items: Optional[List[str]] = None
    ) -> bool:
        """
        Learn category mapping:
        - Merchant → category
        - Text keywords → category
        - Amount → category
        """

        category = category.title()

        if "merchant_map" not in self.user_memory:
            self.user_memory["merchant_map"] = {}

        if merchant:
            self.user_memory["merchant_map"][merchant.lower()] = category

        if "keyword_map" not in self.user_memory:
            self.user_memory["keyword_map"] = {}

        if text:
            for word in text.lower().split():
                if len(word) > 3:
                    self.user_memory["keyword_map"][word] = category

        if amount:
            if "amount_patterns" not in self.user_memory:
                self.user_memory["amount_patterns"] = {}
            bucket = int(amount // 100)
            self.user_memory["amount_patterns"][str(bucket)] = category

        self._save_user_memory()
        return True

    # --------------------------------------------------------
    # MAIN CATEGORY SUGGESTION
    # --------------------------------------------------------
    def suggest_category(
        self,
        text: Optional[str],
        merchant: Optional[str] = None,
        amount: Optional[float] = None
    ) -> List[Tuple[str, float]]:
        """
        Returns ranked list: [(category, score), ...]
        """

        scores: Dict[str, float] = {}

        # 1. Merchant match
        if merchant:
            cname = self.user_memory.get("merchant_map", {}).get(merchant.lower())
            if cname:
                scores[cname] = scores.get(cname, 0) + 5

        # 2. Keyword match
        if text:
            for word in text.lower().split():
                if word in self.user_memory.get("keyword_map", {}):
                    cname = self.user_memory["keyword_map"][word]
                    scores[cname] = scores.get(cname, 0) + 1

        # 3. Amount-based category
        if amount:
            bucket = str(int(amount // 100))
            amt_cat = self.user_memory.get("amount_patterns", {}).get(bucket)
            if amt_cat:
                scores[amt_cat] = scores.get(amt_cat, 0) + 1

        # 4. Base knowledge (keyword scanning)
        if text:
            low = text.lower()
            for cat, words in BASE_CATEGORY_KNOWLEDGE.items():
                for w in words:
                    if w in low:
                        scores[cat] = scores.get(cat, 0) + 1

        # 5. Merchant keyword fallback
        if merchant:
            low_merchant = merchant.lower()
            for cat, words in BASE_CATEGORY_KNOWLEDGE.items():
                for w in words:
                    if w in low_merchant:
                        scores[cat] = scores.get(cat, 0) + 2

        # Final ranking
        if not scores:
            return []

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [(cat, float(score * 20)) for cat, score in ranked]   # convert to 0–100 range

    # --------------------------------------------------------
    # GETTERS
    # --------------------------------------------------------
    def get_all_user_categories(self) -> List[str]:
        """Return categories learned by the user."""
        cats = set()

        for v in self.user_memory.get("merchant_map", {}).values():
            cats.add(v)

        for v in self.user_memory.get("keyword_map", {}).values():
            cats.add(v)

        for v in self.user_memory.get("amount_patterns", {}).values():
            cats.add(v)

        # ensure base categories present
        for base_cat in BASE_CATEGORY_KNOWLEDGE:
            cats.add(base_cat)

        return sorted(list(cats))

    def get_suggested_categories(self) -> List[str]:
        """Return useful default categories."""
        return sorted(list(BASE_CATEGORY_KNOWLEDGE.keys()))

    def get_category_stats(self) -> Dict:
        """Simple stats from user memory."""
        return {
            "merchant_links": len(self.user_memory.get("merchant_map", {})),
            "keyword_links": len(self.user_memory.get("keyword_map", {})),
            "amount_patterns": len(self.user_memory.get("amount_patterns", {})),
        }
