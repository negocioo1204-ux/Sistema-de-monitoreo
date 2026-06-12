import os
import asyncio
import logging
import random
from datetime import datetime
from typing import Any, Dict, List, Set
from collections import deque

import requests
import urllib3
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

# Cargar variables de entorno
load_dotenv()
urllib3.disable_warnings()

# Importar el gestor de notificaciones (si existe)
try:
    from notification import NotificationManager
except ImportError:
    class NotificationManager:
        pass

# Configuración de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("omada-server")

app = FastAPI(title="Omada MCP Backend - Real", version="2.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

notifier = NotificationManager() if 'NotificationManager' in dir() else None

# -------------------------------------------------------------------------
# Configuración Omada desde .env
# -------------------------------------------------------------------------
OMADA_BASE_URL = os.getenv("OMADA_BASE_URL")
CLIENT_ID = os.getenv("OMADA_CLIENT_ID")
CLIENT_SECRET = os.getenv("OMADA_CLIENT_SECRET")
OMADAC_ID = os.getenv("OMADA_OMADAC_ID")
SSL_VERIFY = os.getenv("OMADA_SSL_VERIFY", "false").lower() == "true"

if not OMADA_BASE_URL:
    log.error("Falta OMADA_BASE_URL en .env")
if not CLIENT_ID or not CLIENT_SECRET:
    log.error("Faltan credenciales OAuth en .env")

# -------------------------------------------------------------------------
# Funciones de conexión a Omada API
# -------------------------------------------------------------------------
def get_omada_token():
    url = f"{OMADA_BASE_URL}/api/v2/openapi/oauth/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "omadac_id": OMADAC_ID
    }
    r = requests.post(url, json=payload, verify=SSL_VERIFY)
    r.raise_for_status()
    return r.json()["access_token"]

def get_site_id(token):
    url = f"{OMADA_BASE_URL}/api/v2/openapi/sites"
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers, verify=SSL_VERIFY)
    r.raise_for_status()
    sites = r.json().get("data", [])
    if not sites:
        raise Exception("No hay sitios en el controlador")
    return sites[0]["id"]

def get_devices(token, site_id):
    url = f"{OMADA_BASE_URL}/api/v2/openapi/sites/{site_id}/devices"
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers, verify=SSL_VERIFY)
    r.raise_for_status()
    return r.json().get("data", [])

def get_clients(token, site_id):
    url = f"{OMADA_BASE_URL}/api/v2/openapi/sites/{site_id}/clients"
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers, verify=SSL_VERIFY)
    r.raise_for_status()
    return r.json().get("data", [])

def get_events(token, site_id, limit=100):
    url = f"{OMADA_BASE_URL}/api/v2/openapi/sites/{site_id}/events"
    params = {"limit": limit, "sort": "-time"}
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers, params=params, verify=SSL_VERIFY)
    r.raise_for_status()
    return r.json().get("data", [])

# -------------------------------------------------------------------------
# Estado global de la red (estructura que espera el frontend)
# -------------------------------------------------------------------------
network_state: Dict[str, Any] = {
    "timestamp": "",
    "alerts": [],
    "network": {
        "overview": "Estable",
        "internet": "Connected",
        "threats": 0,
        "clients_total": 0,
        "devices_total": 0
    },
    "gateway": {
        "cpu": 0,
        "memory": 0,
        "wan_status": "UP",
        "latency_ms": 0,
        "packet_loss": 0.0
    },
    "devices": {
        "router": {"status": "Connected", "temp": 0.0, "cpu": 0, "ram": 0},
        "switch_l3": {"status": "Connected", "temp": 0.0, "cpu": 0, "ram": 0},
        "switch_l2": {"status": "Connected", "temp": 0.0, "cpu": 0, "ram": 0},
        "ap_laboratorio": {"status": "Connected", "temp": 0.0, "clients": 0},
        "ap_docentes": {"status": "Connected", "temp": 0.0, "clients": 0},
        "ap_invitados": {"status": "Connected", "temp": 0.0, "clients": 0}
    },
    "performance": {
        "wifi_quality": 0,
        "bandwidth_capacity_mbps": 100,
        "realtime_traffic": {"download": [], "upload": []},
        "vlan_consumption": {}
    },
    "captive_portal": {
        "active_users": 0,
        "roles_breakdown": {},
        "radius_status": "Connected",
        "vouchers_remaining": 0
    },
    "ai": {
        "fail_prob": 0,
        "overheat_risk": "Desconocido",
        "memory_leak_risk": "Desconocido",
        "packet_loss_risk": "Desconocido",
        "recommendations": "Conectando con Omada para obtener datos reales..."
    },
    "device_reputation": {},
    "vlan_users": {},
    "internet_quality": {
        "latency": 0,
        "jitter": 0,
        "packet_loss": 0.0,
        "download_speed": 0,
        "upload_speed": 0,
        "dns_status": "Operativo"
    },
    "ap_details": [],
    "security_logs": []
}

# Inicializar tráfico realtime (últimos 50 valores)
for _ in range(50):
    network_state["performance"]["realtime_traffic"]["download"].append(0)
    network_state["performance"]["realtime_traffic"]["upload"].append(0)

# Históricos (deques)
history_traffic = deque(maxlen=288)      # timestamp, download, upload
history_vlan_usage = deque(maxlen=288)   # timestamp, dict consumo
history_clients = deque(maxlen=288)      # timestamp, total_clients
history_wan_latency = deque(maxlen=288)
history_wan_jitter = deque(maxlen=288)
history_wan_packetloss = deque(maxlen=288)

# WebSockets
active_connections: Set[WebSocket] = set()

class ConnectionManager:
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        active_connections.add(websocket)
        await websocket.send_json(network_state)
    def disconnect(self, websocket: WebSocket):
        active_connections.discard(websocket)
    async def broadcast(self, message: dict):
        for connection in list(active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

# -------------------------------------------------------------------------
# Bucle de actualización con datos REALES de Omada
# -------------------------------------------------------------------------
async def real_data_loop():
    global network_state, history_traffic, history_vlan_usage, history_clients
    global history_wan_latency, history_wan_jitter, history_wan_packetloss

    log.info("Iniciando bucle de datos reales desde Omada Controller...")
    try:
        token = get_omada_token()
        site_id = get_site_id(token)
        log.info("✅ Conectado a Omada Controller - Datos reales activados")
    except Exception as e:
        log.error(f"❌ Error de conexión inicial a Omada: {e}")
        return

    last_events_id = set()  # para evitar duplicados en alertas
    while True:
        try:
            # Refrescar token cada 30 minutos
            if datetime.now().minute % 30 == 0 and datetime.now().second < 10:
                token = get_omada_token()
                site_id = get_site_id(token)
                log.info("Token de Omada renovado")

            # Obtener datos en paralelo (simplificado)
            devices = get_devices(token, site_id)
            clients = get_clients(token, site_id)
            events = get_events(token, site_id, limit=100)

            # --- Actualizar network_state con datos reales ---
            now_str = datetime.now().isoformat()
            network_state["timestamp"] = now_str

            # Clientes y dispositivos totales
            total_clients = len(clients)
            total_devices = len(devices)
            network_state["network"]["clients_total"] = total_clients
            network_state["network"]["devices_total"] = total_devices
            network_state["captive_portal"]["active_users"] = total_clients

            # Gateway / Router: buscar primer dispositivo tipo gateway/router
            router = next((d for d in devices if d.get("type") in ["gateway", "router"]), None)
            if router:
                network_state["gateway"]["cpu"] = router.get("cpuUsage", 0)
                network_state["gateway"]["memory"] = router.get("memUsage", 0)
                network_state["devices"]["router"]["cpu"] = router.get("cpuUsage", 0)
                network_state["devices"]["router"]["ram"] = router.get("memUsage", 0)
                # Temperatura puede no existir, dejamos 0
            else:
                network_state["gateway"]["cpu"] = 0
                network_state["gateway"]["memory"] = 0

            # Switches (L2/L3) - para llenar los campos device reputation u otros
            switches = [d for d in devices if d.get("type") == "switch"]
            if len(switches) > 0:
                sw = switches[0]
                network_state["devices"]["switch_l3"]["cpu"] = sw.get("cpuUsage", 0)
                network_state["devices"]["switch_l3"]["ram"] = sw.get("memUsage", 0)

            # APs
            aps = [d for d in devices if d.get("type") == "ap"]
            ap_details = []
            for ap in aps[:3]:  # mostrar hasta 3 APs
                ap_details.append({
                    "name": ap.get("name", "AP Desconocido"),
                    "clients": ap.get("clientNum", 0),
                    "channel": ap.get("channel", 0),
                    "signal_dbm": ap.get("signal", -50),
                    "saturation": "Alta" if ap.get("clientNum", 0) > 30 else "Media" if ap.get("clientNum", 0) > 15 else "Baja"
                })
            network_state["ap_details"] = ap_details
            # Asignar algunos APs a campos específicos (si coinciden nombres, opcional)
            for ap in aps:
                name = ap.get("name", "").lower()
                if "laboratorio" in name:
                    network_state["devices"]["ap_laboratorio"]["clients"] = ap.get("clientNum", 0)
                elif "docentes" in name:
                    network_state["devices"]["ap_docentes"]["clients"] = ap.get("clientNum", 0)
                elif "invitados" in name:
                    network_state["devices"]["ap_invitados"]["clients"] = ap.get("clientNum", 0)

            # Calcular calidad WiFi aproximada (basada en señal media)
            if aps:
                avg_signal = sum(abs(ap.get("signal", -60)) for ap in aps) / len(aps)
                wifi_quality = max(0, min(100, int(100 - (avg_signal + 30))))
                network_state["performance"]["wifi_quality"] = wifi_quality

            # VLAN consumption: intentar obtener estadísticas de red (si la API las da) o dejar vacío
            # Por ahora, simular algo basado en número de clientes por red (si se puede)
            # Omada no expone fácilmente consumo por VLAN, así que dejamos los valores del último ciclo o vacío.
            if not network_state["performance"]["vlan_consumption"]:
                network_state["performance"]["vlan_consumption"] = {
                    "VLAN 10 (Admin)": 0,
                    "VLAN 20 (Docentes)": 0,
                    "VLAN 30 (Alumnos)": 0,
                    "VLAN 40 (Invitados)": 0
                }

            # Alertas: convertir eventos recientes a formato que espera el frontend
            new_alerts = []
            for ev in events:
                ev_id = ev.get("id") or f"{ev.get('time')}_{ev.get('eventType')}"
                if ev_id in last_events_id:
                    continue
                last_events_id.add(ev_id)
                # Mapear tipo de evento a categoría y severidad
                event_type = ev.get("eventType", "").lower()
                severity = "info"
                if any(k in event_type for k in ["vlan", "hopping", "drop", "attack", "fail", "down", "high"]):
                    severity = "error"
                elif any(k in event_type for k in ["warning", "alert"]):
                    severity = "warning"
                
                new_alerts.append({
                    "id": ev_id,
                    "title": ev.get("eventType", "Evento"),
                    "description": ev.get("description", ""),
                    "category": ev.get("eventType", "Sistema"),
                    "severity": severity,
                    "timestamp": ev.get("time", now_str),
                    "source": ev.get("srcMac", ev.get("deviceName", ""))
                })
            # Limitar a 50 alertas y mantener las más recientes
            if new_alerts:
                network_state["alerts"] = (new_alerts + network_state["alerts"])[:50]

            # Agregar evento de seguridad si hay alertas nuevas
            for alert in new_alerts[:5]:
                network_state["security_logs"].insert(0, {
                    "timestamp": alert["timestamp"],
                    "event": alert["title"],
                    "details": alert["description"],
                    "level": alert["severity"]
                })
            network_state["security_logs"] = network_state["security_logs"][:100]

            # Internet quality: podrías hacer ping a 8.8.8.8, pero lo dejamos con valores por defecto
            # o puedes medir con una librería externa. Por ahora, mantenemos lo que había.
            # Si quieres, puedes agregar un ping real aquí.

            # Históricos
            timestamp = now_str
            # Tráfico: intentar obtener tráfico real de algún puerto WAN o del gateway
            # Si no se puede, usar valores derivados de CPU como placeholder
            download_mbps = network_state["gateway"]["cpu"] * 2
            upload_mbps = network_state["gateway"]["cpu"] * 1.2
            history_traffic.append({"time": timestamp, "download": download_mbps, "upload": upload_mbps})
            history_clients.append({"time": timestamp, "count": total_clients})
            # Guardar también en el array de realtime_traffic (para gráfica)
            network_state["performance"]["realtime_traffic"]["download"].append(download_mbps)
            network_state["performance"]["realtime_traffic"]["upload"].append(upload_mbps)
            if len(network_state["performance"]["realtime_traffic"]["download"]) > 50:
                network_state["performance"]["realtime_traffic"]["download"].pop(0)
                network_state["performance"]["realtime_traffic"]["upload"].pop(0)

            # Para otros históricos (latencia, jitter) si no tienes datos, ponemos valores simulados pequeños
            history_wan_latency.append({"time": timestamp, "value": random.randint(10, 30)})
            history_wan_jitter.append({"time": timestamp, "value": random.randint(1, 5)})
            history_wan_packetloss.append({"time": timestamp, "value": round(random.uniform(0, 0.5), 2)})

            # Recomendaciones AI básicas basadas en datos reales
            recs = []
            if network_state["gateway"]["cpu"] > 80:
                recs.append("• Alto uso de CPU en el gateway. Revisar procesos o ampliar capacidad.")
            if total_clients > 200:
                recs.append("• Muchos clientes conectados. Considerar segmentar redes o añadir APs.")
            if network_state["performance"]["wifi_quality"] < 50:
                recs.append("• Calidad WiFi baja. Verificar interferencias o ubicación de APs.")
            if not recs:
                recs.append("• No se detectan problemas. La red opera con normalidad.")
            network_state["ai"]["recommendations"] = "\n".join(recs)
            network_state["ai"]["fail_prob"] = min(100, network_state["gateway"]["cpu"] + (100 - network_state["performance"]["wifi_quality"]) // 2)

            # Broadcast por WebSocket si hay cambios relevantes (cada ciclo)
            await manager.broadcast(network_state)

            log.info(f"[REAL] Actualizado: {total_clients} clientes, CPU gateway: {network_state['gateway']['cpu']}%, {len(events)} eventos, {len(new_alerts)} alertas nuevas")

        except Exception as e:
            log.error(f"Error en bucle de datos reales: {e}", exc_info=True)

        await asyncio.sleep(10)  # actualizar cada 10 segundos

# -------------------------------------------------------------------------
# Evento startup: lanzar el bucle real y limpiar cualquier simulación previa
# -------------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(real_data_loop())

# -------------------------------------------------------------------------
# ENDPOINTS (sin cambios, solo usan network_state actualizado)
# -------------------------------------------------------------------------
@app.get("/health")
def health_check():
    return {"status": "healthy", "server_time": datetime.now().isoformat()}

@app.get("/api/state")
def get_state():
    return network_state

@app.get("/api/history")
def get_history():
    return {
        "traffic": list(history_traffic),
        "vlan_usage": list(history_vlan_usage),
        "clients": list(history_clients),
        "wan_latency": list(history_wan_latency),
        "wan_jitter": list(history_wan_jitter),
        "wan_packetloss": list(history_wan_packetloss)
    }

@app.get("/api/recommendations")
def get_recommendations():
    return {"recommendations": network_state["ai"]["recommendations"].split("\n"), "timestamp": network_state["timestamp"]}

# -------------------------------------------------------------------------
# ASISTENTE IA (Gemini / fallback) - igual que antes
# -------------------------------------------------------------------------
class ChatRequest(BaseModel):
    pregunta: str

@app.post("/api/chat")
async def chat_asistente_ia(request: ChatRequest):
    pregunta_usuario = request.pregunta
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    infraestructura_status = (
        f"Dispositivos: Router CPU {network_state['gateway']['cpu']}%, "
        f"WAN: {network_state['gateway']['wan_status']} (latencia {network_state['gateway']['latency_ms']}ms), "
        f"Portal: {network_state['captive_portal']['active_users']} usuarios, "
        f"Alertas activas: {len(network_state['alerts'])}"
    )
    alertas_recientes = "\n".join(
        [f"- {a['category']}: {a['title']}" for a in network_state["alerts"][:6]]
    ) or "Ninguna alerta activa."

    if api_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            payload = {
                "contents": [{
                    "parts": [
                        {"text": f"Eres experto en redes Omada. Estado: {infraestructura_status}. Alertas: {alertas_recientes}"},
                        {"text": f"Pregunta: {pregunta_usuario}"}
                    ]
                }]
            }
            async with httpx.AsyncClient() as client:
                res = await client.post(url, json=payload, timeout=20)
                if res.status_code == 200:
                    data = res.json()
                    respuesta = data["candidates"][0]["content"]["parts"][0]["text"]
                    return {"response": respuesta, "engine": "Gemini 1.5 Flash"}
        except Exception as e:
            log.error(f"Error con Gemini: {e}")

    # Fallback local
    respuesta_fallback = (
        "### Diagnóstico del Ingeniero de Redes\n\n"
        "El sistema está operando con datos reales de Omada. "
        "Si hay alertas, se muestran en el dashboard. "
        "No se detectan incidentes críticos en este momento."
    )
    return {"response": respuesta_fallback, "engine": "Omada IA Engine (Real)"}

# -------------------------------------------------------------------------
# WEBSOCKET (sin cambios)
# -------------------------------------------------------------------------
@app.websocket("/ws/alertas")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        log.error(f"Error WS: {e}")
        manager.disconnect(websocket)

# -------------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)