import sqlite3
from flask import Blueprint, flash, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, get_db, login_required

# Definindo o Blueprint
client_bp = Blueprint("client", __name__)


# Trava de segurança escopada para a área de clientes
@client_bp.before_request
def restrict_client_area():
    user_id = session.get("user_id")
    u_type = session.get("user_type")

    # Se um parceiro (user_type == 1) tentar acessar rotas do cliente (que não seja o logout)
    if user_id and u_type == 1 and request.endpoint != "client.logout":
        return redirect("/business/home")


# Rota Principal (Pública ou Tipo 2)
@client_bp.route("/")
def index():
    return render_template("index.html")


# Login de Usuário
@client_bp.route("/login", methods=["GET", "POST"])
def login_user():
    session.clear()

    if request.method == "POST":
        if not request.form.get("username"):
            return apology("Deve inserir Nome de Usuário", 403)
        elif not request.form.get("password"):
            return apology("Deve inserir a senha", 403)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (request.form.get("username"),))
        rows = cursor.fetchall()

        if len(rows) != 1 or not check_password_hash(rows[0]["password_hash"], request.form.get("password")):
            return apology("Usuário e/ou senha inválidos", 403)

        if rows[0]["user_type"] != 2:
            return apology("Acesso dedicado exclusivamente a usuários", 403)

        session["user_id"] = rows[0]["user_id"]
        session["user_type"] = rows[0]["user_type"]

        return redirect("/")
    else:
        return render_template("login.html")


# Registro de Usuário
@client_bp.route("/register", methods=["GET", "POST"])
def register_user():
    session.clear()

    if request.method == "POST":
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

        cursor.execute("SELECT * FROM users WHERE username = ?", (request.form.get("username"),))
        if cursor.fetchone() is not None:
            return apology("Nome de usuário já registrado", 403)

        hash = generate_password_hash(request.form.get("password"))

        cursor.execute(
            "INSERT INTO users (username, password_hash, name, surename, user_type) VALUES (?, ?, ?, ?, ?)",
            (request.form.get("username"), hash, request.form.get("name"), request.form.get("surename"), 2)
        )
        conn.commit()

        session["user_id"] = cursor.lastrowid
        session["user_type"] = 2

        return redirect("/")
    else:
        return render_template("register.html")


# Logout
@client_bp.route("/logout")
def logout():
    session.clear()
    flash("Você saiu da sua conta.")
    return redirect("/")