# """
# FastAPI Main Application - Complete Version
# Wraps your existing 18 Python files as REST API
# """

# from fastapi import FastAPI, Request
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import JSONResponse
# import sys
# import os
# import time

# # Add core to path
# sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# from core.config import settings
# from core.database import DatabaseOperations

# # Create FastAPI app
# app = FastAPI(
#     title=settings.PROJECT_NAME,
#     description="AI-powered financial management with hybrid learning",
#     version=settings.VERSION,
#     docs_url="/docs" if settings.DEBUG else None,
#     redoc_url="/redoc" if settings.DEBUG else None,
# )

# # CORS Middleware - UPDATED
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[
#         "http://localhost:3000",
#         "http://localhost:5173",
#         "https://chatfinance.vercel.app",
#         "https://chatfinance.railway.app",
#         "*"  # Allow all in development (remove in production)
#     ],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Request timing middleware
# @app.middleware("http")
# async def add_process_time_header(request: Request, call_next):
#     start_time = time.time()
#     response = await call_next(request)
#     process_time = time.time() - start_time
#     response.headers["X-Process-Time"] = str(process_time)
#     return response

# # Global exception handler
# @app.exception_handler(Exception)
# async def global_exception_handler(request: Request, exc: Exception):
#     return JSONResponse(
#         status_code=500,
#         content={
#             "success": False,
#             "error": str(exc),
#             "message": "Internal server error"
#         }
#     )

# # Startup event
# @app.on_event("startup")
# async def startup_event():
#     """Initialize application on startup"""
#     print(f"🚀 Starting {settings.PROJECT_NAME} v{settings.VERSION}")
#     print(f"📝 Environment: {settings.ENVIRONMENT}")
    
#     try:
#         # Initialize database
#         DatabaseOperations.initialize_database()
#         print("✅ Database initialized successfully")
#     except Exception as e:
#         print(f"⚠️ Database initialization warning: {e}")
#         # Don't fail startup if DB init has issues

# # Shutdown event
# @app.on_event("shutdown")
# async def shutdown_event():
#     """Cleanup on shutdown"""
#     print(f"👋 Shutting down {settings.PROJECT_NAME}")

# # Include routers
# from api.routes import auth, bills, chat, analytics, voice

# app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
# app.include_router(bills.router, prefix="/api/bills", tags=["Bills"])
# app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
# app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
# app.include_router(voice.router, prefix="/api/voice", tags=["Voice"])

# # Root endpoints
# @app.get("/")
# async def root():
#     """Root endpoint"""
#     return {
#         "message": f"{settings.PROJECT_NAME} API",
#         "version": settings.VERSION,
#         "status": "running",
#         "docs": "/docs" if settings.DEBUG else "Disabled in production"
#     }

# @app.get("/health")
# async def health_check():
#     """Health check endpoint for monitoring"""
#     return {
#         "status": "healthy",
#         "timestamp": time.time(),
#         "version": settings.VERSION
#     }

# @app.get("/api/status")
# async def api_status():
#     """Detailed API status"""
#     return {
#         "api": "operational",
#         "version": settings.VERSION,
#         "environment": settings.ENVIRONMENT,
#         "features": {
#             "ocr": True,
#             "ml_categorization": True,
#             "conversational_ai": True,
#             "analytics": True,
#             "voice": True
#         }
#     }

# # Run with: uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
"""
Main FastAPI application (optimized)
Run with: uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
"""
import time
import shutil
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from core.database import DatabaseOperations

# Routers
from api.routes.auth import router as auth_router
from api.routes.bills import router as bills_router
from api.routes.chat import router as chat_router
from api.routes.analytics import router as analytics_router
from api.routes.voice import router as voice_router

# Check Tesseract availability
import os

tess_path = settings.TESSERACT_PATH
if not os.path.exists(tess_path):
    print(f"⚠ Warning: Tesseract not found at {tess_path}")
else:
    print(f"✔ Tesseract found at {tess_path}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🚀 Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    print(f"📝 Environment: {settings.ENVIRONMENT}")

    try:
        DatabaseOperations.initialize_database()
        print("✅ Database initialized")
    except Exception as e:
        print(f"⚠ DB initialization error: {e}")

    yield

    print("👋 Shutting down application")


# Create app instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)


# CORS (allow frontend React)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware — track request time
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    response.headers["X-Process-Time"] = str(time.time() - start)
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": str(exc), "message": "Internal server error"},
    )


# ------------------------
# 📌 ROUTERS (Corrected)
# ------------------------
app.include_router(auth_router, prefix="/api/auth")
app.include_router(bills_router, prefix="/api/bills")
app.include_router(chat_router)  # <-- PREFIX ALREADY INSIDE chat.py
app.include_router(analytics_router, prefix="/api/analytics")
app.include_router(voice_router, prefix="/api/voice")


# Root endpoints
@app.get("/")
async def root():
    return {
        "message": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs": "/docs" if settings.DEBUG else "Disabled in production",
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": time.time(), "version": settings.VERSION}
