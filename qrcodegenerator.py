import qrcode
import os
import logging
import tempfile
import shutil
import mysql.connector

import aws_config

try:
    import boto3
    from botocore.config import Config as BotoConfig
    from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
except Exception:  # pragma: no cover
    boto3 = None


logger = logging.getLogger(__name__)


def connect():
    return mysql.connector.connect(
        host=aws_config.DB_HOST,
        port=aws_config.DB_PORT,
        user=aws_config.DB_USER,
        password=aws_config.DB_PASSWORD,
        database=aws_config.DB_NAME,
        connection_timeout=10,
    )


def _upload_to_s3(file_path: str, bucket: str, key: str) -> None:
    if boto3 is None:
        raise RuntimeError("boto3 is required for S3 uploads (pip install boto3)")

    # Uses the standard AWS credential provider chain:
    # env vars, shared config/credentials files, or instance/task role (EC2/ECS).
    s3 = boto3.client(
        "s3",
        region_name=aws_config.AWS_REGION,
        config=BotoConfig(retries={"max_attempts": 10, "mode": "standard"}),
    )

    extra_args = {"ContentType": "image/png"}
    if aws_config.QR_S3_PUBLIC_READ:
        extra_args["ACL"] = "public-read"

    try:
        s3.upload_file(file_path, bucket, key, ExtraArgs=extra_args)
    except NoCredentialsError as exc:
        raise RuntimeError(
            "AWS credentials not found. Configure an IAM role (recommended on EC2) "
            "or set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY (and optionally AWS_SESSION_TOKEN)."
        ) from exc
    except (ClientError, BotoCoreError) as exc:
        raise RuntimeError(f"S3 upload failed: {exc}") from exc


def _get_s3_client():
    if boto3 is None:
        raise RuntimeError("boto3 is required for S3 operations (pip install boto3)")

    return boto3.client(
        "s3",
        region_name=aws_config.AWS_REGION,
        config=BotoConfig(retries={"max_attempts": 10, "mode": "standard"}),
    )


def _s3_object_url(bucket: str, key: str) -> str:
    # Prefer virtual-hosted-style URL.
    region = (aws_config.AWS_REGION or "").strip()
    if not region or region == "us-east-1":
        return f"https://{bucket}.s3.amazonaws.com/{key}"
    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"


def _s3_presigned_get_url(bucket: str, key: str, expires_seconds: int = 3600) -> str:
    s3 = _get_s3_client()
    try:
        return s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_seconds,
        )
    except (ClientError, BotoCoreError) as exc:
        raise RuntimeError(f"Failed to create presigned URL: {exc}") from exc


def generate_qr_code(component_id, output_dir=None, component_url: str | None = None):
    """Generate QR code for a component.

    - Generates the QR PNG in a temporary local directory
    - Uploads it to S3 (QR_S3_BUCKET is required)
    - Cleans up the temp file after upload
    - Returns an S3 URL (public URL or presigned URL depending on QR_S3_PUBLIC_READ)
    """
    bucket = aws_config.QR_S3_BUCKET
    if not bucket:
        raise RuntimeError("QR_S3_BUCKET is required (QR codes are served only from S3).")

    # Generate locally into a temp directory, then upload to S3.
    tmp_dir = None
    if output_dir is None:
        tmp_dir = tempfile.mkdtemp(prefix="qr-")
        output_dir = tmp_dir
    os.makedirs(output_dir, exist_ok=True)

    if not component_url:
        public_base_url = aws_config.PUBLIC_BASE_URL.rstrip("/")
        component_url = f"{public_base_url}/components?compid={component_id}"

    qr = qrcode.make(component_url)
    qr_path = os.path.join(output_dir, f"{component_id}.png")
    qr.save(qr_path)
    logger.info(f"QR code generated for component ID: {component_id} at {qr_path}")

    key_prefix = aws_config.QR_S3_PREFIX.strip("/")
    key = f"{key_prefix}/{component_id}.png" if key_prefix else f"{component_id}.png"

    try:
        _upload_to_s3(qr_path, bucket, key)
    finally:
        # Clean up temp directory after upload
        if tmp_dir and os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)

    # Return a URL that the UI can use.
    if aws_config.QR_S3_PUBLIC_READ:
        return _s3_object_url(bucket, key)
    return _s3_presigned_get_url(bucket, key)


def generate_all_qr_codes():
    """Generate QR codes for all components in the database and upload to S3."""
    bucket = aws_config.QR_S3_BUCKET
    if not bucket:
        raise RuntimeError("QR_S3_BUCKET is required (QR codes are served only from S3).")

    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT component_id FROM components")
    component_ids = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()

    public_base_url = aws_config.PUBLIC_BASE_URL.rstrip("/")
    count = 0

    for component_id in component_ids:
        tmp_dir = tempfile.mkdtemp(prefix="qr-")
        try:
            component_url = f"{public_base_url}/components?compid={component_id}"
            qr = qrcode.make(component_url)
            qr_path = os.path.join(tmp_dir, f"{component_id}.png")
            qr.save(qr_path)

            key_prefix = aws_config.QR_S3_PREFIX.strip("/")
            key = f"{key_prefix}/{component_id}.png" if key_prefix else f"{component_id}.png"
            _upload_to_s3(qr_path, bucket, key)
            count += 1
            logger.info(f"QR code uploaded for component ID: {component_id}")
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    logger.info(f"Total QR codes generated and uploaded: {count}")
    return count


# Run this script directly to generate QR codes for all existing components
if __name__ == "__main__":
    generate_all_qr_codes()
