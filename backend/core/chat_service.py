# core/chat_service.py
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from core.conversational_assistant import ConversationalFinancialAssistant
from core.database import DatabaseOperations


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


class ChatService:
    """
    ChatService: thin wrapper that persists user/assistant messages,
    calls the local ConversationalFinancialAssistant, and returns
    a frontend-friendly payload.

    Public static methods:
      - list_sessions(user_id)
      - get_session(user_id, chat_id)
      - create_session(user_id, title)
      - save_message(chat_id, role, content) -> message_id
      - handle_message(user_id, payload) -> dict
      - save_feedback(user_id, chat_id, payload) -> dict
      - get_session_summary(user_id, chat_id) -> dict
    """

    @staticmethod
    def _now():
        return datetime.utcnow()

    @staticmethod
    def list_sessions(user_id: int) -> Dict[str, Any]:
        """
        Return list of chat sessions belonging to the user.
        Each session includes last message preview (if any).
        """
        q = """
            SELECT id, title, created_at, updated_at,
              (SELECT content FROM chat_messages m WHERE m.chat_id = chat_sessions.id ORDER BY created_at DESC LIMIT 1) as last_message_preview
            FROM chat_sessions
            WHERE user_id = %s
            ORDER BY updated_at DESC
        """
        rows = DatabaseOperations.execute_query(q, (user_id,)) or []
        return {"sessions": rows}

    @staticmethod
    def get_session(user_id: int, chat_id: int) -> Dict[str, Any]:
        """
        Validate ownership and return session metadata + messages.
        """
        row = DatabaseOperations.execute_query(
            "SELECT id, title, created_at, updated_at FROM chat_sessions WHERE id = %s AND user_id = %s",
            (chat_id, user_id),
        )
        if not row:
            raise Exception("Chat not found")
        session = row[0]

        msgs = DatabaseOperations.execute_query(
            "SELECT id, role, content, created_at FROM chat_messages WHERE chat_id = %s ORDER BY created_at ASC",
            (chat_id,),
        ) or []

        return {"session": session, "messages": msgs}

    @staticmethod
    def create_session(user_id: int, title: str = "Chat") -> Dict[str, Any]:
        q = "INSERT INTO chat_sessions (user_id, title, created_at, updated_at) VALUES (%s, %s, NOW(), NOW()) RETURNING id, title, created_at, updated_at"
        row = DatabaseOperations.execute_query(q, (user_id, title))
        if not row:
            raise Exception("Failed to create session")
        return {"session": row[0]}

    @staticmethod
    def save_message(chat_id: int, role: str, content: str) -> int:
        """
        Insert a message and bump the session updated_at timestamp.
        Returns the inserted message id (int) or 0 on failure.
        """
        if not content:
            content = ""
        q = "INSERT INTO chat_messages (chat_id, role, content, created_at) VALUES (%s, %s, %s, NOW()) RETURNING id"
        row = DatabaseOperations.execute_query(q, (chat_id, role, content))
        if row and row[0]:
            try:
                DatabaseOperations.execute_query(
                    "UPDATE chat_sessions SET updated_at = NOW() WHERE id = %s",
                    (chat_id,),
                    fetch=False,
                )
            except Exception:
                # don't fail message save if update fails
                pass
            return int(row[0].get("id"))
        return 0

    @staticmethod
    def handle_message(user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entrypoint for sending a message.

        payload: { "message": str, "chat_id": optional int }

        returns:
        {
          "chat_id": int,
          "reply": str,
          "messages": [ {id, role, content, created_at}, ... ],
          "message_id": assistant_message_id,
          "explanations": { "<message_id>": { confidence, explanation, needs_info, suggestions } },
          "updated_categories": optional
        }
        """
        message = (payload.get("message") or "").strip()
        chat_id = payload.get("chat_id")

        # create a new session if not provided
        if not chat_id:
            created = ChatService.create_session(user_id, title="Chat")
            chat_id = created["session"]["id"]

        # verify session belongs to user
        owner = DatabaseOperations.execute_query(
            "SELECT id FROM chat_sessions WHERE id = %s AND user_id = %s", (chat_id, user_id)
        )
        if not owner:
            raise Exception("Chat session not found")

        # persist user message (always save user utterance)
        try:
            ChatService.save_message(chat_id, "user", message)
        except Exception as e:
            # we continue even if save fails — assistant should still reply
            pass

        # instantiate assistant and call logic (all local)
        assistant = ConversationalFinancialAssistant(user_id)
        try:
            resp = assistant.handle_conversation(message or "")
        except Exception as e:
            # Return a friendly fallback and persist assistant message
            fallback = f"❌ Assistant error: {str(e)}"
            msg_id = ChatService.save_message(chat_id, "assistant", fallback)
            messages = DatabaseOperations.execute_query(
                "SELECT id, role, content, created_at FROM chat_messages WHERE chat_id = %s ORDER BY created_at ASC", (chat_id,)
            ) or []
            explanations = {}
            if msg_id:
                explanations[str(msg_id)] = {"confidence": None, "explanation": str(e), "needs_info": False, "suggestions": []}
            return {
                "chat_id": chat_id,
                "reply": fallback,
                "messages": messages,
                "message_id": msg_id,
                "explanations": explanations,
            }

        # resp expected to be a dict with keys like: success, message, confidence, explanation, needs_info, suggestions, updated_categories
        reply_text = resp.get("message") or resp.get("reply") or "No reply"
        confidence = None
        try:
            if resp.get("confidence") is not None:
                confidence = float(resp.get("confidence"))
        except Exception:
            confidence = None
        explanation = resp.get("explanation")
        needs_info = bool(resp.get("needs_info", False))
        suggestions = resp.get("suggestions") or []
        updated_categories = resp.get("updated_categories") if isinstance(resp, dict) else None

        # persist assistant message
        assistant_msg_id = ChatService.save_message(chat_id, "assistant", reply_text)

        # fetch full messages to return to frontend
        messages = DatabaseOperations.execute_query(
            "SELECT id, role, content, created_at FROM chat_messages WHERE chat_id = %s ORDER BY created_at ASC",
            (chat_id,),
        ) or []

        # explanations keyed by saved message id (string key)
        explanations = {}
        if assistant_msg_id:
            explanations[str(assistant_msg_id)] = {
                "confidence": confidence,
                "explanation": explanation,
                "needs_info": needs_info,
                "suggestions": suggestions,
            }

        return {
            "chat_id": chat_id,
            "reply": reply_text,
            "messages": messages,
            "message_id": assistant_msg_id,
            "explanations": explanations,
            "updated_categories": updated_categories,
        }

    @staticmethod
    def save_feedback(user_id: int, chat_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        payload: { message_id: int, correction: {...} }
        Stores user feedback/corrections for assistant messages.
        """
        message_id = payload.get("message_id")
        correction = payload.get("correction", {})

        # validate session belongs to user
        session = DatabaseOperations.execute_query(
            "SELECT id FROM chat_sessions WHERE id = %s AND user_id = %s", (chat_id, user_id)
        )
        if not session:
            raise Exception("Chat session not found")

        DatabaseOperations.execute_query(
            "INSERT INTO chat_feedback (message_id, user_id, correction, created_at) VALUES (%s, %s, %s, NOW())",
            (message_id, user_id, json.dumps(correction)),
            fetch=False,
        )
        return {"saved": True}

    @staticmethod
    def get_session_summary(user_id: int, chat_id: int) -> Dict[str, Any]:
        """
        Lightweight summary computed from chat messages for a chat session:
          - title, message_count
          - simple extraction of monetary amounts from assistant messages saved as "Saved" responses
          - top categories mentioned in assistant messages (heuristic)
        Useful for the UI summarise-chat feature.
        """
        # validate session ownership
        row = DatabaseOperations.execute_query(
            "SELECT id, title FROM chat_sessions WHERE id = %s AND user_id = %s", (chat_id, user_id)
        )
        if not row:
            raise Exception("Chat not found")
        title = row[0].get("title")

        msgs = DatabaseOperations.execute_query(
            "SELECT id, role, content, created_at FROM chat_messages WHERE chat_id = %s ORDER BY created_at ASC", (chat_id,)
        ) or []

        total_spent = 0.0
        categories: Dict[str, int] = {}

        import re

        for m in msgs:
            content = m.get("content") or ""
            # Only count amounts mentioned in assistant messages that look like "Saved Successfully" or "Saved"
            if m.get("role") == "assistant":
                # amount pattern ₹ 123, ₹123.45, 123.45
                am = re.search(r'₹\s*([\d,]+(?:\.\d+)?)', content)
                if am and ("Saved" in content or "Saved Successfully" in content or "Saved Successfully!" in content):
                    try:
                        val = float(am.group(1).replace(",", ""))
                        total_spent += val
                    except Exception:
                        pass
                # category extraction like "**Category:** Food" (from assistant formatting in ConversationalFinancialAssistant)
                c = re.search(r'\*\*Category:\*\*\s*([A-Za-z0-9 _-]+)', content)
                if c:
                    cat = c.group(1).strip()
                    categories[cat] = categories.get(cat, 0) + 1

        summary = {
            "chat_id": chat_id,
            "title": title,
            "message_count": len(msgs),
            "total_spent_in_chat": total_spent,
            "top_categories": sorted(
                [{"category": k, "count": v} for k, v in categories.items()],
                key=lambda x: x["count"],
                reverse=True,
            )[:5],
        }
        return summary
