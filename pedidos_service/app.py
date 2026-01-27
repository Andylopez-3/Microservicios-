from flask import Flask, request,g,jsonify   #importamos g para manejar la conexion a la base de datos , guarda datos durante la peticion
import sqlite3
import requests , logging  # importamos logging para registrar eventos importantes
from functools import wraps # decoradores para que flask no pierda informacion de la funcion original

app = Flask(__name__)

TOKEN_SECRETO = "mi_token_secreto"
URL_SERVICIO_PRODUCTOS = "http://127.0.0.1:5000/productos"
NOMBRE_BASE_DATOS = "pedidos.db"
logging.basicConfig(level=logging.INFO)# configuramos el nivel de logging ,(INFO muestra informacion general del funcionamiento(WARNING, ERROR , CRITICAL))


def obtener_db():
    if "db" not in g:  # si no hay conexion a la base de datos en g
        g.db = sqlite3.connect(NOMBRE_BASE_DATOS)   # creamos la conexion a la base de datos , y lo guardamos en g , asi mantenemos una sola conexion por peticion
        g.db.row_factory = sqlite3.Row   # para que las filas devueltas por las consultas sean accesibles como diccionarios , ya que por defecto son tuplas , ya no [0] , sino ['nombre_columna']
    return g.db

def inicializar_db():
    db = sqlite3.connect(NOMBRE_BASE_DATOS)   # funcion para inicializar la base de datos si no existe , con las columnas necesarias
    db.execute("""
        CREATE TABLE IF NOT  EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_producto INTEGER NOT NULL,
            cantidad INTEGER NOT NULL,
            estado TEXT NOT NULL
        )
    """)
    db.commit()   # guardamos los cambios
    db.close()   # cerramos la conexion a la base de datos


@app.teardown_appcontext    # decorador de flask que pase lo que pase al finalizar de la peticion cierra la conexion a la base de datos
def cerrar_db(exception):   # flask cierra la conexion a la base de datos al finalizar la peticion
    db = g.pop('db', None)    # sacamos la conexion a la base de datos si existe en g , si no existe devuelve None
    if db:                      # si existe la conexion a la base de datos
        db.close()          # cerramos la conexion a la base de datos

def requiere_autenticacion(funcion):
    @wraps(funcion)
    def envoltorio(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")   # verificamos el token en los headers de la peticion  , y lo separamos del prefijo "Bearer "
        if token != TOKEN_SECRETO:        # si el token no coincide
            logging.warning("Intento de acceso no autorizado a pedidos")   # registramos un log de advertencia , de que alguien intento acceder sin autorizacion
            return jsonify({"error": "Token Invalido ,  Quien sos?"}), 403  # devolvemos error 403 al cliente , de que no esta autorizado
        return funcion(*args, **kwargs)
    return envoltorio

def manejar_respuesta_producto(respuesta): # funcion para manejar errores del microservicio de productos
    status = respuesta.status_code    # obtenemos el codigo de estado de la respuesta
    if status == 200:   #si todo esta bien no hay error
        return None
    if status == 404: # si el producto no existe
        return jsonify({"error": "Producto no encontrado"}), 404 # devolvemos error 404 al cliente del servicio de pedidos
    if status in (401,403):  # si no esta autorizado 
        return jsonify({"error": "No autorizado para consultar productos"}), 403  # devolvemos error 403 al cliente del servicio de pedidos
    
    if status >= 500:     # si hay un error del servidor del microservicio de productos
        return jsonify({"error": "Error en el servicio de productos"}), 503 # devolvemos error 503 al cliente del servicio de pedidos
    
    return jsonify({"error": "Error desconocido al consultar productos"}), 502 # si hay otro error desconocido devolvemos error 502 al cliente del servicio de pedidos
    
    
@app.route("/pedidos/<int:id_pedido>", methods=["GET"])  # creamos un endpoint para obtener un pedido por su id , para la peticion del microservicio de pagos
@requiere_autenticacion   # pasa primero por la autenticacion
def obtener_pedido(id_pedido):   # funcion para obtener un pedido por su id
    db = obtener_db()
    cursor = db.execute("SELECT id, id_producto, cantidad, estado FROM pedidos WHERE id=?", (id_pedido,))   # consulta para obtener el pedido por su id en la base de datos
    pedido = cursor.fetchone() # obtenemos la primera fila del resultado de la consulta
    if pedido:  # si existe el pedido en la base de datos
        return jsonify(dict(pedido))  # devolvemos el pedido como un diccionario en formato json
    return jsonify({"error": "Pedido no encontrado"}), 404  # si no existe el pedido devolvemos error 404

@app.route("/pedidos", methods=["POST"])  # creamos un endpoint para crear un nuevo pedido
@requiere_autenticacion  # pasa primero por la autenticacion
def crear_pedido():  # funcion para crear un nuevo pedido
    datos = request.json   # obtenemos los datos de la peticion en formato json
    # verificamos si llega la informacion necesaria , para guardar el pedido
    if not datos or 'id_producto' not in datos or 'cantidad' not in datos:
        return jsonify({"error": " Datos incompletos "}), 400  # devolvemos error 400 al cliente , ya que faltan datos
    try:   # nos aseguramos que los datos son del tipo correcto

        id_producto = int(datos["id_producto"])  # obtenemos el id del producto ,y nos aseguramos que es un entero
        cantidad = int(datos["cantidad"])  # obtenemos la cantidad , y nos aseguramos que es un entero
        if cantidad <= 0 or id_producto <= 0:  # verificamos que sean numeros positivos
            return jsonify({"error": "id_producto y cantidad deben ser numeros enteros positivos"}), 400  # devolvemos error 400 al cliente , por que los datos no son validos
    except (ValueError, TypeError):  # si hay un error al convertir los datos a enteros
        return jsonify({"error": "id_producto y cantidad deben ser numeros enteros"}), 400  # devolvemos error 400 al cliente , por que los datos no son validos

    # Verificar producto en microservicio Productos
    respuesta = None  # una bandera para saber si la respuesta fue exitosa
    for intento in range(3):  # un retry de 3 intentos para conectarse al microservicio de productos

        try:  # hacemos la peticion al microservicio de productos
            respuesta = requests.get(
            f"{URL_SERVICIO_PRODUCTOS}/{id_producto}", 
                headers={"Authorization": f"Bearer {TOKEN_SECRETO}"},
                timeout=3
            ) # esperamos 3 segundos maximo por la respuesta
            break
        except requests.exceptions.RequestException:   # si hay un error en la peticion
            logging.warning(f"REINTENTO {intento + 1}: Servicio de productos no responde")  # registramos un log de advertencia , de que el servicio de productos no respondio
            respuesta = None  # aseguramos que la respuesta sea None en caso de error , para que siga reintentando la conexion
    
    if respuesta is None:  # si despues de los reintentos no se pudo conectar con el microservicio de productos
        logging.error(f"Fallo Critico: No se pudo conectar con el servicio de productos para pedido de ID {id_producto}")  # registramos un log de error critico , de que  se cayo o no responde el servicio de productos
        return jsonify({"error": "Servicio de productos no disponible tras varios intentos" }), 503   # devolvemos error 503 al cliente , por que el servicio de productos no esta disponible
    #manejamos los errores que pueden venir del servicio de productos
    error = manejar_respuesta_producto(respuesta)   
    if error:  # si hay un error , lo devolvemos al cliente
        return error

    conexion = obtener_db()
    cursor = conexion.cursor()
    try:           # guardamos el pedido en la base de datos
        cursor.execute(
            "INSERT INTO pedidos (id_producto, cantidad, estado) VALUES (?, ?, ?)",
            (id_producto, cantidad, "creado")
        )
        conexion.commit() # guardamos los cambios  en la base de datos
        logging.info(f"PEDIDO CREADO: ID {cursor.lastrowid} para producto {id_producto}") # registramos un log de info , de que se creo un nuevo pedido 
    except sqlite3.DatabaseError as e: #si hay un error en la base de datos , lo manejamos
        logging.error(f"Error al crear el pedido : {e}")  # registramos un log de error , de que hubo un error al crear el pedido , en la base de datos
        return jsonify({"error": "Error al crear el pedido"}), 500  # devolvemos error 500 al cliente , por que hubo un error en la base de datos
    
    return jsonify({"mensaje": "Pedido creado correctamente"}), 201  # devolvemos codigo 201 (creado) al cliente , si paso todo bien


if __name__ == "__main__":
    inicializar_db()  # Inicializar base de datos
    app.run(port=5001)  # ejecutamos la aplicacion en el puerto 5001

