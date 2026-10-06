import os

import os

from flask import Flask, flash, redirect, render_template, request, send_from_directory, session, url_for
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from constants import BUSINESS_DDDS
# Importa funções auxiliares
from helpers import apology, brl, category_slug, close_db, format_phone, get_db, normalize_phone
from image_storage import (
    ImageUploadError,
    delete_image_asset,
    delete_owner_image_assets,
    save_image_upload,
)

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
app.config["UPLOAD_FOLDER"] = os.path.join(app.instance_path, "uploads")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
Session(app)

# Registra o encerramento do contexto
app.teardown_appcontext(close_db)

# Registrar os Blueprints na aplicação
app.register_blueprint(client_bp)
app.register_blueprint(business_bp)


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

        cursor.execute("""
            SELECT users.*,
                (SELECT image_id FROM image_assets
                 WHERE owner_type = 'user' AND owner_id = users.user_id AND role = 'profile')
                AS profile_image_id
            FROM users WHERE user_id = ?
        """, (user_id,))
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

    cursor.execute("""
        SELECT users.*,
            (SELECT image_id FROM image_assets
             WHERE owner_type = 'user' AND owner_id = users.user_id AND role = 'profile')
            AS profile_image_id
        FROM users WHERE user_id = ?
    """, (user_id,))
    user = cursor.fetchone()
    conn.close()
    return render_template("profile.html", user=user, ddd_codes=BUSINESS_DDDS)


@app.route("/profile/image", methods=["POST"])
def upload_profile_image():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("client.login_user"))

    conn = get_db()
    try:
        save_image_upload(
            conn, request.files.get("image"), "user", user_id, "profile", request.form
        )
    except ImageUploadError as error:
        flash(str(error), "danger")
    else:
        flash("Imagem de perfil atualizada.", "success")
    finally:
        conn.close()
    return redirect(url_for("profile"))


@app.route("/profile/image/delete", methods=["POST"])
def delete_profile_image():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("client.login_user"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT image_id FROM image_assets
        WHERE owner_type = 'user' AND owner_id = ? AND role = 'profile'
    """, (user_id,))
    asset = cursor.fetchone()
    if asset:
        delete_image_asset(conn, asset["image_id"], "user", user_id)
        flash("Imagem de perfil removida.", "success")
    else:
        flash("Você ainda não possui uma imagem de perfil.", "warning")
    conn.close()
    return redirect(url_for("profile"))


@app.route("/images/<int:image_id>")
def serve_image(image_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT storage_path FROM image_assets WHERE image_id = ?",
        (image_id,)
    )
    asset = cursor.fetchone()
    conn.close()
    if not asset:
        return apology("Imagem não encontrada.", 404)
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        asset["storage_path"],
        mimetype="image/webp",
        max_age=86400,
    )


def _account_deletion_impact(cursor, user_id, user_type):
    cursor.execute(
        "SELECT COUNT(*) AS total FROM appointment WHERE user_id = ? OR provider_id = ?",
        (user_id, user_id)
    )
    client_appointments = cursor.fetchone()["total"]

    if user_type == 2:
        return {
            "account_role": "cliente",
            "business_count": 0,
            "service_count": 0,
            "appointment_count": client_appointments,
            "provider_link_count": 0,
        }

    if user_type != 1:
        return None

    cursor.execute(
        "SELECT COUNT(*) AS total FROM business WHERE owner_id = ?",
        (user_id,)
    )
    business_count = cursor.fetchone()["total"]
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM services s
        JOIN business b ON b.business_id = s.business_id
        WHERE b.owner_id = ?
    """, (user_id,))
    service_count = cursor.fetchone()["total"]
    cursor.execute("""
        SELECT COUNT(DISTINCT a.appointment_id) AS total
        FROM appointment a
        LEFT JOIN services s ON s.service_id = a.service_id
        LEFT JOIN business b ON b.business_id = s.business_id
        WHERE a.user_id = ? OR a.provider_id = ? OR b.owner_id = ?
    """, (user_id, user_id, user_id))
    appointment_count = cursor.fetchone()["total"]
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM business_providers
        WHERE user_id = ? OR business_id IN (
            SELECT business_id FROM business WHERE owner_id = ?
        )
    """, (user_id, user_id))
    provider_link_count = cursor.fetchone()["total"]
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM provider_services
        WHERE user_id = ? OR business_id IN (
            SELECT business_id FROM business WHERE owner_id = ?
        )
    """, (user_id, user_id))
    provider_service_count = cursor.fetchone()["total"]

    return {
        "account_role": "proprietário" if business_count else "prestador",
        "business_count": business_count,
        "service_count": service_count,
        "appointment_count": appointment_count,
        "provider_link_count": provider_link_count,
        "provider_service_count": provider_service_count,
    }


@app.route("/profile/delete", methods=["GET", "POST"])
def delete_account():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("client.login_user"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_type FROM users WHERE user_id = ?",
        (user_id,)
    )
    user = cursor.fetchone()

    if not user:
        session.clear()
        conn.close()
        return redirect(url_for("client.login_user"))

    impact = _account_deletion_impact(cursor, user_id, user["user_type"])
    if impact is None:
        conn.close()
        return apology("Tipo de conta inválido para exclusão.", 400)

    if request.method == "POST":
        if request.form.get("confirm") != "yes":
            flash("Confirme que entende que a exclusão é permanente.", "warning")
            conn.close()
            return render_template("account-delete.html", impact=impact), 400

        account_missing = False
        invalid_account_type = False
        with conn:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_type FROM users WHERE user_id = ?",
                (user_id,)
            )
            current_user = cursor.fetchone()
            if not current_user:
                account_missing = True
            elif current_user["user_type"] not in (1, 2):
                invalid_account_type = True
            else:
                cursor.execute(
                    "SELECT business_id FROM business WHERE owner_id = ?",
                    (user_id,),
                )
                owned_business_ids = [row["business_id"] for row in cursor.fetchall()]
                cursor.execute("""
                    DELETE FROM appointment
                    WHERE user_id = ?
                       OR provider_id = ?
                       OR service_id IN (
                           SELECT s.service_id
                           FROM services s
                           JOIN business b ON b.business_id = s.business_id
                           WHERE b.owner_id = ?
                       )
                """, (user_id, user_id, user_id))
                cursor.execute("""
                    DELETE FROM provider_services
                    WHERE user_id = ? OR business_id IN (
                        SELECT business_id FROM business WHERE owner_id = ?
                    )
                """, (user_id, user_id))
                cursor.execute("""
                    DELETE FROM business_providers
                    WHERE user_id = ? OR business_id IN (
                        SELECT business_id FROM business WHERE owner_id = ?
                    )
                """, (user_id, user_id))
                cursor.execute("""
                    DELETE FROM services
                    WHERE business_id IN (
                        SELECT business_id FROM business WHERE owner_id = ?
                    )
                """, (user_id,))
                cursor.execute("DELETE FROM business WHERE owner_id = ?", (user_id,))
                cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))

        if not account_missing and not invalid_account_type:
            delete_owner_image_assets(conn, "user", user_id)
            for business_id in owned_business_ids:
                delete_owner_image_assets(conn, "business", business_id)
        conn.close()
        if account_missing:
            session.clear()
            return redirect(url_for("client.login_user"))
        if invalid_account_type:
            return apology("Tipo de conta inválido para exclusão.", 400)

        session.clear()
        flash("Sua conta e os dados vinculados foram excluídos.", "success")
        return redirect(url_for("client.index"))

    conn.close()
    return render_template("account-delete.html", impact=impact)


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


# AI used for:
# - organize the code, adjust comments, ensure proper formatting
# - help find what was standard ways to work with Flask, find documentation, and discover best practices
# - Discover the blueprints method and how to use it
# - Get more information about the Flask session object and how to use it
# - Organize the readme file for better understanding, adjust the markdown format and translate it to English.