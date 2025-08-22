import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional


DEFAULT_DB_ENV_VAR = "BUDGETER_DB_PATH"
DEFAULT_DB_PATH = os.environ.get(
	DEFAULT_DB_ENV_VAR,
	str(Path.home() / ".budgeter" / "budgeter.db"),
)


def _ensure_parent_directory(database_path: str) -> None:
	parent_dir = Path(database_path).expanduser().resolve().parent
	parent_dir.mkdir(parents=True, exist_ok=True)


def _apply_migrations(connection: sqlite3.Connection) -> None:
	cursor = connection.cursor()
	# Create schema_version table if not exists
	cursor.execute(
		"""
		CREATE TABLE IF NOT EXISTS schema_version (
			version INTEGER NOT NULL
		);
		"""
	)
	# Initialize version row if empty
	row = cursor.execute("SELECT COUNT(*) FROM schema_version").fetchone()
	if row and row[0] == 0:
		cursor.execute("INSERT INTO schema_version(version) VALUES (0)")

	version = cursor.execute("SELECT version FROM schema_version").fetchone()[0]

	def set_version(v: int) -> None:
		cursor.execute("UPDATE schema_version SET version = ?", (v,))

	# Migration 1: Initial tables
	if version < 1:
		cursor.executescript(
			"""
			CREATE TABLE IF NOT EXISTS profiles (
				id INTEGER PRIMARY KEY CHECK (id = 1),
				name TEXT,
				currency TEXT NOT NULL DEFAULT 'USD',
				monthly_net_income REAL NOT NULL DEFAULT 0,
				savings_rate_target REAL NOT NULL DEFAULT 0.2
			);

			CREATE TABLE IF NOT EXISTS categories (
				id INTEGER PRIMARY KEY,
				name TEXT NOT NULL UNIQUE,
				kind TEXT NOT NULL CHECK (kind IN ('need','want','saving','fixed','income')),
				is_active INTEGER NOT NULL DEFAULT 1
			);

			CREATE TABLE IF NOT EXISTS budgets (
				id INTEGER PRIMARY KEY,
				category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
				month TEXT NOT NULL, -- 'YYYY-MM'
				amount REAL NOT NULL,
				UNIQUE(category_id, month)
			);

			CREATE TABLE IF NOT EXISTS transactions (
				id INTEGER PRIMARY KEY,
				date TEXT NOT NULL, -- ISO 'YYYY-MM-DD'
				amount REAL NOT NULL,
				category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
				description TEXT,
				merchant TEXT,
				account TEXT
			);

			CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(date);
			CREATE INDEX IF NOT EXISTS idx_tx_category ON transactions(category_id);
			CREATE INDEX IF NOT EXISTS idx_budgets_month ON budgets(month);
			"""
		)
		set_version(1)

	connection.commit()


@contextmanager
def get_connection(database_path: Optional[str] = None) -> Iterator[sqlite3.Connection]:
	path = database_path or DEFAULT_DB_PATH
	_ensure_parent_directory(path)
	connection = sqlite3.connect(path)
	connection.row_factory = sqlite3.Row
	_apply_migrations(connection)
	try:
		yield connection
	finally:
		connection.commit()
		connection.close()