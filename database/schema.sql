-- ChatFinance-AI Database Schema
-- HYBRID Learning System with Categories

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- OCR Documents table
CREATE TABLE IF NOT EXISTS ocr_documents (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_path TEXT,
    extracted_text TEXT,
    confidence_score DECIMAL(5, 2),
    processing_time DECIMAL(8, 2),
    ocr_engine VARCHAR(50),
    uploaded_by INTEGER REFERENCES users(id),
    payment_status VARCHAR(20) DEFAULT 'unpaid',
    payment_date TIMESTAMP,
    due_date DATE,
    reminder_date DATE,
    reminder_sent BOOLEAN DEFAULT FALSE,
    amount DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Document Categories table (User's custom categories)
CREATE TABLE IF NOT EXISTS document_categories (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES ocr_documents(id) ON DELETE CASCADE,
    category VARCHAR(100) NOT NULL,
    confidence DECIMAL(5, 2),
    metadata JSONB,
    verified BOOLEAN DEFAULT FALSE,
    verified_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit Log table
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    action VARCHAR(100) NOT NULL,
    table_name VARCHAR(50),
    record_id INTEGER,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_ocr_uploaded_by ON ocr_documents(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_ocr_created_at ON ocr_documents(created_at);
CREATE INDEX IF NOT EXISTS idx_doc_cat_document_id ON document_categories(document_id);
CREATE INDEX IF NOT EXISTS idx_doc_cat_category ON document_categories(category);
CREATE INDEX IF NOT EXISTS idx_doc_cat_metadata ON document_categories USING GIN (metadata);

