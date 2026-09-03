PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    surename TEXT,
    username TEXT UNIQUE,
    password_hash TEXT,
    user_type INTEGER
);

CREATE TABLE IF NOT EXISTS business (
    business_id INTEGER PRIMARY KEY,
    name TEXT,
    description TEXT,
    owner_id INTEGER,
    FOREIGN KEY (owner_id) REFERENCES users (user_id)
);

CREATE TABLE IF NOT EXISTS services (
    service_id INTEGER PRIMARY KEY,
    business_id INTEGER,
    name TEXT,
    description TEXT,
    price REAL,
    FOREIGN KEY (business_id) REFERENCES business (business_id)
);

CREATE TABLE IF NOT EXISTS appointment (
    appointment_id INTEGER PRIMARY KEY,
    user_id INTEGER,
    provider_id INTEGER,
    service_id INTEGER,
    date INTEGER,
    status TEXT,
    FOREIGN KEY (user_id) REFERENCES users (user_id),
    FOREIGN KEY (provider_id) REFERENCES users (user_id),
    FOREIGN KEY (service_id) REFERENCES services (service_id)
);