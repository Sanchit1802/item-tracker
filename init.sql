-- Initialize database schema (run once on RDS)
-- Safe to run multiple times: uses IF NOT EXISTS and idempotent seed inserts.
-- NOTE: DB_NAME in .env should match the database name below.

CREATE DATABASE IF NOT EXISTS component_tracker;
USE component_tracker;

CREATE TABLE IF NOT EXISTS components (
    component_id INT PRIMARY KEY,
    component_name VARCHAR(100),
    current_location VARCHAR(100),
    status VARCHAR(50),
    qr_code_path VARCHAR(200),
    last_updated DATETIME
);

CREATE TABLE IF NOT EXISTS movement_history (
    movement_id INT PRIMARY KEY AUTO_INCREMENT,
    component_id INT,
    location VARCHAR(100),
    status VARCHAR(50),
    timestamp DATETIME,
    CONSTRAINT fk_movement_component
        FOREIGN KEY (component_id) REFERENCES components(component_id)
);

-- Seed data (won't error if already present)
INSERT INTO components (component_id, component_name)
VALUES (101, 'Rubber')
ON DUPLICATE KEY UPDATE component_name = VALUES(component_name);

INSERT INTO components (component_id, component_name)
VALUES (102, 'Plastic')
ON DUPLICATE KEY UPDATE component_name = VALUES(component_name);