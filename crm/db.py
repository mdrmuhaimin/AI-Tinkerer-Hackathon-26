import sqlite3
import re
from datetime import datetime, timezone
from pathlib import Path

import apsw
import sqlite_vec
from sqlite_vec import serialize_float32

from crm.normalize import normalize_email, normalize_name, normalize_phone

DEFAULT_DB_PATH = Path("data/crm.db")
SOURCE = "conference_capture"
_SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  full_name TEXT,
  company TEXT,
  job_title TEXT,
  email TEXT,
  phone TEXT,
  website TEXT,
  address TEXT,
  notes TEXT,
  source TEXT,
  created_at TEXT,
  updated_at TEXT
);
"""
_FTS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS contacts_fts USING fts5(
  contact_id UNINDEXED,
  searchable
);
"""
_DB_ERRORS = (sqlite3.Error, apsw.Error)

_DISPLAY = (
    "full_name",
    "company",
    "job_title",
    "email",
    "phone",
    "website",
    "address",
)
_STOPWORDS = {"a", "an", "at", "did", "do", "i", "in", "is", "me", "met", "my", "of", "the", "who"}


class StoreError(Exception):
    pass


class _Row:
    def __init__(self, names: list[str], values: tuple) -> None:
        self._names = names
        self._values = values
        self._map = dict(zip(names, values))

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._map[key]

    def keys(self):
        return self._map.keys()


class _Cursor:
    def __init__(self, cursor, conn) -> None:
        self._cursor = cursor
        self._conn = conn

    def fetchone(self):
        names = self._names()
        row = self._cursor.fetchone()
        if row is None:
            return None
        return _Row(names, row) if names else row

    def fetchall(self):
        names = self._names()
        rows = self._cursor.fetchall()
        if not names:
            return list(rows)
        return [_Row(names, row) for row in rows]

    def _names(self):
        try:
            return [col[0] for col in self._cursor.getdescription()]
        except (apsw.ExecutionCompleteError, TypeError):
            return None

    @property
    def lastrowid(self):
        return self._conn.last_insert_rowid()


# ponytail: this CPython omits load_extension; drop wrapper if stdlib gains it
class _ExtConnection:
    """sqlite3-shaped wrapper so sqlite_vec.load() works when CPython omits it."""

    def __init__(self, db_path: Path) -> None:
        self._db = apsw.Connection(str(db_path))

    def enable_load_extension(self, enabled: bool) -> None:
        self._db.enableloadextension(bool(enabled))

    def load_extension(self, path: str) -> None:
        self._db.loadextension(path)

    def execute(self, sql: str, params=()):
        return _Cursor(self._db.execute(sql, params), self._db)

    def __enter__(self):
        self._db.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        return self._db.__exit__(exc_type, exc, tb)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _prefer(new, old):
    if new is None or (isinstance(new, str) and not new.strip()):
        return old
    return new


class ContactStore:
    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
        embedding_dim: int | None = None,
    ) -> None:
        self.db_path = Path(db_path)
        self.embedding_dim = embedding_dim
        self.ensure_schema()

    def _connect(self):
        if hasattr(sqlite3.Connection, "enable_load_extension"):
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
        else:
            conn = _ExtConnection(self.db_path)
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return conn

    def ensure_schema(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self._connect() as conn:
                conn.execute(_SCHEMA)
                conn.execute(_FTS_SCHEMA)
                self._backfill_fts(conn)
                if self.embedding_dim is not None:
                    self._create_vec_table(conn, self.embedding_dim)
        except _DB_ERRORS as exc:
            raise StoreError(str(exc)) from exc

    @staticmethod
    def _searchable(row) -> str:
        return " ".join(
            str(row[key]).strip()
            for key in (*_DISPLAY, "notes")
            if row[key] is not None and str(row[key]).strip()
        )

    def _sync_fts(self, conn, contact_id: int, row) -> None:
        conn.execute("DELETE FROM contacts_fts WHERE contact_id=?", (contact_id,))
        conn.execute(
            "INSERT INTO contacts_fts(contact_id, searchable) VALUES (?, ?)",
            (contact_id, self._searchable(row)),
        )

    def _backfill_fts(self, conn) -> None:
        rows = conn.execute(
            "SELECT id, full_name, company, job_title, email, phone, website, address, notes "
            "FROM contacts WHERE id NOT IN (SELECT contact_id FROM contacts_fts)"
        ).fetchall()
        for row in rows:
            self._sync_fts(conn, int(row["id"]), row)

    def _create_vec_table(self, conn, dim: int) -> None:
        conn.execute(
            f"CREATE VIRTUAL TABLE IF NOT EXISTS contact_embeddings "
            f"USING vec0(embedding float[{dim}])"
        )

    def _ensure_vec(self, dim: int) -> None:
        if self.embedding_dim is None:
            self.embedding_dim = dim
        try:
            with self._connect() as conn:
                self._create_vec_table(conn, self.embedding_dim)
        except _DB_ERRORS as exc:
            raise StoreError(str(exc)) from exc

    def find_match(self, normalized: dict) -> int | None:
        # ponytail: full-table scan, index/SQL match if contacts grow
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT id, full_name, company, email, phone FROM contacts ORDER BY id"
                ).fetchall()
        except _DB_ERRORS as exc:
            raise StoreError(str(exc)) from exc

        email_n = normalized.get("email_norm") or ""
        phone_n = normalized.get("phone_norm") or ""
        name_n = normalized.get("name_norm") or ""
        company_n = normalized.get("company_norm") or ""

        if email_n:
            for row in rows:
                if normalize_email(row["email"]) == email_n:
                    return int(row["id"])
            return None
        if phone_n:
            for row in rows:
                if normalize_phone(row["phone"]) == phone_n:
                    return int(row["id"])
            return None
        if name_n and company_n:
            for row in rows:
                if (
                    normalize_name(row["full_name"]) == name_n
                    and normalize_name(row["company"]) == company_n
                ):
                    return int(row["id"])
        return None

    def create(self, fields: dict) -> int:
        now = _now()
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    """
                    INSERT INTO contacts (
                      full_name, company, job_title, email, phone, website, address,
                      notes, source, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        fields.get("full_name"),
                        fields.get("company"),
                        fields.get("job_title"),
                        fields.get("email"),
                        fields.get("phone"),
                        fields.get("website"),
                        fields.get("address"),
                        fields.get("notes"),
                        SOURCE,
                        now,
                        now,
                    ),
                )
                contact_id = int(cur.lastrowid)
                row = conn.execute("SELECT * FROM contacts WHERE id=?", (contact_id,)).fetchone()
                self._sync_fts(conn, contact_id, row)
                return contact_id
        except _DB_ERRORS as exc:
            raise StoreError(str(exc)) from exc

    def update(self, contact_id: int, fields: dict) -> None:
        existing = self.get(contact_id)
        if existing is None:
            raise StoreError(f"contact {contact_id} not found")
        merged = {key: _prefer(fields.get(key), existing[key]) for key in _DISPLAY}
        new_notes = fields.get("notes")
        if new_notes:
            old = existing["notes"]
            merged_notes = f"{old}\n\n{new_notes}" if old else new_notes
        else:
            merged_notes = existing["notes"]
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    UPDATE contacts SET
                      full_name=?, company=?, job_title=?, email=?, phone=?,
                      website=?, address=?, notes=?, updated_at=?
                    WHERE id=?
                    """,
                    (
                        merged["full_name"],
                        merged["company"],
                        merged["job_title"],
                        merged["email"],
                        merged["phone"],
                        merged["website"],
                        merged["address"],
                        merged_notes,
                        _now(),
                        contact_id,
                    ),
                )
                row = conn.execute("SELECT * FROM contacts WHERE id=?", (contact_id,)).fetchone()
                self._sync_fts(conn, contact_id, row)
        except _DB_ERRORS as exc:
            raise StoreError(str(exc)) from exc

    def get(self, contact_id: int) -> dict | None:
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM contacts WHERE id=?", (contact_id,)
                ).fetchone()
        except _DB_ERRORS as exc:
            raise StoreError(str(exc)) from exc
        return dict(row) if row else None

    def search(self, query: str, limit: int = 5) -> list[dict]:
        tokens = [
            token for token in re.findall(r"[^\W_]+", query, flags=re.UNICODE)
            if token.casefold() not in _STOPWORDS
        ]
        if not tokens:
            return []
        match = " OR ".join(f'"{token.replace(chr(34), chr(34) * 2)}"' for token in tokens)
        capped_limit = min(max(limit, 1), 5)
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT c.* FROM contacts_fts f "
                    "JOIN contacts c ON c.id=f.contact_id "
                    "WHERE f.searchable MATCH ? ORDER BY bm25(contacts_fts) LIMIT ?",
                    (match, capped_limit),
                ).fetchall()
        except _DB_ERRORS as exc:
            raise StoreError(str(exc)) from exc
        return [dict(row) for row in rows]

    def upsert_embedding(self, contact_id: int, embedding: list[float]) -> None:
        self._ensure_vec(len(embedding))
        blob = serialize_float32(embedding)
        try:
            with self._connect() as conn:
                conn.execute(
                    "DELETE FROM contact_embeddings WHERE rowid = ?", (contact_id,)
                )
                conn.execute(
                    "INSERT INTO contact_embeddings(rowid, embedding) VALUES (?, ?)",
                    (contact_id, blob),
                )
        except _DB_ERRORS as exc:
            raise StoreError(str(exc)) from exc

    def get_embedding(self, contact_id: int) -> bytes | None:
        try:
            with self._connect() as conn:
                exists = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' "
                    "AND name='contact_embeddings'"
                ).fetchone()
                if exists is None:
                    return None
                row = conn.execute(
                    "SELECT embedding FROM contact_embeddings WHERE rowid = ?",
                    (contact_id,),
                ).fetchone()
        except _DB_ERRORS as exc:
            raise StoreError(str(exc)) from exc
        return bytes(row[0]) if row else None

    def search_similar(
        self, embedding: list[float], limit: int = 5
    ) -> list[tuple[int, float]]:
        blob = serialize_float32(embedding)
        try:
            with self._connect() as conn:
                exists = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' "
                    "AND name='contact_embeddings'"
                ).fetchone()
                if exists is None:
                    return []
                rows = conn.execute(
                    """
                    SELECT rowid, distance FROM contact_embeddings
                    WHERE embedding MATCH ? AND k = ?
                    """,
                    (blob, limit),
                ).fetchall()
        except _DB_ERRORS as exc:
            raise StoreError(str(exc)) from exc
        return [(int(row[0]), float(row[1])) for row in rows]
