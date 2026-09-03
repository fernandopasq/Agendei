import sqlite3
from flask import render_template, redirect, session, g
from functools import wraps

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


# ---- Database Related Helpers -----
def get_db():
    """Get a database connection (one per request)"""
    if "db" not in g:
        g.db = sqlite3.connect("agendei.db")
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(exception=None):
    """Close the database connection at the end of request"""
    db = g.pop("db", None)
    if db is not None:
        db.close()