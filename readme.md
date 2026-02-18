🐧 Proyecto: Microservicios Resilientes (Del Monolito al Ecosistema)
Este proyecto implementa un sistema de gestión de compras basado en una arquitectura de microservicios, demostrando la transición desde un enfoque monolítico hacia servicios autónomos, seguros y tolerantes a fallos.

El sistema fue diseñado cumpliendo principios de separación de responsabilidades, comunicación desacoplada (HTTP Only) y resiliencia ante fallos críticos.

This project implements a purchase management system based on a microservices architecture, demonstrating the transition from a monolithic approach to autonomous, secure, and fault-tolerant services.

🏗️ Arquitectura del Sistema / System Architecture
El sistema está compuesto por tres microservicios independientes, cada uno con una única responsabilidad y su propia base de datos (Database per Service).

| Microservicio | Puerto | Responsabilidad                   | Base de Datos   |
| ------------- | ------ | --------------------------------- |---------------- |
| Productos     | 5000   | Gestión del catálogo de productos | Productos.db    |
| Pedidos       | 5001   | Creación y validación de pedidos  | Pedidos.db      |
| Pagos         | 5002   | Procesamiento de pagos            | Pagos.db        |

📡 Comunicación y Seguridad

Protocolo: Comunicación exclusivamente vía APIs REST con métodos HTTP (GET, POST).

Aislamiento: No se comparten bases de datos; la interacción es puramente a través de endpoints.

Zero-Trust Security: Cada microservicio requiere autenticación mediante Bearer Token. Las solicitudes sin token o inválidas son rechazadas con un error 403.

🛡️ Resiliencia y Tolerancia a Fallos
Este es el núcleo técnico del proyecto, diseñado para sobrevivir a la inestabilidad de la red:

🔁 Retry (Reintentos)
Se implementa lógica de reintentos automáticos (hasta 3 intentos).

Timeout configurado en 3 segundos para evitar bloqueos infinitos.

Mitiga fallos ante caídas temporales o micro-cortes de red.

🔌 Circuit Breaker (Disyuntor)
Implementado en el microservicio de Pedidos y Pagos.

El circuito cambia a estado ABIERTO tras 3 fallos consecutivos, bloqueando llamadas durante un "período de enfriamiento" de 30 segundos.

Previene la saturación del ecosistema y permite la recuperación del servicio afectado.

📝 Logging y Trazabilidad
Cada servicio audita su comportamiento mediante la librería logging de Python, generando archivos específicos (productos.log, pedidos.log, pagos.log):

INFO: Operaciones exitosas y flujo normal.

WARNING: Intentos de acceso no autorizados o reintentos por fallos temporales.

ERROR: Fallos críticos (servicios caídos o errores de base de datos).

🧪 Guía de Pruebas (PowerShell)
Escenario A: Flujo Exitoso
Copia y pega estos comandos para simular una compra completa En powershell:

# 1. Crear Producto
Invoke-RestMethod -Uri "http://127.0.0.1:5000/productos" -Method Post `
-Headers @{"Authorization"="Bearer mi_token_secreto"} `
-ContentType "application/json" `
-Body '{"nombre": "Teclado", "precio": 150.0}'

# 2. Crear Pedido (Llamada interna a Productos)
Invoke-RestMethod -Uri "http://127.0.0.1:5001/pedidos" -Method Post `
-Headers @{"Authorization"="Bearer mi_token_secreto"} `
-ContentType "application/json" `
-Body '{"id_producto": 1, "cantidad": 2}'

# 3. Procesar Pago (Llamada interna a Pedidos)
Invoke-RestMethod -Uri "http://127.0.0.1:5002/pagos" -Method Post `
-Headers @{"Authorization"="Bearer mi_token_secreto"} `
-ContentType "application/json" `
-Body '{"id_pedido": 1}'

Escenario B: Prueba de Resiliencia
Detén el microservicio de Productos.

Intenta crear un pedido.

Resultado esperado: Verás en los logs 3 reintentos (WARNING), luego el circuito se abrirá y recibirás un error 503 Service Unavailable.
