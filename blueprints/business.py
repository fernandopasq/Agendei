import sqlite3
from flask import Blueprint, redirect, render_template, request, session, url_for, flash
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, get_db, normalize_phone, normalize_street

# Definindo o Blueprint com prefixo de URL automático
business_bp = Blueprint("business", __name__, url_prefix="/business")


# Trava de segurança isolada para TODO o módulo /business
@business_bp.before_request
def restrict_business_area():
    user_id = session.get("user_id")
    u_type = session.get("user_type")

    # 1. Rotas públicas dentro do módulo business (não exigem estar logado)
    public_endpoints = ["business.business_landing", "business.login_business", "business.register_business"]

    if request.endpoint in public_endpoints:
        if user_id and u_type == 2:
            return apology("Acesso negado: área restrita a parceiros.", 403)
        return

    # 2. Para qualquer outra rota interna (/business/home, etc.):
    if not user_id:
        return redirect("/business/login")

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
    user_id = session.get("user_id")
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    user_name = user["name"] if user else "Usuário"

    query = """
        SELECT DISTINCT 
            b.business_id, 
            b.business_name, 
            b.category, 
            b.street, 
            b.number, 
            b.neighborhood, 
            b.city, 
            b.state,
            CASE 
                WHEN b.owner_id = ? THEN 'Proprietário' 
                ELSE 'Prestador' 
            END AS role
        FROM business b
        LEFT JOIN business_providers bp ON b.business_id = bp.business_id
        WHERE (b.owner_id = ? OR (bp.user_id = ? AND bp.status = 'active'))
    """
    
    cursor.execute(query, (user_id, user_id, user_id))
    businesses = cursor.fetchall()
    conn.close()

    return render_template("business-home.html", user_name=user_name, businesses=businesses)


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
        elif not normalize_phone(request.form.get("phone_ddd"), request.form.get("phone_number")):
            return apology("Informe um telefone válido.", 403)
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("Senhas devem ser iguais", 403)

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username = ?", (request.form.get("username"),))
        if cursor.fetchone() is not None:
            return apology("Nome de usuário já registrado", 403)

        phone = normalize_phone(request.form.get("phone_ddd"), request.form.get("phone_number"))
        cursor.execute("SELECT 1 FROM users WHERE phone = ?", (phone,))
        if cursor.fetchone() is not None:
            return apology("Este número de telefone já está cadastrado.", 403)

        hash = generate_password_hash(request.form.get("password"))

        cursor.execute(
            "INSERT INTO users (username, password_hash, name, surename, phone, user_type) VALUES (?, ?, ?, ?, ?, ?)",
            (request.form.get("username"), hash, request.form.get("name"), request.form.get("surename"), phone, 1)
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
        business_name = request.form.get("business_name")
        description = request.form.get("description")
        category = request.form.get("category")
        
        cep = request.form.get("cep")
        street = request.form.get("street")
        number = request.form.get("number")
        complement = request.form.get("complement")
        neighborhood = request.form.get("neighborhood")
        city = request.form.get("city")
        state = request.form.get("state")
        phone = normalize_phone(request.form.get("phone_ddd"), request.form.get("phone_number"))

        street = normalize_street(street)
        cep = cep.replace("-", "").strip() if cep else None

        if not business_name or not street or not number or not neighborhood or not city or not state:
            return apology("Preencha todos os campos obrigatórios do endereço.", 400)
        if not phone:
            return apology("Informe um telefone válido para o estabelecimento.", 400)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM business WHERE phone = ?", (phone,))
        if cursor.fetchone() is not None:
            conn.close()
            return apology("Este número de telefone já está cadastrado em outro estabelecimento.", 400)
        cursor.execute(
            """
            INSERT INTO business (
                owner_id, 
                business_name, 
                description, 
                category,
                phone,
                cep, 
                street, 
                number, 
                complement, 
                neighborhood, 
                city, 
                state
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                business_name,
                description,
                category,
                phone,
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


# Solicitação para entrar em equipe (Acessado via /business/join)
@business_bp.route("/join", methods=["GET", "POST"])
def join_request():
    user_id = session.get("user_id")

    if request.method == "POST":
        business_id = request.form.get("business_id")

        if not business_id:
            flash("Estabelecimento inválido.", "danger")
            return redirect(url_for("business.join_request"))

        conn = get_db()
        cursor = conn.cursor()

        # 1. Verifica se o usuário é o próprio proprietário
        cursor.execute("SELECT owner_id FROM business WHERE business_id = ?", (business_id,))
        business = cursor.fetchone()

        if business and business["owner_id"] == user_id:
            flash("Você já é o proprietário deste estabelecimento.", "warning")
            conn.close()
            return redirect(url_for("business.join_request", q=request.args.get("q", "")))

        # 2. Verifica se já existe um vínculo (ativo, pendente ou inativo)
        cursor.execute(
            "SELECT status FROM business_providers WHERE business_id = ? AND user_id = ?",
            (business_id, user_id)
        )
        existing = cursor.fetchone()

        if existing:
            status = existing["status"]
            if status == "active":
                flash("Você já faz parte da equipe deste estabelecimento.", "info")
            elif status == "pending":
                flash("Sua solicitação para este local já está pendente de aprovação.", "warning")
            else:
                flash("Você já possui um registro neste local.", "info")
        else:
            # Insere a solicitação pendente
            cursor.execute(
                """
                INSERT INTO business_providers (business_id, user_id, role, status)
                VALUES (?, ?, 'provider', 'pending')
                """,
                (business_id, user_id)
            )
            conn.commit()
            flash("Solicitação enviada com sucesso! Aguarde a aprovação do proprietário.", "success")

        conn.close()
        return redirect(url_for("business.join_request", q=request.args.get("q", "")))

    # TRATAMENTO DO GET (Busca de estabelecimentos)
    q = request.args.get("q", "").strip()
    businesses = []

    if q:
        conn = get_db()
        cursor = conn.cursor()

        # Busca estabelecimentos trazendo a flag `is_owner` e o `membership_status`
        query = """
            SELECT 
                b.business_id, 
                b.business_name, 
                b.category, 
                b.street, 
                b.number, 
                b.neighborhood, 
                b.city, 
                b.state,
                (b.owner_id = ?) AS is_owner,
                bp.status AS membership_status
            FROM business b
            LEFT JOIN business_providers bp 
                   ON b.business_id = bp.business_id AND bp.user_id = ?
            WHERE LOWER(b.business_name) LIKE LOWER(?)
               OR LOWER(b.street) LIKE LOWER(?)
               OR LOWER(b.neighborhood) LIKE LOWER(?)
            ORDER BY b.business_name ASC
        """
        search_term = f"%{q}%"
        cursor.execute(query, (user_id, user_id, search_term, search_term, search_term))
        businesses = cursor.fetchall()
        conn.close()

    return render_template("business-join.html", businesses=businesses, query=q)


######################################################
# Rotas de gerenciamento de equipe e estabelecimento
######################################################

# 1. ROTA DE GERENCIAMENTO (EXCLUSIVA PARA O PROPRIETÁRIO)
@business_bp.route("/manage/<int:business_id>")
def manage_business(business_id):
    user_id = session.get("user_id")
    conn = get_db()
    cursor = conn.cursor()

    # Confirma se o usuário é o proprietário
    cursor.execute("SELECT * FROM business WHERE business_id = ? AND owner_id = ?", (business_id, user_id))
    business = cursor.fetchone()

    if not business:
        conn.close()
        return apology("Acesso restrito ao proprietário do estabelecimento.", 403)

    # Verifica se o próprio dono está na lista de prestadores ativos do local
    cursor.execute(
        "SELECT 1 FROM business_providers WHERE business_id = ? AND user_id = ? AND status = 'active'",
        (business_id, user_id)
    )
    is_self_provider = cursor.fetchone() is not None

    # A) Serviços cadastrados no local com a lista de prestadores que os atendem
    cursor.execute("""
        SELECT 
            s.*,
            GROUP_CONCAT(u.name || ' ' || u.surename, ', ') AS providers_list
        FROM services s
        LEFT JOIN provider_services ps 
               ON s.service_id = ps.service_id AND s.business_id = ps.business_id
        LEFT JOIN users u 
               ON ps.user_id = u.user_id
        WHERE s.business_id = ?
        GROUP BY s.service_id
        ORDER BY s.name ASC
    """, (business_id,))
    services = cursor.fetchall()

    # B) Agendamentos do local
    cursor.execute("""
        SELECT 
            a.appointment_id, a.date, a.status,
            client.name AS client_name, client.surename AS client_surename,
            provider.name AS provider_name, provider.surename AS provider_surename,
            s.name AS service_name
        FROM appointment a
        JOIN users client ON a.user_id = client.user_id
        JOIN users provider ON a.provider_id = provider.user_id
        JOIN services s ON a.service_id = s.service_id
        WHERE s.business_id = ?
        ORDER BY a.date ASC
    """, (business_id,))
    appointments = cursor.fetchall()

    # C) Solicitações Pendentes de Prestadores
    cursor.execute("""
        SELECT u.user_id, u.name, u.surename, u.username
        FROM business_providers bp
        JOIN users u ON bp.user_id = u.user_id
        WHERE bp.business_id = ? AND bp.status = 'pending'
    """, (business_id,))
    pending_requests = cursor.fetchall()

    # D) Prestadores Ativos na Equipe
    cursor.execute("""
        SELECT u.user_id, u.name, u.surename, u.username, bp.role
        FROM business_providers bp
        JOIN users u ON bp.user_id = u.user_id
        WHERE bp.business_id = ? AND bp.status = 'active'
    """, (business_id,))
    active_members = cursor.fetchall()

    conn.close()

    return render_template(
        "business-manage.html",
        business=business,
        is_self_provider=is_self_provider,
        services=services,
        appointments=appointments,
        pending_requests=pending_requests,
        active_members=active_members
    )


# 2. ROTA DE VISUALIZAÇÃO / PAINEL DO PRESTADOR
@business_bp.route("/view/<int:business_id>")
def provider_view(business_id):
    user_id = session.get("user_id")
    conn = get_db()
    cursor = conn.cursor()

    # Confirma se o usuário é prestador ativo deste local (ou proprietário ativo)
    cursor.execute("""
        SELECT b.* FROM business_providers bp
        JOIN business b ON bp.business_id = b.business_id
        WHERE bp.business_id = ? AND bp.user_id = ? AND bp.status = 'active'
    """, (business_id, user_id))
    business = cursor.fetchone()

    if not business:
        conn.close()
        return apology("Você não faz parte da equipe de prestadores deste estabelecimento.", 403)

    # Agendamentos do PRESTADOR LOGADO neste estabelecimento (ordenados por data)
    cursor.execute("""
        SELECT 
            a.appointment_id, a.date, a.status,
            client.name AS client_name, client.surename AS client_surename,
            provider.name AS provider_name, provider.surename AS provider_surename,
            s.name AS service_name
        FROM appointment a
        JOIN users client ON a.user_id = client.user_id
        JOIN users provider ON a.provider_id = provider.user_id
        JOIN services s ON a.service_id = s.service_id
        WHERE s.business_id = ? AND a.provider_id = ?
        ORDER BY a.date ASC
    """, (business_id, user_id))
    appointments = cursor.fetchall()

    # Busca TODOS os serviços do estabelecimento e indica (1 ou 0) se o prestador atende cada um
    cursor.execute("""
        SELECT 
            s.*,
            CASE WHEN ps.service_id IS NOT NULL THEN 1 ELSE 0 END AS is_assigned
        FROM services s
        LEFT JOIN provider_services ps 
               ON s.service_id = ps.service_id 
              AND ps.business_id = s.business_id 
              AND ps.user_id = ?
        WHERE s.business_id = ?
        ORDER BY s.name ASC
    """, (user_id, business_id))
    services = cursor.fetchall()

    conn.close()

    return render_template(
        "business-provider-view.html",
        business=business,
        appointments=appointments,
        services=services
    )


# 3. ROTA PARA CANCELAR AGENDAMENTO (PRESTADOR / PROPRIETÁRIO)
@business_bp.route("/appointment/<int:appointment_id>/cancel", methods=["POST"])
def cancel_appointment(appointment_id):
    user_id = session.get("user_id")
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE appointment SET status = 'cancelled' WHERE appointment_id = ? AND (provider_id = ? OR user_id = ?)",
        (appointment_id, user_id, user_id)
    )
    conn.commit()
    conn.close()

    flash("Agendamento cancelado.", "info")
    return redirect(request.referrer or url_for("business.home"))


# Aprovar Solicitação
@business_bp.route("/manage/<int:business_id>/approve/<int:provider_user_id>", methods=["POST"])
def approve_provider(business_id, provider_user_id):
    user_id = session.get("user_id")
    conn = get_db()
    cursor = conn.cursor()

    # Verifica permissão do dono
    cursor.execute("SELECT owner_id FROM business WHERE business_id = ?", (business_id,))
    business = cursor.fetchone()

    if not business or business["owner_id"] != user_id:
        conn.close()
        return apology("Ação não autorizada.", 403)

    # Atualiza status via chave composta
    cursor.execute(
        "UPDATE business_providers SET status = 'active' WHERE business_id = ? AND user_id = ?",
        (business_id, provider_user_id)
    )
    conn.commit()
    conn.close()

    flash("Solicitação aprovada com sucesso!", "success")
    return redirect(url_for("business.manage_business", business_id=business_id))


# Recusar / Remover Colaborador
@business_bp.route("/manage/<int:business_id>/reject/<int:provider_user_id>", methods=["POST"])
def reject_provider(business_id, provider_user_id):
    user_id = session.get("user_id")
    conn = get_db()
    cursor = conn.cursor()

    # Verifica permissão do dono
    cursor.execute("SELECT owner_id FROM business WHERE business_id = ?", (business_id,))
    business = cursor.fetchone()

    if not business or business["owner_id"] != user_id:
        conn.close()
        return apology("Ação não autorizada.", 403)

    # Remove o registro via chave composta
    cursor.execute(
        "DELETE FROM business_providers WHERE business_id = ? AND user_id = ?",
        (business_id, provider_user_id)
    )
    conn.commit()
    conn.close()

    flash("Solicitação/membro removido.", "info")
    return redirect(url_for("business.manage_business", business_id=business_id))


# Alternar vínculo do proprietário como prestador no próprio estabelecimento
@business_bp.route("/manage/<int:business_id>/toggle-self-provider", methods=["POST"])
def toggle_self_provider(business_id):
    user_id = session.get("user_id")
    conn = get_db()
    cursor = conn.cursor()

    # Confirma se o usuário logado é realmente o proprietário do local
    cursor.execute("SELECT owner_id FROM business WHERE business_id = ?", (business_id,))
    business = cursor.fetchone()

    if not business or business["owner_id"] != user_id:
        conn.close()
        return apology("Ação não autorizada.", 403)

    # Verifica se o proprietário já está cadastrado na tabela de prestadores
    cursor.execute(
        "SELECT status FROM business_providers WHERE business_id = ? AND user_id = ?",
        (business_id, user_id)
    )
    existing = cursor.fetchone()

    if existing:
        # Se já existir um registro, remove o vínculo de prestador
        cursor.execute(
            "DELETE FROM business_providers WHERE business_id = ? AND user_id = ?",
            (business_id, user_id)
        )
        flash("Você deixou a lista de prestadores deste estabelecimento.", "info")
    else:
        # Se não existir, insere o proprietário como prestador ativo diretamente
        cursor.execute(
            """
            INSERT INTO business_providers (business_id, user_id, role, status)
            VALUES (?, ?, 'owner', 'active')
            """,
            (business_id, user_id)
        )
        flash("Você agora também atua como prestador neste estabelecimento!", "success")

    conn.commit()
    conn.close()

    return redirect(url_for("business.manage_business", business_id=business_id))


###################################
# ROTAS RELACIONADAS AOS SERVIÇOS
###################################

# Exibir formulário de criação de serviço
@business_bp.route("/manage/<int:business_id>/service/new", methods=["GET"])
def create_service_form(business_id):
    user_id = session.get("user_id")
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM business WHERE business_id = ? AND owner_id = ?", (business_id, user_id))
    business = cursor.fetchone()
    conn.close()

    if not business:
        return apology("Estabelecimento não encontrado ou acesso não autorizado.", 403)

    return render_template("service-create.html", business=business)


# Criar novo serviço
@business_bp.route("/manage/<int:business_id>/service/new", methods=["POST"])
def create_service(business_id):
    user_id = session.get("user_id")
    name = request.form.get("name")
    description = request.form.get("description")
    price = request.form.get("price")
    duration_minutes = request.form.get("duration_minutes", type=int)

    if not name or not price or not duration_minutes:
        return apology("Nome, preço e duração do serviço são obrigatórios.", 400)
    if duration_minutes < 5 or duration_minutes > 1440:
        return apology("A duração deve estar entre 5 e 1440 minutos.", 400)

    conn = get_db()
    cursor = conn.cursor()

    # Confirma permissão
    cursor.execute("SELECT owner_id FROM business WHERE business_id = ?", (business_id,))
    business = cursor.fetchone()

    if not business or business["owner_id"] != user_id:
        conn.close()
        return apology("Ação não autorizada.", 403)

    cursor.execute(
        """
        INSERT INTO services (business_id, name, description, price, duration_minutes)
        VALUES (?, ?, ?, ?, ?)
        """,
        (business_id, name, description, float(price), duration_minutes)
    )
    conn.commit()
    conn.close()

    flash("Serviço criado com sucesso!", "success")
    return redirect(url_for("business.manage_business", business_id=business_id))


# Excluir serviço
@business_bp.route("/manage/<int:business_id>/service/<int:service_id>/delete", methods=["POST"])
def delete_service(business_id, service_id):
    user_id = session.get("user_id")
    conn = get_db()
    cursor = conn.cursor()

    # Confirma permissão
    cursor.execute("SELECT owner_id FROM business WHERE business_id = ?", (business_id,))
    business = cursor.fetchone()

    if not business or business["owner_id"] != user_id:
        conn.close()
        return apology("Ação não autorizada.", 403)

    cursor.execute("DELETE FROM services WHERE service_id = ? AND business_id = ?", (service_id, business_id))
    conn.commit()
    conn.close()

    flash("Serviço removido com sucesso.", "info")
    return redirect(url_for("business.manage_business", business_id=business_id))

# Formulário/Ação de Seleção de Serviços do Prestador
@business_bp.route("/view/<int:business_id>/services", methods=["GET", "POST"])
def manage_provider_services(business_id):
    user_id = session.get("user_id")
    conn = get_db()
    cursor = conn.cursor()

    # Confirma se é prestador ativo (ou proprietário ativo) no estabelecimento
    cursor.execute(
        "SELECT 1 FROM business_providers WHERE business_id = ? AND user_id = ? AND status = 'active'",
        (business_id, user_id)
    )
    is_active = cursor.fetchone()

    if not is_active:
        conn.close()
        return apology("Você precisa ser um prestador ativo neste local para gerenciar seus serviços.", 403)

    if request.method == "POST":
        selected_services = request.form.getlist("service_ids")

        cursor.execute(
            "DELETE FROM provider_services WHERE business_id = ? AND user_id = ?",
            (business_id, user_id)
        )

        for service_id in selected_services:
            cursor.execute(
                "INSERT INTO provider_services (business_id, user_id, service_id) VALUES (?, ?, ?)",
                (business_id, user_id, int(service_id))
            )

        cursor.execute("SELECT owner_id FROM business WHERE business_id = ?", (business_id,))
        b_info = cursor.fetchone()
        is_owner = (b_info and b_info["owner_id"] == user_id)

        conn.commit()
        conn.close()

        flash("Serviços prestados atualizados com sucesso!", "success")

        if is_owner:
            return redirect(url_for("business.manage_business", business_id=business_id))
        
        return redirect(url_for("business.provider_view", business_id=business_id))

    # GET: Verifica se o usuário logado é o proprietário do estabelecimento
    cursor.execute("SELECT owner_id FROM business WHERE business_id = ?", (business_id,))
    b_info = cursor.fetchone()
    is_owner = (b_info and b_info["owner_id"] == user_id)

    # Busca os serviços do local e os associados ao usuário
    cursor.execute("SELECT * FROM services WHERE business_id = ?", (business_id,))
    all_services = cursor.fetchall()

    cursor.execute(
        "SELECT service_id FROM provider_services WHERE business_id = ? AND user_id = ?",
        (business_id, user_id)
    )
    assigned = {row["service_id"] for row in cursor.fetchall()}

    conn.close()

    return render_template(
        "provider-services.html",
        business_id=business_id,
        all_services=all_services,
        assigned=assigned,
        is_owner=is_owner
    )