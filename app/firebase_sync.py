import os
import json
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.config import settings

_firestore_client = None
_firebase_initialized = False

def get_firestore_client():
    """
    Initializes and returns the Firestore client if valid Firebase credentials are provided.
    Supports:
      1. FIREBASE_CREDENTIALS (raw JSON string)
      2. FIREBASE_CREDENTIALS_BASE64 (base64 encoded JSON string)
      3. FIREBASE_CREDENTIALS_PATH (file path)
      4. Default local file: firebase_credentials.json / serviceAccountKey.json
    """
    global _firestore_client, _firebase_initialized

    if _firestore_client is not None:
        return _firestore_client

    if _firebase_initialized:
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
    except ImportError:
        print("[FIREBASE] firebase-admin package is not installed.")
        _firebase_initialized = True
        return None

    cred = None

    # Option 1: Raw JSON string from Environment Variable
    if settings.FIREBASE_CREDENTIALS:
        try:
            cred_dict = json.loads(settings.FIREBASE_CREDENTIALS)
            cred = credentials.Certificate(cred_dict)
            print("[FIREBASE] Loaded credentials from FIREBASE_CREDENTIALS env var.")
        except Exception as e:
            print(f"[FIREBASE] Error parsing FIREBASE_CREDENTIALS JSON: {e}")

    # Option 2: Base64 encoded JSON string from Environment Variable (best for Render)
    if not cred and settings.FIREBASE_CREDENTIALS_BASE64:
        try:
            decoded = base64.b64decode(settings.FIREBASE_CREDENTIALS_BASE64).decode("utf-8")
            cred_dict = json.loads(decoded)
            cred = credentials.Certificate(cred_dict)
            print("[FIREBASE] Loaded credentials from FIREBASE_CREDENTIALS_BASE64 env var.")
        except Exception as e:
            print(f"[FIREBASE] Error decoding FIREBASE_CREDENTIALS_BASE64: {e}")

    # Option 3: Custom path from Environment Variable
    if not cred and settings.FIREBASE_CREDENTIALS_PATH:
        p = Path(settings.FIREBASE_CREDENTIALS_PATH)
        if p.is_file():
            try:
                cred = credentials.Certificate(str(p))
                print(f"[FIREBASE] Loaded credentials from file {p}")
            except Exception as e:
                print(f"[FIREBASE] Error reading FIREBASE_CREDENTIALS_PATH: {e}")

    # Option 4: Render Secret Files directory (/etc/secrets)
    if not cred:
        render_secrets_dir = Path("/etc/secrets")
        if render_secrets_dir.is_dir():
            for f in render_secrets_dir.iterdir():
                if f.is_file() and f.suffix.lower() == ".json":
                    try:
                        with open(f, "r", encoding="utf-8") as jf:
                            data = json.load(jf)
                            if data.get("type") == "service_account" or "project_id" in data:
                                cred = credentials.Certificate(str(f))
                                print(f"[FIREBASE] Successfully loaded credentials from Render Secret File: {f}")
                                break
                    except Exception as e:
                        print(f"[FIREBASE] Error inspecting Render secret file {f}: {e}")

    # Option 5: Known file names in project root or current directory
    if not cred:
        search_dirs = [settings.BASE_DIR, Path("."), Path("./data")]
        search_names = [
            "firebase_credentials.json",
            "firebase-credentials.json",
            "serviceAccountKey.json",
            "service_account.json",
            "firebase.json",
            "credentials.json"
        ]
        for sdir in search_dirs:
            if not sdir.is_dir():
                continue
            for fname in search_names:
                p = sdir / fname
                if p.is_file():
                    try:
                        with open(p, "r", encoding="utf-8") as jf:
                            data = json.load(jf)
                            if data.get("type") == "service_account" or "project_id" in data:
                                cred = credentials.Certificate(str(p))
                                print(f"[FIREBASE] Successfully loaded credentials from local file: {p}")
                                break
                    except Exception as e:
                        print(f"[FIREBASE] Error loading file {p}: {e}")
            if cred:
                break

    if cred:
        try:
            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred)
            _firestore_client = firestore.client()
            _firebase_initialized = True
            print("[FIREBASE] Google Cloud Firestore connected and active!")
            return _firestore_client
        except Exception as e:
            print(f"[FIREBASE] Failed initializing Firebase App: {e}")
            _firestore_client = None
            _firebase_initialized = True
            return None
    else:
        _firebase_initialized = True
        return None


def is_firebase_active() -> bool:
    """Returns True if Firestore is initialized and connected."""
    client = get_firestore_client()
    return client is not None


def sync_document(collection: str, doc_id: str, data: Dict[str, Any]) -> bool:
    """
    Saves or merges a single document in Firestore.
    Safe with any datatypes and fails gracefully without raising exceptions.
    """
    client = get_firestore_client()
    if not client:
        return False

    try:
        # Convert non-serializable objects (like sqlite3.Row or tuples)
        doc_data = {}
        for k, v in data.items():
            if isinstance(v, (str, int, float, bool)) or v is None:
                doc_data[k] = v
            elif isinstance(v, datetime):
                doc_data[k] = v.strftime("%Y-%m-%d %H:%M:%S")
            elif isinstance(v, (dict, list)):
                doc_data[k] = v
            else:
                doc_data[k] = str(v)

        client.collection(collection).document(str(doc_id)).set(doc_data, merge=True)
        return True
    except Exception as e:
        print(f"[FIREBASE SYNC ERROR] [{collection}/{doc_id}]: {e}")
        return False


def delete_document(collection: str, doc_id: str) -> bool:
    """Deletes a document from Firestore."""
    client = get_firestore_client()
    if not client:
        return False

    try:
        client.collection(collection).document(str(doc_id)).delete()
        return True
    except Exception as e:
        print(f"[FIREBASE DELETE ERROR] [{collection}/{doc_id}]: {e}")
        return False


# List of tables to sync in proper relational dependency order
PERSISTENT_TABLES = [
    "settings",
    "products",
    "farmers",
    "batches",
    "batch_logs",
    "invoices",
    "payments",
    "feed_requests",
    "expenses",
    "notifications",
]


def backup_all_to_firebase(db_manager) -> Dict[str, Any]:
    """
    Reads all records from SQLite and saves them to Firestore.
    Useful for manual backup or initial sync.
    """
    client = get_firestore_client()
    if not client:
        return {"status": "error", "message": "Firebase is not connected."}

    summary = {}
    total_backed_up = 0

    try:
        with db_manager._get_connection() as conn:
            cur = conn.cursor()
            for table in PERSISTENT_TABLES:
                cur.execute(f"SELECT * FROM {table}")
                rows = cur.fetchall()
                count = 0
                
                # Firestore batch write
                batch = client.batch()
                op_in_batch = 0

                for r in rows:
                    r_dict = dict(r)
                    doc_id = str(r_dict.get("id") or r_dict.get("key"))
                    if not doc_id:
                        continue
                    
                    doc_ref = client.collection(table).document(doc_id)
                    batch.set(doc_ref, r_dict, merge=True)
                    op_in_batch += 1
                    count += 1

                    if op_in_batch >= 400:
                        batch.commit()
                        batch = client.batch()
                        op_in_batch = 0

                if op_in_batch > 0:
                    batch.commit()

                summary[table] = count
                total_backed_up += count

        return {
            "status": "success",
            "message": f"সফলভাবে মোট {total_backed_up} টি রেকর্ড ক্লাউডে ব্যাকআপ হয়েছে।",
            "counts": summary
        }
    except Exception as e:
        print(f"[FIREBASE BACKUP ALL ERROR] {e}")
        return {"status": "error", "message": str(e), "counts": summary}


def restore_all_from_firebase(db_manager) -> Dict[str, Any]:
    """
    Downloads all records from Firestore and restores them into local SQLite tables.
    Uses INSERT OR REPLACE so existing records are updated and missing ones inserted.
    """
    client = get_firestore_client()
    if not client:
        return {"status": "error", "message": "Firebase is not connected."}

    summary = {}
    total_restored = 0

    try:
        with db_manager._get_connection() as conn:
            cur = conn.cursor()

            for table in PERSISTENT_TABLES:
                # Inspect SQLite table columns
                cur.execute(f"PRAGMA table_info({table})")
                cols_info = cur.fetchall()
                col_names = [c[1] for c in cols_info]

                if not col_names:
                    continue

                # Stream documents from Firestore
                docs = client.collection(table).stream()
                restored_in_table = 0

                for doc in docs:
                    data = doc.to_dict()
                    if not data:
                        continue

                    # Match document keys with SQLite columns
                    row_data = {}
                    for col in col_names:
                        row_data[col] = data.get(col, None)

                    # For settings, ensure 'key' exists; for other tables, ensure 'id' exists
                    primary_key = "key" if table == "settings" else "id"
                    if not row_data.get(primary_key):
                        row_data[primary_key] = doc.id

                    placeholders = ", ".join(["?"] * len(col_names))
                    columns_str = ", ".join(col_names)
                    values = [row_data[c] for c in col_names]

                    sql = f"INSERT OR REPLACE INTO {table} ({columns_str}) VALUES ({placeholders})"
                    cur.execute(sql, values)
                    restored_in_table += 1

                summary[table] = restored_in_table
                total_restored += restored_in_table

            conn.commit()

        print(f"[FIREBASE RESTORE] Successfully restored {total_restored} records from Firebase!")
        return {
            "status": "success",
            "message": f"Firebase থেকে {total_restored} টি রেকর্ড সফলভাবে রিস্টোর হয়েছে।",
            "counts": summary
        }
    except Exception as e:
        print(f"[FIREBASE RESTORE ALL ERROR] {e}")
        return {"status": "error", "message": str(e), "counts": summary}


def auto_restore_if_needed(db_manager) -> Dict[str, Any]:
    """
    Automatically called on server startup (e.g. after a new Render deploy).
    Checks if SQLite lost its data (empty or initial seed only) while Firestore has records.
    If so, automatically pulls and restores all documents from Firestore.
    If Firestore is empty and local SQLite has data, it auto-initializes Firestore.
    """
    client = get_firestore_client()
    if not client:
        return {"status": "inactive", "message": "Firebase is not configured."}

    try:
        with db_manager._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM invoices")
            local_invoices = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM farmers")
            local_farmers = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM products")
            local_products = cur.fetchone()[0]

        # Quick check if Firestore has existing collections
        fs_farmers = list(client.collection("farmers").limit(1).stream())
        fs_invoices = list(client.collection("invoices").limit(1).stream())
        fs_products = list(client.collection("products").limit(1).stream())

        firestore_has_records = (len(fs_farmers) > 0) or (len(fs_invoices) > 0) or (len(fs_products) > 0)

        # Condition 1: Render fresh container deploy detected (local database is empty or only default 1 farmer)
        if firestore_has_records and (local_invoices == 0 or local_farmers <= 1):
            print("[FIREBASE AUTO-RESTORE] Fresh container / new deploy detected! Auto-restoring from Firestore...")
            res = restore_all_from_firebase(db_manager)
            return {"status": "auto_restored", "result": res}

        # Condition 2: First-time Firebase setup (Firestore is empty, local database has data)
        elif not firestore_has_records and local_products > 0:
            print("[FIREBASE AUTO-INIT] Fresh Firebase connected. Initializing Firestore with current SQLite data...")
            res = backup_all_to_firebase(db_manager)
            return {"status": "auto_seeded", "result": res}

        else:
            return {"status": "synced", "message": "Local database is in sync with Firebase."}

    except Exception as e:
        print(f"[FIREBASE AUTO-RESTORE CHECK ERROR] {e}")
        return {"status": "error", "message": str(e)}
