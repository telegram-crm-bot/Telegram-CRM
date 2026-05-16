import json
import logging
import os

import firebase_admin
from firebase_admin import credentials, firestore

logger = logging.getLogger(__name__)
_db = None


def init_firebase() -> firestore.Client:
    """Initialize Firebase Admin SDK from a JSON string in the env var."""
    global _db
    if _db is not None:
        return _db

    raw_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if not raw_json:
        raise ValueError("Environment variable FIREBASE_SERVICE_ACCOUNT_JSON is not set.")

    try:
        service_account_info = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError("FIREBASE_SERVICE_ACCOUNT_JSON contains invalid JSON.") from exc

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
    """Lightweight health-check for Firestore."""
    try:
        get_db().collection("crm_users").limit(1).get()
        return "Connected"
    except Exception as exc:
        logger.error("Firestore connection error: %s", exc)
        return f"Error: {exc}"


def get_user_by_website_id(website_id: str) -> dict | None:
    db = get_db()
    docs = db.collection("crm_users").where("website_id", "==", website_id).limit(1).stream()
    for doc in docs:
        return doc.to_dict() | {"id": doc.id}
    return None


def get_user_by_chat_id(chat_id: int) -> dict | None:
    db = get_db()
    docs = db.collection("crm_users").where("telegram_chat_id", "==", chat_id).limit(1).stream()
    for doc in docs:
        return doc.to_dict() | {"id": doc.id}
    return None


def update_user_chat_id(website_id: str, chat_id: int) -> bool:
    db = get_db()
    docs = db.collection("crm_users").where("website_id", "==", website_id).limit(1).stream()
    for doc in docs:
        doc.reference.update({"telegram_chat_id": chat_id})
        return True
    return False


def get_leads_count_by_website_id(website_id: str) -> int:
    db = get_db()
    docs = db.collection("crm_leads").where("website_id", "==", website_id).stream()
    return len(list(docs))


def get_all_registered_chat_ids() -> list[int]:
    db = get_db()
    docs = db.collection("crm_users").where("telegram_chat_id", "!=", None).stream()
    chat_ids: list[int] = []
    for doc in docs:
        data = doc.to_dict()
        chat_id = data.get("telegram_chat_id")
        if chat_id is not None:
            chat_ids.append(chat_id)
    return chat_ids


def update_lead_status(lead_id: str, status: str) -> None:
    db = get_db()
    ref = db.collection("crm_leads").document(lead_id)
    ref.update({"status": status})
