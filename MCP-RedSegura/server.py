from fastapi import FastAPI
from analizador import analizar 

app = FastAPI()

@app.get("/")
def inicio():
    return {"mensaje": "Mi MCP funciona"}

@app.get("/estado-red")
def estado_red():
    # Simulamos valores de la red (puedes cambiarlos para probar)
    cpu_actual = 85 
    resultado_diagnostico = analizar(cpu_actual)
    
    # IMPORTANTE: Aquí mandamos exactamente las llaves que pide el dashboard
    return {
        "router": "MikroTik-Core-Olivos",
        "cpu": cpu_actual,
        "diagnostico": resultado_diagnostico
    }