from flask import Flask, request, g , jsonify
import sqlite3
import requests
from functools import wraps

app = Flask(__name__)

TOKEN_SECRETO = "mi_token_secreto"
URL_SERVICIO_PRODUCTOS = "http://127.0.0.1:5000/productos"
NOMBRE_BASE_DATOS = "pedidos.db"


def obtener_db():
    if "db" not in g:
        g.db = sqlite3.connect(NOMBRE_BASE_DATOS)
        g.db.row_factory = sqlite3.Row
    return g.db

def inicializar_db():
    db = sqlite3.connect(NOMBRE_BASE_DATOS)
    db.execute("""
        CREATE TABLE IF NOT  EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_producto INTEGER NOT NULL,
            cantidad INTEGER NOT NULL,
            estado TEXT NOT NULL
        )
    """)
    db.close()


@app.teardown_appcontext
def cerrar_db(exception):
    db = g.pop("db", None)
    if db:
        db.close()

def requiere_autenticacion(funcion):
    @wraps(funcion)
    def envoltorio(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if token != TOKEN_SECRETO:
            return jsonify({"error": "Forbidden"}), 403
        return funcion(*args, **kwargs)
    return envoltorio

def manejar_respuesta_producto(respuesta):
    status = respuesta.status_code
    if status == 200:
        return None
    if status == 404:
        return jsonify({"error": "Producto no encontrado"}), 404
    
    if status in (401,403):
        return jsonify({"error": "No autorizado para consultar productos"}), 502
    
    if status >= 500:
        return jsonify({"error": "Error en el servicio de productos"}), 503
    
    return jsonify({"error": "Error desconocido al consultar productos"}), 502
    
    
        
@app.route("/pedidos", methods=["POST"])
def crear_pedido():
    datos = request.json
    # verificamos si llega la informacion necesaria , para guardar el pedido
    if not datos or 'id_producto' not in datos or 'cantidad' not in datos:
        return jsonify({"error": "Datos incompletos "}), 400

    id_producto = datos["id_producto"]
    cantidad = datos["cantidad"]

    # Verificar producto en microservicio Productos
    try:
        respuesta = requests.get(
           f"{URL_SERVICIO_PRODUCTOS}/{id_producto}",
            headers={"Authorization": f"Bearer {TOKEN_SECRETO}"},
            timeout=3
        )
    except requests.exceptions.RequestException:
        return jsonify({"error": "Servicio de productos no disponible"}), 503
    #manejamos los errores que pueden venir del servicio de productos
    error = manejar_respuesta_producto(respuesta)   
    if error:
        return error

   
    conexion = obtener_db()
    cursor = conexion.cursor()

    cursor.execute(
        "INSERT INTO pedidos (id_producto, cantidad, estado) VALUES (?, ?, ?)",
        (id_producto, cantidad, "creado")
    )

    conexion.commit()
    conexion.close()

    return jsonify({"mensaje": "Pedido creado correctamente"}), 201


if __name__ == "__main__":
    inicializar_db()
    app.run(port=5001)

