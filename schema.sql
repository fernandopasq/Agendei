PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    surename TEXT,
    username TEXT UNIQUE,
    password_hash TEXT,
    phone TEXT UNIQUE,
    user_type INTEGER
);

CREATE TABLE IF NOT EXISTS business (
    business_id INTEGER PRIMARY KEY,
    name TEXT,
    description TEXT,
    owner_id INTEGER,
    phone TEXT UNIQUE,
    FOREIGN KEY (owner_id) REFERENCES users (user_id)
);

CREATE TABLE IF NOT EXISTS services (
    service_id INTEGER PRIMARY KEY,
    business_id INTEGER,
    name TEXT,
    description TEXT,
    price REAL,
    duration_minutes INTEGER NOT NULL DEFAULT 30,
    FOREIGN KEY (business_id) REFERENCES business (business_id)
);

CREATE TABLE IF NOT EXISTS appointment (
    appointment_id INTEGER PRIMARY KEY,
    user_id INTEGER,
    provider_id INTEGER,
    service_id INTEGER,
    date TEXT,
    appointment_time TEXT,
    duration_minutes INTEGER NOT NULL DEFAULT 30,
    status TEXT,
    FOREIGN KEY (user_id) REFERENCES users (user_id),
    FOREIGN KEY (provider_id) REFERENCES users (user_id),
    FOREIGN KEY (service_id) REFERENCES services (service_id)
);