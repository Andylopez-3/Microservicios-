from flask import Flask, request, jsonify, g
import sqlite3
from functools import wraps 

app = Flask(__name__)
BASE_DE_DATOS = 'productos.db'
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
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL
        )
        """)
    db.commit()
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
    @wraps(funcion)
    def envoltorio(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if token != TOKEN_SECRETO:
            return jsonify({"error": "Token Invalido , Quien sos?"}), 403
        return funcion(*args, **kwargs)
    return envoltorio

# -----------------------------
# Endpoints
# -----------------------------
@app.route("/productos", methods=["GET"])
@requiere_autenticacion
def listar_productos():
    db = obtener_db()
    cursor = db.execute("SELECT id, nombre, precio FROM productos")
    lista_productos = [dict(fila) for fila in cursor.fetchall()]
    return jsonify(lista_productos)

@app.route("/productos/<int:id_producto>", methods=["GET"])
@requiere_autenticacion
def obtener_producto(id_producto):
    db = obtener_db()
    cursor = db.execute("SELECT id, nombre, precio FROM productos WHERE id=?", (id_producto,))
    producto = cursor.fetchone()
    if producto:
        return jsonify(dict(producto))
    return jsonify({"error": "Producto no encontrado"}), 404

@app.route("/productos", methods=["POST"])
@requiere_autenticacion
def crear_producto():
    datos = request.get_json()
    # validamos que contenga los datos que requiere el servidor para guardar en la base de datos
    if not datos or 'nombre' not in datos or 'precio' not in datos:
        return jsonify({"error": "Datos Incompletos"}), 400
    try:
        nombre = str(datos['nombre'])
        precio = float(datos['precio'])
    except (ValueError, TypeError):
        return jsonify({"error": "precio debe ser un numero y nombre debe ser texto"}), 400
     
    db = obtener_db()
    cursor = db.execute(
        "INSERT INTO productos (nombre, precio) VALUES (?, ?)",
        (nombre, precio)
    )
    db.commit()
    return jsonify({"id": cursor.lastrowid}), 201

if __name__ == "__main__":
    # Inicializar base de datos
    inicializar_db()
    app.run(port=5000)
