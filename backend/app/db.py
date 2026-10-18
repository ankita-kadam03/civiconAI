from __future__ import annotations

import copy
import threading
from datetime import datetime
from typing import Any

from app.config import get_settings

COLLECTIONS = (
    "users",
    "departments",
    "categories",
    "regions",
    "complaints",
    "reports",
    "votes",
    "saved_locations",
    "complaint_status_history",
    "comments",
    "assignments",
    "attachments",
    "escalations",
    "escalation_rules",
    "notifications",
    "audit_logs",
    "processed_events",
    "password_resets",
)


def _get_path(doc: dict, key: str) -> Any:
    if "." not in key:
        return doc.get(key)
    cur: Any = doc
    for part in key.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _set_path(doc: dict, key: str, value: Any) -> None:
    if "." not in key:
        doc[key] = value
        return
    parts = key.split(".")
    cur = doc
    for part in parts[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    cur[parts[-1]] = value


def _unset_path(doc: dict, key: str) -> None:
    if "." not in key:
        doc.pop(key, None)
        return
    parts = key.split(".")
    cur = doc
    for part in parts[:-1]:
        cur = cur.get(part)
        if not isinstance(cur, dict):
            return
    cur.pop(parts[-1], None)


def _cmp(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict) and any(str(k).startswith("$") for k in expected):
        for op, val in expected.items():
            if op == "$in":
                if actual not in val:
                    return False
            elif op == "$ne":
                if actual == val:
                    return False
            elif op == "$gt":
                if actual is None or actual <= val:
                    return False
            elif op == "$gte":
                if actual is None or actual < val:
                    return False
            elif op == "$lt":
                if actual is None or actual >= val:
                    return False
            elif op == "$lte":
                if actual is None or actual > val:
                    return False
            elif op == "$exists":
                exists = actual is not None
                if bool(val) != exists:
                    return False
            elif op == "$regex":
                import re

                if actual is None or re.search(str(val), str(actual), re.I) is None:
                    return False
            else:
                return False
        return True
    return actual == expected


def matches(doc: dict, query: dict | None) -> bool:
    if not query:
        return True
    if "$or" in query:
        rest = {k: v for k, v in query.items() if k != "$or"}
        return any(matches(doc, q) for q in query["$or"]) and matches(doc, rest)
    if "$and" in query:
        rest = {k: v for k, v in query.items() if k != "$and"}
        return all(matches(doc, q) for q in query["$and"]) and matches(doc, rest)
    for key, expected in query.items():
        if not _cmp(_get_path(doc, key), expected):
            return False
    return True


class MemoryCursor:
    def __init__(self, docs: list[dict]):
        self._docs = docs
        self._skip = 0
        self._limit = None
        self._sort: list[tuple[str, int]] = []

    def sort(self, key, direction: int = 1):
        if isinstance(key, list):
            self._sort = [(k, d) for k, d in key]
        else:
            self._sort = [(key, direction)]
        return self

    def skip(self, n: int):
        self._skip = n
        return self

    def limit(self, n: int):
        self._limit = n
        return self

    def _apply(self) -> list[dict]:
        docs = list(self._docs)
        for key, direction in reversed(self._sort):
            docs.sort(key=lambda d: (_get_path(d, key) is None, _get_path(d, key)), reverse=direction < 0)
        docs = docs[self._skip :]
        if self._limit is not None:
            docs = docs[: self._limit]
        return [copy.deepcopy(d) for d in docs]

    def __iter__(self):
        return iter(self._apply())

    def __list__(self):
        return self._apply()


class DuplicateKeyError(Exception):
    pass


class MemoryCollection:
    def __init__(self, name: str, lock: threading.RLock, persist: Any | None = None):
        self.name = name
        self._docs: list[dict] = []
        self._lock = lock
        self._unique: dict[str, set] = {}
        self._persist = persist

    def create_index(self, keys, unique: bool = False, **_kwargs):
        if unique:
            field = keys[0][0] if isinstance(keys, list) else keys
            self._unique[field] = set()

    def insert_one(self, doc: dict):
        with self._lock:
            stored = copy.deepcopy(doc)
            for field, seen in self._unique.items():
                val = stored.get(field)
                if val is not None and val in seen:
                    raise DuplicateKeyError(f"Duplicate {field}")
                if val is not None:
                    seen.add(val)
            self._docs.append(stored)
            if self._persist:
                self._persist.write_doc(self.name, stored)
            return type("Res", (), {"inserted_id": stored.get("_id")})()

    def find_one(self, query: dict | None = None, sort=None):
        cur = self.find(query)
        if sort:
            if isinstance(sort, list):
                cur.sort(sort)
            else:
                cur.sort(sort)
        docs = cur._apply()
        return docs[0] if docs else None

    def find(self, query: dict | None = None):
        with self._lock:
            matched = [d for d in self._docs if matches(d, query)]
        return MemoryCursor(matched)

    def count_documents(self, query: dict | None = None) -> int:
        with self._lock:
            return sum(1 for d in self._docs if matches(d, query))

    def update_one(self, query: dict, update: dict, upsert: bool = False):
        with self._lock:
            for doc in self._docs:
                if matches(doc, query):
                    self._apply_update(doc, update)
                    if self._persist:
                        self._persist.write_doc(self.name, doc)
                    return type("Res", (), {"matched_count": 1, "modified_count": 1})()
            if upsert:
                new_doc: dict = {}
                self._apply_update(new_doc, update)
                new_doc.update({k: v for k, v in (query or {}).items() if not str(k).startswith("$")})
                self._docs.append(new_doc)
                if self._persist:
                    self._persist.write_doc(self.name, new_doc)
                return type("Res", (), {"matched_count": 0, "modified_count": 1})()
            return type("Res", (), {"matched_count": 0, "modified_count": 0})()

    def update_many(self, query: dict, update: dict):
        count = 0
        with self._lock:
            for doc in self._docs:
                if matches(doc, query):
                    self._apply_update(doc, update)
                    if self._persist:
                        self._persist.write_doc(self.name, doc)
                    count += 1
        return type("Res", (), {"matched_count": count, "modified_count": count})()

    def delete_one(self, query: dict):
        return self.delete_many(query)

    def delete_many(self, query: dict):
        with self._lock:
            keep = []
            deleted = 0
            for doc in self._docs:
                if matches(doc, query):
                    deleted += 1
                    doc_id = doc.get("_id")
                    if self._persist and doc_id:
                        self._persist.delete_doc(self.name, str(doc_id))
                    for field, seen in self._unique.items():
                        val = doc.get(field)
                        if val in seen:
                            seen.discard(val)
                else:
                    keep.append(doc)
            self._docs = keep
        return type("Res", (), {"deleted_count": deleted})()

    def aggregate(self, pipeline: list[dict]):
        docs = [copy.deepcopy(d) for d in self._docs]
        for stage in pipeline:
            if "$match" in stage:
                docs = [d for d in docs if matches(d, stage["$match"])]
            elif "$group" in stage:
                docs = self._group(docs, stage["$group"])
            elif "$sort" in stage:
                for key, direction in reversed(list(stage["$sort"].items())):
                    docs.sort(key=lambda d: (_get_path(d, key) is None, _get_path(d, key)), reverse=direction < 0)
            elif "$limit" in stage:
                docs = docs[: stage["$limit"]]
        return docs

    def _group(self, docs: list[dict], spec: dict) -> list[dict]:
        key_spec = spec.get("_id")
        buckets: dict[Any, list[dict]] = {}
        for doc in docs:
            if key_spec is None:
                key = None
            elif isinstance(key_spec, str) and key_spec.startswith("$"):
                key = _get_path(doc, key_spec[1:])
            elif isinstance(key_spec, dict):
                key = tuple(_get_path(doc, v[1:]) if isinstance(v, str) and v.startswith("$") else v for v in key_spec.values())
            else:
                key = key_spec
            buckets.setdefault(key, []).append(doc)
        out = []
        for key, group in buckets.items():
            row: dict[str, Any] = {"_id": key if not isinstance(key_spec, dict) else dict(zip(key_spec.keys(), key))}
            for field, acc in spec.items():
                if field == "_id":
                    continue
                if "$sum" in acc:
                    val = acc["$sum"]
                    if val == 1:
                        row[field] = len(group)
                    else:
                        fname = val[1:] if isinstance(val, str) and val.startswith("$") else None
                        row[field] = sum((_get_path(d, fname) or 0) for d in group) if fname else 0
                elif "$avg" in acc:
                    fname = acc["$avg"][1:]
                    nums = [n for n in (_get_path(d, fname) for d in group) if isinstance(n, (int, float))]
                    row[field] = (sum(nums) / len(nums)) if nums else 0
            out.append(row)
        return out

    def _apply_update(self, doc: dict, update: dict) -> None:
        if "$set" in update:
            for k, v in update["$set"].items():
                _set_path(doc, k, v)
        if "$unset" in update:
            for k in update["$unset"].keys():
                _unset_path(doc, k)
        if "$inc" in update:
            for k, v in update["$inc"].items():
                _set_path(doc, k, (_get_path(doc, k) or 0) + v)
        if "$push" in update:
            for k, v in update["$push"].items():
                arr = _get_path(doc, k)
                if not isinstance(arr, list):
                    arr = []
                    _set_path(doc, k, arr)
                arr.append(v)
        if "$setOnInsert" in update and not doc:
            for k, v in update["$setOnInsert"].items():
                _set_path(doc, k, v)


class MemoryDB:
    def __init__(self, persist: Any | None = None):
        self._lock = threading.RLock()
        self._persist = persist
        self._cols = {name: MemoryCollection(name, self._lock, persist) for name in COLLECTIONS}

    def __getitem__(self, name: str) -> MemoryCollection:
        if name not in self._cols:
            self._cols[name] = MemoryCollection(name, self._lock, self._persist)
        return self._cols[name]

    def list_collection_names(self) -> list[str]:
        return list(self._cols.keys())


class Database:
    def __init__(self):
        self.mode = "memory"
        self.client = None
        self.db: Any = MemoryDB()
        self.connected = False
        self.error: str | None = None
        self._firestore: Any | None = None

    def connect(self) -> None:
        settings = get_settings()
        project = settings.firebase_project_resolved

        if project:
            from app.firestore_store import FirestoreBackend

            self._firestore = FirestoreBackend(project)
            self.db = MemoryDB(persist=self._firestore)
            self.mode = "firestore"
            self.connected = True
            self.error = None
            self._hydrate()
            self._indexes()
            return

        if settings.allow_memory_db:
            self.mode = "memory"
            self.db = MemoryDB()
            self.connected = True
            self.error = None
            self._indexes()
            return

        raise RuntimeError("FIREBASE_PROJECT_ID is required. Run: gcloud auth application-default login")

    def _hydrate(self) -> None:
        if not self._firestore:
            return
        for name in COLLECTIONS:
            col = self.db[name]
            col._docs.clear()
            self._firestore.hydrate_collection(col, name)

    def reset_all(self) -> None:
        if self._firestore:
            self._firestore.wipe_all(COLLECTIONS)
        self.db = MemoryDB(persist=self._firestore)
        self._indexes()

    def close(self) -> None:
        self.client = None
        self._firestore = None

    def _indexes(self) -> None:
        try:
            self.db["users"].create_index("email", unique=True)
            self.db["complaints"].create_index("reference", unique=True)
            self.db["complaints"].create_index("submission_hash")
            self.db["complaints"].create_index("geohash")
            self.db["notifications"].create_index("dedupe_key", unique=True)
            self.db["notifications"].create_index([("user_id", 1), ("incident_id", 1)])
            self.db["escalations"].create_index("idempotency_key", unique=True)
            self.db["votes"].create_index("vote_key", unique=True)
            self.db["reports"].create_index("incident_id")
            self.db["reports"].create_index([("incident_id", 1), ("uid", 1)])
            self.db["saved_locations"].create_index("user_id")
            self.db["complaint_status_history"].create_index("incident_id")
            self.db["comments"].create_index("incident_id")
            self.db["audit_logs"].create_index("created_at")
            self.db["categories"].create_index("slug", unique=True)
            self.db["departments"].create_index("code", unique=True)
        except Exception:
            pass

    def col(self, name: str):
        return self.db[name]


database = Database()


def get_db() -> Database:
    return database


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.isoformat() + "Z"
    return dt.isoformat().replace("+00:00", "Z")
