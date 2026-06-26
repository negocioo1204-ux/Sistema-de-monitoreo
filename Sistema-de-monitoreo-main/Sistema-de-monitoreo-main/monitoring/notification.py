import os
import time
import asyncio
import logging
import smtplib
from datetime import datetime
from email.message import EmailMessage
from typing import Any

log = logging.getLogger("omada-notifier")


class NotificationManager:
    def __init__(self) -> None:
        # Carga de credenciales desde el archivo .env o entorno
        self._smtp_host = os.getenv("SMTP_HOST", "")
        self._smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self._smtp_user = os.getenv("SMTP_USER", "")
        self._smtp_pass = os.getenv("SMTP_PASS", "")
        self._smtp_from = os.getenv("SMTP_FROM", self._smtp_user)
        self._smtp_to = os.getenv("SMTP_TO", "")
        self._use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")

        # Verifica que las variables esenciales existan para activar el servicio
        self._enabled = bool(self._smtp_host and self._smtp_user and self._smtp_pass and self._smtp_to)
        
        # Filtros de Urgencia y Tiempo cargados desde el .env
        self._min_severity = os.getenv("NOTIFY_SEVERITY", "error").lower()
        self._cooldown = int(os.getenv("NOTIFY_COOLDOWN", "300"))  # Tiempo en segundos (Ej: 300s = 5 min)
        self._sent: dict[str, float] = {}

        self._severity_levels = {"info": 0, "warning": 1, "error": 2, "critical": 3}
        self._min_level = self._severity_levels.get(self._min_severity, 2) # Por defecto nivel 'error' (2)

        # Mapeo estético de Emojis según tu taxonomía de red
        self._emoji_map = {
            "critical": "🔴",
            "error": "🟠",
            "warning": "🟡",
            "info": "🔵",
            "predictive": "🤖"
        }
        
        # Mapeo de Colores CSS para los bordes y cabeceras del correo HTML
        self._color_map = {
            "critical": "#ef4444",    # Rojo (Caídas de infraestructura)
            "error": "#f97316",       # Naranja (Alertas de seguridad VLAN / ACLs)
            "warning": "#f59e0b",     # Amarillo (Advertencias menores)
            "info": "#3b82f6",        # Azul (Logs normales)
            "predictive": "#8b5cf6"   # Morado/Violeta (Predicciones del Modelo de IA)
        }

        if self._enabled:
            log.info("Módulo de Notificaciones Omada-IA cargado correctamente.")
        else:
            log.info("Notificaciones de email deshabilitadas (falta configurar .env).")

    def _should_send(self, alert: dict[str, Any]) -> bool:
        """Aplica los filtros de urgencia y control de tiempo para evitar SPAM."""
        if not self._enabled:
            return False
            
        severity = alert.get("severity", "info").lower()
        
        # Si es una predicción de IA, la dejamos pasar por su alta importancia
        if severity == "predictive":
            level = 3
        else:
            level = self._severity_levels.get(severity, 0)
        
        # Filtro de Urgencia: Ignora lo que esté por debajo del nivel configurado
        if level < self._min_level:
            return False
            
        # Filtro de Tiempo (Cooldown): Evita enviar correos repetidos del mismo fallo
        title = alert.get("title", "")
        now = time.time()
        last = self._sent.get(title, 0)
        if now - last < self._cooldown:
            return False
            
        self._sent[title] = now
        return True

    async def send_alert(self, alert: dict[str, Any]) -> bool:
        """Diseña y envía la interfaz HTML de un evento individual en la red."""
        if not self._should_send(alert):
            return False

        category = alert.get("category", "Red General")
        severity = alert.get("severity", "info").lower()
        title = alert.get("title", "Alerta de Red")
        detail = alert.get("detail", "No se especificaron detalles.")
        timestamp = alert.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        color = self._color_map.get(severity, "#3b82f6")
        emoji = self._emoji_map.get(severity, "🔵")

        # Generar HTML estético para el correo electrónico
        html = f"""<html><body style="font-family:'Segoe UI',Arial,sans-serif; padding:20px; background-color:#f3f4f6; margin:0;">
        <div style="max-width:600px; margin:0 auto; border-radius:12px; overflow:hidden; box-shadow:0 4px 6px rgba(0,0,0,0.1); background:#fff; border:1px solid #e5e7eb;">
            <div style="background:{color}; color:#fff; padding:20px; font-size:18px; font-weight:bold;">{emoji} SISTEMA OMADA IA: {severity.upper()}</div>
            <div style="padding:24px;">
                <span style="background-color:#f3f4f6; color:#4b5563; padding:4px 10px; border-radius:20px; font-size:12px; font-weight:600; text-transform:uppercase;">{category}</span>
                <h2 style="color:#111827; margin-top:12px; margin-bottom:8px; font-size:20px;">{title}</h2>
                <p style="color:#4b5563; font-size:15px; line-height:1.6; background-color:#f9fafb; padding:12px; border-left:4px solid {color}; border-radius:4px;">{detail}</p>
                <table style="width:100%; border-collapse:collapse; margin-top:20px; font-size:13px; color:#6b7280; border-top:1px solid #e5e7eb;">
                    <tr><td style="padding:8px 0; font-weight:bold;">Origen del Evento:</td><td style="padding:8px 0; text-align:right; color:#374151;">Ecosistema Omada TP-Link</td></tr>
                    <tr><td style="padding:8px 0; font-weight:bold;">Registro de Tiempo:</td><td style="padding:8px 0; text-align:right; color:#374151;">{timestamp}</td></tr>
                </table>
            </div>
            <div style="background:#1f2937; padding:12px; text-align:center; font-size:11px; color:#9ca3af;">Omada MCP - Motor Analítico e IA de Red</div>
        </div></body></html>"""

        msg = EmailMessage()
        msg["Subject"] = f"{emoji} OMADA IA - [{category}] - {title}"
        msg["From"] = self._smtp_from
        msg["To"] = self._smtp_to
        msg.set_content(detail)
        msg.add_alternative(html, subtype="html")

        try:
            # Ejecuta la llamada SMTP síncrona en un hilo separado
            def _send():
                with smtplib.SMTP(self._smtp_host, self._smtp_port, timeout=15) as s:
                    if self._use_tls:
                        s.starttls()
                    s.login(self._smtp_user, self._smtp_pass)
                    s.send_message(msg)

            await asyncio.to_thread(_send)
            log.info(f"📬 Notificación de correo enviada correctamente: [{category}] - {title}")
            return True
        except Exception as e:
            log.error(f"❌ Error al enviar notificación de correo: {e}")
            return False