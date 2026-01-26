from flask import Flask, request, jsonify, g
import sqlite3, requests , logging
from functools import wraps


app = Flask(__name__)
BASE_DE_DATOS = 'pagos.db'
TOKEN_SECRETO = "mi_token_secreto"
URL_SERVICIO_PEDIDOS = "http://127.0.0.1:5001/pedidos"

logging.basicConfig(level=logging.INFO)

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
        if token != TOKEN_SECRETO:   # si el token no coincide
            logging.warning("intenti de pago no autorizado")
            return jsonify({"error": "Token Invalido , Quien sos bro ?"}), 403
        return funcion(*args, **kwargs)
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
    
    try:
        id_pedido = int(datos['id_pedido'])
    except (ValueError, TypeError):
        return jsonify({"error": "id_pedido debe ser un numero entero"}), 400
    # Aqui se simula el procesamiento del pago
    for intento in range(3):
        try:
            respuesta = requests.get(
                f"{URL_SERVICIO_PEDIDOS}/{id_pedido}",
                headers={"Authorization": f"Bearer {TOKEN_SECRETO}"},
                timeout = 3
            )
            break
        except requests.exceptions.RequestException:
            logging.warning(f"REINTENTO PAGO {intento + 1}: No se pudo verificar pedido {id_pedido}")
    
    if respuesta is None:
        return jsonify({"error": "No se pudo verificar el pedido (Servicio pedidos caido o no responde)"}), 503
    
    if respuesta.status_code == 404:
        return jsonify({"error": "El pedido no existe , pago  rechazado"}), 404
    
    if respuesta.status_code in (401,403):
        return jsonify({"error": "No autorizado para consultar pedidos"}), 403
    
    if respuesta.status_code != 200:
        return jsonify({"error": "Error al validar el pedido"}), 502



    db = obtener_db()
    db.execute( 
        "INSERT INTO pagos (id_pedido, estado) VALUES (?, ?)",
        (id_pedido, "exitoso" )
    )
    db.commit()
    logging.info(f"PAGO PROCESADO: Pedido  {id_pedido} ptocesado correctamente")
    return jsonify({"estado": "exitoso" , "mensaje": "Pago procesado"}), 201  # guardamos el estado del pago

if __name__ == "__main__":
    # Inicializar base de datos
    inicializar_db()
    app.run(port=5002)
