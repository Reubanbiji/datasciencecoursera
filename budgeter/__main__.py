import argparse
import json
from typing import Optional

from .service import (
	add_category,
	add_transaction,
	get_budgets,
	get_profile,
	import_transactions_csv,
	export_transactions_csv,
	init_profile,
	list_categories,
	monthly_report,
	recommend_budgets,
	set_budget,
)


def _add_profile_commands(subparsers):
	p = subparsers.add_parser("init-profile", help="Create or reset your profile")
	p.add_argument("--name", type=str, default=None)
	p.add_argument("--currency", type=str, default="USD")
	p.add_argument("--monthly-income", type=float, required=True)
	p.add_argument("--savings-rate", type=float, default=0.2)
	p.add_argument("--db", type=str, default=None)
	p.set_defaults(func=_cmd_init_profile)

	p = subparsers.add_parser("show-profile", help="Show profile")
	p.add_argument("--db", type=str, default=None)
	p.set_defaults(func=_cmd_show_profile)


def _cmd_init_profile(args):
	init_profile(args.name, args.currency, args.monthly_income, args.savings_rate, args.db)
	print("Profile saved.")


def _cmd_show_profile(args):
	p = get_profile(args.db)
	print(json.dumps(p.__dict__, indent=2))


def _add_category_commands(subparsers):
	p = subparsers.add_parser("add-category", help="Add a category")
	p.add_argument("name", type=str)
	p.add_argument("kind", type=str, choices=["need", "want", "saving", "fixed", "income"])
	p.add_argument("--db", type=str, default=None)
	p.set_defaults(func=_cmd_add_category)

	p = subparsers.add_parser("list-categories", help="List categories")
	p.add_argument("--include-inactive", action="store_true")
	p.add_argument("--db", type=str, default=None)
	p.set_defaults(func=_cmd_list_categories)


def _cmd_add_category(args):
	cid = add_category(args.name, args.kind, args.db)
	print(f"Category id={cid}")


def _cmd_list_categories(args):
	cats = list_categories(args.include_inactive, args.db)
	for c in cats:
		print(f"{c.id}\t{c.name}\t{c.kind}\t{'active' if c.is_active else 'inactive'}")


def _add_budget_commands(subparsers):
	p = subparsers.add_parser("set-budget", help="Set budget for a category in a month")
	p.add_argument("category", type=str)
	p.add_argument("month", type=str, help="YYYY-MM")
	p.add_argument("amount", type=float)
	p.add_argument("--db", type=str, default=None)
	p.set_defaults(func=_cmd_set_budget)

	p = subparsers.add_parser("get-budgets", help="Show budgets for a month")
	p.add_argument("month", type=str)
	p.add_argument("--db", type=str, default=None)
	p.set_defaults(func=_cmd_get_budgets)


def _cmd_set_budget(args):
	set_budget(args.category, args.month, args.amount, args.db)
	print("Budget saved.")


def _cmd_get_budgets(args):
	budgets = get_budgets(args.month, args.db)
	print(json.dumps(budgets, indent=2))


def _add_transaction_commands(subparsers):
	p = subparsers.add_parser("add-tx", help="Add a transaction")
	p.add_argument("date", type=str, help="YYYY-MM-DD")
	p.add_argument("amount", type=float)
	p.add_argument("--category", type=str, default=None)
	p.add_argument("--description", type=str, default=None)
	p.add_argument("--merchant", type=str, default=None)
	p.add_argument("--account", type=str, default=None)
	p.add_argument("--db", type=str, default=None)
	p.set_defaults(func=_cmd_add_tx)

	p = subparsers.add_parser("import-csv", help="Import transactions from CSV")
	p.add_argument("csv_path", type=str)
	p.add_argument("--date-col", type=str, required=True)
	p.add_argument("--amount-col", type=str, required=True)
	p.add_argument("--category-col", type=str)
	p.add_argument("--description-col", type=str)
	p.add_argument("--merchant-col", type=str)
	p.add_argument("--account-col", type=str)
	p.add_argument("--db", type=str, default=None)
	p.set_defaults(func=_cmd_import_csv)

	p = subparsers.add_parser("export-csv", help="Export transactions to CSV")
	p.add_argument("csv_path", type=str)
	p.add_argument("--start-date", type=str)
	p.add_argument("--end-date", type=str)
	p.add_argument("--category", type=str)
	p.add_argument("--db", type=str, default=None)
	p.set_defaults(func=_cmd_export_csv)


def _cmd_add_tx(args):
	id_ = add_transaction(args.date, args.amount, args.category, args.description, args.merchant, args.account, args.db)
	print(f"Transaction id={id_}")


def _cmd_import_csv(args):
	count = import_transactions_csv(
		args.csv_path,
		args.date_col,
		args.amount_col,
		args.category_col,
		args.description_col,
		args.merchant_col,
		args.account_col,
		args.db,
	)
	print(f"Imported {count} transactions")


def _cmd_export_csv(args):
	count = export_transactions_csv(
		args.csv_path,
		args.start_date,
		args.end_date,
		args.category,
		args.db,
	)
	print(f"Exported {count} transactions")


def _add_report_commands(subparsers):
	p = subparsers.add_parser("report-month", help="Show monthly report")
	p.add_argument("month", type=str)
	p.add_argument("--db", type=str, default=None)
	p.set_defaults(func=_cmd_report_month)

	p = subparsers.add_parser("recommend", help="Recommend budgets for a month")
	p.add_argument("month", type=str)
	p.add_argument("--db", type=str, default=None)
	p.set_defaults(func=_cmd_recommend)


def _cmd_report_month(args):
	r = monthly_report(args.month, args.db)
	print(json.dumps(r, indent=2))


def _cmd_recommend(args):
	rec = recommend_budgets(args.month, args.db)
	print(json.dumps(rec, indent=2))


def main(argv: Optional[list] = None) -> None:
	parser = argparse.ArgumentParser(prog="budgeter", description="Personal budgeting CLI with SQLite")
	subparsers = parser.add_subparsers(dest="command")

	_add_profile_commands(subparsers)
	_add_category_commands(subparsers)
	_add_budget_commands(subparsers)
	_add_transaction_commands(subparsers)
	_add_report_commands(subparsers)

	args = parser.parse_args(argv)
	if not hasattr(args, "func"):
		parser.print_help()
		return
	args.func(args)


if __name__ == "__main__":
	main()