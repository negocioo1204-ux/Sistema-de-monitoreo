import math
from datetime import datetime
def linear_forecast(series, steps_ahead=6):
    """
    Predice los próximos steps_ahead valores basándose en regresión lineal simple.
    Calcula la pendiente y proyección de la serie histórica provista.
    """
    n = len(series)
    if n < 3:
        return series[-1] if series else 0.0
    
    # x es el índice temporal, y es el valor de la serie
    x_mean = (n - 1) / 2.0
    y_mean = sum(series) / n
    
    num = sum((i - x_mean) * (series[i] - y_mean) for i in range(n))
    den = sum((i - x_mean) ** 2 for i in range(n))
    
    slope = num / den if den != 0 else 0.0
    intercept = y_mean - slope * x_mean
    
    # Proyección
    future_index = n - 1 + steps_ahead
    prediction = slope * future_index + intercept
    return max(0.0, prediction)
def analizar_predictivo(state, history_download, history_upload, history_ram, history_temp, history_wifi):
    """
    Analiza las tendencias históricas y el estado actual de la red para predecir anomalías,
    saturación de ancho de banda, fallas por temperatura y fugas de memoria.
    
    Retorna un diccionario con pronósticos, riesgos calculados, recomendaciones y alertas predictivas.
    """
    predictions = {
        "download_forecast": [],
        "upload_forecast": [],
        "ram_forecast": [],
        "temp_forecast": [],
        "wifi_forecast": [],
        "fail_prob": 0,
        "overheat_risk": "Bajo",
        "memory_leak_risk": "Bajo",
        "congestion_probability": 0,
        "wifi_degradation_risk": "Bajo",
        "time_to_overheat_sec": -1,  # -1 significa estable/sin riesgo
        "time_to_ram_exhaustion_sec": -1,
        "anomalies": [],
        "recommendations": []
    }
    
    # Si no hay suficientes datos para pronóstico, inicializamos valores básicos
    if len(history_download) < 5:
        predictions["recommendations"].append("• Recolectando telemetría inicial para análisis predictivo...")
        return predictions
    # 1. Pronósticos Futuros (próximos 6 ticks: 30 segundos en el simulador)
    for step in range(1, 7):
        predictions["download_forecast"].append(round(linear_forecast(history_download, step), 2))
        predictions["upload_forecast"].append(round(linear_forecast(history_upload, step), 2))
        predictions["ram_forecast"].append(round(linear_forecast(history_ram, step), 2))
        predictions["temp_forecast"].append(round(linear_forecast(history_temp, step), 2))
        predictions["wifi_forecast"].append(round(linear_forecast(history_wifi, step), 2))
    # Métricas actuales
    current_download = history_download[-1]
    current_ram = history_ram[-1]
    current_temp = history_temp[-1]
    current_wifi = history_wifi[-1]
    # 2. Análisis de Congestión WAN (Capacidad máxima 100 Mbps)
    future_download = predictions["download_forecast"][-1] # Proyección a 30s
    if future_download > 90.0:
        predictions["congestion_probability"] = int(min(100, future_download))
        predictions["anomalies"].append({
            "metric": "Tráfico WAN",
            "severity": "critical" if future_download > 95 else "warning",
            "detail": f"Congestión inminente: Tráfico de bajada proyectado a {future_download:.1f} Mbps en 30 segundos (Límite: 100 Mbps)."
        })
        predictions["recommendations"].append("• Sugerido: Activar QoS dinámico para limitar temporalmente el ancho de banda en VLAN 30 (Alumnos).")
    elif future_download > 70.0 and current_download < 50.0:
        predictions["congestion_probability"] = 65
        predictions["anomalies"].append({
            "metric": "Tráfico WAN",
            "severity": "warning",
            "detail": f"Incremento acelerado de tráfico: Proyección de {future_download:.1f} Mbps en los próximos ticks."
        })
        predictions["recommendations"].append("• Sugerido: Monitorear AP Biblioteca por posibles descargas en lote.")
    # 3. Análisis de Fuga de Memoria (RAM Switch L3)
    # Calculamos la pendiente de la RAM en los últimos 5 ticks
    ram_diffs = [history_ram[i] - history_ram[i-1] for i in range(-4, 0)]
    avg_ram_slope = sum(ram_diffs) / len(ram_diffs)
    
    if avg_ram_slope > 1.0 and current_ram > 50:
        # Fuga detectada (RAM sube constantemente)
        predictions["memory_leak_risk"] = "Alto" if avg_ram_slope > 2.0 else "Moderado"
        ticks_to_exhaustion = (95.0 - current_ram) / avg_ram_slope
        time_to_exhaustion_sec = max(5, int(ticks_to_exhaustion * 5)) # Ticks de 5s
        
        predictions["time_to_ram_exhaustion_sec"] = time_to_exhaustion_sec
        predictions["anomalies"].append({
            "metric": "RAM Switch L3",
            "severity": "critical" if ticks_to_exhaustion < 10 else "warning",
            "detail": f"Fuga de memoria activa en Switch L3. Agotamiento total proyectado en {time_to_exhaustion_sec} segundos."
        })
        predictions["recommendations"].append("• Sugerido: Programar reinicio preventivo del Switch L3 para evitar caída forzada del enlace.")
    elif current_ram > 85:
        predictions["memory_leak_risk"] = "Crítico"
        predictions["recommendations"].append("• Crítico: Reiniciar Switch L3 de inmediato (RAM > 85%).")
    # 4. Análisis de Calentamiento / Sobretemperatura (Router ER605)
    temp_diffs = [history_temp[i] - history_temp[i-1] for i in range(-4, 0)]
    avg_temp_slope = sum(temp_diffs) / len(temp_diffs)
    
    if avg_temp_slope > 0.3 and current_temp > 60:
        # Temperatura subiendo
        predictions["overheat_risk"] = "Alto" if avg_temp_slope > 1.0 else "Moderado"
        ticks_to_overheat = (80.0 - current_temp) / avg_temp_slope
        time_to_overheat_sec = max(5, int(ticks_to_overheat * 5))
        
        predictions["time_to_overheat_sec"] = time_to_overheat_sec
        predictions["anomalies"].append({
            "metric": "Temperatura Router",
            "severity": "critical" if ticks_to_overheat < 10 else "warning",
            "detail": f"Aumento térmico acelerado en Router. Umbral de 80°C proyectado en {time_to_overheat_sec} segundos."
        })
        predictions["recommendations"].append("• Sugerido: Reducir carga de procesamiento WAN o activar disipación forzada.")
    elif current_temp > 78:
        predictions["overheat_risk"] = "Crítico"
        predictions["recommendations"].append("• Crítico: Activar refrigeración auxiliar del bastidor principal o suspender puerto WAN secundario.")
    # 5. Análisis de Degradación de Calidad WiFi
    future_wifi = predictions["wifi_forecast"][-1]
    if future_wifi < 50.0:
        predictions["wifi_degradation_risk"] = "Alto"
        predictions["anomalies"].append({
            "metric": "Calidad WiFi",
            "severity": "warning",
            "detail": f"Caída inminente de cobertura WiFi: Calidad proyectada a {future_wifi:.1f}% en 30 segundos (Actual: {current_wifi}%)."
        })
        predictions["recommendations"].append("• Sugerido: Cambiar dinámicamente el canal del AP Biblioteca (saturación electromagnética detectada).")
    # 6. Cálculo de Probabilidad de Falla General del Sistema
    # Se compone de CPU actual, RAM, temperatura y congestión de tráfico
    fail_components = [
        state["gateway"]["cpu"] * 0.3,
        current_ram * 0.3,
        max(0.0, (current_temp - 40) * 1.5),
        predictions["congestion_probability"] * 0.2
    ]
    predictions["fail_prob"] = min(100, int(sum(fail_components)))
    # Recomendación general por defecto si todo está estable
    if not predictions["recommendations"]:
        predictions["recommendations"].append("• Estado de red estable. No se proyectan anomalías en los próximos 10 minutos.")
        
    return predictions