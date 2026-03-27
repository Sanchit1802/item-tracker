from __future__ import annotations

import os


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


# AWS
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")

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

# S3 — QR codes
QR_S3_BUCKET = os.getenv("QR_S3_BUCKET")
QR_S3_PREFIX = os.getenv("QR_S3_PREFIX", "static/qr_codes").strip("/")
QR_S3_PUBLIC_READ = _get_bool("QR_S3_PUBLIC_READ", True)

# S3 — Static assets (logo, CSS, images)
S3_STATIC_BUCKET = os.getenv("S3_STATIC_BUCKET")
S3_STATIC_PREFIX = os.getenv("S3_STATIC_PREFIX", "static").strip("/")


def get_s3_static_url() -> str | None:
    """Build the base URL for serving static assets from S3.

    Returns something like:
        https://bucket-name.s3.ap-south-1.amazonaws.com/static

    Returns None if S3_STATIC_BUCKET is not configured (falls back to local).
    """
    if not S3_STATIC_BUCKET:
        return None
    region = (AWS_REGION or "").strip()
    if not region or region == "us-east-1":
        base = f"https://{S3_STATIC_BUCKET}.s3.amazonaws.com"
    else:
        base = f"https://{S3_STATIC_BUCKET}.s3.{region}.amazonaws.com"
    prefix = S3_STATIC_PREFIX.strip("/")
    if prefix:
        return f"{base}/{prefix}"
    return base
