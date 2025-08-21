# Simple Password Authentication (PBKDF2-HMAC)

This project provides a minimal, dependency-free password hashing and verification utility using PBKDF2-HMAC (stdlib only), a JSON-backed user store, and a small CLI for demo purposes.

Not intended for production as-is. Add proper persistence, logging, input validation, and rate limiting.

## Requirements
- Python 3.9+

## Layout
- `auth/password.py`: PBKDF2 hash/verify utilities
- `auth/store.py`: JSON-backed user store with register/auth/change
- `cli.py`: CLI to interact with the store

## Usage

By default, user data is stored at `auth_app/data/users.json`. Override with `AUTH_STORE_PATH`.

### Register a user
```bash
python -m auth_app.cli register alice S3cret!pass
```

### Authenticate
```bash
python -m auth_app.cli login alice S3cret!pass
```

### Change password
```bash
python -m auth_app.cli change-password alice S3cret!pass N3wS3cret!
```

## Library example
```python
from auth_app.auth.password import hash_password, verify_password, needs_rehash

stored = hash_password("S3cret!pass")
assert verify_password("S3cret!pass", stored)
assert not verify_password("wrong", stored)
if needs_rehash(stored):
    stored = hash_password("S3cret!pass")
```

## Security notes
- Uses PBKDF2-HMAC-SHA256 with 310k iterations by default (2025 baseline).
- Per-user random 16-byte salt stored alongside the hash.
- Constant-time comparison to avoid timing attacks.
- Rehash-on-login if parameters are outdated.

Consider using dedicated libraries like `argon2-cffi` or `passlib` for production.