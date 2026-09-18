import sqlite3
import random
from collections import defaultdict
from datetime import datetime, timedelta
from flask import Blueprint, flash, redirect, render_template, request, session, jsonify, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, get_db, login_required, normalize_phone

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
    user_name = None

    if session.get("user_id"):
        cursor.execute("SELECT name FROM users WHERE user_id = ?", (session["user_id"],))
        user = cursor.fetchone()
        user_name = user["name"] if user else None

    # Recebe os parâmetros de filtro via GET
    search_query = request.args.get("q", "").strip()
    selected_state = request.args.get("state", "").strip()
    selected_city = request.args.get("city", "").strip()
    selected_neighborhood = request.args.get("neighborhood", "").strip()
    selected_category = request.args.get("category", "").strip()

    cursor.execute("""
        SELECT DISTINCT state, city, neighborhood
        FROM business
        JOIN services s ON s.business_id = business.business_id
        WHERE state IS NOT NULL AND state != ''
          AND city IS NOT NULL AND city != ''
          AND neighborhood IS NOT NULL AND neighborhood != ''
        ORDER BY state, city, neighborhood
    """)
    location_rows = cursor.fetchall()
    locations = defaultdict(lambda: defaultdict(list))
    for row in location_rows:
        if row["neighborhood"] not in locations[row["state"]][row["city"]]:
            locations[row["state"]][row["city"]].append(row["neighborhood"])
    locations = {
        state: dict(cities)
        for state, cities in locations.items()
    }

    if selected_state not in locations:
        selected_state = ""
    if selected_state and selected_city not in locations[selected_state]:
        selected_city = ""
    if selected_state and selected_city and selected_neighborhood not in locations[selected_state][selected_city]:
        selected_neighborhood = ""

    # Monta a SQL dinâmica
    query = """
        SELECT 
            b.*,
            GROUP_CONCAT(DISTINCT s.name) AS services_list
        FROM business b
        JOIN services s ON b.business_id = s.business_id
        WHERE 1=1
    """
    params = []

    if search_query:
        query += " AND (b.business_name LIKE ? OR b.description LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])

    if selected_state:
        query += " AND b.state = ?"
        params.append(selected_state)

    if selected_city:
        query += " AND b.city = ?"
        params.append(selected_city)

    if selected_neighborhood:
        query += " AND b.neighborhood = ?"
        params.append(selected_neighborhood)

    if selected_category:
        query += " AND b.category = ?"
        params.append(selected_category)

    query += " GROUP BY b.business_id ORDER BY b.business_name ASC"
    cursor.execute(query, params)
    businesses = cursor.fetchall()

    # Consultas para popular os selects de filtro dinamicamente
    cursor.execute("""
        SELECT DISTINCT b.state
        FROM business b
        JOIN services s ON s.business_id = b.business_id
        WHERE b.state IS NOT NULL AND b.state != ''
        ORDER BY b.state ASC
    """)
    states = [row["state"] for row in cursor.fetchall()]

    cities = sorted({city for state in locations.values() for city in state})
    neighborhoods = sorted({
        neighborhood
        for state in locations.values()
        for city in state.values()
        for neighborhood in city
    })

    cursor.execute("""
        SELECT DISTINCT b.category
        FROM business b
        JOIN services s ON s.business_id = b.business_id
        WHERE b.category IS NOT NULL AND b.category != ''
        ORDER BY b.category ASC
    """)
    categories = [row["category"] for row in cursor.fetchall()]

    conn.close()

    return render_template(
        "index.html",
        businesses=businesses,
        states=states,
        cities=cities,
        neighborhoods=neighborhoods,
        categories=categories,
        search_query=search_query,
        selected_state=selected_state,
        selected_city=selected_city,
        selected_neighborhood=selected_neighborhood,
        selected_category=selected_category,
        user_name=user_name,
        locations=locations
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
            (request.form.get("username"), hash, request.form.get("name"), request.form.get("surename"), phone, 2)
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

################################
# Appointment Routes
################################

# Exemplo de rotas dentro do client_bp
@client_bp.route("/appointment/new/<int:business_id>")
def new_appointment(business_id):
    conn = get_db()
    cursor = conn.cursor()

    # Buscar dados do estabelecimento
    cursor.execute("SELECT * FROM business WHERE business_id = ?", (business_id,))
    business = cursor.fetchone()
    if not business:
        flash("Estabelecimento não encontrado.", "danger")
        return redirect(url_for("client.index"))

    # Buscar serviços do estabelecimento
    cursor.execute("SELECT * FROM services WHERE business_id = ? ORDER BY name ASC", (business_id,))
    services = cursor.fetchall()

    conn.close()
    return render_template("appointment_new.html", business=business, services=services)


@client_bp.route("/appointments")
@login_required
def my_appointments():
    """Lista os agendamentos do cliente, priorizando os mais próximos."""
    conn = get_db()
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
        SELECT
            a.appointment_id,
            a.date,
            a.appointment_time,
            a.duration_minutes,
            a.status,
            s.name AS service_name,
            s.price,
            b.business_name,
            b.business_id,
            b.phone AS business_phone,
            b.street,
            b.number,
            b.complement,
            b.neighborhood,
            b.city,
            b.state,
            TRIM(u.name || ' ' || COALESCE(u.surename, '')) AS provider_name
        FROM appointment a
        JOIN services s ON s.service_id = a.service_id
        JOIN business b ON b.business_id = s.business_id
        LEFT JOIN users u ON u.user_id = a.provider_id
                WHERE a.user_id = ?
                    AND a.status NOT IN ('cancelled', 'completed')
        ORDER BY
            CASE WHEN a.date >= ? THEN 0 ELSE 1 END,
            ABS(julianday(a.date) - julianday(?)),
            a.appointment_time ASC
    """, (session["user_id"], today, today))
    appointments = cursor.fetchall()
    conn.close()

    return render_template(
        "client-appointments.html",
        appointments=appointments,
        today=today
    )


@client_bp.route("/appointment/<int:appointment_id>/cancel", methods=["POST"])
@login_required
def cancel_client_appointment(appointment_id):
    """Cancela somente um agendamento pertencente ao cliente logado."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE appointment
        SET status = 'cancelled'
        WHERE appointment_id = ?
          AND user_id = ?
          AND status != 'cancelled'
    """, (appointment_id, session["user_id"]))
    conn.commit()
    changed = cursor.rowcount
    conn.close()

    if changed:
        flash("Agendamento cancelado com sucesso.", "success")
    else:
        flash("Agendamento não encontrado ou já cancelado.", "warning")
    return redirect(url_for("client.my_appointments"))


@client_bp.route("/api/services/<int:service_id>/staff")
def get_service_staff(service_id):
    """Retorna os prestadores que executam o serviço selecionado."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT
            u.user_id AS staff_id,
            TRIM(u.name || ' ' || COALESCE(u.surename, '')) AS name,
            bp.role
        FROM provider_services ps
        JOIN business_providers bp
          ON bp.business_id = ps.business_id
         AND bp.user_id = ps.user_id
        JOIN users u ON u.user_id = bp.user_id
        WHERE ps.service_id = ?
          AND bp.status = 'active'
        ORDER BY name ASC
    """, (service_id,))
    staff_members = cursor.fetchall()
    
    # Se o serviço ainda não tiver vínculos, oferece todos os prestadores ativos
    # do estabelecimento para que o cliente ainda consiga prosseguir.
    if not staff_members:
        cursor.execute("""
            SELECT DISTINCT
                u.user_id AS staff_id,
                TRIM(u.name || ' ' || COALESCE(u.surename, '')) AS name,
                bp.role
            FROM services s
            JOIN business_providers bp ON bp.business_id = s.business_id
            JOIN users u ON u.user_id = bp.user_id
            WHERE s.service_id = ?
              AND bp.status = 'active'
            ORDER BY name ASC
        """, (service_id,))
        staff_members = cursor.fetchall()

    conn.close()
    return jsonify([dict(st) for st in staff_members])


@client_bp.route("/api/availability")
def get_availability():
    """Retorna a lista de horários livres em um determinado dia para um prestador ou 'qualquer'."""
    business_id = request.args.get("business_id", type=int)
    service_id = request.args.get("service_id", type=int)
    staff_id = request.args.get("staff_id", default="any")  # "any" ou int
    date_str = request.args.get("date")  # YYYY-MM-DD

    if not date_str or not business_id or not service_id:
        return jsonify({"error": "Parâmetros inválidos"}), 400

    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Data inválida"}), 400

    today = datetime.now().date()
    if selected_date < today:
        return jsonify([])

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT duration_minutes FROM services WHERE service_id = ? AND business_id = ?",
        (service_id, business_id)
    )
    service = cursor.fetchone()
    if not service:
        conn.close()
        return jsonify({"error": "Serviço não encontrado"}), 404
    duration = service["duration_minutes"] or 30

    # 2. Buscar prestadores elegíveis
    if staff_id != "any":
        staff_ids = [int(staff_id)]
    else:
        cursor.execute("""
            SELECT DISTINCT ps.user_id
            FROM provider_services ps
            JOIN business_providers bp
              ON bp.business_id = ps.business_id
             AND bp.user_id = ps.user_id
            WHERE ps.service_id = ?
              AND ps.business_id = ?
              AND bp.status = 'active'
        """, (service_id, business_id))
        rows = cursor.fetchall()
        staff_ids = [r["user_id"] for r in rows]
        if not staff_ids:
            cursor.execute("""
                SELECT user_id
                FROM business_providers
                WHERE business_id = ? AND status = 'active'
            """, (business_id,))
            staff_ids = [r["user_id"] for r in cursor.fetchall()]

    # 3. Gerar grade de horários (exemplo: 08:00 às 18:00 de 30 em 30 min)
    # Você pode personalizar para buscar a jornada de trabalho cadastrada do prestador/estabelecimento
    slots = []
    start_time = datetime.strptime(f"{date_str} 08:00", "%Y-%m-%d %H:%M")
    end_time = datetime.strptime(f"{date_str} 18:00", "%Y-%m-%d %H:%M")

    # Buscar agendamentos já existentes na data para filtrar conflitos
    cursor.execute("""
                SELECT a.provider_id, a.appointment_time, a.duration_minutes
                FROM appointment a
                JOIN services s ON s.service_id = a.service_id
                WHERE a.date = ?
                    AND s.business_id = ?
                    AND a.status != 'cancelled'
        """, (date_str, business_id))
    existing_appointments = cursor.fetchall()

    current = start_time
    now = datetime.now()
    while current + timedelta(minutes=duration) <= end_time:
        slot_str = current.strftime("%H:%M")
        available_staff_for_slot = []

        # Para hoje, não oferece horários cujo início já passou.
        if selected_date == today and current <= now:
            current += timedelta(minutes=30)
            continue

        for st_id in staff_ids:
            is_busy = False
            for appointment in existing_appointments:
                if appointment["provider_id"] != st_id:
                    continue

                # Agendamentos antigos sem horário bloqueiam o dia inteiro.
                if not appointment["appointment_time"]:
                    is_busy = True
                    break

                appointment_start = datetime.strptime(
                    f"{date_str} {appointment['appointment_time']}",
                    "%Y-%m-%d %H:%M"
                )
                appointment_end = appointment_start + timedelta(
                    minutes=appointment["duration_minutes"] or 30
                )
                slot_end = current + timedelta(minutes=duration)
                if max(current, appointment_start) < min(slot_end, appointment_end):
                    is_busy = True
                    break

            if not is_busy:
                available_staff_for_slot.append(st_id)

        if available_staff_for_slot:
            slots.append({
                "time": slot_str,
                "available_staff": available_staff_for_slot
            })

        current += timedelta(minutes=30)

    conn.close()
    return jsonify(slots)


@client_bp.route("/appointment/create", methods=["POST"])
def create_appointment():
    """Processa a reserva e realiza o sorteio caso 'qualquer' prestador tenha sido selecionado."""
    if "user_id" not in session:
        flash("Você precisa estar conectado para agendar.", "warning")
        return redirect(url_for("client.login"))

    business_id = request.form.get("business_id")
    service_id = request.form.get("service_id")
    staff_id_raw = request.form.get("staff_id")  # "any" ou id numérico
    date_str = request.form.get("date")
    time_str = request.form.get("time")

    conn = get_db()
    cursor = conn.cursor()

    try:
        requested_start = datetime.strptime(
            f"{date_str} {time_str}",
            "%Y-%m-%d %H:%M"
        )
    except (TypeError, ValueError):
        conn.close()
        return apology("Data ou horário inválido.", 400)

    if requested_start <= datetime.now():
        conn.close()
        flash("Não é possível agendar para um horário que já passou.", "warning")
        return redirect(url_for("client.new_appointment", business_id=business_id))

    cursor.execute(
        "SELECT duration_minutes FROM services WHERE service_id = ? AND business_id = ?",
        (service_id, business_id)
    )
    service = cursor.fetchone()
    if not service:
        conn.close()
        return apology("Serviço não encontrado.", 404)
    duration = service["duration_minutes"] or 30

    # Definição do prestador (Sorteio se for 'any')
    if staff_id_raw == "any":
        available_staff_str = request.form.get("available_staff_list", "")
        if available_staff_str:
            candidate_ids = [int(x) for x in available_staff_str.split(",") if x.isdigit()]
        else:
            candidate_ids = []

        if not candidate_ids:
            flash("Desculpe, o horário selecionado não está mais disponível.", "danger")
            return redirect(url_for("client.new_appointment", business_id=business_id))

        # Sortear aleatoriamente entre os prestadores livres para o horário
        final_staff_id = random.choice(candidate_ids)
    else:
        final_staff_id = int(staff_id_raw)

    # Inserir no banco de dados
    cursor.execute("""
        INSERT INTO appointment
            (user_id, provider_id, service_id, date, appointment_time, duration_minutes, status)
        VALUES (?, ?, ?, ?, ?, ?, 'confirmed')
    """, (session["user_id"], final_staff_id, service_id, date_str, time_str, duration))

    conn.commit()
    conn.close()

    flash("Agendamento realizado com sucesso!", "success")
    return redirect(url_for("client.index"))