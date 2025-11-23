"""
Completeness Checker
Verifies all required files exist
"""

import os
from pathlib import Path

# Required files
REQUIRED_FILES = {
    'backend': [
        'api/main.py',
        'api/__init__.py',
        'api/routes/__init__.py',
        'api/routes/auth.py',
        'api/routes/bills.py',
        'api/routes/chat.py',
        'api/routes/analytics.py',
        'api/routes/voice.py',
        'core/__init__.py',
        'core/config.py',
        'core/database.py',
        'core/analytics_engine.py',
        'core/conversational_assistant.py',
        'core/ocr_processor.py',
        'core/category_learner.py',
        'core/ml_categorizer.py',
        'core/auth.py',
        'core/rag_engine.py',
        'requirements.txt',
        'Dockerfile',
        'railway.json',
        '.env.example',
    ],
    'frontend': [
        'src/components/Login.jsx',
        'src/components/Dashboard.jsx',
        'src/components/Sidebar.jsx',
        'src/components/UploadInvoice.jsx',
        'src/components/ViewInvoices.jsx',
        'src/components/Analytics.jsx',
        'src/components/ChatAssistant.jsx',
        'src/components/ShoppingAssistant.jsx',
        'src/components/VoiceInterface.jsx',
        'src/components/PaymentTracker.jsx',
        'src/components/UserProfile.jsx',
        'src/services/api.js',
        'src/App.jsx',
        'src/main.jsx',
        'src/index.css',
        'package.json',
        'vite.config.js',
        'tailwind.config.js',
        'postcss.config.js',
        'index.html',
        '.env.example',
    ],
    'database': [
        'schema.sql',
    ],
    'root': [
        '.gitignore',
        'README.md',
    ]
}

def check_files():
    """Check if all required files exist"""
    
    missing_files = []
    total_files = 0
    found_files = 0
    
    print("🔍 Checking Project Completeness...\n")
    
    for category, files in REQUIRED_FILES.items():
        print(f"📁 {category.upper()}:")
        
        base_path = Path(category) if category != 'root' else Path('.')
        
        for file in files:
            total_files += 1
            file_path = base_path / file
            
            if file_path.exists():
                print(f"  ✅ {file}")
                found_files += 1
            else:
                print(f"  ❌ {file} (MISSING)")
                missing_files.append(f"{category}/{file}")
        
        print()
    
    # Summary
    print("=" * 50)
    print(f"📊 SUMMARY:")
    print(f"Total Files Required: {total_files}")
    print(f"Files Found: {found_files}")
    print(f"Files Missing: {len(missing_files)}")
    print(f"Completion: {(found_files/total_files)*100:.1f}%")
    print("=" * 50)
    
    if missing_files:
        print("\n⚠️  Missing Files:")
        for file in missing_files:
            print(f"  - {file}")
        print("\n❌ Project is INCOMPLETE")
        return False
    else:
        print("\n✅ Project is 100% COMPLETE!")
        print("🚀 Ready to deploy!")
        return True

if __name__ == "__main__":
    check_files()
