from flask import Flask, render_template, request, redirect
import mysql.connector
from mysql.connector import Error as MySQLError
from datetime import datetime
from qrcodegenerator import generate_qr_code
from dotenv import load_dotenv
import os
import logging

import aws_config

load_dotenv()

app = Flask(__name__)

# If running behind an AWS load balancer / reverse proxy, this helps Flask build
# correct external URLs when proxy headers are set.
# (Requires the proxy to set X-Forwarded-* headers.)
try:  # pragma: no cover
    from werkzeug.middleware.proxy_fix import ProxyFix

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
except Exception:
    pass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def connect():
    if not aws_config.DB_HOST or not aws_config.DB_USER or not aws_config.DB_PASSWORD:
        raise RuntimeError(
            "Database environment variables not set. "
            "Required: DB_HOST, DB_USER, DB_PASSWORD (and optionally DB_NAME, DB_PORT)."
        )
    return mysql.connector.connect(
        host=aws_config.DB_HOST,
        port=aws_config.DB_PORT,
        user=aws_config.DB_USER,
        password=aws_config.DB_PASSWORD,
        database=aws_config.DB_NAME,
        connection_timeout=10,
    )


def get_base_url():
    """Get the base URL from environment or construct it from request"""
    base_url = aws_config.BASE_URL
    if base_url:
        return base_url.rstrip("/")
    # Fallback to request host
    return f"http://{request.host}"


def _template_globals():
    """Common template variables passed to every render_template call."""
    return {
        "public_base_url": aws_config.PUBLIC_BASE_URL,
        "s3_static_url": aws_config.get_s3_static_url(),
    }


@app.route('/')
def home():
    success = request.args.get('success')
    error = request.args.get('error')
    return render_template(
        'home.html',
        success_msg=success,
        error_msg=error,
        **_template_globals(),
    )


@app.route('/update', methods=['POST'])
def update():
    component_id = request.form['compid']
    location = request.form['location']
    status = request.form['status']
    now = datetime.now()

    try:
        conn = connect()
        cursor = conn.cursor()
    except (RuntimeError, MySQLError) as db_err:
        logger.exception("Database connection failed")
        return redirect(f"/?error=Database connection failed: {db_err}")

    try:
        # Update current status
        cursor.execute("""
            UPDATE components
            SET current_location=%s, status=%s, last_updated=%s
            WHERE component_id=%s
        """, (location, status, now, component_id))

        # Insert movement history
        cursor.execute("""
            INSERT INTO movement_history (component_id, location, status, timestamp)
            VALUES (%s, %s, %s, %s)
        """, (component_id, location, status, now))

        conn.commit()
    except MySQLError as db_err:
        logger.exception("Database update failed")
        return redirect(f"/?error=Database update failed: {db_err}")
    finally:
        cursor.close()
        conn.close()

    base_url = get_base_url()
    return redirect(f"{base_url}/components?compid={component_id}")


@app.route('/components', methods=['GET'])
def components():
    component_id = request.args.get('compid')
    if not component_id:
        return redirect("/?error=No component ID provided")

    try:
        conn = connect()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM components WHERE component_id=%s", (component_id,))
        data = cursor.fetchone()
        cursor.close()

        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT timestamp,status,location FROM movement_history WHERE component_id=%s",
            (component_id,),
        )
        history = cursor.fetchall()
        cursor.close()
        conn.close()
    except (RuntimeError, MySQLError) as db_err:
        logger.exception("Database query failed")
        return redirect(f"/?error=Database query failed: {db_err}")

    if data is None:
        return redirect(f"/?error=Component ID {component_id} not found")

    return render_template(
        'item.html', data=data, history=history, compid=component_id,
        **_template_globals(),
    )


@app.route('/add_component', methods=['POST'])
def add_component():
    component_id = request.form['compid']
    component_name = request.form['compname']
    location = request.form.get('location', '')
    status = request.form.get('status', '')
    now = datetime.now()

    try:
        conn = connect()
        cursor = conn.cursor()
    except (RuntimeError, MySQLError) as db_err:
        logger.exception("Database connection failed")
        return redirect(f"/?error=Database connection failed: {db_err}")

    try:
        # Insert into components table
        cursor.execute("""
            INSERT INTO components (component_id, component_name, current_location, status, last_updated)
            VALUES (%s, %s, %s, %s, %s)
        """, (component_id, component_name, location, status, now))

        # Insert into movement history if location and status are provided
        if location and status:
            cursor.execute("""
                INSERT INTO movement_history (component_id, location, status, timestamp)
                VALUES (%s, %s, %s, %s)
            """, (component_id, location, status, now))

        conn.commit()

        # Generate QR code for the new component
        try:
            generate_qr_code(component_id)
        except Exception as qr_error:
            logger.error(f"Error generating QR code: {qr_error}")
            # Continue even if QR generation fails

        return redirect(f"/?success=Component {component_id} added successfully")
    except mysql.connector.IntegrityError:
        return redirect(f"/?error=Component ID {component_id} already exists")
    finally:
        cursor.close()
        conn.close()


@app.route('/record', methods=['GET'])
def record():
    component_id = request.args.get('compid')

    if component_id:
        # Check if component exists in database
        try:
            conn = connect()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT component_id FROM components WHERE component_id=%s", (component_id,)
            )
            result = cursor.fetchone()
            cursor.close()
            conn.close()
        except (RuntimeError, MySQLError) as db_err:
            logger.exception("Database query failed")
            return render_template(
                'home.html', compid=component_id, exists=False,
                error_msg=str(db_err), **_template_globals(),
            )

        if result:
            # Component exists, show QR code
            try:
                # Returns S3 URL when configured, otherwise local file path.
                qr_image_url = generate_qr_code(component_id)
            except Exception as qr_error:
                logger.exception("Error generating QR code")
                return render_template(
                    'home.html',
                    compid=component_id,
                    exists=True,
                    error_msg=f"QR code generation failed: {qr_error}",
                    **_template_globals(),
                )

            return render_template(
                'home.html',
                compid=component_id,
                exists=True,
                qr_image_url=qr_image_url,
                **_template_globals(),
            )
        else:
            # Component doesn't exist, show error
            return render_template(
                'home.html',
                compid=component_id,
                exists=False,
                error=True,
                **_template_globals(),
            )

    # No component ID provided, just show the form
    return render_template('home.html', **_template_globals())


if __name__ == '__main__':
    # Don't use debug mode in production
    debug_mode = aws_config.FLASK_DEBUG
    app.run(host="0.0.0.0", port=aws_config.PORT, debug=debug_mode)
