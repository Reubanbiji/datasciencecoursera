# Budgeter - Personal CLI Budgeting Tool

A lightweight, personalized budgeting CLI app using SQLite. No external dependencies.

## Quickstart

- Initialize your profile (monthly net income and savings target):

```bash
python -m budgeter init-profile --name "Alex" --currency USD --monthly-income 5000 --savings-rate 0.2
```

- Add categories:

```bash
python -m budgeter add-category "Rent" fixed
python -m budgeter add-category "Groceries" need
python -m budgeter add-category "Dining" want
python -m budgeter add-category "Savings" saving
```

- Add a budget for a month:

```bash
python -m budgeter set-budget Groceries 2025-08 600
```

- Add a transaction:

```bash
python -m budgeter add-tx 2025-08-02 54.23 --category Groceries --merchant "Local Market"
```

- See report for a month:

```bash
python -m budgeter report-month 2025-08
```

- Get personalized recommendations for next month:

```bash
python -m budgeter recommend 2025-09
```

- Import transactions from CSV (columns can be mapped):

```bash
python -m budgeter import-csv mybank.csv --date-col Date --amount-col Amount --category-col Category --description-col Description
```

- Export transactions to CSV:

```bash
python -m budgeter export-csv out.csv --start-date 2025-08-01 --end-date 2025-08-31
```

## Database Location

By default, data is stored at `~/.budgeter/budgeter.db`. To override, set `BUDGETER_DB_PATH` or pass `--db /absolute/path/to.db` to commands.

## Notes

- Budgets and reports are per calendar month (`YYYY-MM`).
- Recommendations apply the 50/30/20 rule adjusted by your fixed costs and spending history.