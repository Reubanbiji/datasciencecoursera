"""
Password hashing and verification utilities using PBKDF2-HMAC (stdlib only).

Stored format:
    pbkdf2_{algorithm}${iterations}${salt_b64}${hash_b64}

Defaults follow current practical guidance for PBKDF2-HMAC-SHA256.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from typing import Tuple

# Reasonable defaults for 2025. Adjust iterations upward over time.
DEFAULT_ALGORITHM = "sha256"
DEFAULT_ITERATIONS = 310_000
DEFAULT_SALT_LENGTH = 16  # bytes


def _b64encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64decode(data_str: str) -> bytes:
    return base64.b64decode(data_str.encode("ascii"))


def generate_salt(length: int = DEFAULT_SALT_LENGTH) -> bytes:
    if length < 16:
        # Enforce a practical minimum salt length
        raise ValueError("Salt length must be at least 16 bytes")
    return secrets.token_bytes(length)


def _pbkdf2(password: str, salt: bytes, iterations: int, algorithm: str) -> bytes:
    if not password:
        # Empty passwords are allowed by PBKDF2, but we generally want to avoid them
        raise ValueError("Password must not be empty")
    return hashlib.pbkdf2_hmac(algorithm, password.encode("utf-8"), salt, iterations)


def hash_password(
    password: str,
    *,
    iterations: int = DEFAULT_ITERATIONS,
    algorithm: str = DEFAULT_ALGORITHM,
    salt_length: int = DEFAULT_SALT_LENGTH,
) -> str:
    """
    Hash a password and return a storage string in the format:
        pbkdf2_{algorithm}${iterations}${salt_b64}${hash_b64}
    """
    salt = generate_salt(salt_length)
    dk = _pbkdf2(password, salt, iterations, algorithm)
    return f"pbkdf2_{algorithm}${iterations}${_b64encode(salt)}${_b64encode(dk)}"


def _parse_stored(stored: str) -> Tuple[str, int, bytes, bytes]:
    try:
        method, iterations_str, salt_b64, hash_b64 = stored.split("$")
    except ValueError:
        raise ValueError("Invalid stored password format") from None

    if not method.startswith("pbkdf2_"):
        raise ValueError("Unsupported method (expected pbkdf2_*)")

    algorithm = method[len("pbkdf2_") :]

    try:
        iterations = int(iterations_str)
    except ValueError:
        raise ValueError("Invalid iterations in stored hash") from None

    salt = _b64decode(salt_b64)
    dk = _b64decode(hash_b64)
    return algorithm, iterations, salt, dk


def verify_password(password: str, stored: str) -> bool:
    """
    Verify a plaintext password against a stored PBKDF2 hash string.
    Returns True if the password is correct, False otherwise.
    """
    try:
        algorithm, iterations, salt, expected_dk = _parse_stored(stored)
    except Exception:
        return False

    calculated = _pbkdf2(password, salt, iterations, algorithm)
    return hmac.compare_digest(calculated, expected_dk)


def needs_rehash(
    stored: str,
    *,
    desired_iterations: int = DEFAULT_ITERATIONS,
    desired_algorithm: str = DEFAULT_ALGORITHM,
    min_salt_length: int = DEFAULT_SALT_LENGTH,
) -> bool:
    """
    Indicate whether the stored hash should be upgraded to stronger parameters.
    """
    try:
        algorithm, iterations, salt, _ = _parse_stored(stored)
    except Exception:
        # If it cannot be parsed, treat as needing rehash
        return True

    if algorithm != desired_algorithm:
        return True
    if iterations < desired_iterations:
        return True
    if len(salt) < min_salt_length:
        return True
    return False


def random_password(length: int = 16) -> str:
    """
    Generate a random URL-safe password with the given byte length (~4/3 longer when encoded).
    """
    # token_urlsafe returns text; length is number of bytes before encoding
    return secrets.token_urlsafe(length)