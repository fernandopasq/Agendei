import sqlite3
from flask import Blueprint, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, get_db, normalize_street

# Definindo o Blueprint com prefixo de URL automático
business_bp = Blueprint("business", __name__, url_prefix="/business")


# Trava de segurança isolada para TODO o módulo /business
@business_bp.before_request
def restrict_business_area():
    user_id = session.get("user_id")
    u_type = session.get("user_type")

    # 1. Rotas públicas dentro do módulo business (não exigem estar logado)
    # No Flask, o nome dos endpoints de um Blueprint usam a sintaxe 'nome_blueprint.nome_funcao'
    public_endpoints = ["business.business_landing", "business.login_business", "business.register_business"]

    if request.endpoint in public_endpoints:
        # Se um cliente comum (user_type == 2) tentar acessar as telas de login/cadastro do parceiro
        if user_id and u_type == 2:
            return apology("Acesso negado: área restrita a parceiros.", 403)
        return  # Permite acesso livre para não-logados ou tipo 1

    # 2. Para qualquer outra rota interna (/business/home, etc.):
    # Se não estiver logado, redireciona para a tela de login de empresas
    if not user_id:
        return redirect("/business/login")

    # Se for um cliente comum (user_type == 2), bloqueia
    if u_type == 2:
        return apology("Acesso negado: área restrita a parceiros.", 403)


# Rota institucional (Acessada via /business)
@business_bp.route("")
def business_landing():
    if session.get("user_id") and session.get("user_type") == 1:
        return redirect("/business/home")

    session.clear()
    return render_template("business.html")


# Home do Parceiro (Acessada via /business/home)
@business_bp.route("/home")
def home():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM users WHERE user_id = ?", (session["user_id"],))
    user_name = cursor.fetchone()[0]

    return render_template("business-home.html", user_name=user_name)


# Login do Parceiro (Acessado via /business/login)
@business_bp.route("/login", methods=["GET", "POST"])
def login_business():
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

        if rows[0]["user_type"] != 1:
            return apology("Acesso restrito a parceiros/administradores", 403)

        session["user_id"] = rows[0]["user_id"]
        session["user_type"] = rows[0]["user_type"]

        return redirect("/business/home")
    else:
        return render_template("business-login.html")


# Cadastro do Parceiro (Acessado via /business/register)
@business_bp.route("/register", methods=["GET", "POST"])
def register_business():
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
            (request.form.get("username"), hash, request.form.get("name"), request.form.get("surename"), 1)
        )
        conn.commit()

        session["user_id"] = cursor.lastrowid
        session["user_type"] = 1

        return redirect("/business/home")
    else:
        return render_template("business-register.html")

# Cadastro de Estabelecimento (Acessado via /business/addbusiness)
@business_bp.route("/addbusiness", methods=["GET", "POST"])
def add_store():
    if request.method == "POST":
        # Coletando dados do formulário
        business_name = request.form.get("business_name")
        description = request.form.get("description")
        category = request.form.get("category")
        
        # Dados de Endereço desmembrados
        cep = request.form.get("cep")
        street = request.form.get("street")
        number = request.form.get("number")
        complement = request.form.get("complement")
        neighborhood = request.form.get("neighborhood")
        city = request.form.get("city")
        state = request.form.get("state")

        # Limpando/Normalizando o logradouro (Avenida, Rua, etc)
        street = normalize_street(street)
        # Limpando/Normalizando o CEP
        cep = cep.replace("-", "").strip() if cep else None

        # Validando campos obrigatórios definidos como NOT NULL no banco
        if not business_name or not street or not number or not neighborhood or not city or not state:
            return apology("Preencha todos os campos obrigatórios do endereço.", 400)

        # Inserindo dados na tabela 'business'
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO business (
                owner_id, 
                business_name, 
                description, 
                category,
                cep, 
                street, 
                number, 
                complement, 
                neighborhood, 
                city, 
                state
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                business_name,
                description,
                category,
                cep,
                street,
                number,
                complement,
                neighborhood,
                city,
                state
            )
        )
        conn.commit()
        conn.close()

        return redirect("/business/home")
    else:
        return render_template("business-addbusiness.html")