"""Deterministic SQLite persistence and lexical FTS5 retrieval."""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Mapping

FIELDS = ("full_name", "company", "job_title", "email", "phone", "website", "address")
_STOPWORDS = {"a", "an", "at", "did", "do", "i", "in", "is", "me", "met", "my", "of", "the", "who"}


class SQLiteContactStore:
    def __init__(self, path: str | Path = "crm.sqlite3") -> None:
        self.path = str(path)
        self._create_schema()

    def _connect(self):
        return sqlite3.connect(self.path)

    def _create_schema(self) -> None:
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY, owner_user_id INTEGER NOT NULL,
                    full_name TEXT NOT NULL, company TEXT, job_title TEXT,
                    email TEXT, phone TEXT, website TEXT, address TEXT,
                    voice_transcript TEXT, conversation_notes TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS contacts_fts USING fts5(
                    contact_id UNINDEXED, owner_user_id UNINDEXED, searchable
                );
            """)

    def save(self, owner_user_id: int, result: Mapping) -> int:
        evidence = result["contact_evidence"]
        values = [evidence.get(field) for field in FIELDS]
        transcript = result.get("voice_transcript")
        notes = result.get("conversation_notes")
        searchable = " ".join(str(v) for v in [*values, transcript, notes] if v)
        with self._connect() as db:
            cursor = db.execute(
                "INSERT INTO contacts(owner_user_id, full_name, company, job_title, email, phone, website, address, voice_transcript, conversation_notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (owner_user_id, *values, transcript, notes),
            )
            contact_id = int(cursor.lastrowid)
            db.execute("INSERT INTO contacts_fts(contact_id, owner_user_id, searchable) VALUES (?, ?, ?)",
                       (contact_id, owner_user_id, searchable))
        return contact_id

    def search(self, owner_user_id: int, query: str, limit: int = 5) -> list[dict]:
        tokens = [token for token in re.findall(r"[^\W_]+", query, flags=re.UNICODE)
                  if token.casefold() not in _STOPWORDS]
        if not tokens:
            return []
        match = " OR ".join('"' + token.replace('"', '""') + '"' for token in tokens)
        columns = ", ".join(f"c.{field}" for field in FIELDS)
        with self._connect() as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                f"SELECT {columns}, c.voice_transcript, c.conversation_notes, c.created_at "
                "FROM contacts_fts f JOIN contacts c ON c.id=f.contact_id "
                "WHERE f.searchable MATCH ? AND c.owner_user_id=? "
                "ORDER BY bm25(contacts_fts) LIMIT ?",
                (match, owner_user_id, min(max(limit, 1), 5)),
            ).fetchall()
        return [dict(row) for row in rows]
