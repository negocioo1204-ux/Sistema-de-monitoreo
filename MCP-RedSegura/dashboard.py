import streamlit as st
import requests

# Configuración de la página (Pestaña del navegador)
st.set_page_config(
    page_title="MCP Network Control",
    page_icon="🛡️",
    layout="centered"
)

# Título Principal con estilo
st.title("🛡️ Centro de Control de Red Segura")
st.caption("Protocolo de Contexto de Modelo (MCP) para Entornos Multivendor")
st.markdown("---")

try:
    # Petición de datos al servidor FastAPI
    datos = requests.get("http://127.0.0.1:8000/estado-red").json()
    
    # Extraemos las variables del JSON recibido
    dispositivo = datos.get("router", "Desconocido")
    cpu_val = datos.get("cpu", 0)
    diagnostico = datos.get("diagnostico", "Sin datos")

    # Fila 1: Información General del Dispositivo en un recuadro limpio
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Dispositivo Monitoreado:**")
            st.subheader(f"📟 {dispositivo}")
        with col2:
            # Muestra la métrica de CPU con un color condicional implícito
            st.metric(label="Uso de CPU del Enrutador", value=f"{cpu_val}%")

    st.markdown("### 📊 Análisis de Salud del Sistema")

    # Fila 2: Cuadro de Diagnóstico Inteligente basado en alertas
    if "Alerta" in diagnostico:
        st.error(f"🚨 **{diagnostico}** — Se sugiere revisar las tablas de enrutamiento o mitigar posibles escaneos de puertos.")
    elif "Advertencia" in diagnostico:
        st.warning(f"⚠️ **{diagnostico}** — Tráfico moderado detectado. Monitorear comportamiento.")
    else:
        st.success(f"✅ **{diagnostico}** — Todos los parámetros operativos se encuentran estables.")

except Exception as e:
    st.error("❌ No se pudo conectar con el Servidor MCP. Asegúrate de que FastAPI esté encendido en la otra terminal.")