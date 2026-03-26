# Internship Project (Flask + MySQL)

This is a simple Flask app that tracks components in a MySQL database and generates QR codes for each component.

## Requirements

- Python 3.11+
- MySQL server running locally or remotely

## Setup (local)

```bash
cd "Main Project"
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Environment variables

The app reads these variables (defaults shown):

- `DB_HOST` (default `127.0.0.1`)
- `DB_PORT` (default `3306`)
- `DB_USER` (default `root`)
- `DB_PASSWORD` (default empty)
- `DB_NAME` (default `main`)
- `PORT` (default `5000`)

Optional (QR/links):

- `PUBLIC_BASE_URL` (e.g. `http://localhost:5000`)
- `QR_IMAGE_BASE_URL` (if QR images are hosted elsewhere)
- `QR_S3_BUCKET`, `QR_S3_PREFIX`, `QR_S3_PUBLIC_READ` (only if you want S3 uploads)

You can copy the example file and edit it:

```powershell
Copy-Item .env.example .env
```

## Database tables

The app expects two tables:

- `components` with: `component_id`, `component_name`, `current_location`, `status`, `last_updated`
- `movement_history` with: `component_id`, `location`, `status`, `timestamp`

If you want a starter schema (adjust types/sizes as needed):

```sql
CREATE TABLE IF NOT EXISTS components (
  component_id VARCHAR(64) PRIMARY KEY,
  component_name VARCHAR(255) NOT NULL,
  current_location VARCHAR(255),
  status VARCHAR(255),
  last_updated DATETIME
);

CREATE TABLE IF NOT EXISTS movement_history (
  id INT AUTO_INCREMENT PRIMARY KEY,
  component_id VARCHAR(64) NOT NULL,
  location VARCHAR(255),
  status VARCHAR(255),
  timestamp DATETIME,
  INDEX (component_id),
  CONSTRAINT fk_mh_component
    FOREIGN KEY (component_id) REFERENCES components(component_id)
    ON DELETE CASCADE
);
```

## Run

```bash
cd "Main Project"
python app.py
```

Open:

- http://localhost:5000/
- Health check: http://localhost:5000/health

## Use GitHub (no Docker)

1) Create a new repo on GitHub (no files needed).

2) From this folder:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```
