from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any, Dict

from api.routes.auth import get_current_user_id
from core.chat_service import ChatService

router = APIRouter(prefix="/api/chat")

class MsgPayload(BaseModel):
    message: str
    chat_id: int = None

@router.post("/message")
def post_message(payload: MsgPayload, user_id: int = Depends(get_current_user_id)):
    try:
        out = ChatService.handle_message(user_id=user_id, payload=payload.dict())
        return {"success": True, "data": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
def list_chats(user_id: int = Depends(get_current_user_id)):
    try:
        out = ChatService.list_sessions(user_id)
        return {"success": True, "data": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{chat_id}")
def get_chat(chat_id: int, user_id: int = Depends(get_current_user_id)):
    try:
        out = ChatService.get_session(user_id, chat_id)
        return {"success": True, "data": out}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{chat_id}/feedback")
def feedback(chat_id: int, payload: Dict[str, Any], user_id: int = Depends(get_current_user_id)):
    try:
        out = ChatService.save_feedback(user_id, chat_id, payload)
        return {"success": True, "data": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("")
def create_session(payload: Dict[str, Any], user_id: int = Depends(get_current_user_id)):
    title = payload.get("title", "Chat")
    try:
        out = ChatService.create_session(user_id, title)
        return {"success": True, "data": {"session": out.get("session")}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{chat_id}/summary")
def get_summary(chat_id: int, user_id: int = Depends(get_current_user_id)):
    try:
        out = ChatService.get_session_summary(user_id, chat_id)
        return {"success": True, "data": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# """
# Chat Routes - conversational assistant wrapper
# """
# import os
# import sys
# from fastapi import APIRouter, Depends, HTTPException
# from pydantic import BaseModel
# from typing import Any, Dict

# sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
# from core.conversational_assistant import ConversationalFinancialAssistant
# from .auth import get_current_user_id

# router = APIRouter()


# def _response(success: bool, data=None, message: str = ""):
#     payload = {"success": success}
#     if data is not None:
#         payload["data"] = data
#     if message:
#         payload["message"] = message
#     return payload


# class ChatMessage(BaseModel):
#     message: str


# @router.post("/message")
# async def send_message(msg: ChatMessage, user_id: int = Depends(get_current_user_id)):
#     try:
#         assistant = ConversationalFinancialAssistant(user_id)
#         response = assistant.handle_conversation(msg.message)
#         return _response(True, data=response)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/categories")
# async def get_categories(user_id: int = Depends(get_current_user_id)):
#     from core.category_learner import HybridCategoryLearner
#     try:
#         learner = HybridCategoryLearner(user_id)
#         return _response(True, data={
#             "categories": learner.get_all_user_categories(),
#             "stats": learner.get_category_stats()
#         })
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# """Chat Routes - Uses conversational_assistant.py"""
# from fastapi import APIRouter, Depends, HTTPException
# from pydantic import BaseModel
# import sys, os
# sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
# from core.conversational_assistant import ConversationalFinancialAssistant
# from .auth import get_current_user_id

# router = APIRouter()

# class ChatMessage(BaseModel):
#     message: str

# @router.post("/message")
# async def send_message(msg: ChatMessage, user_id: int = Depends(get_current_user_id)):
#     try:
#         assistant = ConversationalFinancialAssistant(user_id)
#         response = assistant.handle_conversation(msg.message)
#         return response
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @router.get("/categories")
# async def get_categories(user_id: int = Depends(get_current_user_id)):
#     from core.category_learner import HybridCategoryLearner
#     learner = HybridCategoryLearner(user_id)
#     return {
#         "categories": learner.get_all_user_categories(),
#         "stats": learner.get_category_stats()
#     }
