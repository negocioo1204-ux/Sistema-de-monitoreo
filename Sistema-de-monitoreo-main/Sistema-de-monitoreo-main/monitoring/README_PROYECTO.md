# Omada MCP - Centro de Monitoreo Predictivo de Red

## Vision General

Sistema de monitoreo en tiempo real para redes TP-Link Omada. Consta de un
backend FastAPI que genera/simula telemetria de red y un dashboard Streamlit
que visualiza los datos con graficos interactivos Plotly. Disenado para
entornos educativos/institucionales (ej. colegios, campus).

## Arquitectura

┌─────────────────────────────────────────────────────────────┐
│                    monitoring/                                │
│                                                               │
│  server.py ──WebSocket /ws/alertas──► dashboard.py            │
│  (FastAPI)                        (Streamlit + Plotly)       │
│      │                                                        │
│      └── Simulacion interna de datos                          │
│          (no requiere Omada real ni Node.js)                  │
│                                                               │
│  notification.py ── opcional: envio de alertas por email      │
│  analizador.py   ── (vacio, reservado para logica futura)     │
└─────────────────────────────────────────────────────────────┘

## Componentes

### 1. server.py (FastAPI) - 153 lineas

Backend que ejecuta un loop de simulacion y transmite datos por WebSocket.

Rutas:
  GET  /health        → Estado del servidor
  WS   /ws/alertas    → Streaming de telemetria en tiempo real

Datos simulados que genera cada 5 segundos:

  RED:
  - Cantidad de dispositivos (14) y clientes (52)
  - Dispositivos offline (0-2, ciclico cada 10 ticks)
  - Clientes offline (0-5, ciclico cada 7 ticks)
  - Estado de Internet (conectado/desconectado, cada 15 ticks)
  - Amenazas activas (0-3, ciclico cada 12 ticks)

  GATEWAY (Router ER7212PC):
  - CPU: 20-60% normal, picos a 88-97% cada 8 ticks
  - Memoria: 30-70% normal, picos a 88-95% cada 13 ticks
  - Estado WAN

  SEGURIDAD:
  - Intentos bloqueados (incrementales: 1420 + tick)
  - Autenticaciones exitosas/fallidas
  - Nivel de riesgo: ALTO/BAJO
  - Ubicaciones de ataque (coordenadas simuladas)
  - Eventos recientes de seguridad

  RENDIMIENTO:
  - Calidad WiFi: 50-92% (degradacion ciclica)
  - Latencia: 2-52 ms
  - Perdida de paquetes: 0.02-5.00%
  - Trafico en tiempo real (20 puntos por ciclo, senoidal + ruido)
  - Consumo por usuario (3 usuarios simulados)

  DISPOSITIVOS:
  - Dispositivos en linea (14-18)
  - Desconexiones recientes

  IA PREDICTIVA:
  - Probabilidad de falla
  - Prediccion de congestion
  - Recomendaciones automaticas
  - Deteccion de anomalias

  PORTAL CAUTIVO:
  - Usuarios activos (~340-360)
  - Aceptacion de politicas
  - Desglose por rol: Estudiantes, Docentes, Invitados

  ADMINISTRACION:
  - Administradores conectados
  - Bitacora de cambios
  - Historial de amenazas

Alertas simuladas:
  critical: dispositivos offline, internet caido, amenazas activas
  warning:  clientes offline, CPU/memoria alta

### 2. dashboard.py (Streamlit + Plotly) - ~550 lineas

Interfaz visual con 7 pestanas (tabs):

  📡 Resumen General:
    - Estado de red (dispositivos, clientes, internet)
    - Estado del gateway (CPU, memoria con graficos de linea)
    - Alertas recientes (tarjetas con codigo de colores)
    - Historial de amenazas

  🛡️ Seguridad:
    - Metricas: intentos bloqueados, auth OK/fallidas, riesgo
    - Mapa geografico de ataques (Plotly Scattergeo)
    - Eventos recientes de seguridad
    - Detecciones IA

  📊 Rendimiento:
    - Calidad WiFi, latencia, perdida de paquetes
    - Grafico de trafico en tiempo real (descarga/subida)
    - Tendencias (calidad, latencia, perdida)
    - Consumo por usuario

  📱 Dispositivos:
    - Dispositivos en linea/offline
    - Temperatura promedio
    - Registro de desconexiones

  🤖 IA Predictiva:
    - Probabilidad de falla
    - Prediccion de congestion
    - Recomendaciones automaticas
    - Anomalias detectadas

  🧾 Portal Cautivo:
    - Usuarios activos
    - Aceptacion de politicas
    - Desglose por rol (barras visuales)

  🛠️ Administracion:
    - Administradores conectados
    - Bitacora de cambios
    - Historial de amenazas (grafico de barras)

Conexion: WebSocket a ws://localhost:8000/ws/alertas
Fallback: Si websocket-client no esta instalado, genera datos locales

### 3. notification.py (Opcional) - 204 lineas

Modulo de notificaciones por email con:
  - Diseno HTML profesional con emojis y colores
  - Categorizacion: critical, error, warning, predictive
  - Filtro por severidad minima
  - Cooldown entre correos (evita spam)
  - Soporte SMTP con TLS/SSL

### 4. analizador.py (Vacio)

Reservado para logica de analisis personalizada.

## Flujo de Datos

  1. server.py inicia → loop de simulacion cada 5s
  2. Genera payload JSON con todas las metricas
  3. Lo transmite a todos los WebSocket clients conectados
  4. dashboard.py recibe el JSON → actualiza graficos y metricas
  5. Auto-refresh cada 2 segundos (st.rerun)

## Requisitos

  Python 3.11+
  Dependencias: fastapi, uvicorn, streamlit, plotly, numpy,
                pandas, python-dotenv, websockets

## Instalacion

  cd monitoring
  pip install -r requirements.txt

## Ejecucion

### Manual (dos terminales):

  # Terminal 1 - Servidor FastAPI
  python -m uvicorn server:app --host 0.0.0.0 --port 8000

  # Terminal 2 - Dashboard
  streamlit run dashboard.py

### Automatico (Windows):

 双击 run.bat
  (abre servidor + dashboard automaticamente)

## Accesos

  Servidor FastAPI:  http://127.0.0.1:8000
  Health check:      http://127.0.0.1:8000/health
  Documentacion API: http://127.0.0.1:8000/docs
  Dashboard:         http://127.0.0.1:8501

## Notificaciones por Email

Opcional. Configurar en monitoring/.env:

  SMTP_HOST=smtp.gmail.com
  SMTP_PORT=587
  SMTP_USER=tu_correo@gmail.com
  SMTP_PASS=tu_contraseña_app
  SMTP_TO=destinatario@correo.com
  NOTIFY_SEVERITY=warning
  NOTIFY_COOLDOWN=300

## Estructura de Datos (payload WebSocket)

  {
    "timestamp": "ISO-8601",
    "alerts": [{"severity", "title", "detail", "timestamp"}],
    "network":     { "overview", "internet", "threats" },
    "gateway":     { "detail", "wanStatus" },
    "security":    { "blocked_attempts", "auth_success", "auth_failed",
                     "risk_level", "attack_locations", "recent_events" },
    "performance": { "wifi_quality", "latency", "packet_loss",
                     "bandwidth_capacity", "realtime_traffic",
                     "user_consumption" },
    "devices":     { "online", "offline_recent", "avg_temp",
                     "disconnect_logs" },
    "ai":          { "fail_prob", "congestion_pred", "anomalies_log",
                     "auto_recommendations" },
    "captive_portal": { "active_users", "policy_accepted_ratio",
                        "roles_breakdown" },
    "admin":       { "connected_admins", "changelog", "threats_history" }
  }

## Personalizacion

- Escenario educativo: modificar generar_datos_simulados() en server.py
- Nuevas metricas: agregar seccion al payload y tab en dashboard.py
- Colores: editar COLORS en dashboard.py (tema oscuro Catppuccin Mocha)
- Periodicidad: cambiar await asyncio.sleep(5) en server.py
- Fallback offline: editar _fallback_data() en dashboard.py

## Proximos Pasos (ideas)

  [ ] Conectar a Omada MCP real (Node.js) en lugar de simulacion
  [ ] Base de datos historica (SQLite/Postgres)
  [ ] Autenticacion de usuarios
  [ ] Alertas por WhatsApp/Telegram
  [ ] Exportacion de reportes PDF
  [ ] Modo oscuro/claro configurable
  [ ] Panel de administracion web
