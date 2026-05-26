from flask import Flask, render_template, jsonify
from datetime import datetime, timedelta
import time
import json
import os
import requests
app = Flask(__name__)

ruta_json = os.path.join(os.path.dirname(__file__), 'partidos_estaticos.json')

try:
    with open(ruta_json, 'r', encoding='utf-8') as f:
        FIXTURE_ESTATICO = json.load(f)
        print(f" Se cargaron {len(FIXTURE_ESTATICO)} partidos del archivo JSON")
except FileNotFoundError:
    print(f"No se encontró el archivo en la ruta: {ruta_json}")
    FIXTURE_ESTATICO = []

cache_tablero = {}
ultima_actualizacion = 0
TIEMPO_CACHE = 21600

TRADUCCION_PAISES = {
    "Mexico": "México",
    "South Africa": "Sudáfrica",
    "Korea Republic": "Corea del Sur",
    "Czechia": "Chequia",
    "Canada": "Canadá",
    "Bosnia-Herzegovina": "Bosnia y Herzegovina",
    "USA": "Estados Unidos",
    "Paraguay": "Paraguay",
    "Qatar": "Catar",
    "Switzerland": "Suiza",
    "Brazil": "Brasil",
    "Morocco": "Marruecos",
    "Haiti": "Haití",
    "Scotland": "Escocia",
    "Australia": "Australia",
    "Turkey": "Turquía",
    "Germany": "Alemania",
    "Curaçao": "Curazao",
    "Netherlands": "Países Bajos",
    "Japan": "Japón",
    "Côte d'Ivoire": "Costa de Marfil",
    "Ecuador": "Ecuador",
    "Sweden": "Suecia",
    "Tunisia": "Túnez",
    "Spain": "España",
    "Cabo Verde": "Cabo Verde",
    "Belgium": "Bélgica",
    "Egypt": "Egipto",
    "Saudi Arabia": "Arabia Saudita",
    "Uruguay": "Uruguay",
    "IR Iran": "Irán",
    "New Zealand": "Nueva Zelanda",
    "France": "Francia",
    "Senegal": "Senegal",
    "Iraq": "Irak",
    "Norway": "Noruega",
    "Argentina": "Argentina",
    "Algeria": "Argelia",
    "Austria": "Austria",
    "Jordan": "Jordania",
    "Portugal": "Portugal",
    "Congo DR": "República Democrática del Congo",
    "Uzbekistan": "Uzbekistán",
    "Colombia": "Colombia",
    "England": "Inglaterra",
    "Croatia": "Croacia",
    "Ghana": "Ghana",
    "Panama": "Panamá"
}

MESES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto", 
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
}

def traducir_equipo(nombre):
    return TRADUCCION_PAISES.get(nombre, nombre)


def calcular_posiciones_grupos(todos_los_partidos):
    estruct_grupos = {}

    for p in todos_los_partidos:
        g_name = p.get("group_name")
        if not g_name or p.get("round") != "group":
            continue
            
        if g_name not in estruct_grupos:
            estruct_grupos[g_name] = {}
            
        for equipo in [p["home_team"], p["away_team"]]:
            if equipo not in estruct_grupos[g_name]:
                estruct_grupos[g_name][equipo] = {"nombre": equipo, "pj": 0, "pts": 0, "gf": 0, "gc": 0, "dg": 0}

    for p in todos_los_partidos:
        g_name = p.get("group_name")
        if not g_name or p.get("round") != "group" or p.get("status") != "completed":
            continue
            
        e1, e2 = p["home_team"], p["away_team"]
        g1, g2 = int(p["home_score"]), int(p["away_score"])
        
        if e1 in estruct_grupos[g_name]:
            estruct_grupos[g_name][e1]["pj"] += 1
            estruct_grupos[g_name][e1]["gf"] += g1
            estruct_grupos[g_name][e1]["gc"] += g2
        if e2 in estruct_grupos[g_name]:
            estruct_grupos[g_name][e2]["pj"] += 1
            estruct_grupos[g_name][e2]["gf"] += g2
            estruct_grupos[g_name][e2]["gc"] += g1
        
        if g1 > g2 and e1 in estruct_grupos[g_name]:
            estruct_grupos[g_name][e1]["pts"] += 3
        elif g1 < g2 and e2 in estruct_grupos[g_name]:
            estruct_grupos[g_name][e2]["pts"] += 3
        elif g1 == g2:
            if e1 in estruct_grupos[g_name]:
                estruct_grupos[g_name][e1]["pts"] += 1
            if e2 in estruct_grupos[g_name]:
                estruct_grupos[g_name][e2]["pts"] += 1

    grupos_ordenados = []
    for g_name, equipos_dict in estruct_grupos.items():
        lista_equipos = list(equipos_dict.values())
        
        for eq in lista_equipos:
            eq["dg"] = eq["gf"] - eq["gc"]
        
        lista_equipos.sort(key=lambda x: (x["pts"], x["dg"]), reverse=True)
        grupos_ordenados.append({"nombre": f"Grupo {g_name}", "equipos": lista_equipos})
        
    grupos_ordenados.sort(key=lambda x: x["nombre"])
    return grupos_ordenados

def obtener_datos_tablero():
    global cache_tablero, ultima_actualizacion
    ahora = time.time()
    
    fecha_hoy = "2026-06-11" 
    
    if not cache_tablero or (ahora - ultima_actualizacion > TIEMPO_CACHE):
        print("Sincronizando marcadores con la API externa...")
        
        url_api = "https://api.wc2026api.com/matches"
        token_real = "wc26_4TUutBnL1Qgocn3WrVSmmQ"
        headers = {"Authorization": f"Bearer {token_real}", "Accept": "application/json"}
        try:
            respuesta = requests.get(url_api, headers=headers, verify=False)
            resultados_en_vivo = respuesta.json() if respuesta.status_code == 200 else []
        except Exception as e:
            print(f"Error de conexión: {e}")
            resultados_en_vivo = []
        
        diccionario_resultados = {r["id"]: r for r in resultados_en_vivo}
        
        for p in FIXTURE_ESTATICO:
            id_p = p.get("id")
            if id_p in diccionario_resultados:
                datos = diccionario_resultados[id_p]
                p.update({"home_score": datos.get("home_score"), "away_score": datos.get("away_score"), "status": datos.get("status")})
            
            p["home_team"] = traducir_equipo(p["home_team"])
            p["away_team"] = traducir_equipo(p["away_team"])

            fecha_utc_str = p.get("kickoff_utc")
            if fecha_utc_str:
                limpia = fecha_utc_str.split('.')[0] + 'Z' if '.' in fecha_utc_str else fecha_utc_str
                fecha_utc = datetime.strptime(limpia, "%Y-%m-%dT%H:%M:%SZ")
                fecha_peru_dt = fecha_utc - timedelta(hours=5)
                
                p["fecha_peru_str"] = f"{fecha_peru_dt.day} de {MESES[fecha_peru_dt.month]}"
                p["hora_peru"] = fecha_peru_dt.strftime("%H:%M")
        
        hoy = datetime.strptime(fecha_hoy, "%Y-%m-%d")
        manana = (hoy + timedelta(days=1)).strftime("%Y-%m-%d")
        
        todos_interesantes = [p for p in FIXTURE_ESTATICO if p.get("kickoff_utc", "").startswith((fecha_hoy, manana))]
        
        # se ordena por fecha y hora
        todos_interesantes.sort(key=lambda x: x.get("kickoff_utc", ""))
        
        
        principal = None
        for p in todos_interesantes:
            if p.get("status") == "live":
                principal = p
                break
        
        if not principal:
            principal = todos_interesantes[0] if todos_interesantes else None
            
        otros = [p for p in todos_interesantes if p != principal]
        otros.sort(key=lambda x: x.get("kickoff_utc", ""))

        es_fase_grupos = True
        partidos_eliminatoria = []
        
        if fecha_hoy >= "2026-06-28":
            es_fase_grupos = False
            eliminatorias = [p for p in FIXTURE_ESTATICO if p.get("round") != "group"]
            ronda_activa = "R32"
            for p in eliminatorias:
                if p.get("kickoff_utc", "")[:10] >= fecha_hoy:
                    ronda_activa = p.get("round")
                    break
            if fecha_hoy > "2026-07-19": ronda_activa = "final"
            partidos_eliminatoria = [p for p in FIXTURE_ESTATICO if p.get("round") == ronda_activa]
        
        tablas_grupos = calcular_posiciones_grupos(FIXTURE_ESTATICO)
        
        cache_tablero = {
            "principal": principal,
            "otros": otros,
            "grupos": tablas_grupos,
            "es_fase_grupos": es_fase_grupos,
            "partidos_eliminatoria": partidos_eliminatoria 
        }
        ultima_actualizacion = ahora
        
    return cache_tablero

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/datos_tablero')
def api_tablero():
    return jsonify(obtener_datos_tablero())

if __name__ == '__main__':
    app.run(debug=True)