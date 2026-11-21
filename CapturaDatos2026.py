import csv
import json
import os
import socket
import time
from collections import defaultdict
from itertools import combinations
import requests

# ==============================================================================
# CONFIGURACIÓN (PEGA AQUÍ TUS CLAVES DE dev.twitch.tv/console)
# ==============================================================================
CLIENT_ID = "g4rkeuwfwm73gfh81cbxmwow1jdk5y"
CLIENT_SECRET = "eyehrrwo449lwftq1p3pavdtwrbq2s"

IDIOMAS = ["es", "pt"]
CANALES_POR_IDIOMA = 50        # 50 ES + 50 PT = 100 canales
DURACION_SEGUNDOS = 7200       # 2 horas (puedes parar con Ctrl+C sin perder nada)
TOP_ENLACES_POR_CANAL = 15     # Igual que 2021 y 2022
MIN_COMUNES = 2                # Mínimo 2 espectadores compartidos por arista

CARPETA = "datos"
FICHERO_JSON = os.path.join(CARPETA, "historial_2026.json")
os.makedirs(CARPETA, exist_ok=True)


def obtener_token():
    r = requests.post(
        "https://id.twitch.tv/oauth2/token",
        params={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "client_credentials",
        },
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def cargar_datos():
    if os.path.exists(FICHERO_JSON):
        with open(FICHERO_JSON, "r", encoding="utf-8") as f:
            d = json.load(f)
            for k in d["canales"]:
                d["canales"][k]["chatters"] = set(d["canales"][k]["chatters"])
            return d
    return {"sesiones": 0, "canales": {}}


def guardar_todo(datos):
    copia = {"sesiones": datos["sesiones"], "canales": {}}
    for k, v in datos["canales"].items():
        copia["canales"][k] = {
            "nombre": v["nombre"],
            "idioma": v["idioma"],
            "juego": v["juego"],
            "views_max": v["views_max"],
            "chatters": list(v["chatters"]),
        }
    with open(FICHERO_JSON, "w", encoding="utf-8") as f:
        json.dump(copia, f, ensure_ascii=False)

    logins = sorted(datos["canales"].keys())
    with open(os.path.join(CARPETA, "twitch_2026_nodes.csv"), "w", newline="", encoding="utf-8") as fn:
        w = csv.writer(fn)
        w.writerow(["login", "label", "language", "game", "views", "unique_chatters"])
        for lg in logins:
            c = datos["canales"][lg]
            w.writerow([lg, c["nombre"], c["idioma"], c["juego"], c["views_max"], len(c["chatters"])])

    vecinos = defaultdict(list)
    for l1, l2 in combinations(logins, 2):
        comunes = len(datos["canales"][l1]["chatters"] & datos["canales"][l2]["chatters"])
        if comunes >= MIN_COMUNES:
            vecinos[l1].append((comunes, l2))
            vecinos[l2].append((comunes, l1))

    aristas_finales = set()
    with open(os.path.join(CARPETA, "twitch_2026_edges.csv"), "w", newline="", encoding="utf-8") as fe:
        w = csv.writer(fe)
        w.writerow(["source", "target", "weight", "same_language"])
        for u, lista in vecinos.items():
            for peso, v in sorted(lista, reverse=True)[:TOP_ENLACES_POR_CANAL]:
                par = tuple(sorted((u, v)))
                if par not in aristas_finales:
                    aristas_finales.add(par)
                    mismo_id = int(datos["canales"][par[0]]["idioma"] == datos["canales"][par[1]]["idioma"])
                    w.writerow([par[0], par[1], peso, mismo_id])

    return len(logins), len(aristas_finales)


def abrir_socket_irc():
    irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    irc.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 262144)
    irc.connect(("irc.chat.twitch.tv", 6667))
    irc.send(b"PASS SCHMOOPIIE\r\n")
    irc.send(b"NICK justinfan12345\r\n")
    irc.settimeout(1.0)
    return irc


def ejecutar():
    datos = cargar_datos()
    datos["sesiones"] += 1
    print(f"=== INICIANDO SESIÓN {datos['sesiones']} (ES + PT) ===")

    token = obtener_token()
    headers = {"Client-ID": CLIENT_ID, "Authorization": f"Bearer {token}"}
    en_directo = []

    for lang in IDIOMAS:
        resp = requests.get(
            "https://api.twitch.tv/helix/streams",
            headers=headers,
            params={"language": lang, "first": CANALES_POR_IDIOMA},
            timeout=15,
        ).json()
        for s in resp.get("data", []):
            login = s["user_login"].lower()
            en_directo.append(login)
            views = int(s["viewer_count"])
            if login not in datos["canales"]:
                datos["canales"][login] = {
                    "nombre": s["user_name"],
                    "idioma": lang.upper(),
                    "juego": s["game_name"] or "Just Chatting",
                    "views_max": views,
                    "chatters": set(),
                }
            else:
                datos["canales"][login]["views_max"] = max(datos["canales"][login]["views_max"], views)
                if s["game_name"]:
                    datos["canales"][login]["juego"] = s["game_name"]

    print(f"-> Canales en directo hoy: {len(en_directo)} | Acumulados totales: {len(datos['canales'])}")
    irc = abrir_socket_irc()

    inicio = time.time()
    ultimo_guardado = inicio
    ultimo_aviso = inicio
    ultimo_join = 0.0
    indice_join = 0
    mensajes_hoy = 0
    buffer = ""

    try:
        while time.time() - inicio < DURACION_SEGUNDOS:
            ahora = time.time()

            # Unirse por tandas de 15 canales cada 10.5s SIN bloquear la lectura
            if indice_join < len(en_directo) and (ahora - ultimo_join >= 10.5):
                lote = en_directo[indice_join : indice_join + 15]
                try:
                    for c in lote:
                        irc.send(f"JOIN #{c}\r\n".encode("utf-8"))
                    indice_join += len(lote)
                    ultimo_join = ahora
                    print(f"-> Conectado a {indice_join}/{len(en_directo)} chats...")
                except OSError:
                    pass

            try:
                chunk = irc.recv(16384)
                if not chunk:
                    raise ConnectionResetError("Socket cerrado por Twitch")

                buffer += chunk.decode("utf-8", errors="ignore")
                lineas = buffer.split("\r\n")
                buffer = lineas.pop()

                for linea in lineas:
                    if linea.startswith("PING"):
                        irc.send(linea.replace("PING", "PONG", 1).encode("utf-8") + b"\r\n")
                    elif " PRIVMSG #" in linea:
                        usuario = linea.split("!", 1)[0].lstrip(":")
                        canal = linea.split(" PRIVMSG #", 1)[1].split(" :", 1)[0].lower()
                        if canal in datos["canales"]:
                            datos["canales"][canal]["chatters"].add(usuario)
                            mensajes_hoy += 1

            except socket.timeout:
                pass
            except (ConnectionResetError, BrokenPipeError, OSError) as err:
                print(f"-> Corte de red ({err}). Reconectando en 5 segundos...")
                try:
                    irc.close()
                except OSError:
                    pass
                time.sleep(5)
                irc = abrir_socket_irc()
                indice_join = 0
                ultimo_join = 0.0
                buffer = ""
                continue

            ahora = time.time()
            if ahora - ultimo_aviso >= 300:
                min_pasados = int((ahora - inicio) // 60)
                print(f"   [{min_pasados:3d} min] Mensajes leídos hoy: {mensajes_hoy:,}")
                ultimo_aviso = ahora

            if ahora - ultimo_guardado >= 600:
                n_nodos, n_aristas = guardar_todo(datos)
                print(f"   [Autoguardado] {n_nodos} nodos | {n_aristas} aristas en CSV")
                ultimo_guardado = ahora

    except KeyboardInterrupt:
        print("\n-> Captura detenida manualmente. Guardando datos...")
    finally:
        try:
            irc.close()
        except OSError:
            pass
        n_nodos, n_aristas = guardar_todo(datos)
        print(f"=== SESIÓN {datos['sesiones']} FINALIZADA ===")
        print(f"Mensajes leídos hoy: {mensajes_hoy:,} | Total guardado: {n_nodos} vértices y {n_aristas} aristas.")


if __name__ == "__main__":
    ejecutar()
