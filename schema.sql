PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER,
    name TEXT,
    surename TEXT,
    username TEXT UNIQUE,
    password_hash TEXT,
    user_type INTEGER,
    phone TEXT,
    PRIMARY KEY (user_id AUTOINCREMENT)
);

CREATE TABLE IF NOT EXISTS business (
    business_id INTEGER,
    business_name TEXT,
    description TEXT,
    owner_id INTEGER,
    cep TEXT,
    street TEXT NOT NULL,
    number TEXT NOT NULL,
    complement TEXT,
    neighborhood TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'Outros',
    phone TEXT,
    PRIMARY KEY (business_id),
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
    appointment_id INTEGER,
    user_id INTEGER,
    provider_id INTEGER,
    service_id INTEGER,
    date INTEGER,
    status TEXT,
    appointment_time TEXT,
    duration_minutes INTEGER NOT NULL DEFAULT 30,
    PRIMARY KEY (appointment_id),
    FOREIGN KEY (user_id) REFERENCES users (user_id),
    FOREIGN KEY (provider_id) REFERENCES users (user_id),
    FOREIGN KEY (service_id) REFERENCES services (service_id)
);

CREATE TABLE IF NOT EXISTS business_providers (
    business_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role TEXT DEFAULT 'provider',
    status TEXT DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (business_id, user_id),
    FOREIGN KEY (business_id) REFERENCES business (business_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS provider_services (
    business_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    service_id INTEGER NOT NULL,
    PRIMARY KEY (business_id, user_id, service_id),
    FOREIGN KEY (business_id, user_id)
        REFERENCES business_providers (business_id, user_id) ON DELETE CASCADE,
    FOREIGN KEY (service_id) REFERENCES services (service_id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_phone_unique
    ON users (phone);

CREATE UNIQUE INDEX IF NOT EXISTS idx_business_phone_unique
    ON business (phone);