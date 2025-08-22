from __future__ import annotations

import calendar
import datetime as dt
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from .db import get_connection


CategoryKind = str  # 'need' | 'want' | 'saving' | 'fixed' | 'income'


@dataclass
class Profile:
	name: Optional[str]
	currency: str
	monthly_net_income: float
	savings_rate_target: float


@dataclass
class Category:
	id: int
	name: str
	kind: CategoryKind
	is_active: bool


@dataclass
class Transaction:
	id: int
	date: str
	amount: float
	category_id: Optional[int]
	description: Optional[str]
	merchant: Optional[str]
	account: Optional[str]


# ------------------ Profile ------------------

def init_profile(
	name: Optional[str],
	currency: str,
	monthly_net_income: float,	savings_rate_target: float,
	database_path: Optional[str] = None,
) -> None:
	with get_connection(database_path) as conn:
		conn.execute("DELETE FROM profiles")
		conn.execute(
			"""
			INSERT INTO profiles(id, name, currency, monthly_net_income, savings_rate_target)
			VALUES (1, ?, ?, ?, ?)
			""",
			(name, currency, monthly_net_income, savings_rate_target),
		)


def get_profile(database_path: Optional[str] = None) -> Profile:
	with get_connection(database_path) as conn:
		row = conn.execute("SELECT name, currency, monthly_net_income, savings_rate_target FROM profiles WHERE id = 1").fetchone()
		if not row:
			return Profile(name=None, currency="USD", monthly_net_income=0.0, savings_rate_target=0.2)
		return Profile(
			name=row["name"],
			currency=row["currency"],
			monthly_net_income=float(row["monthly_net_income"]),
			savings_rate_target=float(row["savings_rate_target"]),
		)


# ------------------ Categories ------------------

def add_category(name: str, kind: CategoryKind, database_path: Optional[str] = None) -> int:
	if kind not in {"need", "want", "saving", "fixed", "income"}:
		raise ValueError("kind must be one of: need, want, saving, fixed, income")
	with get_connection(database_path) as conn:
		cur = conn.execute(
			"INSERT OR IGNORE INTO categories(name, kind, is_active) VALUES(?, ?, 1)",
			(name, kind),
		)
		if cur.lastrowid:
			return int(cur.lastrowid)
		row = conn.execute("SELECT id FROM categories WHERE name = ?", (name,)).fetchone()
		return int(row["id"]) if row else -1


def list_categories(include_inactive: bool = False, database_path: Optional[str] = None) -> List[Category]:
	with get_connection(database_path) as conn:
		rows = conn.execute(
			"SELECT id, name, kind, is_active FROM categories WHERE (? = 1) OR is_active = 1 ORDER BY name",
			(1 if include_inactive else 0,),
		).fetchall()
		return [Category(int(r["id"]), r["name"], r["kind"], bool(r["is_active"])) for r in rows]


# ------------------ Budgets ------------------

def set_budget(category_name: str, month: str, amount: float, database_path: Optional[str] = None) -> None:
	_validate_month(month)
	with get_connection(database_path) as conn:
		row = conn.execute("SELECT id FROM categories WHERE name = ?", (category_name,)).fetchone()
		if not row:
			raise ValueError(f"Unknown category: {category_name}")
		category_id = int(row["id"])
		conn.execute(
			"INSERT INTO budgets(category_id, month, amount) VALUES(?, ?, ?)\n\t\tON CONFLICT(category_id, month) DO UPDATE SET amount = excluded.amount",
			(category_id, month, amount),
		)


def get_budgets(month: str, database_path: Optional[str] = None) -> Dict[str, float]:
	_validate_month(month)
	with get_connection(database_path) as conn:
		rows = conn.execute(
			"""
			SELECT c.name, b.amount FROM budgets b
			JOIN categories c ON c.id = b.category_id
			WHERE b.month = ?
			ORDER BY c.name
			""",
			(month,),
		).fetchall()
		return {r["name"]: float(r["amount"]) for r in rows}


# ------------------ Transactions ------------------

def add_transaction(
	date: str,	amount: float,	category_name: Optional[str] = None,
	description: Optional[str] = None,	merchant: Optional[str] = None,	account: Optional[str] = None,
	database_path: Optional[str] = None,
) -> int:
	_validate_date(date)
	with get_connection(database_path) as conn:
		category_id: Optional[int] = None
		if category_name:
			row = conn.execute("SELECT id FROM categories WHERE name = ?", (category_name,)).fetchone()
			if not row:
				raise ValueError(f"Unknown category: {category_name}")
			category_id = int(row["id"])
		cur = conn.execute(
			"""
			INSERT INTO transactions(date, amount, category_id, description, merchant, account)
			VALUES(?, ?, ?, ?, ?, ?)
			""",
			(date, amount, category_id, description, merchant, account),
		)
		return int(cur.lastrowid)


def import_transactions_csv(
	csv_path: str,	date_col: str,	amount_col: str,	category_col: Optional[str] = None,
	description_col: Optional[str] = None,	merchant_col: Optional[str] = None,	account_col: Optional[str] = None,
	database_path: Optional[str] = None,
) -> int:
	import csv
	count = 0
	with open(csv_path, "r", newline="", encoding="utf-8") as f:
		reader = csv.DictReader(f)
		for row in reader:
			date = row[date_col].strip()
			_validate_date(date)
			amount = float(row[amount_col])
			category_name = row[category_col].strip() if category_col and row.get(category_col) else None
			description = row[description_col].strip() if description_col and row.get(description_col) else None
			merchant = row[merchant_col].strip() if merchant_col and row.get(merchant_col) else None
			account = row[account_col].strip() if account_col and row.get(account_col) else None
			add_transaction(date, amount, category_name, description, merchant, account, database_path)
			count += 1
	return count


def export_transactions_csv(
	csv_path: str,	start_date: Optional[str] = None,	end_date: Optional[str] = None,	category_name: Optional[str] = None,
	database_path: Optional[str] = None,
) -> int:
	import csv
	if start_date:
		_validate_date(start_date)
	if end_date:
		_validate_date(end_date)
	with get_connection(database_path) as conn:
		params: List[object] = []
		where: List[str] = []
		if start_date:
			where.append("date >= ?")
			params.append(start_date)
		if end_date:
			where.append("date <= ?")
			params.append(end_date)
		if category_name:
			where.append("category_id = (SELECT id FROM categories WHERE name = ?)")
			params.append(category_name)
		where_clause = ("WHERE " + " AND ".join(where)) if where else ""
		rows = conn.execute(
			f"""
			SELECT t.id, t.date, t.amount, c.name as category, t.description, t.merchant, t.account
			FROM transactions t LEFT JOIN categories c ON c.id = t.category_id
			{where_clause}
			ORDER BY t.date
			""",
			tuple(params),
		).fetchall()
		with open(csv_path, "w", newline="", encoding="utf-8") as f:
			writer = csv.writer(f)
			writer.writerow(["id", "date", "amount", "category", "description", "merchant", "account"])
			for r in rows:
				writer.writerow([r["id"], r["date"], r["amount"], r["category"], r["description"], r["merchant"], r["account"]])
			return len(rows)


# ------------------ Reports ------------------

def monthly_report(month: str, database_path: Optional[str] = None) -> Dict[str, object]:
	_validate_month(month)
	start_date = f"{month}-01"
	last_day = calendar.monthrange(int(month[:4]), int(month[5:7]))[1]
	end_date = f"{month}-{last_day:02d}"
	with get_connection(database_path) as conn:
		# Totals
		rows = conn.execute(
			"""
			SELECT c.name as category, COALESCE(SUM(t.amount), 0) as spent
			FROM categories c
			LEFT JOIN transactions t ON t.category_id = c.id AND t.date BETWEEN ? AND ?
			WHERE c.is_active = 1 AND c.kind != 'income'
			GROUP BY c.name
			ORDER BY c.name
			""",
			(start_date, end_date),
		).fetchall()
		spent_by_category = {r["category"]: float(r["spent"]) for r in rows}

		budgets = conn.execute(
			"""
			SELECT c.name, b.amount FROM budgets b JOIN categories c ON c.id = b.category_id WHERE b.month = ?
			""",
			(month,),
		).fetchall()
		budget_by_category = {r["name"]: float(r["amount"]) for r in budgets}

		total_spent = sum(spent_by_category.values())
		total_budget = sum(budget_by_category.values())
		variance = total_budget - total_spent

		return {
			"month": month,
			"spent_by_category": spent_by_category,
			"budget_by_category": budget_by_category,
			"total_spent": total_spent,
			"total_budget": total_budget,
			"variance": variance,
		}


# ------------------ Recommendations ------------------

def recommend_budgets(target_month: str, database_path: Optional[str] = None) -> Dict[str, float]:
	"""Recommend monthly budgets using 50/30/20 adjusted by fixed costs and history."""
	_validate_month(target_month)
	profile = get_profile(database_path)
	income = max(profile.monthly_net_income, 0.0)
	if income <= 0:
		return {}
	with get_connection(database_path) as conn:
		# Compute historical averages for last 3 complete months
		year, month = map(int, target_month.split("-"))
		history_months: List[str] = []
		for i in range(1, 4):
			m = month - i
			y = year
			while m <= 0:
				m += 12
				y -= 1
			history_months.append(f"{y}-{m:02d}")

		rows = conn.execute(
			"""
			SELECT c.name, c.kind, SUBSTR(t.date, 1, 7) as month, COALESCE(SUM(t.amount),0) as spent
			FROM categories c
			LEFT JOIN transactions t ON t.category_id = c.id AND SUBSTR(t.date,1,7) IN ({})
			WHERE c.is_active = 1 AND c.kind != 'income'
			GROUP BY c.name, c.kind, month
			""".format(
				",".join(["?"] * len(history_months)) or "''"
			),
			tuple(history_months),
		).fetchall()

		spend_history: Dict[Tuple[str, str], float] = defaultdict(float)
		category_kinds: Dict[str, str] = {}
		for r in rows:
			category_kinds[r["name"]] = r["kind"]
			if r["month"]:
				spend_history[(r["name"], r["kind"]) ] += float(r["spent"]) / max(len(history_months), 1)

		# Ensure categories exist for allocation
		cat_rows = conn.execute("SELECT name, kind FROM categories WHERE is_active = 1").fetchall()
		for r in cat_rows:
			category_kinds[r["name"]] = r["kind"]

		# Fixed baseline
		fixed_total = sum(v for (n, k), v in spend_history.items() if k == "fixed")

		savings_target = income * max(min(profile.savings_rate_target, 0.95), 0.0)

		needs_target = max(income * 0.5 - fixed_total, 0.0)
		wants_target = income * 0.3

		remaining = income - savings_target - fixed_total
		if remaining < 0:
			# Reduce wants first, then needs
			wants_target = max(wants_target + remaining, 0.0)
			remaining = income - savings_target - fixed_total - wants_target
			needs_target = max(remaining, 0.0)

		# Distribute across categories proportional to history else evenly
		def distribute(target_amount: float, kinds: Iterable[str]) -> Dict[str, float]:
			eligible = [n for n, k in category_kinds.items() if k in set(kinds)]
			if not eligible or target_amount <= 0:
				return {}
			weights = []
			for name in eligible:
				w = spend_history.get((name, category_kinds[name]), 0.0)
				weights.append(max(w, 0.0))
			total_w = sum(weights)
			alloc: Dict[str, float] = {}
			if total_w <= 0:
				per = target_amount / len(eligible)
				for name in eligible:
					alloc[name] = per
			else:
				for name, w in zip(eligible, weights):
					alloc[name] = target_amount * (w / total_w)
			return alloc

		recommended: Dict[str, float] = {}
		# Fixed: use history
		for (name, kind), value in spend_history.items():
			if kind == "fixed":
				recommended[name] = value

		for name, amount in distribute(needs_target, {"need"}).items():
			recommended[name] = recommended.get(name, 0.0) + amount
		for name, amount in distribute(wants_target, {"want"}).items():
			recommended[name] = recommended.get(name, 0.0) + amount

		# Savings category
		# Find or create a saving category
		saving_category_name = None
		for n, k in category_kinds.items():
			if k == "saving":
				saving_category_name = n
				break
		if not saving_category_name:
			saving_category_name = "Savings"
			conn.execute(
				"INSERT OR IGNORE INTO categories(name, kind, is_active) VALUES(?, 'saving', 1)",
				(saving_category_name,),
			)
		recommended[saving_category_name] = max(savings_target, 0.0)

		return {k: float(round(v, 2)) for k, v in recommended.items() if v > 0.0}


# ------------------ Utilities ------------------

def _validate_date(date: str) -> None:
	try:
		dt.datetime.strptime(date, "%Y-%m-%d")
	except ValueError as e:
		raise ValueError("date must be YYYY-MM-DD") from e


def _validate_month(month: str) -> None:
	try:
		dt.datetime.strptime(month + "-01", "%Y-%m-%d")
	except ValueError as e:
		raise ValueError("month must be YYYY-MM") from e