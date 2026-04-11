from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.engine import LunaEngine


def _message_author(item: dict[str, str]) -> str:
    role = str(item.get("role", "assistant") or "assistant")
    if role == "user":
        return "You"
    author = str(item.get("author", "") or "").strip()
    return author or "Luna"


def _serialize_history(history: list[dict[str, str]]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for index, item in enumerate(history):
        role = str(item.get("role", "assistant") or "assistant")
        content = str(item.get("content", "") or "")
        items.append({
            "id": f"msg-{index}",
            "role": role,
            "author": _message_author(item),
            "content": content,
        })
    return items


def _serialize_chats(chats: list[dict[str, str]], current_chat_id: str) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for chat in chats:
        chat_id = str(chat.get("id", "") or "")
        items.append({
            "id": chat_id,
            "title": str(chat.get("title", "New Chat") or "New Chat"),
            "pinned": chat_id == current_chat_id,
            "archived": False,
            "kind": "chat",
            "messageCount": int(str(chat.get("message_count", "0") or "0")),
        })
    return items


def _state(engine: LunaEngine) -> dict[str, Any]:
    current_chat_id = engine.get_current_chat_id()
    chats = _serialize_chats(engine.list_chats(), current_chat_id)
    messages = _serialize_history(engine.memory.load_history())
    pending_title = engine.get_pending_action_title()
    pending_action = {
        "active": bool(pending_title),
        "title": pending_title,
    }
    return {
        "ok": True,
        "currentChatId": current_chat_id,
        "chats": chats,
        "messages": messages,
        "pendingAction": pending_action,
    }


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raw = sys.stdin.read().strip()
    payload = json.loads(raw) if raw else {}
    action = str(payload.get("action", "state") or "state").strip().lower()
    engine = LunaEngine()

    if action == "state":
        result = _state(engine)
    elif action == "create_chat":
        title = str(payload.get("title", "New chat") or "New chat")
        chat_id = engine.create_new_chat(title)
        result = _state(engine)
        result["createdChatId"] = chat_id
    elif action == "switch_chat":
        chat_id = str(payload.get("chatId", "") or "")
        history = engine.switch_chat(chat_id)
        result = _state(engine)
        result["messages"] = _serialize_history(history)
    elif action == "rename_chat":
        chat_id = str(payload.get("chatId", "") or "")
        title = str(payload.get("title", "") or "")
        engine.rename_chat(chat_id, title)
        result = _state(engine)
    elif action == "delete_chat":
        chat_id = str(payload.get("chatId", "") or "")
        engine.delete_chat(chat_id)
        result = _state(engine)
    elif action == "send_message":
        chat_id = str(payload.get("chatId", "") or "")
        text = str(payload.get("text", "") or "")
        force_action_execution = bool(payload.get("forceActionExecution", False))
        if chat_id:
            engine.switch_chat(chat_id)
        original_mode = engine.user_settings.data.agent_execution_mode
        original_override = engine._action_mode_override
        if force_action_execution:
            engine._action_mode_override = "auto"
        try:
            response = engine.chat(text)
        finally:
            engine.user_settings.data.agent_execution_mode = original_mode
            engine._action_mode_override = original_override
        result = _state(engine)
        result["response"] = response
    elif action == "confirm_pending_action":
        response = engine.confirm_pending_action()
        result = _state(engine)
        result["response"] = response
    elif action == "cancel_pending_action":
        response = engine.cancel_pending_action()
        result = _state(engine)
        result["response"] = response
    else:
        result = {"ok": False, "message": f"Unknown bridge action: {action}"}

    sys.stdout.write(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
