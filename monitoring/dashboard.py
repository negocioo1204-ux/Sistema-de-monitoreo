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
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado (glassmorphic)
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .stApp {
        background: radial-gradient(circle at 50% 50%, #0f172a 0%, #090d16 100%) !important;
        color: #f8fafc !important;
    }
    
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
# 🔄 COMUNICACIÓN CON EL BACKEND
# =========================================================================
API_URL = "http://127.0.0.1:8000"

def _get_fallback_state():
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "alerts": [],
        "network": {"overview": "Offline", "internet": "Connected", "threats": 0, "clients_total": 45, "devices_total": 14},
        "gateway": {"cpu": 10, "memory": 20, "wan_status": "UP", "latency_ms": 15, "packet_loss": 0.0},
        "devices": {"router": {"status": "Connected", "temp": 39.0}, "switch_l3": {"status": "Connected", "temp": 36.5, "ram": 48}},
        "performance": {"wifi_quality": 90, "realtime_traffic": {"download": [50]*50, "upload": [15]*50}, "vlan_consumption": {}},
        "captive_portal": {"active_users": 45, "roles_breakdown": {}, "radius_status": "Connected", "vouchers_remaining": 150},
        "ai": {"fail_prob": 2, "recommendations": "Conecta el backend."},
        "device_reputation": {},
        "vlan_users": {},
        "internet_quality": {"jitter": 2, "dns_status": "N/D", "download_speed": 0, "upload_speed": 0},
        "ap_details": []
    }

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
# 📊 INTERFAZ PRINCIPAL
# =========================================================================
st.title(" Omada MCP — Observabilidad de Red & IA")
st.caption("Consola Inteligente Integrada | Análisis Predictivo, Alertas del Portal Cautivo y Segmentación de VLANs")

st.sidebar.markdown("###  Estado del Sistema")
if backend_online:
    st.sidebar.markdown('<p><span class="dot-live"></span> <b>Servidor Backend: ACTIVO</b></p>', unsafe_allow_html=True)
else:
    st.sidebar.markdown('<p><span class="dot-offline"></span> <b>Servidor Backend: OFFLINE</b></p>', unsafe_allow_html=True)
st.sidebar.info(f"Última actualización: {state['timestamp']}")
st.sidebar.markdown("---")
st.sidebar.markdown("###  Centro de Operaciones")
if st.sidebar.button(" Forzar Recarga del Dashboard"):
    st.rerun()

# 7 pestañas
tabs = st.tabs([
    " Vista General",
    " Seguridad & Portal",
    " QoS y Rendimiento",
    " Capa Predictiva",
    " Asistente IA",
    " Mapa de Red",
    " Tendencias Históricas"
])

# -------------------------------------------------------------------------
# PESTAÑA 0: VISTA GENERAL
# -------------------------------------------------------------------------
with tabs[0]:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""<div class="glass-card"><div class="glass-header"> Estado General</div>
                    <h2 style='margin:0;color:#10b981;'>{state['network']['overview']}</h2>
                    <p>Internet: {state['network']['internet']}</p></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="glass-card"><div class="glass-header">👥 Clientes Totales</div>
                    <h2 style='margin:0;color:#3b82f6;'>{state['network']['clients_total']}</h2>
                    <p>Distribuidos por VLAN</p></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="glass-card"><div class="glass-header">🖧 Switches y Router</div>
                    <h2 style='margin:0;color:#f59e0b;'>{state['network']['devices_total']} / 14</h2>
                    <p>Equipos Online</p></div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""<div class="glass-card"><div class="glass-header"> Carga del Router</div>
                    <h2 style='margin:0;color:#8b5cf6;'>CPU: {state['gateway']['cpu']}%</h2>
                    <p>RAM: {state['gateway']['memory']}%</p></div>""", unsafe_allow_html=True)

    st.markdown("---")
    g1, g2 = st.columns([3, 2])
    with g1:
        st.markdown('<div class="glass-header"> Consumo de Ancho de Banda (Real-time)</div>', unsafe_allow_html=True)
        df_traffic = pd.DataFrame({
            "Descarga (Mbps)": state["performance"]["realtime_traffic"]["download"],
            "Subida (Mbps)": state["performance"]["realtime_traffic"]["upload"]
        })
        fig = px.line(df_traffic, color_discrete_map={"Descarga (Mbps)": "#10b981", "Subida (Mbps)": "#3b82f6"})
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#94a3b8',
                          xaxis_title="Tiempo (ticks 5s)", yaxis_title="Mbps")
        st.plotly_chart(fig, use_container_width=True)

    with g2:
        st.markdown('<div class="glass-header"> Centro de Incidentes Críticos</div>', unsafe_allow_html=True)
        incidentes = [a for a in state.get("alerts", []) if a["severity"] in ("critical", "error")]
        if incidentes:
            for inc in incidentes[:5]:
                st.markdown(f"""<div class="alert-box alert-critical">
                                <strong>🔴 {inc['title']}</strong><br/>
                                {inc['detail']}<br/>
                                <span style='font-size:0.7rem;'>{inc['timestamp']}</span>
                            </div>""", unsafe_allow_html=True)
        else:
            st.success(" No hay incidentes críticos activos.")
        st.markdown('<div class="glass-header"> Otras Alertas</div>', unsafe_allow_html=True)
        otras = [a for a in state.get("alerts", []) if a["severity"] not in ("critical", "error")]
        if otras:
            for alert in otras[:5]:
                st.info(f"**{alert['title']}** - {alert['detail']}  \n`{alert['timestamp']}`")
        else:
            st.info("No hay alertas menores.")

# -------------------------------------------------------------------------
# PESTAÑA 1: SEGURIDAD & PORTAL
# -------------------------------------------------------------------------
with tabs[1]:
    st.subheader(" Estado del Portal Cautivo y Segmentación")
    col1, col2, col3 = st.columns(3)
    col1.metric("Usuarios Activos", state["captive_portal"]["active_users"])
    col2.markdown(f"**RADIUS:** :{'green' if state['captive_portal']['radius_status']=='Connected' else 'red'}[{state['captive_portal']['radius_status']}]")
    col3.metric("Vouchers Libres", state["captive_portal"]["vouchers_remaining"])
    st.markdown("---")
    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown('<div class="glass-header">👥 Usuarios por Rol</div>', unsafe_allow_html=True)
        roles = state["captive_portal"]["roles_breakdown"]
        if roles:
            df_roles = pd.DataFrame({"Rol": list(roles.keys()), "Conectados": list(roles.values())})
            fig = px.bar(df_roles, x="Rol", y="Conectados", color="Rol")
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#94a3b8')
            st.plotly_chart(fig, use_container_width=True)
    with col_right:
        st.markdown('<div class="glass-header"> Reputación de Dispositivos</div>', unsafe_allow_html=True)
        if "device_reputation" in state and state["device_reputation"]:
            df_rep = pd.DataFrame(list(state["device_reputation"].items()), columns=["Dispositivo", "Puntuación"])
            def color_rep(val):
                if val >= 80:
                    return "color: #10b981"
                elif val >= 60:
                    return "color: #f59e0b"
                else:
                    return "color: #ef4444"
            # CORRECCIÓN: usar 'map' en lugar de 'applymap'
            st.dataframe(df_rep.style.map(color_rep, subset=["Puntuación"]), use_container_width=True)
        else:
            st.info("No hay datos de reputación.")
    st.markdown("---")
    st.markdown('<div class="glass-header">👥 Análisis de Usuarios por VLAN</div>', unsafe_allow_html=True)
    if "vlan_users" in state:
        df_vu = pd.DataFrame(list(state["vlan_users"].items()), columns=["VLAN", "Usuarios"])
        st.dataframe(df_vu, use_container_width=True)
        st.markdown("**Consumo por VLAN (Mbps)**")
        vlan_cons = state["performance"]["vlan_consumption"]
        if vlan_cons:
            df_bw = pd.DataFrame(list(vlan_cons.items()), columns=["VLAN", "Mbps"])
            st.bar_chart(df_bw.set_index("VLAN"))

# -------------------------------------------------------------------------
# PESTAÑA 2: QoS Y RENDIMIENTO
# -------------------------------------------------------------------------
with tabs[2]:
    st.subheader(" Optimización del Tránsito")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Calidad Wi-Fi", f"{state['performance']['wifi_quality']}%")
    col2.metric("Latencia", f"{state['gateway']['latency_ms']} ms")
    col3.metric("Jitter", f"{state.get('internet_quality',{}).get('jitter',0)} ms")
    col4.metric("Pérdida", f"{round(state['gateway']['packet_loss']*100,2)}%")
    st.markdown(f"**DNS:** {state.get('internet_quality',{}).get('dns_status','N/D')}  |  **Velocidad real:** {state.get('internet_quality',{}).get('download_speed',0)} Mbps ↓ / {state.get('internet_quality',{}).get('upload_speed',0)} Mbps ↑")
    st.markdown("---")
    col_q1, col_q2 = st.columns([1,1])
    with col_q1:
        st.markdown('<div class="glass-header"> Consumo por VLAN (Mbps)</div>', unsafe_allow_html=True)
        vlan_cons = state["performance"]["vlan_consumption"]
        if vlan_cons:
            df_vlan = pd.DataFrame(list(vlan_cons.items()), columns=["VLAN", "Mbps"])
            fig = px.bar(df_vlan, y="VLAN", x="Mbps", orientation="h", color="VLAN")
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#94a3b8')
            st.plotly_chart(fig, use_container_width=True)
    with col_q2:
        st.markdown('<div class="glass-header">📡 Estado de Access Points</div>', unsafe_allow_html=True)
        if "ap_details" in state and state["ap_details"]:
            df_ap = pd.DataFrame(state["ap_details"])
            st.dataframe(df_ap, use_container_width=True)
            max_ap = max(state["ap_details"], key=lambda x: x["clients"])
            st.info(f"🏆 AP más utilizado: **{max_ap['name']}** con {max_ap['clients']} clientes.")
        else:
            st.info("No hay datos de APs.")

# -------------------------------------------------------------------------
# PESTAÑA 3: CAPA PREDICTIVA
# -------------------------------------------------------------------------
with tabs[3]:
    st.subheader(" Análisis Predictivo y Salud")
    col1, col2, col3 = st.columns(3)
    col1.markdown(f"""<div class="glass-card"><div class="glass-header">🌡️ Router</div>
                    <h3>{round(state['devices']['router']['temp'],1)} °C</h3>
                    <p>Riesgo: {state['ai'].get('overheat_risk','Bajo')}</p></div>""", unsafe_allow_html=True)
    col2.markdown(f"""<div class="glass-card"><div class="glass-header">🖧 Switch L3</div>
                    <h3>{state['devices']['switch_l3']['temp']} °C</h3>
                    <p>RAM: {state['devices']['switch_l3'].get('ram',0)}% | Fuga: {state['ai'].get('memory_leak_risk','Bajo')}</p></div>""", unsafe_allow_html=True)
    col3.markdown(f"""<div class="glass-card"><div class="glass-header"> Prob. Caída</div>
                    <h3>{state['ai']['fail_prob']}%</h3>
                    <p>Predicción IA</p></div>""", unsafe_allow_html=True)
    st.markdown("---")
    col_rec, col_pred = st.columns([1,1])
    with col_rec:
        st.markdown('<div class="glass-header"> Recomendación IA</div>', unsafe_allow_html=True)
        st.success(state["ai"]["recommendations"])
        try:
            recs_res = httpx.get(f"{API_URL}/api/recommendations", timeout=3.0)
            if recs_res.status_code == 200:
                recs = recs_res.json()["recommendations"]
                for r in recs:
                    st.markdown(f" {r}")
        except:
            pass
    with col_pred:
        st.markdown('<div class="glass-header"> Alertas Predictivas</div>', unsafe_allow_html=True)
        preds = [a for a in state.get("alerts", []) if a["category"] == " Predicción IA"]
        if preds:
            for p in preds[:4]:
                st.markdown(f"""<div class="alert-box alert-predictive">
                                <strong> {p['title']}</strong><br/>{p['detail']}<br/><span style='font-size:0.7rem;'>{p['timestamp']}</span>
                            </div>""", unsafe_allow_html=True)
        else:
            st.info("No hay alertas predictivas.")

# -------------------------------------------------------------------------
# PESTAÑA 4: ASISTENTE IA
# -------------------------------------------------------------------------
with tabs[4]:
    st.subheader(" Asistente IA de Red")
    st.write("Consulta al experto sobre el estado de la red.")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [{"role": "assistant", "message": "Hola, soy tu Asistente Omada. ¿Cómo puedo ayudarte?"}]
    for chat in st.session_state.chat_history:
        with st.chat_message(chat["role"]):
            st.markdown(chat["message"])
    if prompt := st.chat_input("Escribe tu consulta..."):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.chat_history.append({"role": "user", "message": prompt})
        with st.chat_message("assistant"):
            with st.spinner("Analizando..."):
                try:
                    res = httpx.post(f"{API_URL}/api/chat", json={"pregunta": prompt}, timeout=25)
                    if res.status_code == 200:
                        respuesta = res.json()["response"]
                        st.markdown(respuesta)
                        st.session_state.chat_history.append({"role": "assistant", "message": respuesta})
                    else:
                        st.error("Error en el asistente.")
                except Exception as e:
                    st.error(f"Error: {e}")

# -------------------------------------------------------------------------
# PESTAÑA 5: MAPA DE RED (CORREGIDO - SIN ERROR DE PERMISO)
# -------------------------------------------------------------------------
with tabs[5]:
    st.subheader(" Topología Inteligente de la Red")
    st.markdown("Estado: 🟢 Operativo, 🟡 Advertencia, 🔴 Crítico")
    try:
        from pyvis.network import Network
        import tempfile
        import os
        
        net = Network(height="600px", width="100%", bgcolor="#0f172a", font_color="white")
        
        router_color = "green" if state["devices"]["router"]["status"] == "Connected" else "red"
        sw_l3_color = "green" if state["devices"]["switch_l3"]["status"] == "Connected" else "red"
        ap_biblio_color = "orange" if any(ap["name"]=="AP Biblioteca" and ap["saturation"]=="Alta" for ap in state.get("ap_details",[])) else "green"
        
        net.add_node("Router Principal", title="Router ER605", color=router_color, shape="box")
        net.add_node("Router Backup", title="Router Backup", color="green", shape="box")
        net.add_node("Switch Core L3", title="Switch Core", color=sw_l3_color, shape="box")
        net.add_node("Switch Acceso P1", title="Switch Piso 1", color="green", shape="box")
        net.add_node("Switch Acceso P2", title="Switch Piso 2", color="green", shape="box")
        net.add_node("AP Biblioteca", title="AP Biblioteca", color=ap_biblio_color, shape="dot")
        net.add_node("AP Laboratorio", title="AP Laboratorio", color="green", shape="dot")
        
        net.add_edge("Router Principal", "Switch Core L3")
        net.add_edge("Router Backup", "Switch Core L3")
        net.add_edge("Switch Core L3", "Switch Acceso P1")
        net.add_edge("Switch Core L3", "Switch Acceso P2")
        net.add_edge("Switch Acceso P1", "AP Biblioteca")
        net.add_edge("Switch Acceso P2", "AP Laboratorio")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
            net.save_graph(tmp.name)
            tmp_path = tmp.name
        with open(tmp_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        st.components.v1.html(html_content, height=650, scrolling=False)
        # No eliminamos el archivo para evitar error de permiso
    except ImportError:
        st.error("Instala pyvis: pip install pyvis")
    except Exception as e:
        st.warning(f"Error en el mapa: {e}")

# -------------------------------------------------------------------------
# PESTAÑA 6: TENDENCIAS HISTÓRICAS
# -------------------------------------------------------------------------
with tabs[6]:
    st.subheader(" Evolución Temporal de la Red")
    try:
        res_hist = httpx.get(f"{API_URL}/api/history", timeout=3.0)
        if res_hist.status_code == 200:
            hist = res_hist.json()
            if hist["traffic"]:
                df = pd.DataFrame(hist["traffic"], columns=["timestamp", "download", "upload"])
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                fig = px.line(df, x="timestamp", y=["download", "upload"], title="Tráfico agregado")
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#94a3b8')
                st.plotly_chart(fig, use_container_width=True)
            if hist["clients"]:
                dfc = pd.DataFrame(hist["clients"], columns=["timestamp", "total_clients"])
                dfc["timestamp"] = pd.to_datetime(dfc["timestamp"])
                figc = px.line(dfc, x="timestamp", y="total_clients", title="Clientes conectados")
                figc.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#94a3b8')
                st.plotly_chart(figc, use_container_width=True)
            if hist["wan_latency"] and hist["wan_jitter"]:
                dflat = pd.DataFrame(hist["wan_latency"], columns=["timestamp", "latencia_ms"])
                dfjit = pd.DataFrame(hist["wan_jitter"], columns=["timestamp", "jitter_ms"])
                dfm = pd.merge(dflat, dfjit, on="timestamp")
                dfm["timestamp"] = pd.to_datetime(dfm["timestamp"])
                figj = px.line(dfm, x="timestamp", y=["latencia_ms", "jitter_ms"], title="Latencia y Jitter WAN")
                figj.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#94a3b8')
                st.plotly_chart(figj, use_container_width=True)
        else:
            st.warning("No se pudieron cargar datos históricos.")
    except Exception as e:
        st.error(f"Error: {e}")