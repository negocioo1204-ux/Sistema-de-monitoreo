import os
import asyncio
import logging
import random
import math
import time
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
import analizador
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
app = FastAPI(title="Omada MCP Backend - Inteligente", version="3.0.0")
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
SIMULATE = os.getenv("SIMULATE", "false").lower() == "true"
# -------------------------------------------------------------------------
# Estado global de la red
# -------------------------------------------------------------------------
network_state: Dict[str, Any] = {
    "timestamp": "",
    "alerts": [],
    "network": {
        "overview": "Estable",
        "internet": "Connected",
        "threats": 0,
        "clients_total": 52,
        "devices_total": 14
    },
    "gateway": {
        "cpu": 32,
        "memory": 45,
        "wan_status": "UP",
        "latency_ms": 15,
        "packet_loss": 0.001
    },
    "devices": {
        "router": {"status": "Connected", "temp": 42.5, "cpu": 32, "ram": 45},
        "switch_l3": {"status": "Connected", "temp": 38.0, "cpu": 25, "ram": 48},
        "switch_l2": {"status": "Connected", "temp": 35.0, "cpu": 15, "ram": 38},
        "ap_laboratorio": {"status": "Connected", "temp": 34.0, "clients": 18},
        "ap_administracion": {"status": "Connected", "temp": 33.5, "clients": 14},
        "ap_invitados": {"status": "Connected", "temp": 32.0, "clients": 20}
    },
    "performance": {
        "wifi_quality": 88,
        "bandwidth_capacity_mbps": 100,
        "realtime_traffic": {"download": [], "upload": []},
        "vlan_consumption": {}
    },
    "captive_portal": {
        "active_users": 52,
        "roles_breakdown": {"Estudiantes": 30, "Administración": 12, "Invitados": 10},
        "radius_status": "Connected",
        "vouchers_remaining": 150
    },
    "predictions": {
        "download_forecast": [],
        "upload_forecast": [],
        "ram_forecast": [],
        "temp_forecast": [],
        "wifi_forecast": [],
        "fail_prob": 2,
        "overheat_risk": "Bajo",
        "memory_leak_risk": "Bajo",
        "congestion_probability": 0,
        "wifi_degradation_risk": "Bajo",
        "time_to_overheat_sec": -1,
        "time_to_ram_exhaustion_sec": -1,
        "anomalies": [],
        "recommendations": ["• Estado de red estable. No se proyectan anomalías."],
        "auto_mitigation_active": False
    },
    "vlan_users": {
        "VLAN 10 (Admin)": 5,
        "VLAN 20 (Administración)": 15,
        "VLAN 30 (Alumnos)": 22,
        "VLAN 40 (Invitados)": 10
    },
    "internet_quality": {
        "latency": 15,
        "jitter": 2,
        "packet_loss": 0.001,
        "download_speed": 100.0,
        "upload_speed": 20.0,
        "dns_status": "Operativo"
    },
    "ap_details": [],
    "security_logs": []
}
# Inicializar tráfico realtime (últimos 50 valores)
for _ in range(50):
    network_state["performance"]["realtime_traffic"]["download"].append(25.0)
    network_state["performance"]["realtime_traffic"]["upload"].append(8.0)
# Históricos (deques para tendencias e historial general)
history_traffic = deque(maxlen=288)      # timestamp, download, upload
history_vlan_usage = deque(maxlen=288)   # timestamp, dict consumo
history_clients = deque(maxlen=288)      # timestamp, total_clients
history_wan_latency = deque(maxlen=288)
history_wan_jitter = deque(maxlen=288)
history_wan_packetloss = deque(maxlen=288)
# Históricos específicos de tendencia para el motor predictivo (últimos 30 ticks)
trend_download = deque([25.0]*30, maxlen=30)
trend_upload = deque([8.0]*30, maxlen=30)
trend_ram = deque([48.0]*30, maxlen=30)
trend_temp = deque([42.5]*30, maxlen=30)
trend_wifi = deque([88.0]*30, maxlen=30)
# -------------------------------------------------------------------------
# Variables del Simulador e Incidentes y Auto-Mitigación
# -------------------------------------------------------------------------
sim_scenario = "normal"  # "normal", "mass_download", "memory_leak", "overheating", "wifi_interference", "ddos_attack"
sim_ticks = 0
sim_qos_active = False
auto_mitigation_active = False
# Variables de estado interno de simulación para suavidad
sim_cpu = 32.0
sim_ram = 48.0
sim_temp = 42.5
sim_wifi = 88.0
sim_clients = 52
sim_download = 25.0
sim_upload = 8.0
sim_threats = 0
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
# Función Auxiliar: Agregar Alertas y Notificar por Correo Electrónico
# -------------------------------------------------------------------------
async def add_alert_and_notify(title: str, detail: str, category: str, severity: str, source: str):
    """Inserta una alerta en el estado de la red y envía una notificación por correo electrónico"""
    now_str = datetime.now().isoformat()
    alert = {
        "id": f"alert_{int(time.time())}_{random.randint(100, 999)}",
        "title": title,
        "detail": detail,
        "category": category,
        "severity": severity,
        "timestamp": now_str,
        "source": source
    }
    
    # Insertar al inicio de la lista de alertas
    network_state["alerts"].insert(0, alert)
    network_state["alerts"] = network_state["alerts"][:50]
    
    # Enviar correo en segundo plano
    if notifier:
        asyncio.create_task(notifier.send_alert(alert))
        log.info(f"Notificación encolada para correo: [{category}] {title} (Gravedad: {severity})")
# -------------------------------------------------------------------------
# Funciones de conexión a Omada API (reales)
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
# Bucle de Actualización con Datos REALES de Omada
# -------------------------------------------------------------------------
async def real_data_loop():
    global network_state, history_traffic, history_vlan_usage, history_clients
    global history_wan_latency, history_wan_jitter, history_wan_packetloss
    global trend_download, trend_upload, trend_ram, trend_temp, trend_wifi
    global auto_mitigation_active
    log.info("Iniciando bucle de datos reales desde Omada Controller...")
    try:
        token = get_omada_token()
        site_id = get_site_id(token)
        log.info("✅ Conectado a Omada Controller - Datos reales activados")
    except Exception as e:
        log.error(f"❌ Error de conexión inicial a Omada: {e}")
        log.info("Cambiando automáticamente a MODO SIMULACIÓN de forma persistente.")
        asyncio.create_task(simulated_data_loop())
        return
    last_events_id = set()
    while True:
        try:
            if datetime.now().minute % 30 == 0 and datetime.now().second < 10:
                token = get_omada_token()
                site_id = get_site_id(token)
                log.info("Token de Omada renovado")
            devices = get_devices(token, site_id)
            clients = get_clients(token, site_id)
            events = get_events(token, site_id, limit=100)
            now_str = datetime.now().isoformat()
            network_state["timestamp"] = now_str
            total_clients = len(clients)
            total_devices = len(devices)
            network_state["network"]["clients_total"] = total_clients
            network_state["network"]["devices_total"] = total_devices
            network_state["captive_portal"]["active_users"] = total_clients
            router = next((d for d in devices if d.get("type") in ["gateway", "router"]), None)
            if router:
                cpu_val = router.get("cpuUsage", 0)
                mem_val = router.get("memUsage", 0)
                network_state["gateway"]["cpu"] = cpu_val
                network_state["gateway"]["memory"] = mem_val
                network_state["devices"]["router"]["cpu"] = cpu_val
                network_state["devices"]["router"]["ram"] = mem_val
            else:
                cpu_val = 15
                mem_val = 30
                network_state["gateway"]["cpu"] = cpu_val
                network_state["gateway"]["memory"] = mem_val
            switches = [d for d in devices if d.get("type") == "switch"]
            if switches:
                sw = switches[0]
                sw_cpu = sw.get("cpuUsage", 0)
                sw_ram = sw.get("memUsage", 0)
                network_state["devices"]["switch_l3"]["cpu"] = sw_cpu
                network_state["devices"]["switch_l3"]["ram"] = sw_ram
            else:
                sw_cpu = 10
                sw_ram = 25
                network_state["devices"]["switch_l3"]["cpu"] = sw_cpu
                network_state["devices"]["switch_l3"]["ram"] = sw_ram
            aps = [d for d in devices if d.get("type") == "ap"]
            ap_details = []
            for ap in aps[:3]:
                ap_details.append({
                    "name": ap.get("name", "AP Desconocido"),
                    "clients": ap.get("clientNum", 0),
                    "channel": ap.get("channel", 0),
                    "signal_dbm": ap.get("signal", -50),
                    "saturation": "Alta" if ap.get("clientNum", 0) > 30 else "Media" if ap.get("clientNum", 0) > 15 else "Baja"
                })
            network_state["ap_details"] = ap_details
            for ap in aps:
                name = ap.get("name", "").lower()
                if "laboratorio" in name:
                    network_state["devices"]["ap_laboratorio"]["clients"] = ap.get("clientNum", 0)
                elif "administracion" in name or "docentes" in name:
                    network_state["devices"]["ap_administracion"]["clients"] = ap.get("clientNum", 0)
                elif "invitados" in name:
                    network_state["devices"]["ap_invitados"]["clients"] = ap.get("clientNum", 0)
            wifi_quality = 85
            if aps:
                avg_signal = sum(abs(ap.get("signal", -60)) for ap in aps) / len(aps)
                wifi_quality = max(0, min(100, int(100 - (avg_signal + 30))))
            network_state["performance"]["wifi_quality"] = wifi_quality
            if not network_state["performance"]["vlan_consumption"]:
                network_state["performance"]["vlan_consumption"] = {
                    "VLAN 10 (Admin)": 2.5,
                    "VLAN 20 (Administración)": 8.0,
                    "VLAN 30 (Alumnos)": 15.2,
                    "VLAN 40 (Invitados)": 4.1
                }
            # Procesar alertas reales y enviar por correo electrónico
            new_alerts = []
            for ev in events:
                ev_id = ev.get("id") or f"{ev.get('time')}_{ev.get('eventType')}"
                if ev_id in last_events_id:
                    continue
                last_events_id.add(ev_id)
                event_type = ev.get("eventType", "").lower()
                severity = "info"
                if any(k in event_type for k in ["vlan", "hopping", "drop", "attack", "fail", "down", "high"]):
                    severity = "error"
                elif any(k in event_type for k in ["warning", "alert"]):
                    severity = "warning"
                
                alert_item = {
                    "id": ev_id,
                    "title": ev.get("eventType", "Evento Omada"),
                    "detail": ev.get("description", ""),
                    "category": "Infraestructura",
                    "severity": severity,
                    "timestamp": ev.get("time", now_str),
                    "source": ev.get("deviceName", "Omada Controller")
                }
                new_alerts.append(alert_item)
                
                # Enviar notificación inmediatamente por email si corresponde
                if notifier:
                    asyncio.create_task(notifier.send_alert(alert_item))
            
            if new_alerts:
                network_state["alerts"] = (new_alerts + network_state["alerts"])[:50]
            for alert in new_alerts[:5]:
                network_state["security_logs"].insert(0, {
                    "timestamp": alert["timestamp"],
                    "event": alert["title"],
                    "details": alert["detail"],
                    "level": alert["severity"]
                })
            network_state["security_logs"] = network_state["security_logs"][:100]
            # Simular tráfico para histórico
            download_mbps = cpu_val * 1.5 + random.uniform(-2, 2)
            upload_mbps = cpu_val * 0.4 + random.uniform(-1, 1)
            
            # Guardar históricos generales
            history_traffic.append({"time": now_str, "download": download_mbps, "upload": upload_mbps})
            history_clients.append({"time": now_str, "count": total_clients})
            history_wan_latency.append({"time": now_str, "value": random.randint(12, 28)})
            history_wan_jitter.append({"time": now_str, "value": random.randint(1, 4)})
            history_wan_packetloss.append({"time": now_str, "value": round(random.uniform(0.01, 0.2), 3)})
            network_state["performance"]["realtime_traffic"]["download"].append(round(download_mbps, 2))
            network_state["performance"]["realtime_traffic"]["upload"].append(round(upload_mbps, 2))
            if len(network_state["performance"]["realtime_traffic"]["download"]) > 50:
                network_state["performance"]["realtime_traffic"]["download"].pop(0)
                network_state["performance"]["realtime_traffic"]["upload"].pop(0)
            # Actualizar históricos de tendencia
            trend_download.append(download_mbps)
            trend_upload.append(upload_mbps)
            trend_ram.append(float(sw_ram))
            trend_temp.append(45.0)
            trend_wifi.append(float(wifi_quality))
            # Ejecutar análisis predictivo
            preds = analizador.analizar_predictivo(
                network_state,
                list(trend_download),
                list(trend_upload),
                list(trend_ram),
                list(trend_temp),
                list(trend_wifi)
            )
            
            # Asignar variable de auto-mitigación al estado de predicciones
            preds["auto_mitigation_active"] = auto_mitigation_active
            network_state["predictions"] = preds
            
            # Agregar anomalías del motor predictivo como alertas
            current_predictive_alerts = []
            for idx, anomaly in enumerate(preds["anomalies"]):
                alert_item = {
                    "id": f"pred_{now_str}_{idx}",
                    "title": f"Proyección: {anomaly['metric']}",
                    "detail": anomaly["detail"],
                    "category": "Predicción IA",
                    "severity": "predictive" if anomaly["severity"] == "warning" else "critical",
                    "timestamp": now_str,
                    "source": "Motor IA Predictivo"
                }
                current_predictive_alerts.append(alert_item)
                
                # Auto-notificar alertas de predicciones por email
                if notifier:
                    asyncio.create_task(notifier.send_alert(alert_item))
            
            network_state["alerts"] = [a for a in network_state["alerts"] if a["category"] != "Predicción IA"]
            network_state["alerts"] = (current_predictive_alerts + network_state["alerts"])[:50]
            await manager.broadcast(network_state)
            log.info(f"[REAL] Telemetría real procesada y alertas notificadas.")
        except Exception as e:
            log.error(f"Error en bucle de datos reales: {e}", exc_info=True)
        await asyncio.sleep(5)
# -------------------------------------------------------------------------
# Bucle de Actualización con Datos SIMULADOS (Inteligente & Reactivo)
# -------------------------------------------------------------------------
async def simulated_data_loop():
    global network_state, history_traffic, history_vlan_usage, history_clients
    global history_wan_latency, history_wan_jitter, history_wan_packetloss
    global trend_download, trend_upload, trend_ram, trend_temp, trend_wifi
    global sim_scenario, sim_ticks, sim_qos_active, auto_mitigation_active
    global sim_cpu, sim_ram, sim_temp, sim_wifi, sim_clients, sim_download, sim_upload, sim_threats
    log.info("Iniciando bucle de datos SIMULADOS dinámicos...")
    
    while True:
        try:
            now_str = datetime.now().isoformat()
            network_state["timestamp"] = now_str
            sim_ticks += 1
            # 1. Resolver Lógicas según Escenario Activo
            if sim_scenario == "normal":
                sim_threats = 0
                sim_clients = int(50 + 10 * math.sin(sim_ticks / 10) + random.randint(-2, 2))
                sim_cpu = 25.0 + 10.0 * math.sin(sim_ticks / 5) + random.uniform(-2, 2)
                sim_ram = 45.0 + random.uniform(-0.5, 0.5)
                sim_temp = 41.5 + 4.0 * (sim_cpu / 100.0) + random.uniform(-0.2, 0.2)
                sim_wifi = 88.0 + 3.0 * math.sin(sim_ticks / 8) + random.uniform(-1, 1)
                
                # Consumo nominal
                sim_download = 22.0 + 8.0 * math.sin(sim_ticks / 6) + random.uniform(-2, 2)
                sim_upload = 6.0 + 2.0 * math.sin(sim_ticks / 6) + random.uniform(-0.5, 0.5)
            
            elif sim_scenario == "mass_download":
                sim_clients = int(52 + random.randint(-1, 1))
                sim_cpu = min(95.0, sim_cpu + 6.0 + random.uniform(-1, 1))
                sim_temp = min(75.0, sim_temp + 0.6)
                sim_wifi = max(75.0, sim_wifi - 0.5)
                
                if sim_qos_active:
                    sim_download = max(28.0, sim_download - 14.0)
                    sim_cpu = max(40.0, sim_cpu - 8.0)
                    sim_temp = max(45.0, sim_temp - 0.8)
                else:
                    sim_download = min(98.5, sim_download + 14.0)
                
                sim_upload = min(18.0, sim_upload + 1.5)
                
            elif sim_scenario == "memory_leak":
                sim_clients = int(48 + random.randint(-2, 2))
                sim_cpu = min(80.0, sim_cpu + 0.8)
                sim_temp = min(68.0, sim_temp + 0.2)
                sim_wifi = max(80.0, sim_wifi - 0.2)
                sim_download = 28.0 + random.uniform(-2, 2)
                sim_upload = 7.0 + random.uniform(-1, 1)
                
                sim_ram += 3.5
                
                # Colapso físico al pasar de 97%
                if sim_ram >= 97.0:
                    sim_ram = 0.0
                    sim_cpu = 0.0
                    sim_temp = 25.0
                    sim_wifi = 0.0
                    sim_download = 0.1
                    sim_upload = 0.1
                    network_state["devices"]["switch_l3"]["status"] = "Offline"
                    
                    await add_alert_and_notify(
                        "Switch L3 Offline",
                        "El Switch Principal L3 ha colapsado debido a desbordamiento de memoria RAM (Cerrado por el kernel).",
                        "Física",
                        "critical",
                        "Switch Core L3"
                    )
                    
                    # Auto-reiniciar después de 3 ticks
                    sim_scenario = "normal"
                    sim_ticks = 0
                    sim_ram = 48.0
                    network_state["devices"]["switch_l3"]["status"] = "Connected"
                    await add_alert_and_notify(
                        "Switch L3 Recuperado",
                        "El Switch L3 ha completado el reinicio automático. Tabla de enrutamiento reconstruida.",
                        "Física",
                        "info",
                        "Switch Core L3"
                    )
                    
            elif sim_scenario == "overheating":
                sim_cpu = 92.0 + random.uniform(-1, 1)
                sim_ram = 55.0 + random.uniform(-0.5, 0.5)
                sim_download = 78.0 + random.uniform(-3, 3)
                sim_upload = 14.0 + random.uniform(-1, 1)
                
                sim_temp += 2.2
                
                # Protección térmica WAN apaga a 88°C
                if sim_temp >= 88.0:
                    sim_temp = 55.0
                    sim_cpu = 10.0
                    sim_download = 0.2
                    sim_upload = 0.1
                    network_state["gateway"]["wan_status"] = "DOWN"
                    network_state["network"]["internet"] = "Disconnected"
                    
                    await add_alert_and_notify(
                        "Corte de WAN Preventivo",
                        "Protección Térmica Activa: El puerto WAN se ha desactivado debido a temperatura crítica en el procesador (88°C).",
                        "Hardware",
                        "critical",
                        "Router ER605"
                    )
                    
                    # Restaurar
                    sim_scenario = "normal"
                    sim_ticks = 0
                    network_state["gateway"]["wan_status"] = "UP"
                    network_state["network"]["internet"] = "Connected"
                    
            elif sim_scenario == "wifi_interference":
                sim_clients = max(12, int(sim_clients - 2))
                sim_cpu = 20.0 + random.uniform(-2, 2)
                sim_ram = 44.0
                sim_temp = 43.0
                sim_download = 5.0 + random.uniform(-1, 1)
                sim_upload = 1.2
                
                sim_wifi = max(10.0, sim_wifi - 9.0)
                
            elif sim_scenario == "ddos_attack":
                sim_threats = min(15, sim_threats + random.randint(1, 3))
                sim_clients = int(120 + random.randint(-5, 5))
                sim_cpu = min(99.5, sim_cpu + 18.0)
                sim_ram = min(92.0, sim_ram + 1.2)
                sim_temp = min(82.0, sim_temp + 1.4)
                sim_wifi = max(45.0, sim_wifi - 2.5)
                sim_download = 98.8
                sim_upload = 19.5
                
                if sim_ticks > 6:
                    network_state["network"]["internet"] = "Disconnected"
                    network_state["gateway"]["wan_status"] = "DOWN"
                
                if sim_ticks == 1:
                    await add_alert_and_notify(
                        "Ataque DDoS Detectado",
                        "Inundación masiva de paquetes SYN dirigidos al puerto 80/443 desde múltiples IPs externas.",
                        "Seguridad",
                        "critical",
                        "Firewall Omada"
                    )
            # --- Limitar rangos lógicos ---
            sim_cpu = max(0.0, min(100.0, sim_cpu))
            sim_ram = max(0.0, min(100.0, sim_ram))
            sim_temp = max(20.0, min(100.0, sim_temp))
            sim_wifi = max(0.0, min(100.0, sim_wifi))
            sim_download = max(0.1, min(100.0, sim_download))
            sim_upload = max(0.1, min(100.0, sim_upload))
            # 2. Actualizar Estado Global de Red
            network_state["network"]["overview"] = "Estable" if sim_scenario == "normal" else "Crítico" if sim_scenario in ["ddos_attack"] or sim_ram == 0 or sim_temp > 85 else "Advertencia"
            network_state["network"]["threats"] = sim_threats
            network_state["network"]["clients_total"] = sim_clients
            network_state["captive_portal"]["active_users"] = int(sim_clients * 0.8)
            network_state["network"]["devices_total"] = 13 if (sim_scenario == "memory_leak" and sim_ram == 0) else 14
            
            network_state["gateway"]["cpu"] = int(sim_cpu)
            network_state["gateway"]["memory"] = int(sim_ram)
            network_state["devices"]["router"]["cpu"] = int(sim_cpu)
            network_state["devices"]["router"]["ram"] = int(sim_ram)
            network_state["devices"]["router"]["temp"] = round(sim_temp, 1)
            # Switch
            network_state["devices"]["switch_l3"]["cpu"] = int(sim_cpu * 0.75) if sim_ram > 0 else 0
            network_state["devices"]["switch_l3"]["ram"] = int(sim_ram)
            network_state["devices"]["switch_l3"]["temp"] = round(sim_temp - 4.5, 1) if sim_ram > 0 else 20.0
            # Calidad WiFi y Access Points
            network_state["performance"]["wifi_quality"] = int(sim_wifi)
            network_state["devices"]["ap_laboratorio"]["clients"] = int(sim_clients * 0.35)
            network_state["devices"]["ap_administracion"]["clients"] = int(sim_clients * 0.25)
            network_state["devices"]["ap_invitados"]["clients"] = int(sim_clients * 0.4)
            # VLANs segmentación consumo
            if sim_scenario == "mass_download" and not sim_qos_active:
                v30 = sim_download * 0.85
                v20 = sim_download * 0.08
                v10 = sim_download * 0.04
                v40 = sim_download * 0.03
            elif sim_scenario == "ddos_attack":
                v30 = sim_download * 0.90
                v20 = sim_download * 0.05
                v10 = sim_download * 0.03
                v40 = sim_download * 0.02
            else:
                v30 = sim_download * 0.45
                v20 = sim_download * 0.30
                v10 = sim_download * 0.15
                v40 = sim_download * 0.10
            network_state["performance"]["vlan_consumption"] = {
                "VLAN 10 (Admin)": round(v10, 2),
                "VLAN 20 (Administración)": round(v20, 2),
                "VLAN 30 (Alumnos)": round(v30, 2),
                "VLAN 40 (Invitados)": round(v40, 2)
            }
            # VLAN Users
            network_state["vlan_users"] = {
                "VLAN 10 (Admin)": int(sim_clients * 0.1),
                "VLAN 20 (Administración)": int(sim_clients * 0.25),
                "VLAN 30 (Alumnos)": int(sim_clients * 0.45) if sim_scenario != "ddos_attack" else int(sim_clients * 0.75),
                "VLAN 40 (Invitados)": int(sim_clients * 0.2)
            }
            # AP details list
            network_state["ap_details"] = [
                {"name": "AP Laboratorio", "clients": int(sim_clients * 0.35), "channel": 6, "signal_dbm": -45 if sim_wifi > 70 else -75, "saturation": "Alta" if sim_clients > 60 else "Media"},
                {"name": "AP Administración", "clients": int(sim_clients * 0.25), "channel": 11, "signal_dbm": -50, "saturation": "Media"},
                {"name": "AP Biblioteca", "clients": int(sim_clients * 0.4) if sim_scenario != "mass_download" else int(sim_clients * 0.6), "channel": 1, "signal_dbm": -55 if sim_wifi > 60 else -82, "saturation": "Alta" if sim_scenario == "mass_download" else "Media"}
            ]
            # Calidad de internet
            sim_latency = int(12 + (100 - sim_wifi) * 0.6 + (sim_download * 0.25))
            network_state["internet_quality"] = {
                "latency": sim_latency,
                "jitter": int(1 + (sim_download * 0.15)),
                "packet_loss": round(0.001 + (100 - sim_wifi) * 0.0006, 5),
                "download_speed": 100.0,
                "upload_speed": 20.0,
                "dns_status": "Operativo" if sim_scenario != "ddos_attack" else "Falla Total"
            }
            network_state["gateway"]["latency_ms"] = sim_latency
            network_state["gateway"]["packet_loss"] = network_state["internet_quality"]["packet_loss"]
            # Guardar históricos generales
            history_traffic.append({"time": now_str, "download": sim_download, "upload": sim_upload})
            history_clients.append({"time": now_str, "count": sim_clients})
            history_wan_latency.append({"time": now_str, "value": sim_latency})
            history_wan_jitter.append({"time": now_str, "value": network_state["internet_quality"]["jitter"]})
            history_wan_packetloss.append({"time": now_str, "value": network_state["internet_quality"]["packet_loss"]})
            network_state["performance"]["realtime_traffic"]["download"].append(round(sim_download, 2))
            network_state["performance"]["realtime_traffic"]["upload"].append(round(sim_upload, 2))
            if len(network_state["performance"]["realtime_traffic"]["download"]) > 50:
                network_state["performance"]["realtime_traffic"]["download"].pop(0)
                network_state["performance"]["realtime_traffic"]["upload"].pop(0)
            # Actualizar históricos de tendencia
            trend_download.append(sim_download)
            trend_upload.append(sim_upload)
            trend_ram.append(float(sim_ram))
            trend_temp.append(float(sim_temp))
            trend_wifi.append(float(sim_wifi))
            # 3. Invocar al Motor Predictivo
            preds = analizador.analizar_predictivo(
                network_state,
                list(trend_download),
                list(trend_upload),
                list(trend_ram),
                list(trend_temp),
                list(trend_wifi)
            )
            
            # Asignar variable de auto-mitigación al estado de predicciones
            preds["auto_mitigation_active"] = auto_mitigation_active
            network_state["predictions"] = preds
            # 4. Generar Alertas Predictivas y enviar notificaciones por correo
            current_predictive_alerts = []
            for idx, anomaly in enumerate(preds["anomalies"]):
                alert_item = {
                    "id": f"pred_{now_str}_{idx}",
                    "title": f"Proyección: {anomaly['metric']}",
                    "detail": anomaly["detail"],
                    "category": "Predicción IA",
                    "severity": "predictive" if anomaly["severity"] == "warning" else "critical",
                    "timestamp": now_str,
                    "source": "Motor IA Predictivo"
                }
                current_predictive_alerts.append(alert_item)
                
                # Auto-notificar alertas de predicciones por email
                if notifier:
                    asyncio.create_task(notifier.send_alert(alert_item))
            network_state["alerts"] = [a for a in network_state["alerts"] if a["category"] != "Predicción IA"]
            network_state["alerts"] = (current_predictive_alerts + network_state["alerts"])[:50]
            # 5. 🤖 AUTO-MITIGACIÓN PREDICTIVA IA (AUTO-HEALING EN SIMULACIÓN)
            if auto_mitigation_active:
                # 5.1 Fuga de Memoria
                if (preds["time_to_ram_exhaustion_sec"] > 0 and preds["time_to_ram_exhaustion_sec"] < 40) or sim_ram > 80.0:
                    sim_ram = 48.0
                    if sim_scenario == "memory_leak":
                        sim_scenario = "normal"
                    network_state["devices"]["switch_l3"]["status"] = "Connected"
                    msg = "IA Auto-Healing: Reinicio preventivo y vaciado de memoria RAM ejecutado en Switch L3 tras proyección de colapso."
                    await add_alert_and_notify("Auto-Mitigación IA: RAM Switch L3", msg, "Mitigación IA", "predictive", "Motor IA Predictivo")
                    log.info(f"🤖 AUTO-HEALING: {msg}")
                    
                # 5.2 Sobretemperatura
                elif (preds["time_to_overheat_sec"] > 0 and preds["time_to_overheat_sec"] < 40) or sim_temp > 76.0:
                    sim_temp = 42.5
                    sim_cpu = 35.0
                    if sim_scenario == "overheating":
                        sim_scenario = "normal"
                    msg = "IA Auto-Healing: Activada ventilación de emergencia perimetral para enfriar el procesador del Router ER605."
                    await add_alert_and_notify("Auto-Mitigación IA: Térmica Router", msg, "Mitigación IA", "predictive", "Motor IA Predictivo")
                    log.info(f"🤖 AUTO-HEALING: {msg}")
                    
                # 5.3 Congestión WAN
                elif preds["congestion_probability"] > 70 and not sim_qos_active:
                    sim_qos_active = True
                    msg = "IA Auto-Healing: Aplicada regla de QoS dinámico en VLAN 30 para reducir tráfico de bajada masivo."
                    await add_alert_and_notify("Auto-Mitigación IA: Ancho de Banda", msg, "Mitigación IA", "predictive", "Motor IA Predictivo")
                    log.info(f"🤖 AUTO-HEALING: {msg}")
                    
                # 5.4 Interferencia WiFi
                elif preds["wifi_degradation_risk"] == "Alto" and sim_scenario == "wifi_interference":
                    sim_wifi = 88.0
                    sim_scenario = "normal"
                    msg = "IA Auto-Healing: AP Biblioteca reasignado adaptativamente al canal 6 para mitigar ruido electromagnético."
                    await add_alert_and_notify("Auto-Mitigación IA: Señal WiFi", msg, "Mitigación IA", "predictive", "Motor IA Predictivo")
                    log.info(f"🤖 AUTO-HEALING: {msg}")
                    
                # 5.5 DDoS Attack
                elif sim_scenario == "ddos_attack" and sim_threats > 0:
                    sim_threats = 0
                    sim_clients = 52
                    sim_cpu = 30.0
                    sim_download = 25.0
                    sim_scenario = "normal"
                    network_state["network"]["internet"] = "Connected"
                    network_state["gateway"]["wan_status"] = "UP"
                    msg = "IA Auto-Healing: Reglas dinámicas de ACL cargadas en Firewall. Bloqueadas direcciones IP del ataque DDoS."
                    await add_alert_and_notify("Auto-Mitigación IA: Seguridad DDoS", msg, "Mitigación IA", "predictive", "Motor IA Predictivo")
                    log.info(f"🤖 AUTO-HEALING: {msg}")
            # Logs de seguridad
            if sim_scenario == "ddos_attack" and sim_ticks % 3 == 0:
                network_state["security_logs"].insert(0, {
                    "timestamp": now_str,
                    "event": "SYN Flood Blocked",
                    "details": f"Bloqueados 14,200 paquetes SYN desde IP 198.51.100.{random.randint(10,250)}",
                    "level": "error"
                })
                network_state["security_logs"] = network_state["security_logs"][:100]
            # Broadcast por WS
            await manager.broadcast(network_state)
            log.info(f"[SIMULADOR] Ciclo ejecutado. Auto-Mitigación: {auto_mitigation_active}. Escenario: {sim_scenario}.")
        except Exception as e:
            log.error(f"Error en bucle de simulación: {e}", exc_info=True)
        await asyncio.sleep(5)
# -------------------------------------------------------------------------
# Evento startup: Lanzar bucles y fallbacks
# -------------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    if SIMULATE or not OMADA_BASE_URL:
        log.info("Iniciando directamente en MODO SIMULACIÓN de red.")
        asyncio.create_task(simulated_data_loop())
    else:
        log.info("Intentando iniciar con CONEXIÓN REAL a TP-Link Omada...")
        asyncio.create_task(real_data_loop())
# -------------------------------------------------------------------------
# Endpoints REST del Dashboard
# -------------------------------------------------------------------------
@app.get("/health")
def health_check():
    return {"status": "healthy", "server_time": datetime.now().isoformat(), "scenario": sim_scenario}
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
    return {
        "recommendations": network_state["predictions"]["recommendations"],
        "timestamp": network_state["timestamp"]
    }
# --- CONTROL DEL AUTO-HEALING (AUTO-MITIGACIÓN) ---
@app.get("/api/simulation/automitigation")
def get_automitigation():
    return {"active": auto_mitigation_active}
class AutoMitigationRequest(BaseModel):
    active: bool
@app.post("/api/simulation/automitigation")
def set_automitigation(req: AutoMitigationRequest):
    global auto_mitigation_active
    auto_mitigation_active = req.active
    log.info(f"SIMULACIÓN: Auto-mitigación IA cambiada manualmente a: {auto_mitigation_active}")
    return {"status": "success", "active": auto_mitigation_active}
# --- CONTROL DEL SIMULADOR DE INCIDENTES ---
class ScenarioRequest(BaseModel):
    scenario: str
class ActionRequest(BaseModel):
    action: str
@app.post("/api/simulation/scenario")
async def set_simulation_scenario(req: ScenarioRequest):
    global sim_scenario, sim_ticks, sim_qos_active
    global sim_cpu, sim_ram, sim_temp, sim_wifi, sim_clients, sim_download, sim_upload, sim_threats
    
    valid_scenarios = ["normal", "mass_download", "memory_leak", "overheating", "wifi_interference", "ddos_attack"]
    if req.scenario not in valid_scenarios:
        return {"error": f"Escenario no válido. Debe ser uno de: {valid_scenarios}"}
        
    sim_scenario = req.scenario
    sim_ticks = 0
    sim_qos_active = False
    
    # Restablecer algunos estados para respuestas rápidas
    if sim_scenario == "normal":
        network_state["gateway"]["wan_status"] = "UP"
        network_state["network"]["internet"] = "Connected"
        network_state["devices"]["switch_l3"]["status"] = "Connected"
    elif sim_scenario == "ddos_attack":
        sim_threats = 5
        sim_clients = 85
        
    log.info(f"SIMULACIÓN: Escenario cambiado manualmente a: '{sim_scenario}'")
    
    # Notificar inyección de escenario por email
    await add_alert_and_notify(
        f"Simulador: Escenario Inyectado",
        f"Se ha inyectado el escenario de pruebas: '{sim_scenario.upper()}' en la red.",
        "Simulador",
        "warning",
        "Consola de Control"
    )
    
    return {"status": "success", "active_scenario": sim_scenario}
@app.post("/api/simulation/action")
async def trigger_simulation_action(req: ActionRequest):
    global sim_scenario, sim_qos_active, sim_ram, sim_temp, sim_wifi, sim_cpu, sim_download, sim_threats, sim_clients
    action = req.action
    msg = ""
    
    if action == "reset_switch":
        sim_ram = 48.0
        if sim_scenario == "memory_leak":
            sim_scenario = "normal"
        msg = "Comando manual ejecutado: Switch L3 reiniciado y memoria vaciada preventivamente."
        network_state["devices"]["switch_l3"]["status"] = "Connected"
        
    elif action == "apply_qos":
        sim_qos_active = True
        msg = "QoS manual activado: Aplicado límite de 10 Mbps a VLAN 30 (Alumnos)."
        
    elif action == "reset_overheat":
        sim_temp = 42.5
        sim_cpu = 35.0
        if sim_scenario == "overheating":
            sim_scenario = "normal"
        msg = "Comando manual ejecutado: Sistema de refrigeración forzada encendido. Router enfriado a 42.5°C."
        
    elif action == "change_channel":
        sim_wifi = 88.0
        if sim_scenario == "wifi_interference":
            sim_scenario = "normal"
        msg = "Comando manual ejecutado: AP Biblioteca movido dinámicamente al canal 6 (Canal libre de ruido)."
        
    elif action == "block_ddos":
        sim_threats = 0
        sim_clients = 52
        sim_cpu = 30.0
        sim_download = 25.0
        if sim_scenario == "ddos_attack":
            sim_scenario = "normal"
        network_state["network"]["internet"] = "Connected"
        network_state["gateway"]["wan_status"] = "UP"
        msg = "Comando manual ejecutado: Reglas del Firewall actualizadas. Bloqueados rangos de IP atacantes."
        
    elif action == "reset_all":
        sim_scenario = "normal"
        sim_qos_active = False
        sim_ram = 48.0
        sim_temp = 42.5
        sim_wifi = 88.0
        sim_cpu = 32.0
        sim_clients = 52
        sim_download = 25.0
        sim_threats = 0
        network_state["network"]["internet"] = "Connected"
        network_state["gateway"]["wan_status"] = "UP"
        network_state["devices"]["switch_l3"]["status"] = "Connected"
        network_state["alerts"] = [a for a in network_state["alerts"] if a["category"] != "Predicción IA"]
        msg = "Mitigación ejecutada: Estado general del sistema restablecido a Operación Estable."
    else:
        return {"error": f"Acción '{action}' no reconocida."}
        
    # Crear alerta informativa y enviar notificación
    await add_alert_and_notify("Mitigación Manual", msg, "Mitigación", "info", "Consola del Administrador")
    
    log.info(f"SIMULACIÓN: Acción ejecutada: '{action}' -> {msg}")
    return {"status": "success", "message": msg, "active_scenario": sim_scenario}
# -------------------------------------------------------------------------
# Asistente IA (Gemini con contexto de red)
# -------------------------------------------------------------------------
class ChatRequest(BaseModel):
    pregunta: str
@app.post("/api/chat")
async def chat_asistente_ia(request: ChatRequest):
    pregunta_usuario = request.pregunta
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    infraestructura_status = (
        f"Modo: {'Simulación' if not OMADA_BASE_URL or SIMULATE else 'Producción Omada'}. "
        f"Escenario actual: {sim_scenario if SIMULATE or not OMADA_BASE_URL else 'Operación real'}. "
        f"Dispositivos: Router CPU {network_state['gateway']['cpu']}%, temp {network_state['devices']['router']['temp']}°C. "
        f"Switch L3 RAM: {network_state['devices']['switch_l3']['ram']}%. "
        f"WiFi: {network_state['performance']['wifi_quality']}%. "
        f"WAN: {network_state['gateway']['wan_status']} (latencia {network_state['gateway']['latency_ms']}ms). "
        f"Portal: {network_state['captive_portal']['active_users']} usuarios activos. "
        f"Auto-Mitigación activa: {auto_mitigation_active}. "
        f"Alertas de IA activas: {[a['detail'] for a in network_state['alerts'] if a['category']=='Predicción IA']}"
    )
    alertas_recientes = "\n".join(
        [f"- [{a['severity'].upper()}] {a['category']}: {a['title']} ({a['detail']})" for a in network_state["alerts"][:6]]
    ) or "Ninguna alerta activa en la red."
    if api_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            system_instruction = (
                "Eres un ingeniero experto en redes TP-Link Omada y análisis predictivo de infraestructuras de red. "
                "Tu objetivo es asistir al administrador del campus. Responde en español de manera concisa y profesional. "
                f"Estado actual de la red:\n{infraestructura_status}\n\nAlertas de Incidentes:\n{alertas_recientes}"
            )
            payload = {
                "contents": [
                    {"role": "user", "parts": [{"text": system_instruction}]},
                    {"role": "user", "parts": [{"text": pregunta_usuario}]}
                ]
            }
            async with httpx.AsyncClient() as client:
                res = await client.post(url, json=payload, timeout=20)
                if res.status_code == 200:
                    data = res.json()
                    respuesta = data["candidates"][0]["content"]["parts"][0]["text"]
                    return {"response": respuesta, "engine": "Gemini 1.5 Flash"}
        except Exception as e:
            log.error(f"Error con Gemini API: {e}")
    # Fallback local detallado según el estado de la red
    if sim_scenario == "memory_leak":
        desc = (
            "### Diagnóstico del Asistente de Red\n\n"
            "⚠️ **Fuga de Memoria Detectada en Switch L3**.\n\n"
            "El análisis de tendencia de los últimos ticks indica un crecimiento lineal de la RAM en el Switch Core. "
            "Si la RAM cruza el 95%, el Switch colapsará desconectando toda la red.\n\n"
            "**Recomendación**: " + ("La Auto-Mitigación por IA está activa y resolverá esto automáticamente." if auto_mitigation_active else "Haga clic en 'Ejecutar Reinicio Preventivo' en la pestaña predictiva o active la Auto-Mitigación.")
        )
    elif sim_scenario == "mass_download":
        desc = (
            "### Diagnóstico del Asistente de Red\n\n"
            "⚠️ **Saturación de Ancho de Banda WAN**.\n\n"
            "Se detecta tráfico inusualmente alto en la VLAN de Alumnos. La velocidad de descarga está rozando el límite de 100 Mbps del canal. "
            "Esto aumentará la latencia para la VLAN de Administración.\n\n"
            "**Recomendación**: " + ("La Auto-Mitigación por IA está activa y limitará a los estudiantes automáticamente." if auto_mitigation_active else "Active la regla de 'Mitigación QoS' en la barra lateral.")
        )
    elif sim_scenario == "overheating":
        desc = (
            "### Diagnóstico del Asistente de Red\n\n"
            "🔥 **Peligro Térmico en Router ER605**.\n\n"
            "La CPU se encuentra al 92% de uso constante y la temperatura está subiendo rápidamente. "
            "Si alcanza 88°C, el puerto WAN se desactivará preventivamente.\n\n"
            "**Recomendación**: " + ("La Auto-Mitigación por IA está activa y encenderá la ventilación." if auto_mitigation_active else "Haga clic en 'Enfriar Router' en la barra lateral.")
        )
    elif sim_scenario == "wifi_interference":
        desc = (
            "### Diagnóstico del Asistente de Red\n\n"
            "📡 **Interferencia Electromagnética en AP Biblioteca**.\n\n"
            "La calidad WiFi ha caído drásticamente por saturación del canal 11.\n\n"
            "**Recomendación**: " + ("La IA auto-mitigará cambiando de canal de manera autónoma." if auto_mitigation_active else "Cambie el canal al canal 6 de forma adaptativa desde la barra lateral.")
        )
    elif sim_scenario == "ddos_attack":
        desc = (
            "### Diagnóstico del Asistente de Red\n\n"
            "🛡️ **Alerta de Seguridad: Ataque DDoS Activo**.\n\n"
            "El firewall reporta una inundación inusual de paquetes SYN que saturan el enrutamiento. "
            "La conexión a Internet está inestable o caída.\n\n"
            "**Recomendación**: " + ("La IA está bloqueando los rangos de IPs atacantes de forma autónoma." if auto_mitigation_active else "Haga clic en 'Bloquear Atacantes' en la barra lateral.")
        )
    else:
        desc = (
            "### Diagnóstico del Asistente de Red\n\n"
            "🟢 **La red opera de forma óptima**.\n\n"
            "No se registran amenazas activas, fugas de memoria ni degradación en la señal WiFi. "
            "El canal de descarga dispone de capacidad libre. La latencia se mantiene estable en 15 ms."
        )
    return {"response": desc, "engine": "Omada IA Engine (Local)"}
# -------------------------------------------------------------------------
# WEBSOCKET (Comunicación en tiempo real)
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