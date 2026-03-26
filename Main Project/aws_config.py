"""AWS configuration helpers.

This project is deployed on AWS using:
- EC2 for the Flask app
- RDS MySQL for the database
- S3 for storing QR code images (optional)

The app primarily reads configuration directly from environment variables (see .env.example).
This module centralizes those names/defaults for convenience.
"""

from __future__ import annotations

import os


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


# AWS
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# RDS (MySQL)
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_NAME = os.getenv("DB_NAME", "component_tracker")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# App
FLASK_DEBUG = _get_bool("FLASK_DEBUG", False)
PORT = int(os.getenv("PORT", 5000))
BASE_URL = os.getenv("BASE_URL", "http://localhost:5000").rstrip("/")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", BASE_URL).rstrip("/")

# S3 (optional)
QR_S3_BUCKET = os.getenv("QR_S3_BUCKET")
QR_S3_PREFIX = os.getenv("QR_S3_PREFIX", "qr_codes").strip("/")
QR_S3_PUBLIC_READ = _get_bool("QR_S3_PUBLIC_READ", True)

