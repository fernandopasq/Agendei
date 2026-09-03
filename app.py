import os
import sqlite3

from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

# Import helpers
from helpers import apology, login_required, brl, get_db, close_db, role_required

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["brl"] = brl # -> R$

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Register teardown
app.teardown_appcontext(close_db)

# Global var
user_type = ["adm", "partner", "user"]

# Disables browser caching to prevent sensitive or authenticated pages
# from being displayed when the user clicks the "Back" button.
@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# ====================================
#   MAIN ROUTERS
# ====================================

# Index route
@app.route("/")
def index():
    return render_template("index.html")

# Business index route
@app.route("/business")
def business():
    # Forget any user_id
    session.clear()

    return render_template("business.html")

@app.route("/business/home")
@role_required([1])
def businesshome():

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM users WHERE user_id = ?", (session["user_id"],))
    user_name = cursor.fetchone()[0]

    return render_template("business-home.html", user_name=user_name)

# ====================================
#   REGISTRATION AND LOGIN FOR USERS
# ====================================

@app.route("/login", methods=["GET", "POST"])
def login_user():
    """Log user in"""

    # Forget any user_id
    session.clear()

    if request.method == "POST":
        if not request.form.get("username"):
            return apology("Deve inserir Nome de Usuário", 403)
        elif not request.form.get("password"):
            return apology("Deve inserir a senha", 403)

        # Query database for username
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (request.form.get("username"),))
        rows = cursor.fetchall()

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["password_hash"], request.form.get("password")):
            return apology("Usuário e/ou senha inválidos", 403)

        # Ensure only users can login "user_type == 2"
        if rows[0]["user_type"] != 2:
            return apology("Acesso dedicado exclusivamente a usuários", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["user_id"]

        return redirect("/")
    else:
        return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register_user():
    """Register user"""
    # Ensure no logged-in user makes a register
    session.clear()

    if request.method == "POST":
        # Validations
        if not request.form.get("username"):
            return apology("Deve informar Nome de Usuário", 403)
        elif not request.form.get("name"):
            return apology("Deve informar Nome", 403)
        elif not request.form.get("surename"):
            return apology("Deve informar Sobrenome", 403)
        elif not request.form.get("password"):
            return apology("Deve informar senha", 403)
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("Senhas devem ser iguais", 403)

        conn = get_db()
        cursor = conn.cursor()

        # Check if username already exists
        cursor.execute("SELECT * FROM users WHERE username = ?", (request.form.get("username"),))
        if cursor.fetchone() is not None:
            return apology("Nome de usuário já registrado", 403)

        # Hash the password
        hash = generate_password_hash(request.form.get("password"))

        # Insert user
        cursor.execute(
            "INSERT INTO users (username, password_hash, name, surename, user_type) VALUES (?, ?, ?, ?, ?)",
            (request.form.get("username"), hash, request.form.get("name"), request.form.get("surename"), 2)  # sempre "user"
        )
        conn.commit()

        # Get the new user id
        session["user_id"] = cursor.lastrowid

        # Redirect to home
        return redirect("/")
    else:
        return render_template("register.html")

@app.route("/logout")
def logout():
    """Log user out"""
    # Clear the session
    session.clear()  

    # Redirect to home
    flash("Você saiu da sua conta.")
    return redirect("/")


# ====================================
#   REGISTRATION AND LOGIN FOR BUSINESS
# ====================================

@app.route("/business/login", methods=["GET", "POST"])
def login_business():
    """Log business user in"""

    # Forget any user_id
    session.clear()

    if request.method == "POST":
        if not request.form.get("username"):
            return apology("Deve inserir Nome de Usuário", 403)
        elif not request.form.get("password"):
            return apology("Deve inserir a senha", 403)

        # Query database for username
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (request.form.get("username"),))
        rows = cursor.fetchall()

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["password_hash"], request.form.get("password")):
            return apology("Usuário e/ou senha inválidos", 403)

        # Ensure only partner users can login "user_type == 1"
        if rows[0]["user_type"] != 1:
            return apology("Acesso restrito a parceiros/administradores", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["user_id"]

        return redirect("/business/home")
    else:
        return render_template("business-login.html")

@app.route("/business/register", methods=["GET", "POST"])
def register_business():
    """Register user"""
    # Ensure no logged-in user makes a register
    session.clear()

    if request.method == "POST":
        # Validations
        if not request.form.get("username"):
            return apology("Deve informar Nome de Usuário", 403)
        elif not request.form.get("name"):
            return apology("Deve informar Nome", 403)
        elif not request.form.get("surename"):
            return apology("Deve informar Sobrenome", 403)
        elif not request.form.get("password"):
            return apology("Deve informar senha", 403)
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("Senhas devem ser iguais", 403)

        conn = get_db()
        cursor = conn.cursor()

        # Check if username already exists
        cursor.execute("SELECT * FROM users WHERE username = ?", (request.form.get("username"),))
        if cursor.fetchone() is not None:
            return apology("Nome de usuário já registrado", 403)

        # Hash the password
        hash = generate_password_hash(request.form.get("password"))

        # Insert user
        cursor.execute(
            "INSERT INTO users (username, password_hash, name, surename, user_type) VALUES (?, ?, ?, ?, ?)",
            (request.form.get("username"), hash, request.form.get("name"), request.form.get("surename"), 1)
        )
        conn.commit()

        # Get the new user id
        session["user_id"] = cursor.lastrowid

        # Redirect to home
        return redirect("/business/home")
    else:
        return render_template("business-register.html")


# ====================================
#   GENERAL ERRORS RETURNS
# ====================================

# Deals with 404 error
@app.errorhandler(404)
def not_found(error):
    return apology("Página não encontrada!", 404)

# Deals with 418 error 
@app.errorhandler(418)
def teapot(error):
    return redirect("https://www.google.com/teapot")

# ====================================
#   APP STARTER
# ====================================


if __name__ == "__main__":
    app.run(debug=True)
