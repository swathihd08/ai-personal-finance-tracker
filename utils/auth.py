import hashlib
import json
from pathlib import Path

try:
    from utils.cloud_db import save_user_cloud, load_user_cloud, check_cloud_enabled
    CLOUD_ENABLED = check_cloud_enabled()
except ImportError:
    CLOUD_ENABLED = False
    save_user_cloud = None
    load_user_cloud = None


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
USER_DB_PATH = DATA_DIR / "users.json"


def ensure_storage() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    if not USER_DB_PATH.exists():
        USER_DB_PATH.write_text("{}", encoding="utf-8")


def _hash_password(password: str) -> str:
    salt = hashlib.sha256(password.encode("utf-8")).hexdigest()[:16]
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()
    return f"{salt}:{digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, digest = stored_hash.split(":", 1)
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()
        return candidate == digest
    except ValueError:
        return False


def load_user_store() -> dict:
    ensure_storage()
    # Try cloud storage first
    if CLOUD_ENABLED and load_user_cloud:
        try:
            cloud_data = load_user_cloud("_store")
            if cloud_data:
                return cloud_data
        except Exception:
            pass
    # Fallback to local storage
    with USER_DB_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_user_store(store: dict) -> None:
    ensure_storage()
    # Save to local storage
    with USER_DB_PATH.open("w", encoding="utf-8") as handle:
        json.dump(store, handle, indent=2)
    # Also try to save to cloud
    if CLOUD_ENABLED and save_user_cloud:
        try:
            save_user_cloud("_store", store)
        except Exception:
            pass  # Cloud save failed, but local save succeeded


def create_user(username: str, password: str, full_name: str = "") -> bool:
    store = load_user_store()
    if username in store:
        return False
    store[username] = {
        "full_name": full_name,
        "password_hash": _hash_password(password),
        "transactions": [],
        "budgets": {},
    }
    save_user_store(store)
    return True


def authenticate_user(username: str, password: str) -> dict | None:
    store = load_user_store()
    user = store.get(username)
    if not user:
        return None
    return user if verify_password(password, user.get("password_hash", "")) else None
