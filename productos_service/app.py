from flask import Flask, request, jsonify, g #importamos g para manejar la conexion a la base de datos , guarda datos durante la peticion
import sqlite3 , logging   # importamos logging para registrar eventos importantes
from functools import wraps # decoradores para que flask no pierda informacion de la funcion original

app = Flask(__name__)  #creamos la aplicacion flask
BASE_DE_DATOS = 'productos.db'
TOKEN_SECRETO = "mi_token_secreto"

logging.basicConfig(level=logging.INFO) # configuramos el nivel de logging ,(INFO muestra informacion general del funcionamiento(WARNING, ERROR , CRITICAL))

def obtener_db():
    if 'db' not in g:  # si no hay conexion a la base de datos en g
        g.db = sqlite3.connect(BASE_DE_DATOS) # creamos la conexion a la base de datos , y lo guardamos en g , asi mantenemos una sola conexion por peticion
        g.db.row_factory = sqlite3.Row  # para que las filas devueltas por las consultas sean accesibles como diccionarios , ya que por defecto son tuplas , ya no [0] , sino ['nombre_columna']
    return g.db


def inicializar_db():     # funcion para inicializar la base de datos si no existe , con las columnas necesarias
    db = sqlite3.connect(BASE_DE_DATOS)
    db.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL
        )
        """)
    db.commit()  # guardamos los cambios
    db.close() # cerramos la conexion a la base de datos

@app.teardown_appcontext   # decorador de flask que pase lo que pase al finalizar de la peticion cierra la conexion a la base de datos
def cerrar_db(exception):     # flask cierra la conexion a la base de datos al finalizar la peticion
    db = g.pop('db', None)   # sacamos la conexion a la base de datos si existe en g , si no existe devuelve None
    if db:         # si existe la conexion a la base de datos
        db.close()    # cerramos la conexion a la base de datos


def requiere_autenticacion(funcion):
    @wraps(funcion)
    def envoltorio(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")   # verificamos el token en los headers de la peticion  , y lo separamos del prefijo "Bearer "
        if token != TOKEN_SECRETO:    # si el token no coincide
            logging.warning("Intento de acceso no autorizado a productos")   # registramos un log de advertencia , de que alguien intento acceder sin autorizacion
            return jsonify({"error": "Token Invalido , Quien sos?"}), 403  # devolvemos error 403 al cliente , de que no esta autorizado
        return funcion(*args, **kwargs)
    return envoltorio

@app.route("/productos", methods=["GET"])     # endpoint para listar todos los productos que hay en la base de datos
@requiere_autenticacion   # pasa primero por la autenticacion
def listar_productos(): # funcion para listar todos los productos
    db = obtener_db() # obtenemos la conexion a la base de datos
    cursor = db.execute("SELECT id, nombre, precio FROM productos")   # consulta para obtener todos los productos
    lista_productos = [dict(fila) for fila in cursor.fetchall()]  # convertimos cada fila del resultado de la consulta en un diccionario y lo guardamos en una lista
    return jsonify(lista_productos)  # devolvemos la lista de productos en formato json

@app.route("/productos/<int:id_producto>", methods=["GET"]) # un endpoint para la consulta del servidor de pedidos , obtener un producto por su id
@requiere_autenticacion    # pasa primero por la autenticacion
def obtener_producto(id_producto): # funcion para obtener un producto por su id
    db = obtener_db()
    cursor = db.execute("SELECT id, nombre, precio FROM productos WHERE id=?", (id_producto,)) # consulta para obtener el producto por su id en la base de datos
    producto = cursor.fetchone() # obtenemos la primera fila del resultado de la consulta
    if producto: # si existe el producto en la base de datos
        return jsonify(dict(producto))    # devolvemos el producto como un diccionario en formato json
    return jsonify({"error": "Producto no encontrado"}), 404  # si no existe el producto devolvemos error 404

@app.route("/productos", methods=["POST"])   # endpoint para crear un nuevo producto en la base de datos
@requiere_autenticacion  # pasa primero por la autenticacion
def crear_producto():   # funcion para crear un nuevo producto
    datos = request.get_json()
    # validamos que contenga los datos que requiere el servidor para guardar en la base de datos
    if not datos or 'nombre' not in datos or 'precio' not in datos:
        return jsonify({"error": "Datos Incompletos"}), 400   # si no estan los datos necesarios devolvemos error 400
    try:
        nombre = str(datos['nombre'])     # nos aseguramos que el nombre es una cadena de texto
        precio = float(datos['precio'])   # nos aseguramos que el precio es un numero decimal
    except (ValueError, TypeError):         #  una excepcion de conversion , al convertir los datos
        return jsonify({"error": "precio debe ser un numero y nombre debe ser texto"}), 400   # devolvemos error 400 al cliente
     
    db = obtener_db()
    cursor = db.execute(
        "INSERT INTO productos (nombre, precio) VALUES (?, ?)",
        (nombre, precio)
    ) # insertamos el nuevo producto en la base de datos
    db.commit() # guardamos los cambios en la base de datos
    logging.info(f"PRODUCTO CREADO: {nombre}, - ID: {cursor.lastrowid}")  # registramos en el log la creacion del producto
    return jsonify({"id": cursor.lastrowid}), 201        # devolvemos el id del ultimo producto creado con codigo 201 (creado)

if __name__ == "__main__":
    # Inicializar base de datos
    inicializar_db()
    app.run(port=5000)            # ejecutamos la aplicacion en el puerto 5000
