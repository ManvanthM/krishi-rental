CREATE DATABASE IF NOT EXISTS krishi_equipment_rental;
USE krishi_equipment_rental;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('admin', 'producer', 'farmer') NOT NULL,
    phone VARCHAR(15) NOT NULL,
    aadhaar VARCHAR(12) UNIQUE,
    aadhaar_image VARCHAR(255),
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS equipment (
    id INT AUTO_INCREMENT PRIMARY KEY,
    producer_id INT NOT NULL,
    name VARCHAR(150) NOT NULL,
    description TEXT NOT NULL,
    rent_per_day DECIMAL(10, 2) NOT NULL,
    quantity INT NOT NULL DEFAULT 0,
    max_days INT NOT NULL,
    deposit DECIMAL(10, 2) NOT NULL DEFAULT 0,
    image VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_equipment_producer
        FOREIGN KEY (producer_id) REFERENCES users(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS qc_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    producer_id INT NOT NULL,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    phone VARCHAR(15) NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_qc_producer
        FOREIGN KEY (producer_id) REFERENCES users(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS rentals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    farmer_id INT NOT NULL,
    equipment_id INT NOT NULL,
    qc_id INT NULL,
    from_date DATE NOT NULL,
    to_date DATE NOT NULL,
    returned_on DATE NULL,
    total_days INT NOT NULL,
    total_rent DECIMAL(10, 2) NOT NULL,
    deposit DECIMAL(10, 2) NOT NULL,
    fine_amount DECIMAL(10, 2) NOT NULL DEFAULT 0,
    damage_cost DECIMAL(10, 2) NOT NULL DEFAULT 0,
    refund_amount DECIMAL(10, 2) NOT NULL DEFAULT 0,
    damage_percent INT NOT NULL DEFAULT 0,
    status ENUM('Rented', 'In QC', 'Returned', 'Rejected') NOT NULL DEFAULT 'Rented',
    payment_method ENUM('UPI', 'Card') NOT NULL,
    qc_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    qc_processed_on DATETIME NULL,
    CONSTRAINT fk_rental_farmer
        FOREIGN KEY (farmer_id) REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_rental_equipment
        FOREIGN KEY (equipment_id) REFERENCES equipment(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_rental_qc
        FOREIGN KEY (qc_id) REFERENCES qc_users(id)
        ON DELETE SET NULL
);

CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_equipment_producer ON equipment(producer_id);
CREATE INDEX idx_rentals_status ON rentals(status);
CREATE INDEX idx_rentals_farmer ON rentals(farmer_id);

-- Default admin user is created automatically by the Flask application
-- on first launch if no admin account exists.
