def analizar(cpu):
    if cpu > 80:
        return "Alerta: CPU muy alta"
    elif cpu > 50:
        return "Advertencia: CPU moderada"
    else:
        return "Estado normal"