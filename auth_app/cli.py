#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys

from auth.store import JsonUserStore


def get_store() -> JsonUserStore:
    # Default data path under workspace
    data_path = os.environ.get("AUTH_STORE_PATH", os.path.join(os.path.dirname(__file__), "data", "users.json"))
    return JsonUserStore(data_path)


def cmd_register(args: argparse.Namespace) -> int:
    store = get_store()
    if store.register(args.username, args.password):
        print("User registered")
        return 0
    print("User already exists", file=sys.stderr)
    return 1


def cmd_login(args: argparse.Namespace) -> int:
    store = get_store()
    if store.authenticate(args.username, args.password):
        print("Authentication successful")
        return 0
    print("Authentication failed", file=sys.stderr)
    return 2


def cmd_change_password(args: argparse.Namespace) -> int:
    store = get_store()
    if store.change_password(args.username, args.old_password, args.new_password):
        print("Password changed")
        return 0
    print("Password change failed", file=sys.stderr)
    return 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simple password auth CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_reg = sub.add_parser("register", help="Register a new user")
    p_reg.add_argument("username")
    p_reg.add_argument("password")
    p_reg.set_defaults(func=cmd_register)

    p_login = sub.add_parser("login", help="Authenticate a user")
    p_login.add_argument("username")
    p_login.add_argument("password")
    p_login.set_defaults(func=cmd_login)

    p_chg = sub.add_parser("change-password", help="Change a user's password")
    p_chg.add_argument("username")
    p_chg.add_argument("old_password")
    p_chg.add_argument("new_password")
    p_chg.set_defaults(func=cmd_change_password)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())