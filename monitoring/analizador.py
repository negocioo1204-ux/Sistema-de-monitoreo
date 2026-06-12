def analizar(cpu):
    if cpu > 80:
        return "Alerta: CPU muy alta"
    elif cpu > 50:
        return "Advertencia: CPU moderada"
        return "Estado normal"
    else: 