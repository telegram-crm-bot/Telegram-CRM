import base64
import json
import logging
import os

import firebase_admin
from firebase_admin import credentials, firestore

logger = logging.getLogger(__name__)
_db = None


def _load_service_account() -> dict:
    b64_env = os.getenv("FIREBASE_SERVICE_ACCOUNT_B64")
    if b64_env:
        try:
            decoded = base64.b64decode(b64_env).decode("utf-8")
            return json.loads(decoded)
        except Exception as exc:
            raise ValueError("FIREBASE_SERVICE_ACCOUNT_B64 is invalid.") from exc

    raw_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if raw_json:
        try:
            return json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise ValueError("FIREBASE_SERVICE_ACCOUNT_JSON is invalid.") from exc

    raise ValueError("No Firebase credentials found.")


def init_firebase() -> firestore.Client:
    global _db
    if _db is not None:
        return _db
    service_account_info = _load_service_account()
    cred = credentials.Certificate(service_account_info)
    firebase_admin.initialize_app(cred)
    _db = firestore.client()
    logger.info("Firebase initialized successfully.")
    return _db


def get_db() -> firestore.Client:
    if _db is None:
        return init_firebase()
    return _db


def check_connection() -> str:
    try:
        get_db().collection("crm_users").limit(1).get()
        return "Connected"
    except Exception as exc:
        logger.error("Firestore connection error: %s", exc)
        return f"Error: {exc}"


# ===== НОВЫЕ ФУНКЦИИ ДЛЯ BWS CRM =====

def link_user_by_uid(uid: str, chat_id: str) -> bool:
    """Связывает Telegram клиента с его профилем в BWS CRM по UID"""
    db = get_db()
    doc_ref = db.collection("crm_users").document(uid)
    doc = doc_ref.get()
    if doc.exists:
        doc_ref.update({"telegram_chat_id": chat_id})
        return True
    return False


def get_user_by_chat_id(chat_id: str) -> dict | None:
    """Ищет пользователя по chat_id"""
    db = get_db()
    # Проверяем как строку (новый формат CRM)
    docs = db.collection("crm_users").where("telegram_chat_id", "==", str(chat_id)).limit(1).stream()
    for doc in docs:
        return doc.to_dict() | {"id": doc.id}
    
    # Резервная проверка как числа (старый формат твоего старого бота)
    docs_int = db.collection("crm_users").where("telegram_chat_id", "==", int(chat_id)).limit(1).stream()
    for doc in docs_int:
        return doc.to_dict() | {"id": doc.id}
        
    return None

def get_all_registered_chat_ids() -> list[int]:
    db = get_db()
    docs = db.collection("crm_users").where("telegram_chat_id", "!=", None).stream()
    chat_ids = []
    for doc in docs:
        chat_id = doc.to_dict().get("telegram_chat_id")
        if chat_id:
            chat_ids.append(int(chat_id))
    return chat_ids
