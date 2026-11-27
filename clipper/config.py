"""Configuración del bot. Todo se puede cambiar con variables de entorno
(en GitHub: Settings > Secrets and variables > Actions > Variables)."""
import os
from zoneinfo import ZoneInfo


def _str(nombre, defecto):
    return os.getenv(nombre) or defecto


def _int(nombre, defecto):
    try:
        return int(os.getenv(nombre, defecto))
    except ValueError:
        return int(defecto)


# --- Fuente ---
# URL del directo. "/live" siempre apunta a la transmisión activa del canal.
CANAL_LIVE_URL = _str("CANAL_LIVE_URL", "https://www.youtube.com/@AlofokeRadioShow/live")
SEGMENTO_SEG = _int("SEGMENTO_SEG", 3600)          # pedazos de 1 hora = 1 consulta de IA por hora (24 al día)
DURACION_TRABAJO = _int("DURACION_TRABAJO", 14400)  # cada turno graba 4 horas y le pasa el relevo al siguiente
YT_COOKIES = os.getenv("YT_COOKIES", "")           # contenido de cookies.txt si YouTube bloquea

# Carpeta pública de Google Drive con tus grabaciones de pantalla del directo.
# Si está puesta, el bot usa esos videos en lugar de grabar YouTube.
DRIVE_CARPETA = os.getenv("DRIVE_CARPETA", "").strip()
FUENTE = "drive" if DRIVE_CARPETA else "youtube"

# --- Transcripción ---
WHISPER_MODELO = _str("WHISPER_MODELO", "small")  # tiny | base | small

# --- Clips ---
CLIP_MIN_SEG = _int("CLIP_MIN_SEG", 25)
CLIP_MAX_SEG = _int("CLIP_MAX_SEG", 80)
CLIPS_POR_SEGMENTO = _int("CLIPS_POR_SEGMENTO", 15)  # máximo de clips por cada pedazo
PUNTAJE_MINIMO = max(7, _int("PUNTAJE_MINIMO", 7))         # 1-10; debajo de esto no se publica
ZOOM = float(_str("ZOOM", "0.75"))            # fracción del ancho original que se conserva

# --- Publicación ---
ZONA = ZoneInfo("America/Santo_Domingo")
MAX_POR_DIA = min(17, max(0, _int("MAX_POR_DIA", 17)))              # por página: Meta permite 30 Reels por API cada 24 h
HORA_INICIO = _int("HORA_INICIO", 7)               # publica desde las 7 a.m.
HORA_FIN = _int("HORA_FIN", 23)                    # hasta medianoche
MIN_ENTRE_POSTS = _int("MIN_ENTRE_POSTS", 30)      # minutos mínimos entre Reels
MAX_COLA = _int("MAX_COLA", 80)                    # clips guardados como máximo
MAX_EDAD_HORAS = min(6, _int("MAX_EDAD_HORAS", 6))        # un clip más viejo ya no es noticia
HASHTAGS = _str("HASHTAGS", "#LaCasaDeAlofoke3 #Alofoke #LaCasaDeAlofoke #RepublicaDominicana")

ENVIAR_TODOS_TELEGRAM = _str("ENVIAR_TODOS_TELEGRAM", "1") == "1"  # 1 = te manda TODOS los clips (para TikTok/IG a mano)

# --- Quién elige los momentos (en orden; si uno falla o se agota, pasa al siguiente).
# Por ahora solo Gemini gratis y Codex (ChatGPT Plus). Para sumar Claude cuando se renueve
# su límite, pon la variable ELEGIDORES = gemini,codex,claude
ELEGIDORES = [x.strip() for x in _str("ELEGIDORES", "gemini,codex").split(",") if x.strip()]
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODELO = _str("GEMINI_MODELO", "gemini-3.5-flash-lite")
GEMINI_ALTERNATIVOS = [x.strip() for x in _str("GEMINI_ALTERNATIVOS", "gemini-3.8-flash").split(",") if x.strip()]

# --- Credenciales ---
# Páginas donde publica. Secreto FB_PAGINAS en formato JSON, por ejemplo:
# [{"nombre": "Pagina 1", "id": "123", "token": "EAA..."}, {"nombre": "Pagina 2", "id": "456", "token": "EAA..."}]
# Si no existe, usa FB_PAGE_ID y FB_PAGE_TOKEN (una sola página).
def _paginas():
    import json
    crudo = os.getenv("FB_PAGINAS", "").strip()
    # El teclado del iPhone cambia " por comillas curvas; las arreglamos.
    for curva in ("\u201c", "\u201d", "\u201e", "\u2033"):
        crudo = crudo.replace(curva, '"')
    if crudo:
        try:
            return [p for p in json.loads(crudo) if p.get("id") and p.get("token")]
        except ValueError:
            print("[config] FB_PAGINAS no es un JSON válido")
    pid, tok = os.getenv("FB_PAGE_ID", ""), os.getenv("FB_PAGE_TOKEN", "")
    return [{"nombre": "Página", "id": pid, "token": tok}] if pid and tok else []


FB_PAGINAS = _paginas()

# El repositorio es público y sus registros también: GitHub oculta cada token individual.
if os.getenv("GITHUB_ACTIONS"):
    for _p in FB_PAGINAS:
        print(f"::add-mask::{_p['token']}")
GRAPH_VERSION = _str("GRAPH_VERSION", "v21.0")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
REPO = os.getenv("GITHUB_REPOSITORY", "")
MODO_PRUEBA = os.getenv("MODO_PRUEBA", "0") == "1"  # 1 = no publica, solo manda por Telegram

# Subtítulos discretos opcionales (0 = estilo limpio).
SUBTITULOS = _str("SUBTITULOS", "0") == "1"
