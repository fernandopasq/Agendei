import re
import unicodedata

from flask import render_template, redirect, session, g
from functools import wraps
import sqlite3

# Decorator to ensure user is logged in
def login_required(f):
    """Garante que o usuário está logado no sistema"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function

# Apology function to render error messages
def apology(message, code=400):
    """Render message as an apology to user."""
    return render_template("apology.html", message=message, code=code), code


def brl(value):
    """Format value as BRL."""
    return f"R${value:,.2f}"


def category_slug(category):
    """Convert a category label into a stable CSS-friendly slug."""
    if not category:
        return "outros"

    normalized = unicodedata.normalize("NFKD", category)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-") or "outros"


def format_phone(phone):
    """Format a Brazilian phone number stored as digits."""
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 11:
        return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
    if len(digits) == 10:
        return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
    return phone or "Não informado"


def normalize_phone(ddd, number):
    """Return a Brazilian phone number as digits after basic validation."""
    ddd_digits = re.sub(r"\D", "", ddd or "")
    number_digits = re.sub(r"\D", "", number or "")
    if len(ddd_digits) != 2 or len(number_digits) not in (8, 9):
        return None
    return ddd_digits + number_digits


# ---- Database Related Helpers -----
def get_db():
    """Get a database connection (one per request)"""
    if "db" not in g:
        g.db = sqlite3.connect("agendei.db")
        g.db.row_factory = sqlite3.Row
        _ensure_booking_columns(g.db)
        _ensure_contact_columns(g.db)
    return g.db


def _ensure_booking_columns(db):
    """Add booking fields to databases created with the original schema."""
    cursor = db.cursor()

    service_columns = {row[1] for row in cursor.execute("PRAGMA table_info(services)")}
    if "duration_minutes" not in service_columns:
        cursor.execute(
            "ALTER TABLE services ADD COLUMN duration_minutes INTEGER NOT NULL DEFAULT 30"
        )

    appointment_columns = {row[1] for row in cursor.execute("PRAGMA table_info(appointment)")}
    if "appointment_time" not in appointment_columns:
        cursor.execute("ALTER TABLE appointment ADD COLUMN appointment_time TEXT")
    if "duration_minutes" not in appointment_columns:
        cursor.execute(
            "ALTER TABLE appointment ADD COLUMN duration_minutes INTEGER NOT NULL DEFAULT 30"
        )

    db.commit()


def _ensure_contact_columns(db):
    """Add contact fields and populate legacy rows with fictional numbers."""
    cursor = db.cursor()

    user_columns = {row[1] for row in cursor.execute("PRAGMA table_info(users)")}
    if "phone" not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN phone TEXT")
    cursor.execute("""
        UPDATE users
        SET phone = '11' || printf('%09d', user_id)
        WHERE phone IS NULL OR phone = ''
    """)

    business_columns = {row[1] for row in cursor.execute("PRAGMA table_info(business)")}
    if "phone" not in business_columns:
        cursor.execute("ALTER TABLE business ADD COLUMN phone TEXT")
    cursor.execute("""
        UPDATE business
        SET phone = '11' || printf('%09d', business_id)
        WHERE phone IS NULL OR phone = ''
    """)

    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_phone_unique ON users(phone)")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_business_phone_unique ON business(phone)")

    db.commit()


def close_db(exception=None):
    """Close the database connection at the end of request"""
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ---- Normalização de Endereços -----

def normalize_street(street):
    if not street:
        return ""
    
    # Remove espaços extras no início/fim
    street = street.strip()
    
    # Dicionário de substituições para os tipos de logradouro mais comuns no Brasil
    replacements = {
        r'^\b(Av|Avd|Aven)\b\.?': 'Avenida',
        r'^\b(R|Rua)\b\.?': 'Rua',
        r'^\b(Al|Alam)\b\.?': 'Alameda',
        r'^\b(Pça|Pca)\b\.?': 'Praça',
        r'^\b(Rod)\b\.?': 'Rodovia',
        r'^\b(Dr|Doutor)\b\.?': 'Doutor',
        r'^\b(Prof|Professor)\b\.?': 'Professor'
    }
    
    for pattern, replacement in replacements.items():
        street = re.sub(pattern, replacement, street, flags=re.IGNORECASE)
        
    return street