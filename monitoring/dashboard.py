import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import httpx
import time
from datetime import datetime
# =========================================================================
# 🎨 DISEÑO ESTÉTICO Y CONFIGURACIÓN PREMIUM DE LA PÁGINA (Cyber-Glassmorphism)
# =========================================================================
st.set_page_config(
    page_title="Omada MCP — Centro de Control Inteligente",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)
# Estilos CSS inyectados para una apariencia súper premium y futurista
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Fondo con gradiente profundo y animado */
    .stApp {
        background: radial-gradient(circle at 50% 50%, #0d1527 0%, #060911 100%) !important;
        color: #f8fafc !important;
    }
    
    /* Pestañas (Tabs) personalizadas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background-color: rgba(10, 15, 30, 0.7);
        padding: 8px;
        border-radius: 16px;
        border: 1px solid rgba(0, 242, 254, 0.1);
        backdrop-filter: blur(10px);
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        background-color: transparent;
        border-radius: 10px;
        color: #94a3b8;
        font-weight: 600;
        font-size: 1.0rem;
        border: none;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        padding: 0px 18px;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        color: #00f2fe;
        background-color: rgba(0, 242, 254, 0.05);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%) !important;
        color: #0f172a !important;
        box-shadow: 0 0 15px rgba(0, 242, 254, 0.35);
        font-weight: 700 !important;
    }
    /* Tarjetas Glassmorphism cibernéticas */
    .cyber-card {
        background: rgba(10, 18, 36, 0.45);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(0, 242, 254, 0.15);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
    }
    
    .cyber-card:hover {
        border-color: rgba(0, 242, 254, 0.45);
        box-shadow: 0 15px 35px rgba(0, 242, 254, 0.12);
        transform: translateY(-3px);
    }
    
    .cyber-header {
        font-size: 1.05rem;
        font-weight: 700;
        color: #e2e8f0;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 8px;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }
    
    /* Títulos con neón degradado */
    .glow-title {
        background: linear-gradient(135deg, #ffffff 30%, #a18cd1 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    /* Alertas y Notificaciones */
    .alert-box {
        padding: 14px 18px;
        border-radius: 12px;
        margin-bottom: 12px;
        font-size: 0.95rem;
        line-height: 1.5;
        border-left: 5px solid transparent;
        background: rgba(15, 23, 42, 0.5);
        box-shadow: 0 4px 20px rgba(0,0,0,0.25);
    }
    
    .alert-critical {
        border-left-color: #ff0055;
        background: rgba(255, 0, 85, 0.07);
        border: 1px solid rgba(255, 0, 85, 0.18);
        border-left-width: 5px;
        box-shadow: 0 0 10px rgba(255, 0, 85, 0.08);
    }
    
    .alert-warning {
        border-left-color: #ffb300;
        background: rgba(255, 179, 0, 0.06);
        border: 1px solid rgba(255, 179, 0, 0.15);
        border-left-width: 5px;
    }
    .alert-predictive {
        border-left-color: #d946ef;
        background: rgba(217, 70, 239, 0.08);
        border: 1px solid rgba(217, 70, 239, 0.18);
        border-left-width: 5px;
        box-shadow: 0 0 12px rgba(217, 70, 239, 0.08);
    }
    
    .alert-info {
        border-left-color: #00f2fe;
        background: rgba(0, 242, 254, 0.05);
        border: 1px solid rgba(0, 242, 254, 0.15);
        border-left-width: 5px;
    }
    
    /* Indicadores dinámicos tipo NOC */
    .dot-pulse-green {
        height: 12px;
        width: 12px;
        background-color: #39ff14;
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 10px #39ff14;
        animation: pulse-green 1.8s infinite;
    }
    .dot-pulse-orange {
        height: 12px;
        width: 12px;
        background-color: #ffb300;
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 10px #ffb300;
        animation: pulse-orange 1.8s infinite;
    }
    .dot-pulse-red {
        height: 12px;
        width: 12px;
        background-color: #ff0055;
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 12px #ff0055;
        animation: pulse-red 1.5s infinite;
    }
    @keyframes pulse-green {
        0% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(57, 255, 20, 0.6); }
        70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(57, 255, 20, 0); }
        100% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(57, 255, 20, 0); }
    }
    @keyframes pulse-orange {
        0% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(255, 179, 0, 0.6); }
        70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(255, 179, 0, 0); }
        100% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(255, 179, 0, 0); }
    }
    @keyframes pulse-red {
        0% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(255, 0, 85, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(255, 0, 85, 0); }
        100% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(255, 0, 85, 0); }
    }
    /* Terminal de seguridad retro-futurista */
    .security-terminal {
        background-color: #030712 !important;
        border: 1px solid rgba(0, 242, 254, 0.3) !important;
        border-radius: 12px !important;
        padding: 16px !important;
        font-family: 'JetBrains Mono', monospace !important;
        color: #39ff14 !important;
        font-size: 0.85rem !important;
        max-height: 250px;
        overflow-y: auto;
        box-shadow: inset 0 0 15px rgba(0, 242, 254, 0.1), 0 5px 20px rgba(0,0,0,0.5);
    }
    </style>
    """,
    unsafe_allow_html=True
)
# =========================================================================
# 🔄 COMUNICACIÓN CON EL BACKEND FASTAPI
# =========================================================================
API_URL = "http://127.0.0.1:8000"
def _get_fallback_state():
    """Genera un estado offline de resguardo completo"""
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "alerts": [
            {"id": "fall_0", "title": "Sin Conexión al Servidor", "detail": "El backend FastAPI no está activo. Iniciando en modo local desconectado.", "category": "Sistema", "severity": "warning", "timestamp": "Ahora", "source": "Dashboard"}
        ],
        "network": {"overview": "Estable", "internet": "Connected", "threats": 0, "clients_total": 45, "devices_total": 14},
        "gateway": {"cpu": 15, "memory": 48, "wan_status": "UP", "latency_ms": 12, "packet_loss": 0.0001},
        "devices": {
            "router": {"status": "Connected", "temp": 39.5, "cpu": 15, "ram": 48},
            "switch_l3": {"status": "Connected", "temp": 36.0, "cpu": 10, "ram": 35},
            "switch_l2": {"status": "Connected", "temp": 32.0, "cpu": 8, "ram": 28},
            "ap_laboratorio": {"status": "Connected", "temp": 30.0, "clients": 15},
            "ap_administracion": {"status": "Connected", "temp": 29.5, "clients": 12},
            "ap_invitados": {"status": "Connected", "temp": 29.0, "clients": 18}
        },
        "performance": {
            "wifi_quality": 92,
            "bandwidth_capacity_mbps": 100,
            "realtime_traffic": {"download": [20.0]*50, "upload": [5.0]*50},
            "vlan_consumption": {"VLAN 10 (Admin)": 2.0, "VLAN 20 (Administración)": 6.5, "VLAN 30 (Alumnos)": 10.2, "VLAN 40 (Invitados)": 3.3}
        },
        "captive_portal": {"active_users": 45, "roles_breakdown": {"Estudiantes": 25, "Administración": 12, "Invitados": 8}, "radius_status": "Connected", "vouchers_remaining": 150},
        "predictions": {
            "download_forecast": [20.0]*6,
            "upload_forecast": [5.0]*6,
            "ram_forecast": [35.0]*6,
            "temp_forecast": [36.0]*6,
            "wifi_forecast": [92.0]*6,
            "fail_prob": 5,
            "overheat_risk": "Bajo",
            "memory_leak_risk": "Bajo",
            "congestion_probability": 0,
            "wifi_degradation_risk": "Bajo",
            "time_to_overheat_sec": -1,
            "time_to_ram_exhaustion_sec": -1,
            "anomalies": [],
            "recommendations": ["• Para activar el análisis de tendencias predictivas en tiempo real, encienda el backend FastAPI."]
        },
        "device_reputation": {"PC-Admin-01": 99, "Movil-Profesor": 95, "Laptop-Alumno": 75},
        "vlan_users": {"VLAN 10 (Admin)": 4, "VLAN 20 (Administración)": 12, "VLAN 30 (Alumnos)": 21, "VLAN 40 (Invitados)": 8},
        "internet_quality": {"latency": 12, "jitter": 1, "packet_loss": 0.0001, "download_speed": 100.0, "upload_speed": 20.0, "dns_status": "Operativo"},
        "ap_details": [],
        "security_logs": []
    }
# Intentar conectar con el backend
try:
    res = httpx.get(f"{API_URL}/api/state", timeout=1.5)
    if res.status_code == 200:
        state = res.json()
        backend_online = True
    else:
        state = _get_fallback_state()
        backend_online = False
except Exception:
    state = _get_fallback_state()
    backend_online = False
# Obtener estado de Auto-Mitigación
try:
    auto_mitig_res = httpx.get(f"{API_URL}/api/simulation/automitigation", timeout=1.0)
    auto_mitigation_active = auto_mitig_res.json().get("active", False)
except:
    auto_mitigation_active = False
# =========================================================================
# 🎛️ PANEL DE CONTROL DE SIMULACIÓN (SIDEBAR)
# =========================================================================
st.sidebar.markdown(f'<h2 class="glow-title" style="margin-top:0;">📡 Omada MCP</h2>', unsafe_allow_html=True)
st.sidebar.caption("Centro de Monitoreo Inteligente")
# Indicador de estado del Servidor Backend
if backend_online:
    st.sidebar.markdown('<p><span class="dot-pulse-green"></span> <b>Servidor Backend: CONECTADO</b></p>', unsafe_allow_html=True)
else:
    st.sidebar.markdown('<p><span class="dot-pulse-red"></span> <b>Servidor Backend: DESCONECTADO</b></p>', unsafe_allow_html=True)
st.sidebar.markdown("---")
# Panel del Simulador (solo habilitado si el backend está activo)
st.sidebar.markdown("###  Simulador de Incidentes")
if backend_online:
    # Obtener escenario activo desde la salud
    try:
        health = httpx.get(f"{API_URL}/health").json()
        active_scenario = health.get("scenario", "normal")
    except:
        active_scenario = "normal"
        
    scenarios_dict = {
        "normal": "🟢 Operación Estable (Normal)",
        "mass_download": " Descarga Masiva (Tráfico)",
        "memory_leak": " Fuga de Memoria (Switch L3)",
        "overheating": " Sobretemperatura (Router)",
        "wifi_interference": " Interferencia WiFi (Señal)",
        "ddos_attack": " Inundación DDoS (Seguridad)"
    }
    
    selected_scenario_label = st.sidebar.selectbox(
        "Seleccionar Escenario de Red:",
        options=list(scenarios_dict.values()),
        index=list(scenarios_dict.keys()).index(active_scenario)
    )
    
    # Invertir el diccionario para buscar por valor
    selected_scenario = [k for k, v in scenarios_dict.items() if v == selected_scenario_label][0]
    
    if st.sidebar.button("💥 Inyectar Escenario de Anomalía", use_container_width=True):
        try:
            r = httpx.post(f"{API_URL}/api/simulation/scenario", json={"scenario": selected_scenario})
            if r.status_code == 200:
                st.sidebar.success(f"Escenario '{selected_scenario}' inyectado.")
                time.sleep(0.5)
                st.rerun()
        except Exception as e:
            st.sidebar.error(f"Error al inyectar: {e}")
            
    st.sidebar.markdown("### 🛠️ Acciones de Mitigación")
    
    c1, c2 = st.sidebar.columns(2)
    with c1:
        if st.sidebar.button(" Reset Switch", use_container_width=True, help="Mitiga fuga de memoria"):
            httpx.post(f"{API_URL}/api/simulation/action", json={"action": "reset_switch"})
            st.rerun()
        if st.sidebar.button(" Enfriar Router", use_container_width=True, help="Mitiga sobrecalentamiento"):
            httpx.post(f"{API_URL}/api/simulation/action", json={"action": "reset_overheat"})
            st.rerun()
    with c2:
        if st.sidebar.button(" Limitar Tránsito", use_container_width=True, help="Aplica QoS dinámico"):
            httpx.post(f"{API_URL}/api/simulation/action", json={"action": "apply_qos"})
            st.rerun()
        if st.sidebar.button(" Bloquear Atacantes", use_container_width=True, help="Mitiga DDoS perimetral"):
            httpx.post(f"{API_URL}/api/simulation/action", json={"action": "block_ddos"})
            st.rerun()
            
    if st.sidebar.button("🟢 Limpiar y Restablecer Estado Normal", use_container_width=True):
        httpx.post(f"{API_URL}/api/simulation/action", json={"action": "reset_all"})
        st.rerun()
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🤖 Operaciones Inteligentes")
    auto_mitig_toggle = st.sidebar.checkbox(
        "Auto-Mitigación IA (Auto-Healing)",
        value=auto_mitigation_active,
        help="La IA prevendrá y resolverá fallas de red de manera autónoma antes de que ocurran."
    )
    if auto_mitig_toggle != auto_mitigation_active:
        try:
            httpx.post(f"{API_URL}/api/simulation/automitigation", json={"active": auto_mitig_toggle})
            st.sidebar.success("Configuración de Auto-Mitigación actualizada.")
            time.sleep(0.5)
            st.rerun()
        except:
            pass
else:
    st.sidebar.warning("⚠️ Bucle de simulación desactivado. El servidor FastAPI local no responde. Inicia 'run.bat' para activar los escenarios interactivos.")
st.sidebar.markdown("---")
st.sidebar.info(f"Última lectura: {state['timestamp']}")
if st.sidebar.button("🔄 Forzar Recarga"):
    st.rerun()
# =========================================================================
# 📊 PÁGINA PRINCIPAL - CABECERA
# =========================================================================
col_head1, col_head2 = st.columns([8, 1])
with col_head1:
    st.markdown(f'<h1 class="glow-title" style="margin-bottom: 5px;">📡 Centro de Control Predictivo de Red</h1>', unsafe_allow_html=True)
    st.caption("Consola NOC Integrada | Análisis y Regresión Lineal de Tendencias de Tránsito y Fallas de Hardware")
with col_head2:
    # Indicador de severidad general del NOC
    overall_status = state["network"]["overview"]
    if overall_status == "Estable":
        st.markdown('<div style="text-align:right; margin-top:20px;"><span class="dot-pulse-green"></span></div>', unsafe_allow_html=True)
    elif overall_status == "Advertencia":
        st.markdown('<div style="text-align:right; margin-top:20px;"><span class="dot-pulse-orange"></span></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="text-align:right; margin-top:20px;"><span class="dot-pulse-red"></span></div>', unsafe_allow_html=True)
# 7 Pestañas
tabs = st.tabs([
    " Control General (NOC)",
    " Capa Predictiva IA",
    "🔒 Seguridad & Portal",
    " Rendimiento & APs",
    "🤖 Asistente de Red",
    " Mapa de Topología",
    " Evolución Histórica"
])
# Banner de Auto-Mitigación
if state.get("predictions", {}).get("auto_mitigation_active", False) or auto_mitigation_active:
    st.markdown("""
        <div class="alert-box alert-predictive" style="margin-top: 10px; margin-bottom: 20px; text-align: center; background: rgba(217, 70, 239, 0.08); border-left-color: #d946ef; border-left-width: 5px;">
            <strong>🤖 PILOTO AUTOMÁTICO IA ACTIVO (Auto-Healing)</strong>: El motor predictivo tiene permitido mitigar anomalías y desvíos de telemetría de forma autónoma.
        </div>
        """, unsafe_allow_html=True)
# =========================================================================
# TAB 0: VISTA GENERAL (NOC)
# =========================================================================
with tabs[0]:
    # Fila de Métricas Glassmorphic
    col1, col2, col3, col4 = st.columns(4)
    
    # Mapear estado
    net_status = state["network"]["overview"]
    net_color = "#10b981" if net_status == "Estable" else "#f59e0b" if net_status == "Advertencia" else "#ff0055"
    
    with col1:
        st.markdown(f"""
            <div class="cyber-card">
                <div class="cyber-header"> Estado General</div>
                <h2 style="margin: 0; color: {net_color}; font-weight:800;">{net_status}</h2>
                <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 0.9rem;">Internet: {state['network']['internet']}</p>
            </div>
            """, unsafe_allow_html=True)
            
    with col2:
        st.markdown(f"""
            <div class="cyber-card">
                <div class="cyber-header"> Clientes Totales</div>
                <h2 style="margin: 0; color: #00f2fe; font-weight:800;">{state['network']['clients_total']}</h2>
                <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 0.9rem;">Portal Cautivo Activo</p>
            </div>
            """, unsafe_allow_html=True)
            
    with col3:
        st.markdown(f"""
            <div class="cyber-card">
                <div class="cyber-header">🖧 Switches y Router</div>
                <h2 style="margin: 0; color: #ffb300; font-weight:800;">{state['network']['devices_total']} / 14</h2>
                <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 0.9rem;">Equipos del Campus</p>
            </div>
            """, unsafe_allow_html=True)
            
    with col4:
        st.markdown(f"""
            <div class="cyber-card">
                <div class="cyber-header"> Carga del Gateway</div>
                <h2 style="margin: 0; color: #d946ef; font-weight:800;">CPU: {state['gateway']['cpu']}%</h2>
                <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 0.9rem;">Memoria RAM: {state['gateway']['memory']}%</p>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("<br/>", unsafe_allow_html=True)
    
    # Dos columnas principales: Gráfico de consumo de banda predictivo + Centro de alertas
    g1, g2 = st.columns([5, 3])
    
    with g1:
        st.markdown('<div class="cyber-header"> Consumo de Banda WAN en Tiempo Real y Pronóstico</div>', unsafe_allow_html=True)
        
        # Obtener histórico del estado actual
        hist_dl = list(state["performance"]["realtime_traffic"]["download"])
        hist_ul = list(state["performance"]["realtime_traffic"]["upload"])
        
        # Obtener predicciones
        pred_dl = list(state["predictions"]["download_forecast"])
        pred_ul = list(state["predictions"]["upload_forecast"])
        
        # Crear los índices temporales correspondientes (e.g. -50 a 0 ticks para el pasado)
        past_x = list(range(-len(hist_dl), 0))
        future_x = list(range(0, len(pred_dl)))
        
        fig = go.Figure()
        
        # Histórico de Descarga
        fig.add_trace(go.Scatter(
            x=past_x, y=hist_dl,
            mode='lines',
            name='Descarga Histórica',
            line=dict(color='#00f2fe', width=3),
            fill='tozeroy',
            fillcolor='rgba(0, 242, 254, 0.04)'
        ))
        
        # Proyección de Descarga
        if pred_dl:
            fig.add_trace(go.Scatter(
                x=future_x, y=[hist_dl[-1]] + pred_dl[:-1],
                mode='lines+markers',
                name='Proyección Descarga (IA)',
                line=dict(color='#d946ef', width=3, dash='dash')
            ))
            
        # Histórico de Subida
        fig.add_trace(go.Scatter(
            x=past_x, y=hist_ul,
            mode='lines',
            name='Subida Histórica',
            line=dict(color='#3b82f6', width=2)
        ))
        
        # Proyección de Subida
        if pred_ul:
            fig.add_trace(go.Scatter(
                x=future_x, y=[hist_ul[-1]] + pred_ul[:-1],
                mode='lines+markers',
                name='Proyección Subida (IA)',
                line=dict(color='#a18cd1', width=2, dash='dash')
            ))
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(15, 23, 42, 0.25)',
            font_color='#94a3b8',
            xaxis_title="Ticks de Muestreo (5s)",
            yaxis_title="Mbps",
            height=380,
            margin=dict(l=10, r=10, t=20, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)
    with g2:
        st.markdown('<div class="cyber-header"> Alertas y Diagnósticos en Tiempo Real</div>', unsafe_allow_html=True)
        
        # Filtrar alertas predictivas y alertas normales críticas
        critical_alerts = [a for a in state["alerts"] if a["severity"] in ["critical", "error"]]
        predictive_alerts = [a for a in state["alerts"] if a["category"] == "Predicción IA"]
        info_alerts = [a for a in state["alerts"] if a["severity"] not in ["critical", "error"] and a["category"] != "Predicción IA"]
        
        if not critical_alerts and not predictive_alerts and not info_alerts:
            st.success("🟢 No se registran alertas ni incidencias en la red.")
        
        # Renderizar alertas críticas
        if critical_alerts:
            for alert in critical_alerts[:3]:
                st.markdown(f"""
                    <div class="alert-box alert-critical">
                        <strong>🔴 {alert['title']}</strong> (Categoría: {alert['category']})<br/>
                        {alert['detail']}<br/>
                        <span style="font-size:0.75rem; color:#94a3b8;">Origen: {alert['source']} | {alert['timestamp']}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
        # Renderizar alertas predictivas
        if predictive_alerts:
            for alert in predictive_alerts[:3]:
                st.markdown(f"""
                    <div class="alert-box alert-predictive">
                        <strong> {alert['title']} (Proyección Preventiva)</strong><br/>
                        {alert['detail']}<br/>
                        <span style="font-size:0.75rem; color:#94a3b8;">Calculado por: Motor Predictivo Omada | {alert['timestamp']}</span>
                    </div>
                    """, unsafe_allow_html=True)
        # Renderizar alertas de información
        if info_alerts:
            with st.expander(" Alertas Informativas y Mitigaciones"):
                for alert in info_alerts[:5]:
                    st.markdown(f"""
                        <div class="alert-box alert-info">
                            <strong>{alert['title']}</strong><br/>
                            {alert['detail']}<br/>
                            <span style="font-size:0.7rem; color:#94a3b8;">{alert['timestamp']}</span>
                        </div>
                        """, unsafe_allow_html=True)
# =========================================================================
# TAB 1: CAPA PREDICTIVA IA
# =========================================================================
with tabs[1]:
    st.subheader(" Centro de Análisis y Proyecciones de Red")
    
    col_pred1, col_pred2 = st.columns([4, 6])
    
    # 1. Indicadores de Riesgo (Gauges)
    with col_pred1:
        st.markdown('<div class="cyber-header">🔌 Riesgo de Falla y Proyecciones</div>', unsafe_allow_html=True)
        
        fail_prob = state["predictions"]["fail_prob"]
        
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = fail_prob,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Probabilidad de Falla General", 'font': {'size': 18, 'color': '#f8fafc'}},
            gauge = {
                'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "#94a3b8"},
                'bar': {'color': "#d946ef"},
                'bgcolor': "rgba(30, 41, 59, 0.4)",
                'borderwidth': 2,
                'bordercolor': "rgba(0, 242, 254, 0.2)",
                'steps': [
                    {'range': [0, 40], 'color': 'rgba(16, 185, 129, 0.15)'},
                    {'range': [40, 75], 'color': 'rgba(245, 158, 11, 0.15)'},
                    {'range': [75, 100], 'color': 'rgba(239, 68, 68, 0.15)'}
                ],
                'threshold': {
                    'line': {'color': "#ff0055", 'width': 4},
                    'thickness': 0.75,
                    'value': 85
                }
            }
        ))
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#94a3b8', height=240, margin=dict(t=30, b=0, l=20, r=20))
        st.plotly_chart(fig, use_container_width=True)
        
        # Contadores regresivos para caídas estimadas
        t_overheat = state["predictions"]["time_to_overheat_sec"]
        t_ram = state["predictions"]["time_to_ram_exhaustion_sec"]
        
        st.markdown("---")
        st.markdown("###  Cuenta Regresiva de Hardware")
        
        if t_ram > 0:
            st.markdown(f"""
                <div class="alert-box alert-critical" style="text-align:center;">
                    <span style="font-size:0.9rem; text-transform:uppercase;"> Tiempo Estimado para Colapso de Switch L3</span>
                    <h1 style="margin:5px 0; color:#ff0055; font-size:2.2rem; font-weight:800;">{t_ram} s</h1>
                    <span style="font-size:0.8rem; color:#f8fafc;">Fuga de memoria RAM detectada. Se proyecta caída de puertos.</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <div class="alert-box alert-info" style="text-align:center;">
                    <span style="font-size:0.9rem; text-transform:uppercase; color:#94a3b8;"> Salud del Switch Core L3</span>
                    <h3 style="margin:5px 0; color:#10b981; font-weight:700;">Estable / Sin Fuga</h3>
                    <span style="font-size:0.8rem; color:#94a3b8;">RAM operando bajo el umbral normal.</span>
                </div>
                """, unsafe_allow_html=True)
                
        if t_overheat > 0:
            st.markdown(f"""
                <div class="alert-box alert-critical" style="text-align:center;">
                    <span style="font-size:0.9rem; text-transform:uppercase;"> Tiempo Estimado para Apagado Térmico</span>
                    <h1 style="margin:5px 0; color:#ffb300; font-size:2.2rem; font-weight:800;">{t_overheat} s</h1>
                    <span style="font-size:0.8rem; color:#f8fafc;">Aumento térmico acelerado en Router. Desconexión inminente.</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <div class="alert-box alert-info" style="text-align:center;">
                    <span style="font-size:0.9rem; text-transform:uppercase; color:#94a3b8;">🌡️ Temperatura del Router ER605</span>
                    <h3 style="margin:5px 0; color:#10b981; font-weight:700;">Estable / Refrigerado</h3>
                    <span style="font-size:0.8rem; color:#94a3b8;">Temperatura en equilibrio térmico normal.</span>
                </div>
                """, unsafe_allow_html=True)
    # 2. Recomendaciones y Análisis Detallado
    with col_pred2:
        st.markdown('<div class="cyber-header"> Recomendaciones Inteligentes de Autogestión</div>', unsafe_allow_html=True)
        
        # Caja de recomendaciones con neón
        recs = state["predictions"]["recommendations"]
        recs_html = "".join([f"<p style='margin: 8px 0; font-size: 1.05rem;'>{r}</p>" for r in recs])
        st.markdown(f"""
            <div class="cyber-card" style="border-color:#d946ef; background: rgba(217, 70, 239, 0.02);">
                {recs_html}
            </div>
            """, unsafe_allow_html=True)
            
        # Botón dinámico de mitigación según escenario predictivo
        if t_ram > 0:
            if st.button("🧹 Aplicar Mitigación: Reiniciar Switch Principal L3", type="primary", use_container_width=True):
                r = httpx.post(f"{API_URL}/api/simulation/action", json={"action": "reset_switch"})
                st.success("Acción preventiva ejecutada con éxito.")
                time.sleep(0.5)
                st.rerun()
        elif t_overheat > 0:
            if st.button(" Aplicar Mitigación: Encender Ventilación Forzada del Router", type="primary", use_container_width=True):
                r = httpx.post(f"{API_URL}/api/simulation/action", json={"action": "reset_overheat"})
                st.success("Refrigeración auxiliar encendida preventivamente.")
                time.sleep(0.5)
                st.rerun()
        elif state["predictions"]["congestion_probability"] > 60:
            if st.button("📶 Aplicar QoS Dinámico en VLAN 30", type="primary", use_container_width=True):
                r = httpx.post(f"{API_URL}/api/simulation/action", json={"action": "apply_qos"})
                st.success("Tasa de descarga limitada a alumnos.")
                time.sleep(0.5)
                st.rerun()
        elif state["predictions"]["wifi_degradation_risk"] == "Alto":
            if st.button("📡 Aplicar Salto de Canal Dinámico", type="primary", use_container_width=True):
                r = httpx.post(f"{API_URL}/api/simulation/action", json={"action": "change_channel"})
                st.success("Canal WiFi cambiado preventivamente.")
                time.sleep(0.5)
                st.rerun()
        st.markdown("###  Anomalías Detectadas por Tendencia")
        anomalies = state["predictions"]["anomalies"]
        if anomalies:
            for an in anomalies:
                st.warning(f"**{an['metric']}** - {an['detail']}")
        else:
            st.info("No se han registrado desviaciones ni anomalías en la telemetría actual.")
        st.markdown("---")
        st.markdown("### 📊 Gráficos de Proyección (Análisis de Tendencias)")
        
        # Graficar proyección de RAM y Temperatura
        t_temp_f = state["predictions"]["temp_forecast"]
        t_ram_f = state["predictions"]["ram_forecast"]
        
        if t_temp_f and t_ram_f:
            sub_col1, sub_col2 = st.columns(2)
            with sub_col1:
                st.markdown("<p style='font-size:0.85rem; text-align:center;'>Proyección Térmica Router (°C)</p>", unsafe_allow_html=True)
                fig_t = go.Figure()
                fig_t.add_trace(go.Scatter(x=list(range(-5, 0)), y=[state['devices']['router']['temp']]*5, mode='lines', name='Histórico', line=dict(color='#00f2fe')))
                fig_t.add_trace(go.Scatter(x=list(range(0, 6)), y=[state['devices']['router']['temp']] + t_temp_f[:-1], mode='lines+markers', name='Proyección', line=dict(color='#d946ef', dash='dash')))
                fig_t.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#94a3b8', height=160, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig_t, use_container_width=True)
            with sub_col2:
                st.markdown("<p style='font-size:0.85rem; text-align:center;'>Proyección RAM Switch L3 (%)</p>", unsafe_allow_html=True)
                fig_r = go.Figure()
                fig_r.add_trace(go.Scatter(x=list(range(-5, 0)), y=[state['devices']['switch_l3']['ram']]*5, mode='lines', name='Histórico', line=dict(color='#00f2fe')))
                fig_r.add_trace(go.Scatter(x=list(range(0, 6)), y=[state['devices']['switch_l3']['ram']] + t_ram_f[:-1], mode='lines+markers', name='Proyección', line=dict(color='#d946ef', dash='dash')))
                fig_r.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#94a3b8', height=160, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig_r, use_container_width=True)
# =========================================================================
# TAB 2: SEGURIDAD & PORTAL CAUTIVO
# =========================================================================
with tabs[2]:
    st.subheader("🔒 Estado del Portal Cautivo & Logs de Seguridad")
    
    col_sec1, col_sec2 = st.columns([1, 1])
    
    with col_sec1:
        st.markdown('<div class="cyber-header"> Usuarios del Portal y Segmentación</div>', unsafe_allow_html=True)
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Usuarios Activos", state["captive_portal"]["active_users"])
        col_m2.metric("Vouchers Libres", state["captive_portal"]["vouchers_remaining"])
        
        # Desglose por roles
        roles = state["captive_portal"]["roles_breakdown"]
        if roles:
            df_roles = pd.DataFrame({"Rol": list(roles.keys()), "Conectados": list(roles.values())})
            fig = px.bar(df_roles, x="Rol", y="Conectados", color="Rol", title="Distribución por Rol")
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#94a3b8', height=240)
            st.plotly_chart(fig, use_container_width=True)
            
    with col_sec2:
        st.markdown('<div class="cyber-header"> Registro de Cortafuegos</div>', unsafe_allow_html=True)
        st.markdown(f"**Nivel de Amenazas Activas**: {state['network']['threats']}")
    st.markdown("---")
    
    # Terminal de logs en tiempo real
    st.markdown('<div class="cyber-header"> Consola Perimetral del Cortafuegos (Logs de Amenazas)</div>', unsafe_allow_html=True)
    logs = state.get("security_logs", [])
    if logs:
        log_text = ""
        for l in logs:
            lvl_marker = "[CRIT]" if l['level'] == 'critical' else "[WARN]" if l['level'] == 'warning' else "[INFO]"
            log_text += f"{l['timestamp']} {lvl_marker} {l['event']}: {l['details']}\n"
        st.text_area("Live Terminal Logs", value=log_text, height=180, label_visibility="collapsed")
    else:
        st.markdown('<div class="security-terminal">> Terminal inicializada. Esperando eventos de seguridad perimetral...</div>', unsafe_allow_html=True)
# =========================================================================
# TAB 3: QoS Y RENDIMIENTO
# =========================================================================
with tabs[3]:
    st.subheader("📶 Métricas de Capa Física y Calidad de Servicio")
    
    col_p1, col_p2, col_p3, col_p4 = st.columns(4)
    col_p1.metric("Calidad Wi-Fi General", f"{state['performance']['wifi_quality']}%")
    col_p2.metric("Latencia WAN", f"{state['gateway']['latency_ms']} ms")
    col_p3.metric("Jitter de Conexión", f"{state['internet_quality']['jitter']} ms")
    col_p4.metric("Pérdida de Paquetes", f"{round(state['gateway']['packet_loss']*100, 3)}%")
    
    st.markdown(f"**Estado del Servidor DNS:** {state['internet_quality']['dns_status']}  |  **Velocidad de Enlace WAN:** {state['internet_quality']['download_speed']} Mbps ↓ / {state['internet_quality']['upload_speed']} Mbps ↑")
    st.markdown("---")
    
    col_q1, col_q2 = st.columns([1, 1])
    with col_q1:
        st.markdown('<div class="cyber-header"> Consumo de Ancho de Banda por VLAN (Mbps)</div>', unsafe_allow_html=True)
        vlan_cons = state["performance"]["vlan_consumption"]
        if vlan_cons:
            df_vlan = pd.DataFrame(list(vlan_cons.items()), columns=["VLAN", "Mbps"])
            fig = px.bar(df_vlan, y="VLAN", x="Mbps", orientation="h", color="VLAN", color_discrete_sequence=px.colors.sequential.Teal)
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#94a3b8', height=260)
            st.plotly_chart(fig, use_container_width=True)
            
    with col_q2:
        st.markdown('<div class="cyber-header">📡 Puntos de Acceso Activos (APs)</div>', unsafe_allow_html=True)
        if "ap_details" in state and state["ap_details"]:
            df_ap = pd.DataFrame(state["ap_details"])
            st.dataframe(df_ap, use_container_width=True)
            
            # Buscar AP más saturado
            max_ap = max(state["ap_details"], key=lambda x: x["clients"])
            st.info(f"🏆 AP con Mayor Demanda: **{max_ap['name']}** con {max_ap['clients']} clientes en el canal {max_ap['channel']}.")
        else:
            st.info("Buscando APs... Sin datos de antenas.")
# =========================================================================
# TAB 4: ASISTENTE IA DE RED
# =========================================================================
with tabs[4]:
    st.subheader("🤖 Consultas al Asistente Inteligente")
    st.write("El modelo tiene acceso en tiempo real a la telemetría, las alertas de incidentes y las proyecciones futuras.")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [{"role": "assistant", "message": "Hola, soy el Asistente Omada IA. Analizo constantemente las tendencias de hardware y tráfico. ¿En qué puedo ayudarte?"}]
        
    for chat in st.session_state.chat_history:
        with st.chat_message(chat["role"]):
            st.markdown(chat["message"])
            
    if prompt := st.chat_input("Preguntar sobre el estado predictivo de la red..."):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.chat_history.append({"role": "user", "message": prompt})
        
        with st.chat_message("assistant"):
            with st.spinner("Analizando telemetría y pronósticos..."):
                try:
                    res = httpx.post(f"{API_URL}/api/chat", json={"pregunta": prompt}, timeout=25)
                    if res.status_code == 200:
                        respuesta = res.json()["response"]
                        st.markdown(respuesta)
                        st.session_state.chat_history.append({"role": "assistant", "message": respuesta})
                    else:
                        st.error("Error al obtener respuesta del asistente.")
                except Exception as e:
                    st.error(f"Error: {e}")
# =========================================================================
# TAB 5: MAPA DE TOPOLOGÍA
# =========================================================================
with tabs[5]:
    st.subheader("🕸️ Topología Lógica y Física de la Red")
    st.markdown("Estado de los Nodos: 🟢 Conectado, 🟡 Degradado, 🔴 Fuera de Servicio")
    
    try:
        from pyvis.network import Network
        import tempfile
        import os
        
        net = Network(height="600px", width="100%", bgcolor="#0b101d", font_color="white")
        
        # Determinar colores dinámicos
        router_status = state["devices"]["router"]["status"]
        sw_status = state["devices"]["switch_l3"]["status"]
        
        router_color = "#10b981" if router_status == "Connected" else "#ff0055"
        sw_color = "#10b981" if sw_status == "Connected" else "#ff0055"
        
        # Color AP
        ap_saturation = "green"
        if "ap_details" in state and state["ap_details"]:
            if any(ap["name"]=="AP Biblioteca" and ap["saturation"]=="Alta" for ap in state["ap_details"]):
                ap_saturation = "#ffb300"
        
        # Construcción del grafo
        net.add_node("Router ER605", title="Router Gateway ER605", color=router_color, shape="box")
        net.add_node("Router Backup", title="Enlace redundante", color="#10b981", shape="box")
        net.add_node("Switch Core L3", title="Switch de Distribución Core L3", color=sw_color, shape="box")
        net.add_node("Switch Piso 1", title="Switch L2 Acceso", color="#10b981", shape="box")
        net.add_node("Switch Piso 2", title="Switch L2 Acceso", color="#10b981", shape="box")
        net.add_node("AP Biblioteca", title="AP EAP650", color=ap_saturation, shape="dot")
        net.add_node("AP Laboratorio", title="AP EAP650", color="#10b981", shape="dot")
        net.add_node("AP Administración", title="AP EAP650", color="#10b981", shape="dot")
        
        net.add_edge("Router ER605", "Switch Core L3", width=4, color="#00f2fe")
        net.add_edge("Router Backup", "Switch Core L3", width=2, color="#94a3b8")
        net.add_edge("Switch Core L3", "Switch Piso 1", width=3, color="#00f2fe")
        net.add_edge("Switch Core L3", "Switch Piso 2", width=3, color="#00f2fe")
        net.add_edge("Switch Piso 1", "AP Biblioteca", width=2, color="#3b82f6")
        net.add_edge("Switch Piso 1", "AP Administración", width=2, color="#3b82f6")
        net.add_edge("Switch Piso 2", "AP Laboratorio", width=2, color="#3b82f6")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
            net.save_graph(tmp.name)
            tmp_path = tmp.name
        with open(tmp_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        st.components.v1.html(html_content, height=600, scrolling=False)
    except Exception as e:
        st.error(f"Error al inicializar la topología gráfica: {e}")
# =========================================================================
# TAB 6: EVOLUCIÓN HISTÓRICA
# =========================================================================
with tabs[6]:
    st.subheader(" Históricos Guardados por el Servidor")
    
    try:
        res_hist = httpx.get(f"{API_URL}/api/history", timeout=3.0)
        if res_hist.status_code == 200:
            hist = res_hist.json()
            
            if hist["traffic"]:
                df = pd.DataFrame(hist["traffic"], columns=["time", "download", "upload"])
                df["time"] = pd.to_datetime(df["time"])
                fig = px.line(df, x="time", y=["download", "upload"], title="Consumo WAN Agregado (Mbps)")
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15, 23, 42, 0.25)', font_color='#94a3b8')
                st.plotly_chart(fig, use_container_width=True)
                
            if hist["clients"]:
                dfc = pd.DataFrame(hist["clients"], columns=["time", "count"])
                dfc["time"] = pd.to_datetime(dfc["time"])
                figc = px.line(dfc, x="time", y="count", title="Evolución de Dispositivos Conectados")
                figc.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15, 23, 42, 0.25)', font_color='#94a3b8')
                st.plotly_chart(figc, use_container_width=True)
                
            if hist["wan_latency"] and hist["wan_jitter"]:
                dflat = pd.DataFrame(hist["wan_latency"], columns=["time", "value"])
                dfjit = pd.DataFrame(hist["wan_jitter"], columns=["time", "value"])
                # Fusionar
                dfm = pd.merge(dflat, dfjit, on="time", suffixes=("_lat", "_jit"))
                dfm["time"] = pd.to_datetime(dfm["time"])
                figj = px.line(dfm, x="time", y=["value_lat", "value_jit"], title="Latencia y Jitter WAN (ms)")
                figj.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15, 23, 42, 0.25)', font_color='#94a3b8')
                st.plotly_chart(figj, use_container_width=True)
        else:
            st.warning("No se pudieron cargar datos históricos desde el servidor backend.")
    except Exception as e:
        st.error(f"Error al recuperar históricos: {e}")