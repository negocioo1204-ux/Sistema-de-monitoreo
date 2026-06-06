import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import httpx
import time
from datetime import datetime

# =========================================================================
# 🎨 DISEÑO ESTÉTICO Y CONFIGURACIÓN PREMIUM DE LA PÁGINA
# =========================================================================
st.set_page_config(
    page_title="Omada MCP - Centro de Control Inteligente",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inyectar CSS personalizado para lograr estética oscura premium (glassmorphic)
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&display=swap');
    
    /* Fuente global y colores base */
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Fondo con degradado radial oscuro */
    .stApp {
        background: radial-gradient(circle at 50% 50%, #0f172a 0%, #090d16 100%) !important;
        color: #f8fafc !important;
    }
    
    /* Modificaciones en pestañas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: rgba(15, 23, 42, 0.6);
        padding: 6px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 8px;
        color: #94a3b8;
        font-weight: 600;
        border: none;
        transition: all 0.3s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        color: #ffffff;
        background-color: rgba(255, 255, 255, 0.05);
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #3b82f6 !important;
        color: #ffffff !important;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
    }

    /* Tarjeta estilo Glassmorphism */
    .glass-card {
        background: rgba(30, 41, 59, 0.45);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    
    .glass-card:hover {
        border-color: rgba(59, 130, 246, 0.4);
        transform: translateY(-2px);
    }

    .glass-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: #f1f5f9;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Alertas con bordes glowing y colores temáticos */
    .alert-box {
        padding: 12px 16px;
        border-radius: 10px;
        margin-bottom: 12px;
        font-size: 0.95rem;
        line-height: 1.5;
        border-left: 5px solid transparent;
        background: rgba(30, 41, 59, 0.3);
    }
    .alert-critical {
        border-left-color: #ef4444;
        background: rgba(239, 68, 68, 0.08);
        border: 1px solid rgba(239, 68, 68, 0.15);
        border-left-width: 5px;
    }
    .alert-error {
        border-left-color: #f97316;
        background: rgba(249, 115, 22, 0.08);
        border: 1px solid rgba(249, 115, 22, 0.15);
        border-left-width: 5px;
    }
    .alert-warning {
        border-left-color: #f59e0b;
        background: rgba(245, 158, 11, 0.08);
        border: 1px solid rgba(245, 158, 11, 0.15);
        border-left-width: 5px;
    }
    .alert-predictive {
        border-left-color: #8b5cf6;
        background: rgba(139, 92, 246, 0.08);
        border: 1px solid rgba(139, 92, 246, 0.15);
        border-left-width: 5px;
    }
    .alert-info {
        border-left-color: #3b82f6;
        background: rgba(59, 130, 246, 0.08);
        border: 1px solid rgba(59, 130, 246, 0.15);
        border-left-width: 5px;
    }

    /* Puntos parpadeantes para estado */
    .dot-live {
        height: 10px;
        width: 10px;
        background-color: #10b981;
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 8px #10b981;
        animation: pulse 1.8s infinite;
    }
    .dot-offline {
        height: 10px;
        width: 10px;
        background-color: #ef4444;
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 8px #ef4444;
    }
    @keyframes pulse {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================================================================
# 🔄 COMUNICACIÓN CON EL BACKEND (REST API y Carga de Estado)
# =========================================================================
API_URL = "http://127.0.0.1:8000"

def _get_fallback_state():
    """Genera datos locales de fallback por si el servidor backend no responde."""
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "alerts": [
            {
                "category": "⚠️ Simulación",
                "severity": "warning",
                "title": "Backend FastAPI desconectado",
                "detail": "El dashboard no se pudo conectar al servidor local en http://127.0.0.1:8000. Mostrando datos de simulación local.",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        ],
        "network": {"overview": "Offline (Local)", "internet": "Connected", "threats": 0, "clients_total": 45, "devices_total": 14},
        "gateway": {"cpu": 10, "memory": 20, "wan_status": "UP", "latency_ms": 15, "packet_loss": 0.0},
        "devices": {
            "router": {"status": "Connected", "temp": 39.0, "cpu": 10, "ram": 35},
            "switch_l3": {"status": "Connected", "temp": 36.5, "cpu": 15, "ram": 48},
            "switch_l2": {"status": "Connected", "temp": 32.0, "cpu": 5, "ram": 25},
            "ap_laboratorio": {"status": "Connected", "temp": 35.0, "clients": 18},
            "ap_docentes": {"status": "Connected", "temp": 34.0, "clients": 12},
            "ap_invitados": {"status": "Connected", "temp": 32.0, "clients": 15}
        },
        "performance": {
            "wifi_quality": 90,
            "bandwidth_capacity_mbps": 100,
            "realtime_traffic": {"download": [50]*50, "upload": [15]*50},
            "vlan_consumption": {"VLAN 10 (Admin)": 5.0, "VLAN 20 (Docentes)": 8.0, "VLAN 30 (Alumnos)": 20.0, "VLAN 40 (Invitados)": 12.0}
        },
        "captive_portal": {
            "active_users": 45,
            "roles_breakdown": {"Alumnos": 20, "Docentes": 15, "Invitados": 10},
            "radius_status": "Connected",
            "vouchers_remaining": 150
        },
        "ai": {
            "fail_prob": 2,
            "overheat_risk": "Bajo",
            "memory_leak_risk": "Bajo",
            "packet_loss_risk": "Bajo",
            "recommendations": "Conecta e inicia el servidor FastAPI en el puerto 8000 para habilitar alertas automáticas y predicciones reales."
        }
    }

# Consultar el estado de red actual desde el backend
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

# =========================================================================
# 📊 ESTRUCTURA DE LA INTERFAZ
# =========================================================================
st.title("Omada MCP — Observabilidad de Red & IA 🔗")
st.caption("Consola Inteligente Integrada | Análisis Predictivo, Alertas del Portal Cautivo y Segmentación de VLANs")

# Barra lateral con estado de conexión y acciones
st.sidebar.markdown("### 🤖 Estado del Sistema")
if backend_online:
    st.sidebar.markdown('<p><span class="dot-live"></span> <b>Servidor Backend: ACTIVO</b></p>', unsafe_allow_html=True)
else:
    st.sidebar.markdown('<p><span class="dot-offline"></span> <b>Servidor Backend: OFFLINE</b></p>', unsafe_allow_html=True)

st.sidebar.info(f"Última actualización: {state['timestamp']}")

# Opciones de simulación manual si se desea probar
st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Centro de Operaciones")
if st.sidebar.button("Forzar Recarga del Dashboard 🔄"):
    st.rerun()

# Definir las 5 pestañas principales
tabs = st.tabs([
    "📡 Vista General",
    "🔑 Seguridad & Portal Cautivo",
    "⚡ QoS y Rendimiento",
    "🤖 Capa Predictiva",
    "💬 Asistente IA de Red"
])

# -------------------------------------------------------------------------
# PESTAÑA 1: VISTA GENERAL
# -------------------------------------------------------------------------
with tabs[0]:
    # Fila de métricas rápidas (KPIs)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(
            f"""<div class="glass-card">
                <div class="glass-header">🌐 Estado General</div>
                <h2 style='margin:0;color:#10b981;'>{state['network']['overview']}</h2>
                <p style='margin:5px 0 0 0;font-size:0.85rem;color:#94a3b8;'>Salida de Internet: {state['network']['internet']}</p>
            </div>""",
            unsafe_allow_html=True
        )
        
    with col2:
        st.markdown(
            f"""<div class="glass-card">
                <div class="glass-header">👥 Clientes Totales</div>
                <h2 style='margin:0;color:#3b82f6;'>{state['network']['clients_total']}</h2>
                <p style='margin:5px 0 0 0;font-size:0.85rem;color:#94a3b8;'>Distribuidos por VLAN</p>
            </div>""",
            unsafe_allow_html=True
        )
        
    with col3:
        st.markdown(
            f"""<div class="glass-card">
                <div class="glass-header">🖥️ Switches y Router</div>
                <h2 style='margin:0;color:#f59e0b;'>{state['network']['devices_total']} / 14</h2>
                <p style='margin:5px 0 0 0;font-size:0.85rem;color:#94a3b8;'>Equipos Online en Omada</p>
            </div>""",
            unsafe_allow_html=True
        )
        
    with col4:
        cpu_gate = state["gateway"]["cpu"]
        ram_gate = state["gateway"]["memory"]
        st.markdown(
            f"""<div class="glass-card">
                <div class="glass-header">🧠 Carga del Router</div>
                <h2 style='margin:0;color:#8b5cf6;'>CPU: {cpu_gate}%</h2>
                <p style='margin:5px 0 0 0;font-size:0.85rem;color:#94a3b8;'>Uso de Memoria RAM: {ram_gate}%</p>
            </div>""",
            unsafe_allow_html=True
        )

    st.markdown("---")
    
    # Dos columnas principales: Gráfico de Tráfico y Feed de Alertas
    g1, g2 = st.columns([3, 2])
    
    with g1:
        st.markdown('<div class="glass-header">📈 Consumo de Ancho de Banda (Real-time)</div>', unsafe_allow_html=True)
        # Crear un gráfico interactivo de Plotly para el tráfico
        df_traffic = pd.DataFrame({
            "Descarga (Mbps)": state["performance"]["realtime_traffic"]["download"],
            "Subida (Mbps)": state["performance"]["realtime_traffic"]["upload"]
        })
        
        fig = px.line(
            df_traffic, 
            color_discrete_map={"Descarga (Mbps)": "#10b981", "Subida (Mbps)": "#3b82f6"}
        )
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#94a3b8',
            xaxis_title="Tiempo (Ticks de 5s)",
            yaxis_title="Velocidad (Mbps)",
            margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        fig.update_xaxes(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
        fig.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
        st.plotly_chart(fig, use_container_width=True)
        
    with g2:
        st.markdown('<div class="glass-header">🚨 Alertas Recientes y Logs Activos</div>', unsafe_allow_html=True)
        
        alerts_list = state.get("alerts", [])
        if not alerts_list:
            st.info("No hay alertas activas en el sistema. Todo se encuentra operando bajo parámetros estándar.")
        else:
            for alert in alerts_list[:7]:
                severity = alert["category"]
                sev_style = alert["severity"].lower()
                
                # Definir emojis
                emoji = "🔵"
                if sev_style == "critical":
                    emoji = "🔴"
                elif sev_style == "error":
                    emoji = "🟠"
                elif sev_style == "warning":
                    emoji = "🟡"
                elif sev_style == "predictive":
                    emoji = "🤖"
                
                st.markdown(
                    f"""<div class="alert-box alert-{sev_style}">
                        <strong>{emoji} {alert['title']}</strong><br/>
                        <span style='font-size:0.8rem;color:#94a3b8;'>Categoría: {alert['category']} | {alert['timestamp']}</span><br/>
                        <span style='color:#cbd5e1;font-size:0.88rem;'>{alert['detail']}</span>
                    </div>""",
                    unsafe_allow_html=True
                )

# -------------------------------------------------------------------------
# PESTAÑA 2: SEGURIDAD & PORTAL CAUTIVO
# -------------------------------------------------------------------------
with tabs[1]:
    st.subheader("🔑 Estado del Portal Cautivo y Segmentación por VLAN")
    
    col_port1, col_port2, col_port3 = st.columns(3)
    with col_port1:
        st.metric("Usuarios de Portal Activos", state["captive_portal"]["active_users"], delta=None)
    with col_port2:
        rad_status = state["captive_portal"]["radius_status"]
        rad_color = "green" if rad_status == "Connected" else "red"
        st.markdown(f"**Servidor de Autenticación RADIUS:** :{rad_color}[{rad_status}]")
    with col_port3:
        st.metric("Vouchers de Invitados Libres", state["captive_portal"]["vouchers_remaining"])
        
    st.markdown("---")
    
    col_vlan_charts, col_vlan_logs = st.columns([1, 1])
    
    with col_vlan_charts:
        st.markdown('<div class="glass-header">📊 Desglose de Usuarios Conectados por Rol</div>', unsafe_allow_html=True)
        roles = state["captive_portal"]["roles_breakdown"]
        df_roles = pd.DataFrame({
            "Rol": list(roles.keys()),
            "Conectados": list(roles.values())
        })
        fig_roles = px.bar(
            df_roles, x="Rol", y="Conectados", 
            color="Rol", color_discrete_sequence=["#ef4444", "#3b82f6", "#10b981"]
        )
        fig_roles.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#94a3b8',
            showlegend=False,
            margin=dict(l=10, r=10, t=10, b=10)
        )
        fig_roles.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
        st.plotly_chart(fig_roles, use_container_width=True)
        
    with col_vlan_logs:
        st.markdown('<div class="glass-header">🔒 Logs de Seguridad y Filtrado de VLAN</div>', unsafe_allow_html=True)
        # Filtrar alertas de seguridad y portal
        logs_seguridad = [
            a for a in state["alerts"] 
            if a["category"] in ("🛡️ VLAN Segmentación", "🔒 Seguridad", "🔑 Portal Cautivo")
        ]
        
        if not logs_seguridad:
            st.success("No se registran violaciones de seguridad en las VLAN ni en el portal cautivo.")
        else:
            for log_sec in logs_seguridad[:5]:
                sev = log_sec["severity"]
                st.markdown(
                    f"""<div class="alert-box alert-{sev}">
                        <strong>{log_sec['title']}</strong><br/>
                        <span style='font-size:0.8rem;color:#e2e8f0;'>Categoría: {log_sec['category']} | {log_sec['timestamp']}</span><br/>
                        <span style='font-size:0.88rem;color:#f1f5f9;'>{log_sec['detail']}</span>
                    </div>""",
                    unsafe_allow_html=True
                )

# -------------------------------------------------------------------------
# PESTAÑA 3: QOS Y RENDIMIENTO
# -------------------------------------------------------------------------
with tabs[2]:
    st.subheader("⚡ Optimización del Tránsito y QoS Dinámico")
    
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        st.metric("Calidad Promedio del Wi-Fi", f"{state['performance']['wifi_quality']}%", delta=None)
    with col_p2:
        st.metric("Latencia al DNS Gateway", f"{state['gateway']['latency_ms']} ms", delta=None)
    with col_p3:
        st.metric("Pérdida de Paquetes en WAN", f"{round(state['gateway']['packet_loss']*100, 2)}%", delta=None)
        
    st.markdown("---")
    
    col_qos_stats, col_qos_logs = st.columns([1, 1])
    
    with col_qos_stats:
        st.markdown('<div class="glass-header">📊 Consumo de Ancho de Banda por VLAN (Mbps)</div>', unsafe_allow_html=True)
        vlan_cons = state["performance"]["vlan_consumption"]
        df_vlan = pd.DataFrame({
            "VLAN": list(vlan_cons.keys()),
            "Ancho de Banda (Mbps)": list(vlan_cons.values())
        })
        fig_vlan = px.bar(
            df_vlan, y="VLAN", x="Ancho de Banda (Mbps)", 
            orientation="h", color="VLAN",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_vlan.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#94a3b8',
            showlegend=False,
            margin=dict(l=10, r=10, t=10, b=10)
        )
        fig_vlan.update_xaxes(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
        st.plotly_chart(fig_vlan, use_container_width=True)
        
    with col_qos_logs:
        st.markdown('<div class="glass-header">⚡ Logs del Motor de QoS Dinámico</div>', unsafe_allow_html=True)
        # Filtrar alertas de QoS
        logs_qos = [
            a for a in state["alerts"] 
            if a["category"] == "⚡ QoS Dinámico"
        ]
        
        if not logs_qos:
            st.info("El QoS dinámico está operando en segundo plano. No se han requerido mitigaciones de ancho de banda recientemente.")
        else:
            for l_qos in logs_qos[:5]:
                st.markdown(
                    f"""<div class="alert-box alert-{l_qos['severity']}">
                        <strong>{l_qos['title']}</strong><br/>
                        <span style='font-size:0.8rem;color:#e2e8f0;'>{l_qos['timestamp']}</span><br/>
                        <span style='font-size:0.88rem;color:#f1f5f9;'>{l_qos['detail']}</span>
                    </div>""",
                    unsafe_allow_html=True
                )

# -------------------------------------------------------------------------
# PESTAÑA 4: CAPA PREDICTIVA (ALERTAS TEMPRANAS)
# -------------------------------------------------------------------------
with tabs[3]:
    st.subheader("🤖 Análisis Predictivo y Salud de los Dispositivos")
    
    col_temp1, col_temp2, col_temp3 = st.columns(3)
    
    with col_temp1:
        temp_r = state["devices"]["router"]["temp"]
        st.markdown(
            f"""<div class="glass-card">
                <div class="glass-header">🌡️ Router ER605</div>
                <h3 style="margin:0;color:#ef4444;">{round(temp_r, 1)} °C</h3>
                <p style="margin:5px 0 0 0;font-size:0.8rem;color:#94a3b8;">Límite térmico: 70°C | Riesgo: {state['ai']['overheat_risk']}</p>
            </div>""",
            unsafe_allow_html=True
        )
        
    with col_temp2:
        temp_sw = state["devices"]["switch_l3"]["temp"]
        ram_sw = state["devices"]["switch_l3"]["ram"]
        st.markdown(
            f"""<div class="glass-card">
                <div class="glass-header">🌡️ Switch L3 SG3428X</div>
                <h3 style="margin:0;color:#10b981;">{temp_sw} °C</h3>
                <p style="margin:5px 0 0 0;font-size:0.8rem;color:#94a3b8;">Uso RAM: {ram_sw}% | Fuga RAM: {state['ai']['memory_leak_risk']}</p>
            </div>""",
            unsafe_allow_html=True
        )
        
    with col_temp3:
        st.markdown(
            f"""<div class="glass-card">
                <div class="glass-header">🤖 Probabilidad de Caída</div>
                <h3 style="margin:0;color:#8b5cf6;">{state['ai']['fail_prob']}%</h3>
                <p style="margin:5px 0 0 0;font-size:0.8rem;color:#94a3b8;">Calculado por algoritmo de IA</p>
            </div>""",
            unsafe_allow_html=True
        )

    st.markdown("---")
    
    col_pred_rec, col_pred_logs = st.columns([1, 1])
    
    with col_pred_rec:
        st.markdown('<div class="glass-header">🤖 Recomendación Preventiva de la IA</div>', unsafe_allow_html=True)
        st.success(state["ai"]["recommendations"])
        
        # Simular gráfico indicador de probabilidad
        st.markdown("<br/>", unsafe_allow_html=True)
        fig_fail = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = state["ai"]["fail_prob"],
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Probabilidad de Congestión / Fallo en 24hs", 'font': {'color': '#94a3b8', 'size': 16}},
            gauge = {
                'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "#94a3b8"},
                'bar': {'color': "#8b5cf6"},
                'bgcolor': "rgba(30,41,59,0.5)",
                'borderwidth': 2,
                'bordercolor': "rgba(255,255,255,0.08)",
                'steps': [
                    {'range': [0, 30], 'color': 'rgba(16, 185, 129, 0.15)'},
                    {'range': [30, 70], 'color': 'rgba(245, 158, 11, 0.15)'},
                    {'range': [70, 100], 'color': 'rgba(239, 68, 68, 0.15)'}
                ],
            }
        ))
        fig_fail.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            font={'color': "#f8fafc"},
            margin=dict(l=20, r=20, t=40, b=20),
            height=260
        )
        st.plotly_chart(fig_fail, use_container_width=True)

    with col_pred_logs:
        st.markdown('<div class="glass-header">🔮 Registro de Predicciones del Algoritmo</div>', unsafe_allow_html=True)
        
        # Filtrar alertas predictivas
        logs_pred = [
            a for a in state["alerts"] 
            if a["category"] == "🤖 Predicción IA"
        ]
        
        if not logs_pred:
            st.info("No hay anomalías predictivas registradas. Los tiempos de respuesta y las temperaturas se mantienen estables.")
        else:
            for l_pred in logs_pred[:4]:
                st.markdown(
                    f"""<div class="alert-box alert-predictive">
                        <strong>🔮 {l_pred['title']}</strong><br/>
                        <span style='font-size:0.8rem;color:#e2e8f0;'>Frecuencia de muestreo: 5s | {l_pred['timestamp']}</span><br/>
                        <span style='font-size:0.88rem;color:#f1f5f9;'>{l_pred['detail']}</span>
                    </div>""",
                    unsafe_allow_html=True
                )

# -------------------------------------------------------------------------
# PESTAÑA 5: ASISTENTE IA DE RED
# -------------------------------------------------------------------------
with tabs[4]:
    st.subheader("💬 Asistente IA de Infraestructura y Diagnóstico Omada")
    st.write("Consulta al Asistente experto (CCIE) sobre el estado actual del router, switches, portal cautivo o anomalías en las VLANs.")
    
    # Inicializar historial de chat en session_state si no existe
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {
                "role": "assistant",
                "message": "Hola, soy tu Asistente de Red experto de Omada. Analizo la telemetría del controlador en tiempo real. ¿Cómo puedo ayudarte hoy?"
            }
        ]

    # Mostrar mensajes de chat previos
    for chat in st.session_state.chat_history:
        with st.chat_message(chat["role"]):
            st.markdown(chat["message"])

    # Entrada del chat del usuario
    if prompt := st.chat_input("Escribe tu consulta aquí... (ej: '¿Por qué la VLAN de alumnos está lenta?' o '¿Cómo está la red hoy?')"):
        # Mostrar el mensaje del usuario
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Guardar en el historial
        st.session_state.chat_history.append({"role": "user", "message": prompt})
        
        # Realizar llamada al endpoint de chat de FastAPI
        with st.chat_message("assistant"):
            with st.spinner("🤖 Analizando telemetría y diagnosticando..."):
                try:
                    res = httpx.post(f"{API_URL}/api/chat", json={"pregunta": prompt}, timeout=25.0)
                    if res.status_code == 200:
                        data = res.json()
                        respuesta_ia = data["response"]
                        engine = data["engine"]
                        st.markdown(respuesta_ia)
                        st.caption(f"Motor de inferencia: {engine}")
                    else:
                        respuesta_ia = f"❌ Error del servidor de chat (HTTP {res.status_code})"
                        st.markdown(respuesta_ia)
                except Exception as e:
                    respuesta_ia = f"❌ Error al conectar con el motor de chat: {e}"
                    st.markdown(respuesta_ia)
                    
        # Guardar en el historial la respuesta del asistente
        st.session_state.chat_history.append({"role": "assistant", "message": respuesta_ia})

# =========================================================================
# 🔄 BUCLE DE AUTO-REFRESCO PARA STREAMLIT
# =========================================================================
# Refresca el dashboard cada 5 segundos de forma silenciosa para captar datos en tiempo real
time.sleep(5)
st.rerun()