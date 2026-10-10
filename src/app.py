"""
Aplicação de demonstração DELIBERADAMENTE VULNERÁVEL (uso exclusivamente didático).
Cada vulnerabilidade está marcada com "VULN" para facilitar a correlação com os
resultados das ferramentas (Semgrep, pip-audit e OWASP ZAP).
NUNCA publique esta aplicação em um ambiente real.
"""
import hashlib
import sqlite3
import subprocess

from flask import Flask, jsonify, request

app = Flask(__name__)
app.config["SECRET_KEY"] = "super-secret-key-123"  # VULN: segredo hardcoded

# VULN: MD5 é inadequado para armazenar senhas
ADMIN_HASH = hashlib.md5(b"admin123").hexdigest()


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
    # VULN: XSS refletido (entrada do usuário devolvida sem escape)
    return f"<h1>Olá, {name}!</h1>"


@app.route("/user")
def user():
    name = request.args.get("name", "")
    conn = get_db()
    # VULN: SQL Injection (query montada por formatação de string)
    query = f"SELECT id, name, email FROM users WHERE name = '{name}'"
    rows = conn.execute(query).fetchall()
    return jsonify([{"id": r[0], "name": r[1], "email": r[2]} for r in rows])


@app.route("/ping")
def ping():
    host = request.args.get("host", "127.0.0.1")
    # VULN: Command Injection (shell=True com entrada do usuário)
    result = subprocess.run(
        f"ping -c 1 {host}", shell=True, capture_output=True, text=True, timeout=5
    )
    return f"<pre>{result.stdout}</pre>"


if __name__ == "__main__":
    # VULN: debug=True expõe o console do Werkzeug; host 0.0.0.0 expõe em todas as interfaces
    app.run(host="0.0.0.0", port=5000, debug=True)
