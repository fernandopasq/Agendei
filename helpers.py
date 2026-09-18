import re
import unicodedata
from datetime import datetime, timedelta

from flask import render_template, redirect, session, g
from functools import wraps
import sqlite3

# Decorador que garante que o usuário está autenticado
def login_required(f):
    """Garante que o usuário está logado no sistema"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function

# Função de erro que renderiza mensagens para o usuário
def apology(message, code=400):
    """Renderiza uma mensagem de erro para o usuário."""
    return render_template("apology.html", message=message, code=code), code


def brl(value):
    """Formata um valor em reais."""
    return f"R${value:,.2f}"


def category_slug(category):
    """Converte o nome de uma categoria em um identificador CSS estável."""
    if not category:
        return "outros"

    normalized = unicodedata.normalize("NFKD", category)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-") or "outros"


def format_phone(phone):
    """Formata um telefone brasileiro armazenado como dígitos."""
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 11:
        return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
    if len(digits) == 10:
        return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
    return phone or "Não informado"


def normalize_phone(ddd, number):
    """Retorna um telefone brasileiro em dígitos após validação básica."""
    ddd_digits = re.sub(r"\D", "", ddd or "")
    number_digits = re.sub(r"\D", "", number or "")
    if len(ddd_digits) != 2 or len(number_digits) not in (8, 9):
        return None
    return ddd_digits + number_digits


# ---- Funções auxiliares do banco de dados -----
def get_db():
    """Obtém uma conexão com o banco por requisição."""
    if "db" not in g:
        g.db = sqlite3.connect("agendei.db")
        g.db.row_factory = sqlite3.Row
        _ensure_booking_columns(g.db)
        _ensure_contact_columns(g.db)
        _mark_past_appointments_completed(g.db)
    return g.db


def _ensure_booking_columns(db):
    """Adiciona campos de agendamento a bancos criados com o schema original."""
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
    """Adiciona campos de contato e preenche registros antigos com números fictícios."""
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


def _mark_past_appointments_completed(db):
    """Marca como concluídos os agendamentos confirmados cujo horário já passou."""
    cursor = db.cursor()
    now = datetime.now()
    cursor.execute("""
        SELECT appointment_id, date, appointment_time
        FROM appointment
        WHERE status = 'confirmed'
    """)

    completed_ids = []
    for appointment in cursor.fetchall():
        try:
            if not appointment["appointment_time"]:
                appointment_end = datetime.strptime(str(appointment["date"]), "%Y-%m-%d")
            else:
                appointment_start = datetime.strptime(
                    f"{appointment['date']} {appointment['appointment_time']}",
                    "%Y-%m-%d %H:%M"
                )
                cursor.execute(
                    "SELECT duration_minutes FROM appointment WHERE appointment_id = ?",
                    (appointment["appointment_id"],)
                )
                duration = cursor.fetchone()["duration_minutes"] or 30
                appointment_end = appointment_start + timedelta(minutes=duration)
        except (TypeError, ValueError):
            continue

        if appointment_end <= now:
            completed_ids.append((appointment["appointment_id"],))

    if completed_ids:
        cursor.executemany(
            "UPDATE appointment SET status = 'completed' WHERE appointment_id = ?",
            completed_ids
        )
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