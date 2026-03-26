from flask import Flask, render_template, request, redirect
import mysql.connector
from datetime import datetime
from qrcodegenerator import generate_qr_code
from dotenv import load_dotenv
import os
import logging

load_dotenv()

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def connect():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

def get_base_url():
    """Get the base URL from environment or construct it from request"""
    base_url = os.getenv("BASE_URL")
    if base_url:
        return base_url.rstrip("/")
    # Fallback to request host
    return f"http://{request.host}"

@app.route('/')
def home():
    success = request.args.get('success')
    error = request.args.get('error')
    return render_template('home.html', success_msg=success, error_msg=error)

@app.route('/update', methods=['POST'])
def update():
    component_id = request.form['compid']
    location = request.form['location']
    status = request.form['status']
    now = datetime.now()

    conn = connect()
    cursor = conn.cursor()

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
    cursor.close()
    conn.close()
    base_url = get_base_url()
    return redirect(f"{base_url}/components?compid={component_id}")

@app.route('/components', methods=['GET'])
def components():
    component_id = request.args.get('compid')
    conn = connect()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM components WHERE component_id=%s", (component_id,))
    data = cursor.fetchone()
    cursor.close()
    conn.close()

    conn = connect()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT timestamp,status,location FROM movement_history WHERE component_id=%s", (component_id,))
    history = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('item.html', data=data, history=history, compid=component_id)

@app.route('/add_component', methods=['POST'])
def add_component():
    component_id = request.form['compid']
    component_name = request.form['compname']
    location = request.form.get('location', '')
    status = request.form.get('status', '')
    now = datetime.now()

    conn = connect()
    cursor = conn.cursor()

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
        cursor.close()
        conn.close()

        # Generate QR code for the new component
        try:
            generate_qr_code(component_id)
        except Exception as qr_error:
            logger.error(f"Error generating QR code: {qr_error}")
            # Continue even if QR generation fails

        return redirect(f"/?success=Component {component_id} added successfully")
    except mysql.connector.IntegrityError:
        cursor.close()
        conn.close()
        return redirect(f"/?error=Component ID {component_id} already exists")

@app.route('/record', methods=['GET'])
def record():
    component_id = request.args.get('compid')

    if component_id:
        # Check if component exists in database
        conn = connect()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT component_id FROM components WHERE component_id=%s", (component_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result:
            # Component exists, show QR code
            qr_image_url = f"/static/qr_codes/{component_id}.png"
            return render_template('home.html', compid=component_id, exists=True, qr_image_url=qr_image_url)
        else:
            # Component doesn't exist, show error
            return render_template('home.html', compid=component_id, exists=False, error=True)

    # No component ID provided, just show the form
    return render_template('home.html')

if __name__ == '__main__':
    # Don't use debug mode in production
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=debug_mode)
