from .auth import router as auth_router
from .bills import router as bills_router
from .chat import router as chat_router
from .analytics import router as analytics_router
from .voice import router as voice_router

__all__ = ["auth_router", "bills_router", "chat_router", "analytics_router", "voice_router"]

# """
# API Routes Package
# Exports all route modules
# """

# from . import auth, bills, chat, analytics, voice

# __all__ = ['auth', 'bills', 'chat', 'analytics', 'voice']
