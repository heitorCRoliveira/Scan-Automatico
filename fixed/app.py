"""
Versão CORRIGIDA da aplicação (Shift Left: correções feitas após o feedback do pipeline).
Copie este arquivo para src/app.py e o requirements.txt desta pasta para a raiz.
"""
import ipaddress
import os
import secrets
import sqlite3
import subprocess

from flask import Flask, jsonify, request
from markupsafe import escape
from werkzeug.security import generate_password_hash

app = Flask(__name__)
# FIX: segredo vem do ambiente (nunca hardcoded no repositório)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

# FIX: hash de senha com algoritmo apropriado (salt + custo computacional)
ADMIN_HASH = generate_password_hash("admin123")


def get_db():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, password_hash TEXT)"
    )
    conn.executemany(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        [
            ("alice", "alice@example.com", ADMIN_HASH),
            ("bob", "bob@example.com", ADMIN_HASH),
        ],
    )
    return conn


@app.after_request
def security_headers(resp):
    # FIX: cabeçalhos de segurança (corrige alertas do ZAP)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; frame-ancestors 'none'; form-action 'self'"
    )
    resp.headers["Server"] = "webserver"  # não revela versão do servidor
    return resp


@app.route("/")
def index():
    return (
        "<h1>Demo DevSecOps</h1>"
        "<ul>"
        '<li><a href="/greet?name=Ana">Saudação</a></li>'
        '<li><a href="/user?name=alice">Consulta de usuário</a></li>'
        '<li><a href="/ping?host=127.0.0.1">Ping</a></li>'
        "</ul>"
    )


@app.route("/greet")
def greet():
    name = request.args.get("name", "visitante")
    # FIX: escape da entrada antes de devolvê-la no HTML
    return f"<h1>Olá, {escape(name)}!</h1>"


@app.route("/user")
def user():
    name = request.args.get("name", "")
    conn = get_db()
    # FIX: query parametrizada
    rows = conn.execute(
        "SELECT id, name, email FROM users WHERE name = ?", (name,)
    ).fetchall()
    return jsonify([{"id": r[0], "name": r[1], "email": r[2]} for r in rows])


@app.route("/ping")
def ping():
    host = request.args.get("host", "127.0.0.1")
    # FIX: valida que é um IP e executa sem shell, com lista de argumentos
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return "<pre>host inválido</pre>", 400
    result = subprocess.run(
        ["ping", "-c", "1", host], capture_output=True, text=True, timeout=5
    )
    return f"<pre>{escape(result.stdout)}</pre>"


if __name__ == "__main__":
    # FIX: debug desativado por padrão e bind somente em localhost
    app.run(host="127.0.0.1", port=5000, debug=os.environ.get("FLASK_DEBUG") == "1")
