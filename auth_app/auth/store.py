"""
A minimal JSON-backed user store for demo purposes.
Not for production without proper locking and persistence guarantees.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, Optional

from .password import hash_password, verify_password, needs_rehash


@dataclass
class User:
    username: str
    password_hash: str


class JsonUserStore:
    def __init__(self, path: str):
        self.path = path
        self._users: Dict[str, User] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.path):
            self._users = {}
            return
        with open(self.path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        self._users = {
            username: User(username=username, password_hash=data["password_hash"]) for username, data in raw.items()
        }

    def _save(self) -> None:
        directory = os.path.dirname(self.path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({u: {"password_hash": usr.password_hash} for u, usr in self._users.items()}, f, indent=2)

    def get_user(self, username: str) -> Optional[User]:
        return self._users.get(username)

    def register(self, username: str, password: str) -> bool:
        if username in self._users:
            return False
        self._users[username] = User(username=username, password_hash=hash_password(password))
        self._save()
        return True

    def authenticate(self, username: str, password: str) -> bool:
        user = self._users.get(username)
        if not user:
            return False
        if not verify_password(password, user.password_hash):
            return False
        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
            self._save()
        return True

    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        user = self._users.get(username)
        if not user:
            return False
        if not verify_password(old_password, user.password_hash):
            return False
        user.password_hash = hash_password(new_password)
        self._save()
        return True