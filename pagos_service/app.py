from flask import Flask, request, jsonify, g
import sqlite3


app = Flask(__name__)
BASE_DE_DATOS = 'pagos.db'
TOKEN_SECRETO = "mi_token_secreto"

# -----------------------------
# Funciones de base de datos
# -----------------------------
def obtener_db():
    if 'db' not in g:
        g.db = sqlite3.connect(BASE_DE_DATOS)
        g.db.row_factory = sqlite3.Row
    return g.db

def inicializar_db():
    db = sqlite3.connect(BASE_DE_DATOS)
    db.execute("""
        CREATE TABLE IF NOT EXISTS pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_pedido INTEGER NOT NULL,
            estado TEXT NOT NULL
        )
    """)
    db.close()

@app.teardown_appcontext
def cerrar_db(exception):
    db = g.pop('db', None)
    if db:
        db.close()

# -----------------------------
# Autenticación básica
# -----------------------------
def requiere_autenticacion(funcion):
    def envoltorio(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if token != TOKEN_SECRETO:
            return jsonify({"error": "Forbidden"}), 403
        return funcion(*args, **kwargs)
    envoltorio.__name__ = funcion.__name__
    return envoltorio

# -----------------------------
# Endpoints
# -----------------------------
@app.route("/pagos", methods=["POST"])
@requiere_autenticacion
def procesar_pago():
    datos = request.get_json()
    # verificamos si llega la informacion necesaria , para procesar el pago
    if not datos or 'id_pedido' not in datos:
        return jsonify({ "error": "Datos Incompletos "}) , 400
    pago_exitoso = True 

    db = obtener_db()
    db.execute(
        "INSERT INTO pagos (id_pedido, estado) VALUES (?, ?)",
        (datos['id_pedido'], "exitoso" if pago_exitoso else "fallido")
    )
    db.commit()
    return jsonify({"estado": "exitoso"} if pago_exitoso else {"estado": "fallido"}), 201

if __name__ == "__main__":
    # Inicializar base de datos
    inicializar_db()
    app.run(port=5002)
