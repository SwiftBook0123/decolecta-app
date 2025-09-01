from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import httpx
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")

TOKEN_FILE = "token.txt"
API_BASE_URL = "https://api.decolecta.com/v1/reniec/dni?numero="

# 🔑 Obtener token
def obtener_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    token = obtener_token()
    if not token:
        return templates.TemplateResponse("token.html", {"request": request})
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/guardar-token")
async def guardar_token(token: str = Form(...)):
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(token.strip())
    return RedirectResponse("/", status_code=303)

@app.post("/consultar", response_class=HTMLResponse)
async def consultar(request: Request, dnis: str = Form(...), nombres: str = Form(...)):
    token = obtener_token()
    headers = {"Authorization": f"Bearer {token}"}
    dni_list = dnis.strip().split("\n")
    nombres_list = nombres.strip().split("\n")

    resultados = []
    async with httpx.AsyncClient(timeout=10) as client:
        for dni, linea in zip(dni_list, nombres_list):
            partes = linea.strip().split("\t")
            if len(partes) != 3:
                resultados.append({
                    "dni": dni,
                    "nombre_ingresado": "Formato inválido",
                    "apellido_paterno_ingresado": "",
                    "apellido_materno_ingresado": "",
                    "nombre_api": "",
                    "apellido_paterno_api": "",
                    "apellido_materno_api": ""
                })
                continue

            nombre, ap_paterno, ap_materno = partes
            try:
                resp = await client.get(f"{API_BASE_URL}{dni.strip()}", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    resultados.append({
                        "dni": dni,
                        "nombre_ingresado": nombre,
                        "apellido_paterno_ingresado": ap_paterno,
                        "apellido_materno_ingresado": ap_materno,
                        "nombre_api": data.get("first_name", ""),
                        "apellido_paterno_api": data.get("first_last_name", ""),
                        "apellido_materno_api": data.get("second_last_name", "")
                    })
                else:
                    # 🚨 Cuando API responde con error, reemplazamos por lo ingresado + "No data"
                    resultados.append({
                        "dni": dni,
                        "nombre_ingresado": nombre,
                        "apellido_paterno_ingresado": ap_paterno,
                        "apellido_materno_ingresado": ap_materno,
                        "nombre_api": f"{nombre} (No data)",
                        "apellido_paterno_api": f"{ap_paterno} (No data)",
                        "apellido_materno_api": f"{ap_materno} (No data)"
                    })
            except Exception as e:
                resultados.append({
                    "dni": dni,
                    "nombre_ingresado": nombre,
                    "apellido_paterno_ingresado": ap_paterno,
                    "apellido_materno_ingresado": ap_materno,
                    "nombre_api": f"{nombre} (No data)",
                    "apellido_paterno_api": f"{ap_paterno} (No data)",
                    "apellido_materno_api": f"{ap_materno} (No data)"
                })

    return templates.TemplateResponse("resultados.html", {"request": request, "resultados": resultados})
