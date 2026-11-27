"""Sube Reels a la página de Facebook y avisa por Telegram."""
import os

import requests

from . import config


def _graph(ruta):
    return f"https://graph.facebook.com/{config.GRAPH_VERSION}/{ruta}"


class ErrorFacebook(RuntimeError):
    def __init__(self, paso, datos):
        err = datos.get("error", {}) if isinstance(datos, dict) else {}
        self.codigo = err.get("code")
        self.tipo = err.get("type", "")
        self.mensaje = err.get("message", str(datos))[:300]
        super().__init__(f"Facebook falló en {paso}: [{self.codigo}] {self.mensaje}")

    @property
    def token_malo(self):
        """Token vencido, revocado o sin permisos."""
        return self.codigo in (190, 102, 10, 200) or self.tipo == "OAuthException"

    @property
    def limite(self):
        return self.codigo in (4, 17, 32, 613, 368) or "limit" in self.mensaje.lower()


def _ok(r, paso):
    try:
        datos = r.json()
    except ValueError:
        datos = {"texto": r.text[:300]}
    if r.status_code >= 400 or "error" in datos:
        raise ErrorFacebook(paso, datos)
    return datos


def reel(ruta_video, descripcion, pagina, token):
    """Publica un Reel en la página indicada. Devuelve el id del video."""
    inicio = _ok(requests.post(_graph(f"{pagina}/video_reels"),
                               data={"upload_phase": "start", "access_token": token}, timeout=60),
                 "inicio")
    video_id, upload_url = inicio["video_id"], inicio["upload_url"]

    tam = os.path.getsize(ruta_video)
    with open(ruta_video, "rb") as f:
        _ok(requests.post(upload_url, data=f, timeout=600,
                          headers={"Authorization": f"OAuth {token}",
                                   "offset": "0", "file_size": str(tam)}), "subida")

    _ok(requests.post(_graph(f"{pagina}/video_reels"), timeout=60, data={
        "upload_phase": "finish", "video_id": video_id, "video_state": "PUBLISHED",
        "description": descripcion, "access_token": token}), "publicación")
    print(f"[publicar] Reel enviado: {video_id}")
    return video_id


def estado_reel(video_id, token, intentos=6, espera=30):
    """Espera a que Facebook procese el Reel. Devuelve 'ready', 'error' o 'processing'."""
    import time
    ultimo = "processing"
    for _ in range(intentos):
        time.sleep(espera)
        try:
            r = requests.get(_graph(video_id), timeout=30,
                             params={"fields": "status", "access_token": token}).json()
        except (requests.RequestException, ValueError):
            continue
        st = r.get("status", {})
        ultimo = st.get("video_status", ultimo)
        if ultimo in ("ready", "error"):
            break
        if st.get("publishing_phase", {}).get("status") == "complete":
            return "ready"
    return ultimo


_ultimos_avisos = {}


def telegram(texto, video=None, clave=None, cada_min=60):
    """Manda un mensaje (o video). Con `clave`, el mismo aviso se manda máximo una vez
    cada `cada_min` minutos, para no llenarte el Telegram si un error se repite."""
    import time
    if not (config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID):
        return
    if clave:
        if time.time() - _ultimos_avisos.get(clave, 0) < cada_min * 60:
            return
        _ultimos_avisos[clave] = time.time()
    base = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}"
    for _ in range(3):
        try:
            if video and os.path.exists(video) and os.path.getsize(video) < 49_000_000:
                with open(video, "rb") as f:
                    r = requests.post(f"{base}/sendVideo", timeout=300, files={"video": f},
                                      data={"chat_id": config.TELEGRAM_CHAT_ID, "caption": texto[:1000]})
            else:
                r = requests.post(f"{base}/sendMessage", timeout=60,
                                  data={"chat_id": config.TELEGRAM_CHAT_ID, "text": texto[:4000]})
            if r.status_code == 429:  # Telegram pide esperar
                time.sleep(int(r.json().get("parameters", {}).get("retry_after", 5)) + 1)
                continue
            time.sleep(1.5)
            return
        except (requests.RequestException, ValueError, OSError) as e:
            print("[telegram] no se pudo avisar:", type(e).__name__)
            time.sleep(5)
