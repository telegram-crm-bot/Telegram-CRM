import base64
import json
import logging
import os

import firebase_admin
from firebase_admin import credentials, firestore

logger = logging.getLogger(__name__)
_db = None


def _load_service_account() -> dict:
    """Load service account from Base64 (preferred) or raw JSON string."""
    b64_env = os.getenv("FIREBASE_SERVICE_ACCOUNT_B64")
    if b64_env:
        try:
            decoded = base64.b64decode(b64_env).decode("utf-8")
            return json.loads(decoded)
        except Exception as exc:
            raise ValueError(
                "FIREBASE_SERVICE_ACCOUNT_B64 is set but cannot be decoded/parsed. "
                "Ensure it is a valid Base64-encoded JSON string."
            ) from exc

    raw_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if raw_json:
        try:
            return json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise ValueError("FIREBASE_SERVICE_ACCOUNT_JSON contains invalid JSON.") from exc

    raise ValueError(
        "No Firebase credentials found. Set either FIREBASE_SERVICE_ACCOUNT_B64 "
        "(Base64-encoded JSON, recommended for Railway) or FIREBASE_SERVICE_ACCOUNT_JSON."
    )


def init_firebase() -> firestore.Client:
    """Initialize Firebase Admin SDK from environment variables."""
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
