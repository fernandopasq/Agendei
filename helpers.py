import requests
import sqlite3

from flask import redirect, render_template, session, g, request
from functools import wraps

# Apology function to render error messages
def apology(message, code=400):
    """Render message as an apology to user."""
    return render_template("apology.html", message=message, code=code), code


# Login required decorator
def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function

# Role required decorator
def role_required(allowed_types):
    """
    Decorator to restrict route access based on user_type. 
    allowed_types: list of integers corresponding to the allowed user types.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is loged in
            if session.get("user_id") is None:
                if request.path.startswith("/business"):
                    return redirect("/business/login")
                else:
                    return redirect("/login")

            # Looks for user_type on db
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT user_type FROM users WHERE user_id = ?", (session["user_id"],))
            row = cursor.fetchone()

            # If type does not match, refuses
            if row is None or row["user_type"] not in allowed_types:
                return apology("Acesso restrito", 403)

            return f(*args, **kwargs)
        return decorated_function
    return decorator


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