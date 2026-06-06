import asyncio
import logging
import os
import random
import time
from datetime import datetime
from typing import Any, Dict, List, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from dotenv import load_dotenv

# Cargar variables de entorno del archivo .env
load_dotenv()

# Importar el gestor de notificaciones
from notification import NotificationManager

# Configuración de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("omada-server")

app = FastAPI(title="Omada MCP Backend", version="1.0.0")

# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar notificador de correo
notifier = NotificationManager()

# -------------------------------------------------------------------------
# 🌐 CLIENTE DE CONEXIÓN REAL A OMADA OPENAPI
# -------------------------------------------------------------------------
class OmadaRealClient:
    def __init__(self):
        self.base_url = os.getenv("OMADA_BASE_URL", "").strip()
        self.client_id = os.getenv("OMADA_CLIENT_ID", "").strip()
        self.client_secret = os.getenv("OMADA_CLIENT_SECRET", "").strip()
        self.omadac_id = os.getenv("OMADA_OMADAC_ID", "").strip()
        self.site_id = os.getenv("OMADA_SITE_ID", "").strip()
        self.strict_ssl = os.getenv("OMADA_STRICT_SSL", "true").lower() in ("1", "true", "yes")
        
        self.access_token = None
        self.token_expiry = 0
        
        # Habilitar conexión si los parámetros básicos existen
        self.enabled = bool(self.base_url and self.client_id and self.client_secret and self.omadac_id)
        
        # Desactivar advertencias de SSL si se opta por omitir validaciones (certificados autofirmados)
        if not self.strict_ssl:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
    async def get_valid_token(self) -> str:
        """Autentica y obtiene el token de acceso, renovándolo si expiró."""
        if self.access_token and time.time() < self.token_expiry:
            return self.access_token

        url = f"{self.base_url}/openapi/authorize/token"
        params = {"grant_type": "client_credentials"}
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "omadacId": self.omadac_id
        }
        
        verify = self.strict_ssl
        async with httpx.AsyncClient(verify=verify) as client:
            res = await client.post(url, json=payload, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data.get("errorCode") == 0:
                    result = data.get("result", {})
                    self.access_token = result.get("accessToken")
                    # Restar un margen de seguridad de 30s al tiempo de expiración
                    expires_in = result.get("expiresIn", 3600)
                    self.token_expiry = time.time() + expires_in - 30
                    log.info("🔐 Autenticado exitosamente con el Controlador Omada.")
                    return self.access_token
                else:
                    raise Exception(f"Error Omada API: {data.get('msg')}")
            else:
                raise Exception(f"HTTP Error {res.status_code}: {res.text}")

    async def get_devices(self, token: str) -> List[Dict[str, Any]]:
        """Obtiene la lista de routers, switches y APs del controlador."""
        url = f"{self.base_url}/openapi/v1/sites/{self.site_id}/devices"
        headers = {"Authorization": f"AccessToken={token}"}
        
        verify = self.strict_ssl
        async with httpx.AsyncClient(verify=verify) as client:
            res = await client.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data.get("errorCode") == 0:
                    return data.get("result", {}).get("data", [])
            return []

    async def get_clients(self, token: str) -> List[Dict[str, Any]]:
        """Obtiene la lista de clientes activos conectados a la red."""
        url = f"{self.base_url}/openapi/v1/sites/{self.site_id}/clients"
        headers = {"Authorization": f"AccessToken={token}"}
        
        verify = self.strict_ssl
        async with httpx.AsyncClient(verify=verify) as client:
            res = await client.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data.get("errorCode") == 0:
                    return data.get("result", {}).get("data", [])
            return []

    async def get_logs(self, token: str) -> List[Dict[str, Any]]:
        """Obtiene los logs y eventos de seguridad recientes del controlador."""
        url = f"{self.base_url}/openapi/v1/sites/{self.site_id}/logs"
        headers = {"Authorization": f"AccessToken={token}"}
        
        verify = self.strict_ssl
        async with httpx.AsyncClient(verify=verify) as client:
            res = await client.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data.get("errorCode") == 0:
                    return data.get("result", {}).get("data", [])
            return []

# Inicializar cliente de Omada real
omada_real = OmadaRealClient()

# -------------------------------------------------------------------------
# 📊 ESTADO ESTRUCTURADO DE LA RED
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
        "cpu": 25,
        "memory": 45,
        "wan_status": "UP",
        "latency_ms": 12,
        "packet_loss": 0.05
    },
    "devices": {
        "router": {"status": "Connected", "temp": 42.0, "cpu": 15, "ram": 42},
        "switch_l3": {"status": "Connected", "temp": 38.5, "cpu": 22, "ram": 55},
        "switch_l2": {"status": "Connected", "temp": 34.0, "cpu": 8, "ram": 30},
        "ap_laboratorio": {"status": "Connected", "temp": 39.0, "clients": 24},
        "ap_docentes": {"status": "Connected", "temp": 36.5, "clients": 13},
        "ap_invitados": {"status": "Connected", "temp": 35.0, "clients": 15}
    },
    "performance": {
        "wifi_quality": 88,
        "bandwidth_capacity_mbps": 100,
        "realtime_traffic": {"download": [], "upload": []},
        "vlan_consumption": {
            "VLAN 10 (Admin)": 12.5,
            "VLAN 20 (Docentes)": 8.2,
            "VLAN 30 (Alumnos)": 45.0,
            "VLAN 40 (Invitados)": 15.4
        }
    },
    "captive_portal": {
        "active_users": 52,
        "roles_breakdown": {
            "Alumnos": 30,
            "Docentes": 13,
            "Invitados": 9
        },
        "radius_status": "Connected",
        "vouchers_remaining": 120
    },
    "ai": {
        "fail_prob": 12,
        "overheat_risk": "Bajo",
        "memory_leak_risk": "Bajo",
        "packet_loss_risk": "Bajo",
        "recommendations": "El sistema se encuentra operando bajo parámetros normales. No se requieren acciones."
    }
}

# Inicializar tráfico histórico
for _ in range(50):
    network_state["performance"]["realtime_traffic"]["download"].append(random.randint(60, 80))
    network_state["performance"]["realtime_traffic"]["upload"].append(random.randint(15, 25))

# Almacén de conexiones WebSocket activas
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
# 🧠 SIMULACIÓN ASÍNCRONA Y POLLEO REAL
# -------------------------------------------------------------------------
async def simular_red_loop():
    tick = 0
    wan_down_ticks = 0
    overheat_ticks = 0
    memory_leak_ticks = 0
    
    while True:
        try:
            tick += 1
            now = datetime.now()
            network_state["timestamp"] = now.strftime("%Y-%m-%d %H:%M:%S")
            
            # Intentar conexión real a Omada si está configurado en .env
            real_data_loaded = False
            if omada_real.enabled:
                try:
                    token = await omada_real.get_valid_token()
                    devices = await omada_real.get_devices(token)
                    clients = await omada_real.get_clients(token)
                    logs = await omada_real.get_logs(token)
                    
                    if devices:
                        real_data_loaded = True
                        network_state["network"]["devices_total"] = len(devices)
                        network_state["network"]["clients_total"] = len(clients)
                        network_state["captive_portal"]["active_users"] = len(clients)
                        
                        # Mapear dispositivos reales
                        router_found = False
                        switch_l3_found = False
                        ap_clients_count = 0
                        
                        for dev in devices:
                            dev_type = dev.get("type", "").lower()
                            dev_name = dev.get("name", "").lower()
                            dev_status = "Connected" if dev.get("status") == 1 else "Disconnected"
                            dev_cpu = dev.get("cpuUtil", 10)
                            dev_ram = dev.get("memUtil", 30)
                            # Nota: La temperatura depende de que el modelo físico lo exponga
                            dev_temp = dev.get("temperature", 38.0) 
                            
                            if "gateway" in dev_type or "router" in dev_name:
                                network_state["devices"]["router"] = {"status": dev_status, "temp": dev_temp, "cpu": dev_cpu, "ram": dev_ram}
                                network_state["gateway"]["cpu"] = dev_cpu
                                network_state["gateway"]["memory"] = dev_ram
                                router_found = True
                            elif "switch" in dev_type:
                                if "l3" in dev_name or "core" in dev_name or not switch_l3_found:
                                    network_state["devices"]["switch_l3"] = {"status": dev_status, "temp": dev_temp, "cpu": dev_cpu, "ram": dev_ram}
                                    switch_l3_found = True
                                else:
                                    network_state["devices"]["switch_l2"] = {"status": dev_status, "temp": dev_temp, "cpu": dev_cpu, "ram": dev_ram}
                            elif "ap" in dev_type or "eap" in dev_type:
                                ap_clients = dev.get("clientNum", 0)
                                ap_clients_count += ap_clients
                        
                        # Distribuir clientes en los APs simulados para visualización
                        network_state["devices"]["ap_laboratorio"]["clients"] = max(2, int(ap_clients_count * 0.45))
                        network_state["devices"]["ap_docentes"]["clients"] = max(1, int(ap_clients_count * 0.3))
                        network_state["devices"]["ap_invitados"]["clients"] = max(1, int(ap_clients_count * 0.25))

                    # Cargar logs reales si hay disponibles
                    if logs:
                        for l in logs[:5]:
                            # Estructurar al formato del Dashboard
                            real_alert = {
                                "category": "⚙️ Logs Omada",
                                "severity": "info" if l.get("level") == 1 else "warning",
                                "title": l.get("module", "Evento de Sistema"),
                                "detail": l.get("content", "Detalle del evento del sistema."),
                                "timestamp": l.get("time", network_state["timestamp"])
                            }
                            # Evitar duplicados rápidos
                            if not any(a["title"] == real_alert["title"] and a["detail"] == real_alert["detail"] for a in network_state["alerts"]):
                                network_state["alerts"].insert(0, real_alert)
                                
                    log.info("📊 Telemetría física y logs cargados de forma exitosa desde el Omada Controller.")
                except Exception as ex:
                    log.warning(f"⚠️ No se pudo obtener datos reales de Omada (Fallo: {ex}). Continuando en Fallback Simulado.")

            # --- Fallback Simulado (Ejecutado si no hay conexión real o para enriquecer métricas) ---
            # Tráfico en tiempo real (seno + ruido)
            dl_base = 65 + 15 * random.random()
            ul_base = 18 + 5 * random.random()
            
            # Si no cargó datos reales, hacer fluctuaciones completas
            if not real_data_loaded:
                network_state["performance"]["vlan_consumption"]["VLAN 30 (Alumnos)"] = round(40 + random.randint(-15, 25), 1)
                network_state["performance"]["vlan_consumption"]["VLAN 40 (Invitados)"] = round(12 + random.randint(-5, 8), 1)
                
                # A) Caída WAN simulada
                if network_state["gateway"]["wan_status"] == "DOWN":
                    wan_down_ticks += 1
                    if wan_down_ticks >= 6:
                        network_state["gateway"]["wan_status"] = "UP"
                        network_state["gateway"]["latency_ms"] = 12
                        network_state["gateway"]["packet_loss"] = 0.05
                        network_state["network"]["overview"] = "Estable"
                        wan_down_ticks = 0
                        alerta_res = {
                            "category": "🌐 Router Principal",
                            "severity": "info",
                            "title": "Conectividad WAN Restablecida",
                            "detail": "El enlace WAN principal ha vuelto a responder correctamente a las peticiones ICMP hacia los DNS de Google.",
                            "timestamp": network_state["timestamp"]
                        }
                        network_state["alerts"].insert(0, alerta_res)
                        await notifier.send_alert(alerta_res)
                    else:
                        dl_base = 0
                        ul_base = 0
                else:
                    if random.random() < 0.02:
                        network_state["gateway"]["wan_status"] = "DOWN"
                        network_state["gateway"]["latency_ms"] = 999
                        network_state["gateway"]["packet_loss"] = 1.00
                        network_state["network"]["overview"] = "Crítico"
                        alerta_wan = {
                            "category": "🌐 Router Principal",
                            "severity": "critical",
                            "title": "Pérdida de conectividad WAN (Internet Caído)",
                            "detail": "La interfaz WAN1 física se encuentra caída. Se detectó pérdida total de paquetes hacia los DNS de Google de forma continua.",
                            "timestamp": network_state["timestamp"]
                        }
                        network_state["alerts"].insert(0, alerta_wan)
                        await notifier.send_alert(alerta_wan)
            
            # B) Alertas de Seguridad & Portal Cautivo (Simuladas en background)
            # Brute Force en Administración
            if random.random() < 0.04:
                alerta_bf = {
                    "category": "🔑 Portal Cautivo",
                    "severity": "error",
                    "title": "Intento de Fuerza Bruta: Administración",
                    "detail": "Se detectaron 15 intentos fallidos de inicio de sesión con el usuario 'admin_net' en el portal cautivo desde la IP 192.168.40.88 (VLAN Invitados).",
                    "timestamp": network_state["timestamp"]
                }
                network_state["alerts"].insert(0, alerta_bf)
                await notifier.send_alert(alerta_bf)
                
            # Acceso Fuera de Horario
            if random.random() < 0.03:
                alerta_horario = {
                    "category": "🔑 Portal Cautivo",
                    "severity": "warning",
                    "title": "Acceso fuera de horario: VLAN Alumnos",
                    "detail": "Dispositivo con MAC CC:BB:AA:11:22:33 intentó autenticarse en el portal de Alumnos a las 23:14hs, infringiendo la política de desconexión nocturna.",
                    "timestamp": network_state["timestamp"]
                }
                network_state["alerts"].insert(0, alerta_horario)

            # MAC Spoofing
            if random.random() < 0.03:
                alerta_spoof = {
                    "category": "🔒 Seguridad",
                    "severity": "critical",
                    "title": "Posible Suplantación de MAC (MAC Spoofing)",
                    "detail": "Se detectó el registro de la dirección MAC 00:1A:2B:3C:4D:5E (perteneciente a un dispositivo administrativo de la VLAN 10) solicitando autenticación desde un Access Point asignado a la VLAN 40 (Invitados).",
                    "timestamp": network_state["timestamp"]
                }
                network_state["alerts"].insert(0, alerta_spoof)
                await notifier.send_alert(alerta_spoof)

            # VLAN Hopping
            if random.random() < 0.03:
                alerta_hopping = {
                    "category": "🛡️ VLAN Segmentación",
                    "severity": "critical",
                    "title": "Detección de Intento de Salto de VLAN (VLAN Hopping)",
                    "detail": "El Switch Capa 3 SG3428X descartó 180 paquetes con etiquetas 802.1Q duplicadas originadas en el puerto 14 (VLAN 30 Alumnos) con destino a la VLAN 10 (Administración).",
                    "timestamp": network_state["timestamp"]
                }
                network_state["alerts"].insert(0, alerta_hopping)
                await notifier.send_alert(alerta_hopping)

            # Evasión de QoS (VPN Bypass)
            if random.random() < 0.04:
                alerta_bypass = {
                    "category": "⚡ QoS Dinámico",
                    "severity": "warning",
                    "title": "Intento de Evasión de QoS Detectado",
                    "detail": "El cliente con IP 192.168.30.125 (VLAN Alumnos) está transmitiendo tráfico cifrado UDP masivo hacia el puerto 1194 (OpenVPN) para evadir las políticas del portal.",
                    "timestamp": network_state["timestamp"]
                }
                network_state["alerts"].insert(0, alerta_bypass)

            # QoS Hogging (Acaparamiento)
            if random.random() < 0.05:
                alerta_hogging = {
                    "category": "⚡ QoS Dinámico",
                    "severity": "info",
                    "title": "Priorización Activa: Reducción por Acaparamiento",
                    "detail": "La VLAN 30 (Alumnos) superó los 80 Mbps de consumo. El QoS dinámico redujo automáticamente la prioridad de esta VLAN y limitó su ancho de banda a 40 Mbps para proteger la navegación de Administración.",
                    "timestamp": network_state["timestamp"]
                }
                network_state["alerts"].insert(0, alerta_hogging)
                network_state["performance"]["vlan_consumption"]["VLAN 30 (Alumnos)"] = 40.0

            # C) Predicción Predictiva (Calentamiento Router)
            if not real_data_loaded:
                if random.random() < 0.03 or overheat_ticks > 0:
                    if overheat_ticks == 0:
                        overheat_ticks = 1
                    overheat_ticks += 1
                    network_state["devices"]["router"]["temp"] += 1.5
                    network_state["ai"]["overheat_risk"] = "Crítico"
                    network_state["ai"]["fail_prob"] = min(98, network_state["ai"]["fail_prob"] + 8)
                    
                    if network_state["devices"]["router"]["temp"] > 68.0:
                        alerta_pred_temp = {
                            "category": "🤖 Predicción IA",
                            "severity": "predictive",
                            "title": "Predicción de Apagado por Temperatura",
                            "detail": f"ALERTA TEMPRANA: La temperatura del Router ER605 sube a 1.5°C por minuto (actual: {round(network_state['devices']['router']['temp'], 1)}°C). Apagado por protección térmica estimado en las próximas 1.5 horas.",
                            "timestamp": network_state["timestamp"]
                        }
                        network_state["alerts"].insert(0, alerta_pred_temp)
                        await notifier.send_alert(alerta_pred_temp)
                        network_state["devices"]["router"]["temp"] = 42.0
                        network_state["ai"]["overheat_risk"] = "Bajo"
                        overheat_ticks = 0

            # Mantener histórico corto de alertas
            network_state["alerts"] = network_state["alerts"][:30]
            
            # Actualizar histórico de tráfico de red
            network_state["performance"]["realtime_traffic"]["download"].append(round(dl_base, 1))
            network_state["performance"]["realtime_traffic"]["upload"].append(round(ul_base, 1))
            
            network_state["performance"]["realtime_traffic"]["download"] = network_state["performance"]["realtime_traffic"]["download"][-50:]
            network_state["performance"]["realtime_traffic"]["upload"] = network_state["performance"]["realtime_traffic"]["upload"][-50:]
            
            # Actualizar resumen de recomendaciones
            active_alerts = network_state["alerts"]
            if active_alerts:
                highest_severity = "info"
                for a in active_alerts[:5]:
                    if a["severity"] == "critical":
                        highest_severity = "critical"
                        break
                    elif a["severity"] == "error":
                        highest_severity = "error"
                
                if highest_severity == "critical":
                    network_state["ai"]["fail_prob"] = random.randint(65, 95)
                    network_state["ai"]["recommendations"] = "CRÍTICO: Se han detectado fallos estructurales o alertas de intrusión (VLAN Hopping / Spoofing). Revisa la topología y las políticas ACL."
                elif highest_severity == "error":
                    network_state["ai"]["fail_prob"] = random.randint(35, 60)
                    network_state["ai"]["recommendations"] = "ADVERTENCIA: Intentos de intrusión o consumo inusual detectado. Recomendado revisar logs de accesos del portal cautivo."
                else:
                    network_state["ai"]["fail_prob"] = random.randint(10, 30)
                    network_state["ai"]["recommendations"] = "INFORMACIÓN: Eventos estándar registrados. Tránsito fluyendo adecuadamente."
            else:
                network_state["ai"]["fail_prob"] = 5
                network_state["ai"]["recommendations"] = "El sistema se encuentra operando bajo parámetros normales. No se requieren acciones."

            # Broadcast WebSocket
            await manager.broadcast(network_state)
            
        except Exception as e:
            log.error(f"Error en loop de simulación/polleo: {e}")
            
        await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(simular_red_loop())

# -------------------------------------------------------------------------
# 🚪 ENDPOINTS REST BASICOS
# -------------------------------------------------------------------------
@app.get("/health")
def health_check():
    return {"status": "healthy", "server_time": datetime.now().isoformat()}

@app.get("/api/state")
def get_state():
    return network_state

# -------------------------------------------------------------------------
# 🤖 ASISTENTE DE IA DE INFRAESTRUCTURA (Gemini API)
# -------------------------------------------------------------------------
class ChatRequest(BaseModel):
    pregunta: str

@app.post("/api/chat")
async def chat_asistente_ia(request: ChatRequest):
    pregunta_usuario = request.pregunta
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    
    infraestructura_status = (
        f"Dispositivos: Router ER605 ({network_state['devices']['router']['status']}, Temp: {network_state['devices']['router']['temp']}°C), "
        f"Switch L3 SG3428X ({network_state['devices']['switch_l3']['status']}, Temp: {network_state['devices']['switch_l3']['temp']}°C), "
        f"Switch L2 ({network_state['devices']['switch_l2']['status']}, Temp: {network_state['devices']['switch_l2']['temp']}°C).\n"
        f"Conectividad WAN: {network_state['gateway']['wan_status']} (Latencia: {network_state['gateway']['latency_ms']}ms, Pérdida: {round(network_state['gateway']['packet_loss']*100, 2)}%).\n"
        f"Portal Cautivo: {network_state['captive_portal']['active_users']} usuarios activos (Alumnos: {network_state['captive_portal']['roles_breakdown']['Alumnos']}, "
        f"Docentes: {network_state['captive_portal']['roles_breakdown']['Docentes']}, Invitados: {network_state['captive_portal']['roles_breakdown']['Invitados']}), "
        f"Servidor RADIUS: {network_state['captive_portal']['radius_status']}, Vouchers restantes: {network_state['captive_portal']['vouchers_remaining']}.\n"
        f"Tráfico por VLAN: Alumnos {network_state['performance']['vlan_consumption']['VLAN 30 (Alumnos)']} Mbps (límite 100 Mbps), "
        f"Invitados {network_state['performance']['vlan_consumption']['VLAN 40 (Invitados)']} Mbps.\n"
        f"Riesgos IA: Sobrecalentamiento Router: {network_state['ai']['overheat_risk']}, Fuga Memoria Switch L3: {network_state['ai']['memory_leak_risk']}, Probabilidad de Fallo: {network_state['ai']['fail_prob']}%."
    )
    
    alertas_recientes = "\n".join(
        [f"- [{a['severity'].upper()}] {a['category']}: {a['title']} - {a['detail']}" for a in network_state["alerts"][:6]]
    )
    if not alertas_recientes:
        alertas_recientes = "Ninguna alerta activa registrada en este momento."

    system_prompt = (
        "Eres un Ingeniero de Redes Senior (CCIE / Omada Certified Specialist) a cargo del mantenimiento de una red corporativa e institucional escolar. "
        "Se te presentará una consulta del usuario y el estado estructurado actual de la red. "
        "Debes responder analizando críticamente el estado y proporcionando diagnósticos técnicos rigurosos pero comprensibles, además de pasos para mitigar los problemas activos.\n\n"
        "DIRECTRICES:\n"
        "1. Prioriza las alertas críticas (ej. intentos de VLAN Hopping, caídas de la WAN, MAC Spoofing, o sobrecalentamiento).\n"
        "2. Si la pregunta es sobre la lentitud de la VLAN de Alumnos, analiza el tráfico de la VLAN 30, si el QoS dinámico está limitando su prioridad (hogging), o si hay sospechas de evasión (VPN Bypass).\n"
        "3. Usa markdown profesional con listas, negritas y bloques de código de ser necesario.\n"
        "4. Responde en español.\n\n"
        f"ESTADO ACTUAL DE LA RED:\n{infraestructura_status}\n\n"
        f"ALERTAS RECIENTES:\n{alertas_recientes}\n"
    )

    if api_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": system_prompt},
                            {"text": f"Pregunta del Administrador: {pregunta_usuario}"}
                        ]
                    }
                ]
            }
            
            async with httpx.AsyncClient() as client:
                res = await client.post(url, json=payload, headers=headers, timeout=20)
                if res.status_code == 200:
                    data = res.json()
                    respuesta_ia = data["candidates"][0]["content"]["parts"][0]["text"]
                    return {"response": respuesta_ia, "engine": "Gemini 1.5 Flash (Real)"}
                else:
                    log.error(f"Error de API de Gemini (HTTP {res.status_code}): {res.text}")
        except Exception as e:
            log.error(f"Fallo al conectar con la API de Gemini: {e}")

    # Fallback determinista local inteligente
    log.info("Ejecutando diagnóstico local de IA (Fallback Engine)")
    pregunta_lower = pregunta_usuario.lower()
    
    if "alumno" in pregunta_lower or "lenta" in pregunta_lower or "vlan 30" in pregunta_lower:
        con_hogging = any("Hogging" in a["title"] for a in network_state["alerts"])
        con_bypass = any("Evasión" in a["title"] for a in network_state["alerts"])
        
        if con_hogging:
            respuesta_fallback = (
                "### 🤖 Diagnóstico del Ingeniero de Redes (Simulación Local IA)\n\n"
                "La **VLAN 30 (Alumnos) está experimentando restricciones de velocidad** en este momento porque ha superado el umbral de consumo de 80 Mbps. "
                "El **QoS Dinámico** se ha activado de forma automática (evento *Priorización Activa*), limitando el ancho de banda temporalmente a **40 Mbps** "
                "para garantizar que la VLAN 10 (Administración) tenga recursos suficientes para la operación escolar.\n\n"
                "**Recomendaciones:**\n"
                "1. **Mantener la calma:** El QoS dinámico está haciendo su trabajo de forma correcta.\n"
                "2. **Aumentar la cola:** Si es necesario, desde el controlador Omada puedes subir el límite de la cola de Alumnos de 40 Mbps a 60 Mbps temporalmente.\n"
                "3. **Monitorear descargas:** Revisa si hay descargas P2P activas en esa VLAN."
            )
        elif con_bypass:
            respuesta_fallback = (
                "### 🤖 Diagnóstico del Ingeniero de Redes (Simulación Local IA)\n\n"
                "He detectado un **intento de evasión de QoS** en la VLAN 30 (Alumnos) desde la IP `192.168.30.125`. "
                "Este usuario está intentando realizar una conexión VPN cifrada (OpenVPN / puerto 1194) para bypassear el límite del portal cautivo. "
                "Esto genera tráfico masivo UDP que está ralentizando la red inalámbrica para el resto de los alumnos.\n\n"
                "**Acciones de mitigación recomendadas:**\n"
                "1. **Bloqueo de puerto:** Configura una regla de ACL en el Switch Capa 3 o Router Omada para denegar el tráfico UDP al puerto 1194 en la VLAN de Alumnos.\n"
                "2. **Bloqueo del cliente:** Desconecta o pon en lista negra al host con IP `192.168.30.125` desde la consola Omada."
            )
        else:
            respuesta_fallback = (
                "### 🤖 Diagnóstico del Ingeniero de Redes (Simulación Local IA)\n\n"
                f"La VLAN de Alumnos está consumiendo actualmente **{network_state['performance']['vlan_consumption']['VLAN 30 (Alumnos)']} Mbps**.\n"
                "No hay alertas críticas de QoS ni evasión en este instante, pero la calidad promedio del Wi-Fi es de "
                f"{network_state['performance']['wifi_quality']}%. Recomiendo realizar un análisis de espectro en el AP del Laboratorio "
                "para descartar interferencias en canales de 2.4 GHz."
            )
            
    elif "como esta" in pregunta_lower or "estado" in pregunta_lower or "red hoy" in pregunta_lower:
        alertas_criticas = [a for a in network_state["alerts"] if a["severity"] in ("critical", "error")]
        if alertas_criticas:
            detalle_alertas = "\n".join([f"- **{a['category']}**: {a['title']} ({a['detail']})" for a in alertas_criticas[:3]])
            respuesta_fallback = (
                "### 🤖 Diagnóstico del Ingeniero de Redes (Simulación Local IA)\n\n"
                "La red está operando con **riesgo elevado**. He detectado incidentes que requieren tu atención:\n\n"
                f"{detalle_alertas}\n\n"
                "**Recomendación de prioridad:**\n"
                "Atiende primero las alertas críticas marcadas en rojo (ej. intentos de VLAN Hopping o suplantación de MAC) ya que "
                "pueden comprometer la seguridad de la red de administración y del clúster de servidores Blockchain."
            )
        else:
            respuesta_fallback = (
                "### 🤖 Diagnóstico del Ingeniero de Redes (Simulación Local IA)\n\n"
                "¡Buenas noticias! **La red se encuentra estable y saludable en este momento.**\n"
                "- **Dispositivos:** Todos los switches, router y APs están conectados (temperaturas promedio de 37°C).\n"
                "- **Enlaces WAN:** Enlace principal activo con latencia de 12ms (pérdida de paquetes de 0.05%).\n"
                "- **Portal Cautivo:** Operando con normalidad. Servidor RADIUS activo.\n\n"
                "Sigue monitoreando de forma habitual."
            )
            
    elif "temperatura" in pregunta_lower or "caliente" in pregunta_lower:
        temp_r = network_state["devices"]["router"]["temp"]
        if temp_r > 60.0:
            respuesta_fallback = (
                "### 🤖 Diagnóstico del Ingeniero de Redes (Simulación Local IA)\n\n"
                f"⚠️ **ALERTA DE SOBRECALENTAMIENTO:** El Router ER605 se encuentra a **{round(temp_r, 1)}°C** (lo normal es <50°C). "
                "El algoritmo predictivo estima un apagado del sistema de borde en poco tiempo por protección térmica si la temperatura sigue subiendo.\n\n"
                "**Acción correctiva urgente:**\n"
                "1. Verifica físicamente la ventilación en el rack o gabinete del router.\n"
                "2. Asegúrate de que los ventiladores extractores del rack estén funcionando."
            )
        else:
            respuesta_fallback = (
                "### 🤖 Diagnóstico del Ingeniero de Redes (Simulación Local IA)\n\n"
                "Las temperaturas de los dispositivos están dentro de rangos normales:\n"
                f"- **Router Principal ER605:** {round(temp_r, 1)}°C (Estable)\n"
                f"- **Switch L3 SG3428X:** {network_state['devices']['switch_l3']['temp']}°C (Estable)\n"
                f"- **Switch L2 Acceso:** {network_state['devices']['switch_l2']['temp']}°C (Estable)\n"
                "No hay anomalías térmicas en los racks de comunicación."
            )
    else:
        respuesta_fallback = (
            "### 🤖 Diagnóstico del Ingeniero de Redes (Simulación Local IA)\n\n"
            "Entendido. He analizado las métricas generales del controlador Omada:\n"
            f"- **CPU General del Router:** {network_state['gateway']['cpu']}%\n"
            f"- **Clientes de Red Activos:** {network_state['network']['clients_total']} dispositivos conectados.\n"
            "Indícame si tienes alguna duda específica sobre la segmentación de VLANs, la configuración del portal cautivo o el clúster de blockchain."
        )

    return {"response": respuesta_fallback, "engine": "Omada IA Engine (Mock Fallback)"}

@app.websocket("/ws/alertas")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        log.error(f"Error en conexión WebSocket: {e}")
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)