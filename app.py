import os

from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

# Importa funções auxiliares
from helpers import apology, brl, category_slug, close_db, format_phone, get_db, normalize_phone

# Importa os Blueprints
from blueprints.client import client_bp
from blueprints.business import business_bp

# Configura a aplicação
app = Flask(__name__)

# Filtros personalizados
app.jinja_env.filters["brl"] = brl  # -> R$
app.jinja_env.filters["category_slug"] = category_slug
app.jinja_env.filters["phone"] = format_phone

# Configura a sessão para usar o sistema de arquivos
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Registra o encerramento do contexto
app.teardown_appcontext(close_db)

# Registrar os Blueprints na aplicação
app.register_blueprint(client_bp)
app.register_blueprint(business_bp)


DDD_CODES = [
    "11", "12", "13", "14", "15", "16", "17", "18", "19", "21", "22", "24",
    "27", "28", "31", "32", "33", "34", "35", "37", "38", "41", "42", "43",
    "44", "45", "46", "47", "48", "49", "51", "53", "54", "55", "61", "62",
    "63", "64", "65", "66", "67", "68", "69", "71", "73", "74", "75", "77",
    "79", "81", "82", "83", "84", "85", "86", "87", "88", "89", "91", "92",
    "93", "94", "95", "96", "97", "98", "99"
]


@app.route("/profile", methods=["GET", "POST"])
def profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("client.login_user"))

    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        surename = request.form.get("surename", "").strip()
        username = request.form.get("username", "").strip()
        phone = normalize_phone(request.form.get("phone_ddd"), request.form.get("phone_number"))
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirmation = request.form.get("confirmation", "")

        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        current_user = cursor.fetchone()
        cursor.execute("SELECT user_id FROM users WHERE username = ? AND user_id != ?", (username, user_id))
        username_taken = cursor.fetchone()
        cursor.execute("SELECT user_id FROM users WHERE phone = ? AND user_id != ?", (phone, user_id))
        phone_taken = cursor.fetchone()

        if not name or not surename or not username or not phone:
            flash("Preencha todos os dados pessoais corretamente.", "danger")
        elif username_taken:
            flash("Este nome de usuário já está em uso.", "danger")
        elif phone_taken:
            flash("Este número de telefone já está cadastrado.", "danger")
        elif new_password and not check_password_hash(current_user["password_hash"], current_password):
            flash("A senha atual está incorreta.", "danger")
        elif new_password and new_password != confirmation:
            flash("As novas senhas devem ser iguais.", "danger")
        else:
            password_hash = current_user["password_hash"]
            if new_password:
                password_hash = generate_password_hash(new_password)
            cursor.execute("""
                UPDATE users
                SET name = ?, surename = ?, username = ?, phone = ?, password_hash = ?
                WHERE user_id = ?
            """, (name, surename, username, phone, password_hash, user_id))
            conn.commit()
            flash("Perfil atualizado com sucesso.", "success")

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return render_template("profile.html", user=user, ddd_codes=DDD_CODES)


# Disables browser caching
@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# ====================================
#   RETORNOS DE ERROS GERAIS
# ====================================

@app.errorhandler(404)
def not_found(error):
    return apology("Página não encontrada!", 404)


@app.errorhandler(418)
def teapot(error):
    return redirect("https://www.google.com/teapot")


# ====================================
#   APP STARTER
# ====================================

if __name__ == "__main__":
    app.run(debug=True)