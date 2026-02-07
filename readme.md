🐧 Proyecto: Microservicios Resilientes

(Del Monolito al Ecosistema)

Este proyecto implementa un sistema de gestión de compras basado en una arquitectura de microservicios, demostrando la transición desde un enfoque monolítico hacia servicios autónomos, seguros y tolerantes a fallos.

El sistema fue diseñado cumpliendo principios de separación de responsabilidades, comunicación desacoplada y resiliencia ante fallos.

🏗️ Arquitectura del Sistema

El sistema está compuesto por tres microservicios independientes, cada uno con una única responsabilidad y su propia base de datos.
| Microservicio | Puerto | Responsabilidad                   |
| ------------- | ------ | --------------------------------- |
| Productos     | 5000   | Gestión del catálogo de productos |
| Pedidos       | 5001   | Creación y validación de pedidos  |
| Pagos         | 5002   | Procesamiento de pagos            |


📡 Comunicación

Comunicación exclusivamente vía APIs REST

Uso de métodos HTTP correctos (GET, POST)

No se comparten bases de datos

La interacción entre servicios se realiza únicamente por HTTP

🔐 Seguridad

Cada microservicio requiere autenticación mediante Bearer Token

Las solicitudes sin token o con token inválido son rechazadas (403)

Modelo Zero-Trust entre servicios

💽 Persistencia

Cada microservicio posee su propia base de datos SQLite

No existen tablas compartidas

Las bases de datos son completamente independientes

🛡️ Resiliencia y Tolerancia a Fallos
🔁 Retry

Se implementa lógica de reintentos automáticos (hasta 3 intentos)

Timeout configurado en 3 segundos

Evita fallos ante caídas temporales o micro-cortes de red

🔌 Circuit Breaker

Implementado en el microservicio Pedidos

El circuito se abre tras múltiples fallos consecutivos

Se bloquean llamadas durante un período de enfriamiento

Previene la saturación del sistema ante servicios caídos

📝 Logging y Trazabilidad

Cada microservicio registra eventos relevantes utilizando la librería logging:

INFO: operaciones exitosas (creación de pedidos/pagos)

WARNING: reintentos por fallos temporales

ERROR: fallos críticos (servicios caídos, errores de base de datos)

🧪 Guía de Pruebas (PowerShell)
Escenario A: Flujo exitoso

# Crear Producto
Invoke-RestMethod -Uri "http://127.0.0.1:5000/productos" -Method Post `
-Headers @{"Authorization"="Bearer mi_token_secreto"} `
-ContentType "application/json" `
-Body '{"nombre": "Teclado", "precio": 150.0}'

# Crear Pedido
Invoke-RestMethod -Uri "http://127.0.0.1:5001/pedidos" -Method Post `
-Headers @{"Authorization"="Bearer mi_token_secreto"} `
-ContentType "application/json" `
-Body '{"id_producto": 1, "cantidad": 2}'

# Procesar Pago
Invoke-RestMethod -Uri "http://127.0.0.1:5002/pagos" -Method Post `
-Headers @{"Authorization"="Bearer mi_token_secreto"} `
-ContentType "application/json" `
-Body '{"id_pedido": 1}'

Escenario B: Prueba de Resiliencia

1-Detener el servicio Productos

2-Intentar crear un pedido

Invoke-RestMethod -Uri "http://127.0.0.1:5001/pedidos" -Method Post `
-Headers @{"Authorization"="Bearer mi_token_secreto"} `
-ContentType "application/json" `
-Body '{"id_producto": 1, "cantidad": 1}'

📌 Resultado esperado:

Se registran 3 reintentos (WARNING)

El circuito se abre

Se devuelve error 503 Service Unavailable

✅ Cumplimiento del Desafío

✔️ Mínimo 3 microservicios

✔️ APIs REST independientes

✔️ Autenticación entre servicios

✔️ Bases de datos separadas

✔️ Resiliencia (Retry + Circuit Breaker)

✔️ Clean Code y responsabilidades claras

🎯 Veredicto

Este proyecto demuestra una implementación funcional y coherente de una arquitectura de microservicios resiliente, cumpliendo con todos los requisitos del desafío planteado.
