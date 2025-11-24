---

# # **ChatFinance-AI (FinBot)**

### *AI-Driven (Non-LLM), Rule-Based Personal Finance Assistant*

FinBot is a **conversational personal finance management system** built without LLMs.
It uses a **rule-based NLU engine**, **hybrid ML categorizer**, **OCR-powered receipt parsing**, **analytics engine**, and **RAG-based bill search** to give users a fully automated and intelligent financial experience.

---

# ## 🚀 **Features**

### **🔹 OCR-powered Bill & Receipt Extraction**

* Upload images/PDFs
* Extracts text, totals, dates, merchants
* Parses item lines (qty, unit price, total)
* Handles noisy, skewed, or low-quality bills

### **🔹 Hybrid Categorization System**

* TF-IDF + Logistic Regression classifier
* User-specific category learning
* Merchant → category mapping
* Keyword → category mapping
* Amount bucket learning
* Explainable, deterministic predictions

### **🔹 Rule-Based Conversational Assistant (NO LLMs Used)**

Natural-language commands like:

```
"Spent 250 on groceries"
"Paid 500 for petrol"
"What is my food spending this month?"
"Saved 300 today"
```

Assistant performs:

* Intent parsing
* Amount extraction
* Merchant detection
* Category inference
* Pending transaction completion
* Save transaction as bill or manual entry

### **🔹 Voice Input Support**

* Upload audio
* Speech-to-text conversion
* Automatically processed by conversational engine

### **🔹 Fully Itemized Bill Storage**

* Merchants
* Bills
* Bill items
* Inventory & history updates

### **🔹 Advanced Analytics**

* Daily, weekly, monthly spending
* Category breakdown
* Trends (increasing/decreasing)
* Month-over-month comparison
* Spending patterns (day-of-week, category frequency)
* Budget & insights engine

### **🔹 RAG-Based Bill Search**

Retrieve receipts using natural queries:

```
"Find Dmart bill"
"Show pizza receipt from February"
```

### **🔹 Secure Auth System**

* JWT login
* Hashed passwords
* Account management

### **🔹 Modular FastAPI Backend**

Routers:
`/api/auth`, `/api/chat`, `/api/bills`, `/api/analytics`, `/api/voice`


# ## 📂 **Project Structure**

```
backend/
├── api/
│   ├── auth.py
│   ├── bills.py
│   ├── chat.py
│   ├── voice.py
│   └── analytics.py
│
├── core/
│   ├── ocr_processor.py
│   ├── ocr_item_extractor.py
│   ├── conversational_assistant.py
│   ├── category_learner.py
│   ├── ml_hybrid_categorizer.py
│   ├── analytics_engine.py
│   ├── chat_service.py
│   ├── rag_engine.py
│   ├── config.py
│   └── database.py
│
├── sql/
│   └── schema.sql
│
└── main.py
```

---

# ## ⚙️ **Tech Stack**

| Layer        | Technologies                                    |
| ------------ | ----------------------------------------------- |
| Backend      | **FastAPI**, Python                             |
| Database     | **PostgreSQL**, psycopg2                        |
| OCR          | **Tesseract OCR**, OpenCV                       |
| ML           | **Scikit-learn (TF-IDF + Logistic Regression)** |
| Voice        | SpeechRecognition                               |
| Storage      | JSON-based learning models                      |
| Architecture | Modular, REST-based                             |

---

# ## 📦 **Installation & Setup**

### **1. Clone the repo**

```bash
git clone https://github.com/Sohan9022/Finbot.git
cd ChatFinance-AI/backend
```

### **2. Create a virtual environment**

```bash
python -m venv venv
source venv/bin/activate   # macOS/Linux
venv\Scripts\activate      # Windows
```

### **3. Install dependencies**

```bash
pip install -r requirements.txt
```

### **4. Configure environment variables**

Create `.env` file:

```
DATABASE_URL=postgresql://user:pass@localhost:5432/chatfinance_db
SECRET_KEY=your_secret
TESSERACT_PATH=/usr/bin/tesseract   # or Windows install path
```

### **5. Initialize database**

```bash
python -c "from core.database import DatabaseOperations; DatabaseOperations.initialize_database()"
```

### **6. Run server**

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

---

# ## 🧠 **Core Components Explained**

## **1️⃣ OCR Processor**

* Preprocessing: grayscale, threshold, denoise, deskew
* Extracts all text, lines, words, confidence scores
* Outputs structured bill text for item parser

## **2️⃣ Line Item Extractor**

* Regex-driven analyzers
* Detects:

  * Item names
  * Qty indicators (“pcs”, “nos”, “qty”)
  * Unit price
  * Line totals
* Identifies:

  * Merchant
  * Date
  * Total amount

## **3️⃣ Conversational Assistant (Rule-Based)**

Handles:

* "Spent X on Y"
* "Paid"
* "Saved"
* "Earned"
* "How much did I spend?"

Performs:

* Intent classification
* Regex-based amount extraction
* Merchant parsing
* Category inference
* Pending transaction confirmation

NO LLM used.

## **4️⃣ Hybrid ML Categorizer**

* TF-IDF vectorizer → Logistic Regression
* Combined with semantic learner
* Weighted fusion for final category

## **5️⃣ Analytics Engine**

Provides:

* Daily / Weekly / Monthly spending
* Category breakdown
* Trends (up/down)
* Month-over-month comparison
* Pattern detection (day of week, frequency)
* Insights generator

## **6️⃣ RAG Engine**

* Stores text from OCR
* Keyword-based retrieval
* Returns best-matching receipts

---

# ## 📡 **API Documentation (Summary)**

### **Auth**

```
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me
```

### **Bills**

```
POST /api/bills/upload
GET  /api/bills/list
GET  /api/bills/{id}
PUT  /api/bills/{id}
DELETE /api/bills/{id}
```

### **Chat**

```
POST /api/chat/message
GET  /api/chat/sessions
```

### **Analytics**

```
GET /api/analytics/dashboard
GET /api/analytics/category-breakdown
GET /api/analytics/daily
GET /api/analytics/weekly
GET /api/analytics/monthly
GET /api/analytics/spending-patterns
GET /api/analytics/insights
```

### **Voice**

```
POST /api/voice/transcribe
```

---

# ## 🧪 **Demo Commands**

```
“Spent 230 on groceries”
“How much did I spend this week?”
“Show my fuel spending”
“I saved 500 today”
“Add salary of 25000”
```

---

# ## 🛠️ **Future Enhancements**

* Budget recommendations
* Multi-user shared wallets
* Fraud/anomaly detection
* SMS parsing
* Live bank transaction sync
* Mobile app (React Native / Flutter)

---

# ## 🤝 **Contributing**

Pull requests are welcome!
Fork the repo, create a feature branch, and submit a PR.

---

# ## 📜 **License**

MIT License © 2025

---

# ## ⭐ **Support the Project**

If you find FinBot useful, consider starring ⭐ the repository!

