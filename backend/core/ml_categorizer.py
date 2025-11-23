# """
# ML Categorizer - Works with Hybrid Learning System
# """

# import json
# import os
# from typing import Dict, Any
# from category_learner import HybridCategoryLearner

# class BillCategorizer:
#     """Smart categorizer using hybrid system"""
    
#     def __init__(self, user_id: int):
#         self.user_id = user_id
#         self.learner = HybridCategoryLearner(user_id)
    
#     def categorize(self, text: str, merchant: str = None, amount: float = None) -> Dict[str, Any]:
#         """
#         Categorize bill using hybrid learning
#         Returns intelligent suggestions based on user history + base knowledge
#         """
        
#         if not text and not merchant:
#             return {
#                 'suggestions': [],
#                 'confidence': 0.0,
#                 'method': 'no_data',
#                 'all_user_categories': self.learner.get_all_user_categories(),
#                 'suggested_defaults': self.learner.get_suggested_categories()
#             }
        
#         # Get AI suggestions (hybrid approach)
#         suggestions = self.learner.suggest_category(
#             text=text,
#             merchant=merchant,
#             amount=amount
#         )
        
#         if suggestions:
#             top_category, top_confidence = suggestions[0]
            
#             return {
#                 'suggestions': suggestions,
#                 'top_category': top_category,
#                 'confidence': top_confidence,
#                 'method': 'hybrid_intelligence',
#                 'all_user_categories': self.learner.get_all_user_categories(),
#                 'suggested_defaults': self.learner.get_suggested_categories()
#             }
        
#         return {
#             'suggestions': [],
#             'confidence': 0.0,
#             'method': 'no_match',
#             'all_user_categories': self.learner.get_all_user_categories(),
#             'suggested_defaults': self.learner.get_suggested_categories()
#         }
    
#     def learn_from_user_input(self, category: str, text: str, 
#                              merchant: str = None, amount: float = None, 
#                              items: list = None) -> bool:
#         """Learn from user's choice"""
#         return self.learner.learn_from_input(
#             category=category,
#             text=text,
#             merchant=merchant,
#             amount=amount,
#             items=items
#         )
    
#     def get_user_categories(self) -> list:
#         """Get all user's categories"""
#         return self.learner.get_all_user_categories()
    
#     def get_suggested_categories(self) -> list:
#         """Get suggested default categories"""
#         return self.learner.get_suggested_categories()
    
#     def get_category_stats(self) -> Dict:
#         """Get category statistics"""
#         return self.learner.get_category_stats()
"""
ML Categorizer - Works with Hybrid Learning System
Cleaned & optimized for production use
"""

from typing import Dict, Any, List, Optional
from category_learner import HybridCategoryLearner


class BillCategorizer:
    """
    Smart categorizer using hybrid learning system:
    - Matches text + merchant + amount
    - Considers user history + base knowledge
    - Returns ranked category suggestions
    """

    def __init__(self, user_id: int):
        self.user_id = int(user_id)
        self.learner = HybridCategoryLearner(self.user_id)

    # -------------------------------------------------------
    # PRIMARY CATEGORY SUGGESTION METHOD
    # -------------------------------------------------------
    def categorize(
        self,
        text: Optional[str],
        merchant: Optional[str] = None,
        amount: Optional[float] = None
    ) -> Dict[str, Any]:

        text = text or ""

        # No useful data → return defaults
        if not text.strip() and not merchant:
            return {
                "suggestions": [],
                "top_category": None,
                "confidence": 0.0,
                "method": "no_data",
                "all_user_categories": self.get_user_categories(),
                "suggested_defaults": self.get_suggested_categories()
            }

        # Ask hybrid learner for category suggestions
        suggestions = self.learner.suggest_category(
            text=text,
            merchant=merchant,
            amount=amount
        )

        # If suggestions exist
        if suggestions:
            top_category, top_conf = suggestions[0]
            return {
                "suggestions": suggestions,
                "top_category": top_category,
                "confidence": float(top_conf),
                "method": "hybrid_intelligence",
                "all_user_categories": self.get_user_categories(),
                "suggested_defaults": self.get_suggested_categories()
            }

        # Fallback if no match found
        return {
            "suggestions": [],
            "top_category": None,
            "confidence": 0.0,
            "method": "no_match",
            "all_user_categories": self.get_user_categories(),
            "suggested_defaults": self.get_suggested_categories()
        }

    # -------------------------------------------------------
    # LEARNING FROM USER INPUT
    # -------------------------------------------------------
    def learn_from_user_input(
        self,
        category: str,
        text: str,
        merchant: Optional[str] = None,
        amount: Optional[float] = None,
        items: Optional[List[str]] = None
    ) -> bool:
        """
        Record user feedback to train the hybrid categorizer.
        """
        return self.learner.learn_from_input(
            category=category,
            text=text,
            merchant=merchant,
            amount=amount,
            items=items
        )

    # -------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------
    def get_user_categories(self) -> List[str]:
        """Return all user-learned categories."""
        return self.learner.get_all_user_categories()

    def get_suggested_categories(self) -> List[str]:
        """Return AI-suggested default categories."""
        return self.learner.get_suggested_categories()

    def get_category_stats(self) -> Dict[str, Any]:
        """Return aggregated user category stats."""
        return self.learner.get_category_stats()
