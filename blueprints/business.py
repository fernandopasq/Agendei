import sqlite3
from flask import Blueprint, redirect, render_template, request, session, url_for, flash
from werkzeug.security import check_password_hash, generate_password_hash

from constants import BUSINESS_CATEGORIES, BUSINESS_DDDS, BRAZILIAN_STATES
from helpers import apology, get_db, normalize_phone, normalize_street
from image_storage import (
    ImageUploadError,
    delete_image_asset,
    delete_owner_image_assets,
    move_gallery_image,
    save_image_upload,
)

APPOINTMENT_PAGE_SIZE = 15

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

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS total FROM users WHERE user_type = 2")
    client_count = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(DISTINCT bp.user_id) AS total
        FROM business_providers bp
        WHERE bp.role = 'provider' AND bp.status = 'active'
    """)
    provider_count = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM appointment
        WHERE status IN ('requested', 'confirmed')
    """)
    appointment_count = cursor.fetchone()["total"]
    conn.close()

    session.clear()
    return render_template(
        "business.html",
        client_count=client_count,
        provider_count=provider_count,
        appointment_count=appointment_count
    )


# Página inicial do parceiro (acessada via /business/home)
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


# Login do parceiro (acessado via /business/login)
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
        return render_template("business-register.html", ddds=BUSINESS_DDDS)


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
        return render_template(
            "business-addbusiness.html",
            ddds=BUSINESS_DDDS,
            categories=BUSINESS_CATEGORIES,
            states=BRAZILIAN_STATES
        )


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
    status_filter = request.args.get("status", "")
    if status_filter not in {"", "pending", "confirmed", "cancelled", "completed"}:
        status_filter = ""
    service_filter = request.args.get("service_id", type=int)
    provider_filter = request.args.get("provider_id", type=int)
    sort_order = request.args.get("order", "asc")
    if sort_order not in {"asc", "desc"}:
        sort_order = "asc"

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

    cursor.execute("""
        SELECT DISTINCT u.user_id, u.name, u.surename
        FROM appointment a
        JOIN users u ON u.user_id = a.provider_id
        JOIN services s ON s.service_id = a.service_id
        WHERE s.business_id = ?
        ORDER BY u.name, u.surename
    """, (business_id,))
    appointment_providers = cursor.fetchall()

    # B) Agendamentos do local
    appointment_query = """
        SELECT 
            a.appointment_id, a.date, a.appointment_time, a.status,
            client.name AS client_name, client.surename AS client_surename,
            provider.user_id AS provider_id,
            provider.name AS provider_name, provider.surename AS provider_surename,
            s.name AS service_name
        FROM appointment a
        JOIN users client ON a.user_id = client.user_id
        JOIN users provider ON a.provider_id = provider.user_id
        JOIN services s ON a.service_id = s.service_id
        WHERE s.business_id = ?
    """
    appointment_params = [business_id]
    if status_filter == "pending":
        appointment_query += " AND a.status IN ('requested', 'pending')"
    elif status_filter:
        appointment_query += " AND a.status = ?"
        appointment_params.append(status_filter)
    if service_filter:
        appointment_query += " AND s.service_id = ?"
        appointment_params.append(service_filter)
    if provider_filter:
        appointment_query += " AND a.provider_id = ?"
        appointment_params.append(provider_filter)
    count_query = (
        "SELECT COUNT(*) "
        + appointment_query[appointment_query.index("FROM appointment a"):]
    )
    cursor.execute(count_query, appointment_params)
    total_appointments = cursor.fetchone()[0]
    total_pages = max(
        1,
        (total_appointments + APPOINTMENT_PAGE_SIZE - 1) // APPOINTMENT_PAGE_SIZE
    )
    current_page = request.args.get("page", 1, type=int)
    current_page = min(max(current_page, 1), total_pages)
    appointment_query += (
        f" ORDER BY a.date {sort_order.upper()}, "
        f"a.appointment_time {sort_order.upper()}, "
        f"a.appointment_id {sort_order.upper()} LIMIT ? OFFSET ?"
    )
    appointment_params.extend([
        APPOINTMENT_PAGE_SIZE,
        (current_page - 1) * APPOINTMENT_PAGE_SIZE
    ])
    cursor.execute(appointment_query, appointment_params)
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

    cursor.execute("""
        SELECT image_id, position
        FROM image_assets
        WHERE owner_type = 'business' AND owner_id = ? AND role = 'gallery'
        ORDER BY position, image_id
    """, (business_id,))
    gallery_images = cursor.fetchall()
    cursor.execute("""
        SELECT image_id FROM image_assets
        WHERE owner_type = 'business' AND owner_id = ? AND role = 'banner'
    """, (business_id,))
    banner_image = cursor.fetchone()

    conn.close()

    return render_template(
        "business-manage.html",
        business=business,
        is_self_provider=is_self_provider,
        services=services,
        appointments=appointments,
        appointment_providers=appointment_providers,
        status_filter=status_filter,
        service_filter=service_filter,
        provider_filter=provider_filter,
        sort_order=sort_order,
        current_page=current_page,
        total_pages=total_pages,
        total_appointments=total_appointments,
        page_size=APPOINTMENT_PAGE_SIZE,
        pending_requests=pending_requests,
        active_members=active_members,
        gallery_images=gallery_images,
        banner_image=banner_image
    )


@business_bp.route("/manage/<int:business_id>/images/upload", methods=["POST"])
def upload_business_image(business_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM business WHERE business_id = ? AND owner_id = ?",
        (business_id, session.get("user_id")),
    )
    if not cursor.fetchone():
        conn.close()
        return apology("Acesso restrito ao proprietário do estabelecimento.", 403)

    role = request.form.get("role")
    if role not in {"banner", "gallery"}:
        conn.close()
        return apology("Tipo de imagem inválido.", 400)
    if role == "banner":
        try:
            save_image_upload(
                conn, request.files.get("image"), "business", business_id, role, request.form
            )
        except ImageUploadError as error:
            flash(str(error), "danger")
        else:
            flash("Banner atualizado com sucesso.", "success")
    else:
        images = [
            image for image in request.files.getlist("images")
            if image and image.filename
        ]
        if not images:
            flash("Selecione pelo menos uma imagem para a galeria.", "warning")
        else:
            saved_count = 0
            upload_error = None
            for image in images:
                try:
                    save_image_upload(
                        conn, image, "business", business_id, role, request.form
                    )
                    saved_count += 1
                except ImageUploadError as error:
                    upload_error = error
                    break
            if upload_error:
                if saved_count:
                    flash(
                        f"{saved_count} imagem(ns) adicionada(s). As demais não foram "
                        f"processadas: {upload_error}",
                        "warning",
                    )
                else:
                    flash(str(upload_error), "danger")
            else:
                flash(
                    f"{saved_count} imagem(ns) adicionada(s) à galeria.",
                    "success",
                )
    conn.close()
    return redirect(url_for("business.manage_business", business_id=business_id))


@business_bp.route(
    "/manage/<int:business_id>/images/<int:image_id>/delete", methods=["POST"]
)
def remove_business_image(business_id, image_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM business WHERE business_id = ? AND owner_id = ?",
        (business_id, session.get("user_id")),
    )
    if not cursor.fetchone():
        conn.close()
        return apology("Acesso restrito ao proprietário do estabelecimento.", 403)

    removed = delete_image_asset(conn, image_id, "business", business_id)
    conn.close()
    flash(
        "Imagem removida." if removed else "Imagem não encontrada.",
        "success" if removed else "warning",
    )
    return redirect(url_for("business.manage_business", business_id=business_id))


@business_bp.route(
    "/manage/<int:business_id>/images/<int:image_id>/move/<direction>", methods=["POST"]
)
def reorder_business_image(business_id, image_id, direction):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM business WHERE business_id = ? AND owner_id = ?",
        (business_id, session.get("user_id")),
    )
    if not cursor.fetchone():
        conn.close()
        return apology("Acesso restrito ao proprietário do estabelecimento.", 403)

    moved = move_gallery_image(conn, image_id, business_id, direction)
    conn.close()
    if not moved:
        flash("A imagem não pode ser movida nessa direção.", "warning")
    return redirect(url_for("business.manage_business", business_id=business_id))


@business_bp.route("/manage/<int:business_id>/delete", methods=["GET", "POST"])
def delete_business(business_id):
    user_id = session.get("user_id")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT business_name FROM business WHERE business_id = ? AND owner_id = ?",
        (business_id, user_id)
    )
    business = cursor.fetchone()
    if not business:
        conn.close()
        return apology("Estabelecimento não encontrado ou acesso não autorizado.", 403)

    if request.method == "POST":
        if request.form.get("confirm") != "yes":
            flash("Confirme que entende que a exclusão é permanente.", "warning")
            conn.close()
            return redirect(url_for("business.delete_business", business_id=business_id))

        business_missing = False
        with conn:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM business WHERE business_id = ? AND owner_id = ?",
                (business_id, user_id)
            )
            if not cursor.fetchone():
                business_missing = True
            else:
                cursor.execute("""
                    DELETE FROM appointment
                    WHERE service_id IN (
                        SELECT service_id FROM services WHERE business_id = ?
                    )
                """, (business_id,))
                cursor.execute("DELETE FROM provider_services WHERE business_id = ?", (business_id,))
                cursor.execute("DELETE FROM business_providers WHERE business_id = ?", (business_id,))
                cursor.execute("DELETE FROM services WHERE business_id = ?", (business_id,))
                cursor.execute(
                    "DELETE FROM business WHERE business_id = ? AND owner_id = ?",
                    (business_id, user_id)
                )

        if not business_missing:
            delete_owner_image_assets(conn, "business", business_id)
        conn.close()
        if business_missing:
            return apology("Estabelecimento não encontrado ou acesso não autorizado.", 403)
        flash("Estabelecimento e todos os dados vinculados foram excluídos.", "success")
        return redirect(url_for("business.home"))

    cursor.execute(
        "SELECT COUNT(*) AS total FROM services WHERE business_id = ?",
        (business_id,)
    )
    service_count = cursor.fetchone()["total"]
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM appointment a
        JOIN services s ON s.service_id = a.service_id
        WHERE s.business_id = ?
    """, (business_id,))
    appointment_count = cursor.fetchone()["total"]
    cursor.execute(
        "SELECT COUNT(*) AS total FROM business_providers WHERE business_id = ?",
        (business_id,)
    )
    provider_count = cursor.fetchone()["total"]
    cursor.execute(
        "SELECT COUNT(*) AS total FROM provider_services WHERE business_id = ?",
        (business_id,)
    )
    provider_service_count = cursor.fetchone()["total"]
    conn.close()

    return render_template(
        "business-delete-confirm.html",
        title="Excluir estabelecimento",
        description=f"O estabelecimento “{business['business_name']}” e os dados abaixo serão removidos:",
        items=[
            ("Serviços", service_count),
            ("Agendamentos desses serviços", appointment_count),
            ("Vínculos de prestadores", provider_count),
            ("Associações entre prestadores e serviços", provider_service_count),
        ],
        cancel_url=url_for("business.manage_business", business_id=business_id),
        submit_label="Excluir estabelecimento",
    )


@business_bp.route("/manage/<int:business_id>/edit", methods=["GET", "POST"])
def edit_business(business_id):
    user_id = session.get("user_id")
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM business WHERE business_id = ? AND owner_id = ?",
        (business_id, user_id)
    )
    business = cursor.fetchone()
    if not business:
        conn.close()
        return apology("Estabelecimento não encontrado ou acesso não autorizado.", 403)

    if request.method == "POST":
        business_name = request.form.get("business_name", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "").strip()
        phone = normalize_phone(request.form.get("phone_ddd"), request.form.get("phone_number"))
        cep = request.form.get("cep", "").replace("-", "").strip() or None
        street = normalize_street(request.form.get("street"))
        number = request.form.get("number", "").strip()
        complement = request.form.get("complement", "").strip()
        neighborhood = request.form.get("neighborhood", "").strip()
        city = request.form.get("city", "").strip()
        state = request.form.get("state", "").strip()

        cursor.execute(
            "SELECT 1 FROM business WHERE phone = ? AND business_id != ?",
            (phone, business_id)
        )
        phone_taken = cursor.fetchone()

        if not all([business_name, category, phone, street, number, neighborhood, city, state]):
            flash("Preencha todos os campos obrigatórios do estabelecimento.", "danger")
        elif phone_taken:
            flash("Este número de telefone já está cadastrado em outro estabelecimento.", "danger")
        else:
            cursor.execute("""
                UPDATE business
                SET business_name = ?, description = ?, category = ?, phone = ?,
                    cep = ?, street = ?, number = ?, complement = ?,
                    neighborhood = ?, city = ?, state = ?
                WHERE business_id = ? AND owner_id = ?
            """, (
                business_name, description, category, phone, cep, street, number,
                complement, neighborhood, city, state, business_id, user_id
            ))
            conn.commit()
            conn.close()
            flash("Estabelecimento atualizado com sucesso.", "success")
            return redirect(url_for("business.manage_business", business_id=business_id))

    conn.close()
    return render_template(
        "business-edit.html",
        business=business,
        ddds=BUSINESS_DDDS,
        categories=BUSINESS_CATEGORIES,
        states=BRAZILIAN_STATES
    )


# 2. ROTA DE VISUALIZAÇÃO / PAINEL DO PRESTADOR
@business_bp.route("/view/<int:business_id>")
def provider_view(business_id):
    user_id = session.get("user_id")
    conn = get_db()
    cursor = conn.cursor()
    status_filter = request.args.get("status", "")
    if status_filter not in {"", "pending", "confirmed", "cancelled", "completed"}:
        status_filter = ""
    service_filter = request.args.get("service_id", type=int)
    sort_order = request.args.get("order", "asc")
    if sort_order not in {"asc", "desc"}:
        sort_order = "asc"

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

    # Agendamentos do prestador logado, com filtros opcionais
    appointment_query = """
        SELECT 
            a.appointment_id, a.date, a.appointment_time, a.status,
            client.name AS client_name, client.surename AS client_surename,
            provider.name AS provider_name, provider.surename AS provider_surename,
            s.name AS service_name
        FROM appointment a
        JOIN users client ON a.user_id = client.user_id
        JOIN users provider ON a.provider_id = provider.user_id
        JOIN services s ON a.service_id = s.service_id
                WHERE s.business_id = ?
                    AND a.provider_id = ?
    """
    appointment_params = [business_id, user_id]
    if status_filter == "pending":
        appointment_query += " AND a.status IN ('requested', 'pending')"
    elif status_filter:
        appointment_query += " AND a.status = ?"
        appointment_params.append(status_filter)
    if service_filter:
        appointment_query += " AND s.service_id = ?"
        appointment_params.append(service_filter)
    count_query = (
        "SELECT COUNT(*) "
        + appointment_query[appointment_query.index("FROM appointment a"):]
    )
    cursor.execute(count_query, appointment_params)
    total_appointments = cursor.fetchone()[0]
    total_pages = max(
        1,
        (total_appointments + APPOINTMENT_PAGE_SIZE - 1) // APPOINTMENT_PAGE_SIZE
    )
    current_page = request.args.get("page", 1, type=int)
    current_page = min(max(current_page, 1), total_pages)
    appointment_query += (
        f" ORDER BY a.date {sort_order.upper()}, "
        f"a.appointment_time {sort_order.upper()}, "
        f"a.appointment_id {sort_order.upper()} LIMIT ? OFFSET ?"
    )
    appointment_params.extend([
        APPOINTMENT_PAGE_SIZE,
        (current_page - 1) * APPOINTMENT_PAGE_SIZE
    ])
    cursor.execute(appointment_query, appointment_params)
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
        services=services,
        status_filter=status_filter,
        service_filter=service_filter,
        sort_order=sort_order,
        current_page=current_page,
        total_pages=total_pages,
        total_appointments=total_appointments,
        page_size=APPOINTMENT_PAGE_SIZE
    )


# 3. ROTA PARA CANCELAR AGENDAMENTO (PRESTADOR / PROPRIETÁRIO)
@business_bp.route("/appointment/<int:appointment_id>/cancel", methods=["POST"])
def cancel_appointment(appointment_id):
    user_id = session.get("user_id")
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT a.provider_id, s.business_id, b.owner_id
        FROM appointment a
        JOIN services s ON s.service_id = a.service_id
        JOIN business b ON b.business_id = s.business_id
        WHERE a.appointment_id = ?
    """, (appointment_id,))
    appointment = cursor.fetchone()
    if not appointment:
        conn.close()
        return apology("Agendamento não encontrado.", 404)

    is_owner = appointment["owner_id"] == user_id
    is_assigned_provider = appointment["provider_id"] == user_id
    if is_assigned_provider and not is_owner:
        cursor.execute("""
            SELECT 1 FROM business_providers
            WHERE business_id = ? AND user_id = ? AND status = 'active'
        """, (appointment["business_id"], user_id))
        is_assigned_provider = cursor.fetchone() is not None
    if not is_owner and not is_assigned_provider:
        conn.close()
        return apology("Você não tem permissão para cancelar este agendamento.", 403)

    cursor.execute("""
        UPDATE appointment
        SET status = 'cancelled'
        WHERE appointment_id = ? AND status IN ('requested', 'confirmed')
    """, (appointment_id,))
    changed = cursor.rowcount
    conn.commit()
    conn.close()

    if changed:
        flash("Agendamento cancelado.", "info")
    else:
        flash("Este agendamento não pode mais ser cancelado.", "warning")
    if is_owner:
        return redirect(url_for(
            "business.manage_business",
            business_id=appointment["business_id"]
        ))
    return redirect(url_for(
        "business.provider_view",
        business_id=appointment["business_id"]
    ))


@business_bp.route("/appointment/<int:appointment_id>/confirm", methods=["POST"])
def confirm_appointment(appointment_id):
    user_id = session.get("user_id")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.provider_id, s.business_id, b.owner_id
        FROM appointment a
        JOIN services s ON s.service_id = a.service_id
        JOIN business b ON b.business_id = s.business_id
        WHERE a.appointment_id = ?
    """, (appointment_id,))
    appointment = cursor.fetchone()
    if not appointment:
        conn.close()
        return apology("Agendamento não encontrado.", 404)

    is_owner = appointment["owner_id"] == user_id
    is_assigned_provider = appointment["provider_id"] == user_id
    if is_assigned_provider and not is_owner:
        cursor.execute("""
            SELECT 1 FROM business_providers
            WHERE business_id = ? AND user_id = ? AND status = 'active'
        """, (appointment["business_id"], user_id))
        is_assigned_provider = cursor.fetchone() is not None
    if not is_owner and not is_assigned_provider:
        conn.close()
        return apology("Você não tem permissão para confirmar este agendamento.", 403)

    cursor.execute("""
        UPDATE appointment
        SET status = 'confirmed'
        WHERE appointment_id = ? AND status = 'requested'
    """, (appointment_id,))
    changed = cursor.rowcount
    conn.commit()
    conn.close()

    if changed:
        flash("Solicitação de agendamento confirmada.", "success")
    else:
        flash("Esta solicitação não está mais pendente.", "warning")
    if is_owner:
        return redirect(url_for(
            "business.manage_business",
            business_id=appointment["business_id"]
        ))
    return redirect(url_for(
        "business.provider_view",
        business_id=appointment["business_id"]
    ))


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

    cursor.execute(
        "SELECT owner_id FROM business WHERE business_id = ?",
        (business_id,)
    )
    business = cursor.fetchone()

    if not business or business["owner_id"] != user_id:
        conn.close()
        return apology("Ação não autorizada.", 403)

    cursor.execute(
        "SELECT status FROM business_providers WHERE business_id = ? AND user_id = ?",
        (business_id, provider_user_id)
    )
    provider = cursor.fetchone()
    if not provider:
        conn.close()
        flash("Vínculo de prestador não encontrado.", "warning")
        return redirect(url_for("business.manage_business", business_id=business_id))
    if provider_user_id == user_id:
        conn.close()
        return apology("O proprietário não pode ser removido da própria equipe.", 400)
    conn.close()
    return redirect(url_for(
        "business.remove_provider",
        business_id=business_id,
        provider_user_id=provider_user_id
    ))


@business_bp.route(
    "/manage/<int:business_id>/provider/<int:provider_user_id>/remove",
    methods=["GET", "POST"]
)
def remove_provider(business_id, provider_user_id):
    user_id = session.get("user_id")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.name, u.surename, b.owner_id
        FROM business_providers bp
        JOIN users u ON u.user_id = bp.user_id
        JOIN business b ON b.business_id = bp.business_id
        WHERE bp.business_id = ? AND bp.user_id = ?
    """, (business_id, provider_user_id))
    provider = cursor.fetchone()
    if not provider or provider["owner_id"] != user_id:
        conn.close()
        return apology("Prestador não encontrado ou acesso não autorizado.", 403)
    if provider_user_id == user_id:
        conn.close()
        return apology("O proprietário não pode ser removido da própria equipe.", 400)

    if request.method == "POST":
        if request.form.get("confirm") != "yes":
            flash("Confirme que entende que os agendamentos serão removidos.", "warning")
            conn.close()
            return redirect(url_for(
                "business.remove_provider",
                business_id=business_id,
                provider_user_id=provider_user_id
            ))

        provider_missing = False
        with conn:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.cursor()
            cursor.execute("""
                SELECT bp.user_id
                FROM business_providers bp
                JOIN business b ON b.business_id = bp.business_id
                WHERE bp.business_id = ? AND bp.user_id = ?
                  AND b.owner_id = ? AND bp.user_id != b.owner_id
            """, (business_id, provider_user_id, user_id))
            if not cursor.fetchone():
                provider_missing = True
            else:
                cursor.execute("""
                    DELETE FROM appointment
                    WHERE provider_id = ?
                      AND service_id IN (
                          SELECT service_id FROM services WHERE business_id = ?
                      )
                """, (provider_user_id, business_id))
                cursor.execute(
                    "DELETE FROM provider_services WHERE business_id = ? AND user_id = ?",
                    (business_id, provider_user_id)
                )
                cursor.execute(
                    "DELETE FROM business_providers WHERE business_id = ? AND user_id = ?",
                    (business_id, provider_user_id)
                )

        conn.close()
        if provider_missing:
            return apology("Prestador não encontrado ou acesso não autorizado.", 403)
        flash("Prestador e seus agendamentos deste estabelecimento foram removidos.", "info")
        return redirect(url_for("business.manage_business", business_id=business_id))

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM appointment a
        JOIN services s ON s.service_id = a.service_id
        WHERE a.provider_id = ? AND s.business_id = ?
    """, (provider_user_id, business_id))
    appointment_count = cursor.fetchone()["total"]
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM provider_services
        WHERE business_id = ? AND user_id = ?
    """, (business_id, provider_user_id))
    service_count = cursor.fetchone()["total"]
    conn.close()

    return render_template(
        "business-delete-confirm.html",
        title="Remover prestador",
        description=(
            f"{provider['name']} {provider['surename']} será removido da equipe "
            "deste estabelecimento. A conta e os outros vínculos dele serão mantidos."
        ),
        items=[
            ("Agendamentos com este prestador neste estabelecimento", appointment_count),
            ("Associações do prestador a serviços", service_count),
        ],
        cancel_url=url_for("business.manage_business", business_id=business_id),
        submit_label="Remover prestador",
    )


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


@business_bp.route("/manage/<int:business_id>/service/<int:service_id>/edit", methods=["GET", "POST"])
def edit_service(business_id, service_id):
    user_id = session.get("user_id")
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.*, b.business_name, b.category
        FROM services s
        JOIN business b ON b.business_id = s.business_id
        WHERE s.service_id = ? AND s.business_id = ? AND b.owner_id = ?
    """, (service_id, business_id, user_id))
    service = cursor.fetchone()
    if not service:
        conn.close()
        return apology("Serviço não encontrado ou acesso não autorizado.", 403)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        price_raw = request.form.get("price", "").strip()
        duration_minutes = request.form.get("duration_minutes", type=int)

        try:
            price = float(price_raw)
        except (TypeError, ValueError):
            price = None

        if not name or price is None or price < 0 or not duration_minutes:
            flash("Informe nome, preço e duração válidos.", "danger")
        elif duration_minutes < 5 or duration_minutes > 1440:
            flash("A duração deve estar entre 5 e 1440 minutos.", "danger")
        else:
            cursor.execute("""
                UPDATE services
                SET name = ?, description = ?, price = ?, duration_minutes = ?
                WHERE service_id = ? AND business_id = ?
            """, (name, description, price, duration_minutes, service_id, business_id))
            conn.commit()
            conn.close()
            flash("Serviço atualizado com sucesso.", "success")
            return redirect(url_for("business.manage_business", business_id=business_id))

    conn.close()
    return render_template("service-edit.html", service=service, business_id=business_id)


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
@business_bp.route("/manage/<int:business_id>/service/<int:service_id>/delete", methods=["GET", "POST"])
def delete_service(business_id, service_id):
    user_id = session.get("user_id")
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.name
        FROM services s
        JOIN business b ON b.business_id = s.business_id
        WHERE s.service_id = ? AND s.business_id = ? AND b.owner_id = ?
    """, (service_id, business_id, user_id))
    service = cursor.fetchone()
    if not service:
        conn.close()
        return apology("Serviço não encontrado ou acesso não autorizado.", 403)

    if request.method == "POST":
        if request.form.get("confirm") != "yes":
            flash("Confirme que entende que a exclusão é permanente.", "warning")
            conn.close()
            return redirect(url_for(
                "business.delete_service",
                business_id=business_id,
                service_id=service_id
            ))

        service_missing = False
        with conn:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM services s
                JOIN business b ON b.business_id = s.business_id
                WHERE s.service_id = ? AND s.business_id = ? AND b.owner_id = ?
            """, (service_id, business_id, user_id))
            if not cursor.fetchone():
                service_missing = True
            else:
                cursor.execute("DELETE FROM appointment WHERE service_id = ?", (service_id,))
                cursor.execute("DELETE FROM provider_services WHERE service_id = ?", (service_id,))
                cursor.execute(
                    "DELETE FROM services WHERE service_id = ? AND business_id = ?",
                    (service_id, business_id)
                )

        conn.close()
        if service_missing:
            return apology("Serviço não encontrado ou acesso não autorizado.", 403)
        flash("Serviço e agendamentos vinculados foram removidos.", "info")
        return redirect(url_for("business.manage_business", business_id=business_id))

    cursor.execute(
        "SELECT COUNT(*) AS total FROM appointment WHERE service_id = ?",
        (service_id,)
    )
    appointment_count = cursor.fetchone()["total"]
    cursor.execute(
        "SELECT COUNT(*) AS total FROM provider_services WHERE service_id = ?",
        (service_id,)
    )
    provider_count = cursor.fetchone()["total"]
    conn.close()

    return render_template(
        "business-delete-confirm.html",
        title="Remover serviço",
        description=f"O serviço “{service['name']}” e os dados abaixo serão removidos:",
        items=[
            ("Agendamentos", appointment_count),
            ("Associações de prestadores ao serviço", provider_count),
        ],
        cancel_url=url_for("business.manage_business", business_id=business_id),
        submit_label="Remover serviço",
    )

# Formulário e ação de seleção de serviços do prestador
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

    # GET: verifica se o usuário autenticado é o proprietário do estabelecimento
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