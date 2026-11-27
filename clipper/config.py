"""Configuración del bot. Todo se puede cambiar con variables de entorno
(en GitHub: Settings > Secrets and variables > Actions > Variables)."""

import os
import json
import math
from zoneinfo import ZoneInfo


def _limpiar(valor):
    """Elimina espacios y caracteres invisibles."""
    if valor is None:
        return ""

    valor = str(valor)

    for caracter in (
        "\u200b",
        "\u200c",
        "\u200d",
        "\ufeff",
        "\u2060",
    ):
        valor = valor.replace(caracter, "")

    return valor.strip()


def _str(nombre, defecto):
    valor = _limpiar(os.getenv(nombre))
    return valor or defecto


def _int(nombre, defecto):
    try:
        return int(_str(nombre, str(defecto)))
    except (ValueError, TypeError):
        print(f"[config] {nombre} inválido; usando {defecto}")
        return int(defecto)


def _float(nombre, defecto):
    try:
        valor = float(_str(nombre, str(defecto)))

        if not math.isfinite(valor):
            return float(defecto)

        return valor

    except (ValueError, TypeError):
        return float(defecto)


def _bool(nombre, defecto="0"):
    valor = _str(nombre, defecto).lower()
    return valor in ("1", "true", "yes", "si", "sí", "on")


# --- Fuente ---

CANAL_LIVE_URL = _str(
    "CANAL_LIVE_URL",
    "https://www.youtube.com/@AlofokeRadioShow/live"
)

# Fragmentos de 10 minutos.
SEGMENTO_SEG = max(60, _int("SEGMENTO_SEG", 600))

# Cada turno graba durante 4 horas.
DURACION_TRABAJO = _int("DURACION_TRABAJO", 14400)

# Conservar el formato original de las cookies.
YT_COOKIES = os.getenv("YT_COOKIES", "")

# Fuente alternativa desde Google Drive.
DRIVE_CARPETA = _str("DRIVE_CARPETA", "")
FUENTE = "drive" if DRIVE_CARPETA else "youtube"


# --- Transcripción ---

MODELOS_WHISPER_VALIDOS = {
    "tiny.en",
    "tiny",
    "base.en",
    "base",
    "small.en",
    "small",
    "medium.en",
    "medium",
    "large-v1",
    "large-v2",
    "large-v3",
    "large",
    "distil-large-v2",
    "distil-medium.en",
    "distil-small.en",
    "distil-large-v3",
    "distil-large-v3.5",
    "large-v3-turbo",
    "turbo",
}

WHISPER_MODELO = _str(
    "WHISPER_MODELO",
    "small"
).lower()

if WHISPER_MODELO not in MODELOS_WHISPER_VALIDOS:
    print("[config] Modelo Whisper inválido; usando small")
    WHISPER_MODELO = "small"

print(f"[config] Modelo Whisper: {WHISPER_MODELO}")


# --- Clips ---

CLIP_MIN_SEG = max(1, _int("CLIP_MIN_SEG", 25))

CLIP_MAX_SEG = max(
    CLIP_MIN_SEG,
    _int("CLIP_MAX_SEG", 80)
)

CLIPS_POR_SEGMENTO = max(
    1,
    _int("CLIPS_POR_SEGMENTO", 5)
)

# Nunca permitir una puntuación inferior a 7.
PUNTAJE_MINIMO = min(
    10,
    max(7, _int("PUNTAJE_MINIMO", 7))
)

ZOOM = min(
    1.0,
    max(0.1, _float("ZOOM", 0.75))
)


# --- Publicación ---

ZONA = ZoneInfo("America/Santo_Domingo")

# Máximo de 17 Reels diarios por página.
MAX_POR_DIA = min(
    17,
    max(0, _int("MAX_POR_DIA", 17))
)

HORA_INICIO = min(
    23,
    max(0, _int("HORA_INICIO", 7))
)

HORA_FIN = min(
    23,
    max(HORA_INICIO, _int("HORA_FIN", 23))
)

MIN_ENTRE_POSTS = max(
    1,
    _int("MIN_ENTRE_POSTS", 30)
)

MAX_COLA = max(
    1,
    _int("MAX_COLA", 80)
)

MAX_EDAD_HORAS = min(
    6,
    max(1, _int("MAX_EDAD_HORAS", 6))
)

HASHTAGS = _str(
    "HASHTAGS",
    "#LaCasaDeAlofoke3 #Alofoke "
    "#LaCasaDeAlofoke #RepublicaDominicana"
)

ENVIAR_TODOS_TELEGRAM = _bool(
    "ENVIAR_TODOS_TELEGRAM",
    "1"
)


# --- Inteligencia artificial ---

ELEGIDORES = [
    _limpiar(x).lower()
    for x in _str(
        "ELEGIDORES",
        "gemini,codex"
    ).split(",")
    if _limpiar(x)
]

GEMINI_API_KEY = _str("GEMINI_API_KEY", "")

GEMINI_MODELO = _str(
    "GEMINI_MODELO",
    "gemini-3.5-flash-lite"
)

GEMINI_ALTERNATIVOS = [
    _limpiar(x)
    for x in _str(
        "GEMINI_ALTERNATIVOS",
        "gemini-3.8-flash"
    ).split(",")
    if _limpiar(x)
]


# --- Credenciales de Facebook ---

def _paginas():

    crudo = os.getenv("FB_PAGINAS", "").strip()

    # Corregir comillas curvas del teclado del iPhone.
    for curva in (
        "\u201c",
        "\u201d",
        "\u201e",
        "\u2033",
    ):
        crudo = crudo.replace(curva, '"')

    if crudo:

        try:
            datos = json.loads(crudo)

            if not isinstance(datos, list):
                raise ValueError("Se esperaba una lista")

            paginas = []

            for p in datos:

                if not isinstance(p, dict):
                    continue

                pid = _limpiar(p.get("id"))
                tok = _limpiar(p.get("token"))
                nombre = _limpiar(p.get("nombre"))

                if pid and tok:
                    paginas.append({
                        "nombre": nombre or "Página",
                        "id": pid,
                        "token": tok,
                    })

            return paginas

        except (ValueError, TypeError):
            print("[config] FB_PAGINAS no es un JSON válido")

    pid = _str("FB_PAGE_ID", "")
    tok = _str("FB_PAGE_TOKEN", "")

    return [
        {
            "nombre": "Página",
            "id": pid,
            "token": tok
        }
    ] if pid and tok else []


FB_PAGINAS = _paginas()


# Ocultar los tokens individuales en GitHub Actions.

if os.getenv("GITHUB_ACTIONS"):

    for _p in FB_PAGINAS:
        print(f"::add-mask::{_p['token']}")


GRAPH_VERSION = _str(
    "GRAPH_VERSION",
    "v21.0"
)

TELEGRAM_TOKEN = _str(
    "TELEGRAM_TOKEN",
    ""
)

TELEGRAM_CHAT_ID = _str(
    "TELEGRAM_CHAT_ID",
    ""
)

REPO = _str(
    "GITHUB_REPOSITORY",
    ""
)

MODO_PRUEBA = _bool(
    "MODO_PRUEBA",
    "0"
)


# --- Edición visual ---

# 0 = estilo limpio.
# 1 = subtítulos discretos.

SUBTITULOS = _bool(
    "SUBTITULOS",
    "0"
)


# --- Diagnóstico inicial seguro ---

print("[config] Configuración cargada correctamente")
print(f"[config] Fuente: {FUENTE}")
print(f"[config] Segmentos: {SEGMENTO_SEG} segundos")
print(f"[config] Whisper: {WHISPER_MODELO}")
print(f"[config] Puntuación mínima: {PUNTAJE_MINIMO}")
print(f"[config] Clips por segmento: {CLIPS_POR_SEGMENTO}")
print(f"[config] Máximo diario por página: {MAX_POR_DIA}")
print(f"[config] Páginas configuradas: {len(FB_PAGINAS)}")
print(f"[config] Modo prueba: {MODO_PRUEBA}")
print(f"[config] Elegidores: {', '.join(ELEGIDORES)}")
print(f"[config] Modelo Gemini: {GEMINI_MODELO}")

for _pagina in FB_PAGINAS:
    print(f"[config] Página configurada: {_pagina['nombre']}")
