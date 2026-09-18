import os

from flask import Flask, redirect
from flask_session import Session

# Import helpers
from helpers import apology, brl, category_slug, close_db

# Import Blueprints
from blueprints.client import client_bp
from blueprints.business import business_bp

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["brl"] = brl  # -> R$
app.jinja_env.filters["category_slug"] = category_slug

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Register teardown
app.teardown_appcontext(close_db)

# Registrar os Blueprints na aplicação
app.register_blueprint(client_bp)
app.register_blueprint(business_bp)


# Disables browser caching
@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# ====================================
#   GENERAL ERRORS RETURNS
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