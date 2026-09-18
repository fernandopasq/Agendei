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
    conn = get_db()
    cursor = conn.cursor()

    # Recebe os parâmetros de filtro via GET
    search_query = request.args.get("q", "").strip()
    selected_city = request.args.get("city", "").strip()
    selected_neighborhood = request.args.get("neighborhood", "").strip()
    selected_service = request.args.get("service", "").strip()

    # Monta a SQL dinâmica para listagem dos estabelecimentos
    query = """
        SELECT DISTINCT b.* 
        FROM business b
        LEFT JOIN services s ON b.business_id = s.business_id
        WHERE 1=1
    """
    params = []

    if search_query:
        query += " AND (b.business_name LIKE ? OR b.description LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])

    if selected_city:
        query += " AND b.city = ?"
        params.append(selected_city)

    if selected_neighborhood:
        query += " AND b.neighborhood = ?"
        params.append(selected_neighborhood)

    if selected_service:
        query += " AND s.name = ?"
        params.append(selected_service)

    query += " ORDER BY b.business_name ASC"
    cursor.execute(query, params)
    businesses = cursor.fetchall()

    # Consultas para popular os selects de filtro dinamicamente
    cursor.execute("SELECT DISTINCT city FROM business WHERE city IS NOT NULL AND city != '' ORDER BY city ASC")
    cities = [row["city"] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT neighborhood FROM business WHERE neighborhood IS NOT NULL AND neighborhood != '' ORDER BY neighborhood ASC")
    neighborhoods = [row["neighborhood"] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT name FROM services WHERE name IS NOT NULL AND name != '' ORDER BY name ASC")
    services_list = [row["name"] for row in cursor.fetchall()]

    conn.close()

    return render_template(
        "index.html",
        businesses=businesses,
        cities=cities,
        neighborhoods=neighborhoods,
        services_list=services_list,
        search_query=search_query,
        selected_city=selected_city,
        selected_neighborhood=selected_neighborhood,
        selected_service=selected_service
    )


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