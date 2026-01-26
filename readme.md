🐧 Proyecto: Microservicios Resilientes (El Fin del Mamut)
Este proyecto demuestra la transición de una arquitectura monolítica a un ecosistema de tres microservicios autónomos, enfocándose en la seguridad, la persistencia independiente y la tolerancia a fallos.

🏗️ Arquitectura y Flujo de Datos
El sistema se comunica mediante APIs REST siguiendo este flujo:

Productos (5000): Repositorio de la verdad sobre el catálogo.

Pedidos (5001): Valida la existencia de productos antes de registrar una orden.

Pagos (5002): Verifica que el pedido exista en el servicio de Pedidos antes de procesar el pago.

🚀 Características Avanzadas
1. Resiliencia y Tolerancia a Fallos (Retry Logic)
Se implementó un mecanismo de reintentos automáticos en las comunicaciones inter-servicio:

Si un servicio dependiente no responde, el sistema realiza hasta 3 intentos con un timeout de 3 segundos.

Esto evita fallos ante micro-cortes de red o reinicios de servicios.

2. Logging y Trazabilidad
Cada servicio utiliza la librería logging de Python para registrar eventos críticos:

INFO: Registra transacciones exitosas (Ej: Creación de pedidos/pagos).

WARNING: Notifica reintentos cuando un servicio vecino está temporalmente fuera de línea.

ERROR: Reporta fallos críticos de base de datos o desconexión total.

3. Seguridad Zero-Trust
Cada petición requiere un Bearer Token en el encabezado de autorización, garantizando que solo servicios autorizados puedan comunicarse entre sí.

🛠️ Guía de Pruebas (PowerShell)
Para verificar la robustez del sistema, ejecutar los siguientes comandos en orden:

Escenario A: Compra Exitosa (Camino Feliz)
PowerShell
# 1. Crear Producto
Invoke-RestMethod -Uri "http://127.0.0.1:5000/productos" -Method Post -Headers @{"Authorization"="Bearer mi_token_secreto"} -ContentType "application/json" -Body '{"nombre": "Teclado", "precio": 150.0}'

# 2. Crear Pedido
Invoke-RestMethod -Uri "http://127.0.0.1:5001/pedidos" -Method Post -Headers @{"Authorization"="Bearer mi_token_secreto"} -ContentType "application/json" -Body '{"id_producto": 1, "cantidad": 2}'

# 3. Procesar Pago
Invoke-RestMethod -Uri "http://127.0.0.1:5002/pagos" -Method Post -Headers @{"Authorization"="Bearer mi_token_secreto"} -ContentType "application/json" -Body '{"id_pedido": 1}'
Escenario B: Prueba de Resiliencia (Servicio Caído)
Apagar el servicio de Productos (Ctrl+C).

Intentar crear un pedido:

PowerShell
Invoke-RestMethod -Uri "http://127.0.0.1:5001/pedidos" -Method Post -Headers @{"Authorization"="Bearer mi_token_secreto"} -ContentType "application/json" -Body '{"id_producto": 1, "cantidad": 1}'
Observación: El servicio de Pedidos registrará 3 advertencias (WARNING) de reintento antes de devolver un error 503 Service Unavailable.