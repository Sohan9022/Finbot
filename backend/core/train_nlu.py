# backend/core/train_nlu.py
"""
Train script for local NLU.
Saves model to backend/models/nlu_pipeline.joblib
"""

from nlu_classifier import train_and_save

# Expanded training dataset: many paraphrases for each intent.
examples = [
    # -----------------------------
    # Expense recording (varied forms)
    # -----------------------------
    ("Spent 499 on dining at Domino's", "expense_recording"),
    ("Paid 150 for lunch", "expense_recording"),
    ("Bought groceries for 320 at Dmart", "expense_recording"),
    ("I paid 200 for petrol", "expense_recording"),
    ("Paid ₹350 for dinner", "expense_recording"),
    ("Just spent 120 on coffee", "expense_recording"),
    ("I bought a new t-shirt for 999", "expense_recording"),
    ("Paid rent 12000", "expense_recording"),
    ("I paid electricity bill of 1800", "expense_recording"),
    ("Book taxi for 230 charged", "expense_recording"),

    # -----------------------------
    # Saving recording
    # -----------------------------
    ("Saved 200 today", "saving_recording"),
    ("Put aside 1000", "saving_recording"),
    ("I set aside 500 this month", "saving_recording"),
    ("Transferred 2000 to savings", "saving_recording"),
    ("Added 300 to my emergency fund", "saving_recording"),

    # -----------------------------
    # Income recording
    # -----------------------------
    ("I got paid 15000 salary", "income_recording"),
    ("Received payment of 5000 from client", "income_recording"),
    ("Got paid 3000 for freelancing", "income_recording"),
    ("Income of 25000 credited", "income_recording"),

    # -----------------------------
    # Spending queries (category/time)
    # -----------------------------
    ("How much did I spend on food this month", "spending_query"),
    ("Show my spending on groceries", "spending_query"),
    ("What did I spend on fuel last month", "spending_query"),
    ("How much did I spend on dining this week", "spending_query"),
    ("Show me my telecom bills this year", "spending_query"),
    ("How much have I spent on shopping", "spending_query"),
    ("Total spent on utilities", "spending_query"),
    ("Spending on subscriptions this month", "spending_query"),

    # -----------------------------
    # Product frequency queries
    # -----------------------------
    ("Which brand of milk did I buy most frequently", "product_frequency_query"),
    ("How many times did I buy milk", "product_frequency_query"),
    ("Which company milk I bought most frequently", "product_frequency_query"),
    ("Which products did I buy the most", "product_frequency_query"),
    ("Most products I bought", "product_frequency_query"),
    ("Which item do I buy repeatedly", "product_frequency_query"),
    ("What product shows up most in my bills", "product_frequency_query"),
    ("Which product do I purchase most often", "product_frequency_query"),
    ("How often do I buy bread", "product_frequency_query"),
    ("Count of times I purchased milk", "product_frequency_query"),

    # -----------------------------
    # Product price / most expensive items
    # -----------------------------
    ("Most expensive items I bought", "product_price_query"),
    ("Which were my top 5 expensive purchases", "product_price_query"),
    ("Show my highest price purchases", "product_price_query"),
    ("What are my priciest items", "product_price_query"),

    # -----------------------------
    # Top expenses
    # -----------------------------
    ("Show top expenses", "top_expenses_query"),
    ("Top 10 expenses", "top_expenses_query"),
    ("Which categories am I spending most on", "top_expenses_query"),
    ("List my biggest expenses", "top_expenses_query"),

    # -----------------------------
    # Recent transactions
    # -----------------------------
    ("Show recent transactions", "recent_transactions_query"),
    ("Latest transactions", "recent_transactions_query"),
    ("What did I spend yesterday", "recent_transactions_query"),
    ("Show my last 10 transactions", "recent_transactions_query"),

    # -----------------------------
    # Category list
    # -----------------------------
    ("What are my categories", "category_list_query"),
    ("List my categories", "category_list_query"),
    ("Show me categories", "category_list_query"),

    # -----------------------------
    # Analysis / insights
    # -----------------------------
    ("Analyze my spending", "analysis_query"),
    ("Give me insights", "analysis_query"),
    ("Any trends in my spending", "analysis_query"),
    ("Provide financial insights", "analysis_query"),
    ("Compare spending month over month", "analysis_query"),

    # -----------------------------
    # Help & general
    # -----------------------------
    ("What can you do", "help"),
    ("Help", "help"),
    ("How do I use you", "help"),
    ("Show me commands", "help"),

    # -----------------------------
    # Unknown / chit-chat examples
    # -----------------------------
    ("hello", "unknown"),
    ("hi", "unknown"),
    ("thanks", "unknown"),
    ("ok", "unknown"),
    ("good morning", "unknown"),
    ("bye", "unknown"),

    # -----------------------------
    # Paraphrases & corner cases (to generalize)
    # -----------------------------
    ("I spent a lot on food last month, show me details", "spending_query"),
    ("Which grocery items I purchase most often", "product_frequency_query"),
    ("Which brand do I buy more, Amul or Aavin", "product_frequency_query"),
    ("Show items with highest total spend", "product_price_query"),
    ("What was my largest single expense", "product_price_query"),
    ("How many times did I go to Starbucks", "product_frequency_query"),
    ("List purchases made at Dmart", "spending_query"),
    ("Give me a breakdown of my expenses", "analysis_query"),
    ("What are my recurring payments", "analysis_query"),
    ("Show my subscription costs", "spending_query"),
    ("Did I spend more this month than last month", "analysis_query"),
    ("Which days do I spend the most", "analysis_query"),
    ("How many times I shopped for clothes", "product_frequency_query"),
    ("Which store I visited most often", "product_frequency_query"),

    # -----------------------------
    # More varied recording forms to improve detection
    # -----------------------------
    ("Just bought coffee for 75", "expense_recording"),
    ("Paid ₹350 for groceries at Reliance", "expense_recording"),
    ("Transfer 2000 to savings account", "saving_recording"),
    ("Salary credited 45000", "income_recording"),
    ("Got a payment of 2500 from Upwork", "income_recording"),
    ("Saved 50 rupees today", "saving_recording"),
    ("I returned an item and got refund of 100", "income_recording"),

    # -----------------------------
    # Edge case paraphrases
    # -----------------------------
    ("Which item recurs most in my bills", "product_frequency_query"),
    ("Which vendor supplies me most frequently", "product_frequency_query"),
    ("Most bought brand", "product_frequency_query"),
    ("What have I spent on petrol so far this year", "spending_query"),
    ("Total electricity payments this year", "spending_query"),
    ("Top spends in November", "top_expenses_query"),
    ("Show my top categories in last 6 months", "analysis_query"),
]

if __name__ == "__main__":
    print("[TRAIN] Examples:", len(examples))
    train_and_save(examples)
    print("[TRAIN] Done.")
