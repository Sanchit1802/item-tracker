import qrcode
import os
import mysql.connector
try:
    import boto3
except Exception:  # pragma: no cover
    boto3 = None

def connect():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )


def _upload_to_s3(file_path: str, bucket: str, key: str) -> None:
    if boto3 is None:
        raise RuntimeError("boto3 is required for S3 uploads (pip install boto3)")

    s3 = boto3.client("s3")
    extra_args = {"ContentType": "image/png"}
    if os.getenv("QR_S3_PUBLIC_READ", "").lower() in {"1", "true", "yes"}:
        extra_args["ACL"] = "public-read"
    s3.upload_file(file_path, bucket, key, ExtraArgs=extra_args)

def generate_qr_code(component_id, output_dir=None, component_url: str | None = None):
    """Generate QR code for a component.

    - Writes the QR PNG to the local output_dir (defaults to static/qr_codes)
    - Optionally uploads it to S3 if QR_S3_BUCKET is set
    """
    # Get the directory where this script is located
    if output_dir is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(script_dir, 'static', 'qr_codes')

    os.makedirs(output_dir, exist_ok=True)
    if not component_url:
        public_base_url = os.getenv("PUBLIC_BASE_URL", "http://localhost:5000").rstrip("/")
        component_url = f"{public_base_url}/components?compid={component_id}"

    qr = qrcode.make(component_url)
    qr_path = os.path.join(output_dir, f"{component_id}.png")
    qr.save(qr_path)
    print(f"QR code generated for component ID: {component_id} at {qr_path}")

    bucket = os.getenv("QR_S3_BUCKET")
    if bucket:
        key_prefix = os.getenv("QR_S3_PREFIX", "qr_codes").strip("/")
        key = f"{key_prefix}/{component_id}.png" if key_prefix else f"{component_id}.png"
        _upload_to_s3(qr_path, bucket, key)

    return qr_path

def generate_all_qr_codes(output_dir=None):
    """Generate QR codes for all components in the database"""
    # Get the directory where this script is located
    if output_dir is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(script_dir, 'static', 'qr_codes')

    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT component_id FROM components")
    component_ids = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()

    os.makedirs(output_dir, exist_ok=True)

    public_base_url = os.getenv("PUBLIC_BASE_URL", "http://localhost:5000").rstrip("/")
    for component_id in component_ids:
        qr = qrcode.make(f"{public_base_url}/components?compid={component_id}")
        qr_path = os.path.join(output_dir, f"{component_id}.png")
        qr.save(qr_path)
        print(f"QR code generated for component ID: {component_id}")

    print(f"Total QR codes generated: {len(component_ids)}")
    return len(component_ids)

# Run this script directly to generate QR codes for all existing components
if __name__ == "__main__":
    generate_all_qr_codes()

