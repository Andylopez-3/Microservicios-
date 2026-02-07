from flask import Flask, request, jsonify, g   #importamos g para manejar la conexion a la base de datos , guarda datos durante la peticion
import sqlite3, requests , logging    # importamos logging para registrar eventos importantes
from functools import wraps    # decoradores para que flask no pierda informacion de la funcion original
from datetime import datetime ,timedelta , timezone

app = Flask(__name__)   # creamos la aplicacion flask

BASE_DE_DATOS = 'pagos.db'  # nombre de la base de datos
TOKEN_SECRETO = "mi_token_secreto"  # token secreto para la autenticacion
URL_SERVICIO_PEDIDOS = "http://127.0.0.1:5001/pedidos"  # URL del MICROservicio de pedidos

logging.basicConfig(
    filename="pagos.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
    ) # configuramos el nivel de logging ,(INFO muestra informacion general del funcionamiento(WARNING, ERROR , CRITICAL))

breaker_states_pedidos ={
    "estado" : "CERRADO",
    "fallos" : 0 ,
    "max_fallos" : 3,
    "abierto_hasta" : None
}

def puede_llamar_pedidos(): # funcion para verificar si podemos llamar al servicio de pedidos
    now = datetime.now(timezone.utc)
    estado = breaker_states_pedidos["estado"]

    if estado == "CERRADO":
        return True
    
    if estado == "ABIERTO":
        if now >= breaker_states_pedidos["abierto_hasta"]: # verificamos si ya paso el tiempo de espera
            #pasar a SEMI_ABIERTO para probar si se recupero
            breaker_states_pedidos["estado"] = "SEMI_ABIERTO"
            logging.info("Circuit breaker abierto a semi_abierto: Probando recuperacion del microservicio pedido")
            return True
        return False
    if estado == "SEMI_ABIERTO":  # en semi_abierto permitimo 1 intento de prueba
        return True
    
    return False

def registrar_exito_pedidos(): # esta funcion es para llamar cuando el servicio de pedidos respondio sin errores
    estado_actual = breaker_states_pedidos["estado"]

    if estado_actual == "SEMI_ABIERTO":
        # servicio  recuperado , cerrar circuito
        breaker_states_pedidos["estado"] = "CERRADO"
        breaker_states_pedidos["fallos"] = 0
        breaker_states_pedidos["abierto_hasta"] = None
        logging.info("Servicio de pedidos recuperado : circuito cerrado")
    elif estado_actual == "CERRADO" and breaker_states_pedidos["fallos"] > 0 :
        #reseteamos fallos previos
        breaker_states_pedidos["fallos"] = 0

def registrar_fallos_pedidos(): # llamar cuando hubo error 500+ o timeout
    breaker_states_pedidos["fallos"] += 1
    estado_actual = breaker_states_pedidos["estado"]

    logging.error(f"Fallo en servicio de pedidos. Fallos: {breaker_states_pedidos['fallos']}/{breaker_states_pedidos['max_fallos']}")
    
    if estado_actual == "SEMI_ABIERTO" : # fallamos en la prueba , volver a abrir
        breaker_states_pedidos["estado"] = "ABIERTO"
        breaker_states_pedidos["abierto_hasta"] = datetime.now(timezone.utc) + timedelta(seconds=30)
        logging.error("circuit breaker: Fallo en prueba , abierto por 30s")

    elif breaker_states_pedidos["fallos"] >= breaker_states_pedidos["max_fallos"]:
        #Demasiados fallos , abrir circuito
        breaker_states_pedidos["estado"] = "ABIERTO"
        breaker_states_pedidos["abierto_hasta"] = datetime.now(timezone.utc) + timedelta(seconds=30)
        logging.error("Circuit Breaker : Demasiados fallos , Abierto por 30s")


def obtener_db():
    if 'db' not in g:    # si no hay conexion a la base de datos en g
        g.db = sqlite3.connect(BASE_DE_DATOS)  # creamos la conexion a la base de datos , y lo guardamos en g , asi mantenemos una sola conexion por peticion
        g.db.row_factory = sqlite3.Row   # para que las filas devueltas por las consultas sean accesibles como diccionarios , ya que por defecto son tuplas , ya no [0] , sino ['nombre_columna']
    return g.db

def inicializar_db():
    db = sqlite3.connect(BASE_DE_DATOS)  # funcion para inicializar la base de datos si no existe , con las columnas necesarias
    db.execute("""
        CREATE TABLE IF NOT EXISTS pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_pedido INTEGER NOT NULL,
            estado TEXT NOT NULL
        )
    """)
    db.commit()  # guardamos los cambios
    db.close()  # cerramos la conexion a la base de datos

@app.teardown_appcontext   # decorador de flask que pase lo que pase al finalizar de la peticion cierra la conexion a la base de datos
def cerrar_db(exception):   # flask cierra la conexion a la base de datos al finalizar la peticion
    db = g.pop('db', None)  # sacamos la conexion a la base de datos si existe en g , si no existe devuelve None
    if db:                   # si existe la conexion a la base de datos
        db.close()           # cerramos la conexion a la base de datos

def requiere_autenticacion(funcion):
    @wraps(funcion)
    def envoltorio(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")  # verificamos el token en los headers de la peticion  , y lo separamos del prefijo "Bearer "
        if token != TOKEN_SECRETO:   # si el token no coincide
            logging.warning("intento de pago no autorizado")  # registramos un log de advertencia , de que alguien intento acceder sin autorizacion
            return jsonify({"error": "Token Invalido , Quien sos bro ?"}), 403  # devolvemos error 403 al cliente , de que no esta autorizado
        return funcion(*args, **kwargs)
    return envoltorio

def manejar_respuesta_pedido(respuesta): # maneja errores del servicio de pedidos
    status = respuesta.status_code # obtenemos el codigo de estado de la respuesta

    if status == 200:   #si todo esta bien no hay error
        registrar_exito_pedidos() # registramos exito
        return None
    
    if status == 404: # si el pedido no existe
        return jsonify({"error": "El pedido no existe , pago rechazado"}), 404 # devolvemos error 404 al cliente del servicio de pagos
    
    if status in (401,403):  # si no esta autorizado
        return jsonify({"error": "No autorizado para consultar pedidos"}), 403  # devolvemos error 403 al cliente del servicio de pagos
    
    if status >= 500:  # si hay un error del servidor del microservicio de pedidos
        registrar_fallos_pedidos()  # registramos el fallo
        return jsonify({"error": "Error interno en el servicio de pedidos"}), 502 # devolvemos error 502 al cliente del servicio de pagos
    
    return jsonify({"error": "Error desconocido al consultar pedidos"}), 502  # si hay otro error desconocido devolvemos error 502 al cliente del servicio de pagos

@app.route("/pagos", methods=["POST"])  # creamos un endpoint para procesar los pagos 
@requiere_autenticacion  # [pasa primero por la autenticacion]
def procesar_pago():   # funcion para procesar el pago de un pedido
    datos = request.get_json()     # obtenemos los datos enviados en la peticion
    # verificamos si llega la informacion necesaria , para procesar el pago
    if not datos or 'id_pedido' not in datos:
        return jsonify({ "error": "Datos Incompletos "}) , 400  # devolvemos error 400 al cliente , por que los datos estan incompletos
    
    try: # convertimos el id_pedido a entero
        id_pedido = int(datos['id_pedido'])
    except (ValueError, TypeError):  # si no se puede convertir a entero devolvemos error 400
        return jsonify({"error": "id_pedido debe ser un numero entero"}), 400
    
    # verificamos el circuit breaker
    if not puede_llamar_pedidos():
        logging.warning("Pago rechazado : Circuit Breaker Abierto")
        return jsonify({"Error": "Servicio de pedidos temporalmente no disponible"}) , 503
    
    respuesta = None  # bandera para saber si se obtuvo respuesta del servicio de pedidos
    for intento in range(3):  # un retry de 3 intentos para comunicarse con el servicio de pedidos
        try:  # intentamos hacer la peticion al servicio de pedidos
            respuesta = requests.get(
                f"{URL_SERVICIO_PEDIDOS}/{id_pedido}",
                headers={"Authorization": f"Bearer {TOKEN_SECRETO}"},
                timeout = 3
            )
            break
        except requests.exceptions.RequestException:   # si hay un error en la peticion , esperamos un poco y reintentamos
            logging.warning(f"REINTENTO PAGO {intento + 1}: No se pudo verificar pedido {id_pedido}")   # registramos un log de advertencia , de que no se pudo comunicar con el servicio de pedidos
    
    if respuesta is None:  # si no se obtuvo respuesta del servicio de pedidos despues de los reintentos
        logging.error(f"Fallo Critico: Servicio de pedidos caido al procesar pago para pedido {id_pedido}")  # registramos un log de error critico , de que el servicio de pedidos esta caido
        registrar_fallos_pedidos()  # registramos el fallo
        return jsonify({"error": "No se pudo verificar el pedido (Servicio pedidos caido o no responde)"}), 503  # devolvemos error 503 al cliente , por que el servicio de pedidos no esta disponible o cayo 
    
    #manejamos los errores que pueden venir del servicio de pedidos
    error = manejar_respuesta_pedido(respuesta)
    if error: # si hay un error , lo devolvemos al cliente
        return error



    db = obtener_db() # obtenemos la conexion a la base de datos
    db.execute( 
        "INSERT INTO pagos (id_pedido, estado) VALUES (?, ?)",
        (id_pedido, "exitoso" )
    ) # insertamos el nuevo pago en la base de datos
    db.commit()  # guardamos los cambios en la base de datos
    logging.info(f"PAGO PROCESADO: Pedido  {id_pedido} procesado correctamente") # registramos en el log de INFO  , por  la creacion del pago
    return jsonify({"estado": "exitoso" , "mensaje": "Pago procesado"}), 201  # devolvemos codigo 201 (creado) al cliente , si todo salio bien

if __name__ == "__main__":
    # Inicializar base de datos
    inicializar_db()
    app.run(port=5002)  # ejecutamos la aplicacion en el puerto 5002
