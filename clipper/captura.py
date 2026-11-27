"""Graba un pedazo del directo de YouTube."""
import os
import subprocess
import tempfile

from . import config


def _cookies_args():
    if not config.YT_COOKIES.strip():
        return []
    ruta = os.path.join(tempfile.gettempdir(), "yt_cookies.txt")
    with open(ruta, "w") as f:
        f.write(config.YT_COOKIES)
    return ["--cookies", ruta]


def url_directo():
    """Devuelve la URL HLS (.m3u8) del directo, o None si no está en vivo."""
    cmd = ["yt-dlp", "-g", "--no-warnings", "-f", "best[height<=720]/best",
           *_cookies_args(), config.CANAL_LIVE_URL]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        print("[captura] yt-dlp falló:", r.stderr.strip()[-800:])
        return None
    lineas = [l for l in r.stdout.splitlines() if l.startswith("http")]
    return lineas[0] if lineas else None


def grabar(destino, segundos=None):
    """Graba `segundos` del directo en `destino` (.ts). Devuelve True si quedó algo útil."""
    segundos = segundos or config.SEGMENTO_SEG
    url = url_directo()
    if not url:
        return False
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "10",
           "-i", url, "-t", str(segundos), "-c", "copy", destino]
    try:
        subprocess.run(cmd, timeout=segundos + 300)
    except subprocess.TimeoutExpired:
        print("[captura] ffmpeg tardó de más; uso lo grabado")
    ok = os.path.exists(destino) and os.path.getsize(destino) > 5_000_000
    print(f"[captura] {'ok' if ok else 'sin datos'}: {destino}")
    return ok


def extraer_audio(video, wav, wav_voz):
    """`wav`: audio original (para medir volumen).
    `wav_voz`: audio con las voces bajas subidas, para que Whisper entienda los susurros."""
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", video,
                    "-vn", "-ac", "1", "-ar", "16000", wav,
                    "-vn", "-ac", "1", "-ar", "16000",
                    "-af", "highpass=f=80,lowpass=f=7500,dynaudnorm=f=150:g=15:p=0.9:m=20", wav_voz],
                   check=True)


class GrabadorContinuo:
    """Graba el directo sin parar, cortado en pedazos de SEGMENTO_SEG segundos
    (seg_<hora>_<número>.ts). Si el directo se cae, reintenta hasta `fin`."""

    def __init__(self, carpeta, fin, avisar=None):
        import threading
        self.carpeta, self.fin = carpeta, fin
        self.avisar = avisar or (lambda texto: None)
        os.makedirs(carpeta, exist_ok=True)
        self.hilo = threading.Thread(target=self._correr, daemon=True)

    def iniciar(self):
        self.hilo.start()

    def vivo(self):
        return self.hilo.is_alive()

    def _correr(self):
        import time
        fallos = 0
        while time.time() < self.fin - 60:
            url = url_directo()
            if not url:
                fallos += 1
                print("[captura] el directo no está disponible; reintento en 2 min")
                if fallos == 3:  # ~6 min sin poder grabar
                    self.avisar("Bot Alofoke: no puedo grabar el directo desde hace unos minutos. "
                                "Si el reality sigue al aire, puede que YouTube esté bloqueando "
                                "(ver YT_COOKIES en el README).")
                time.sleep(120)
                continue
            fallos = 0
            restante = int(self.fin - time.time())
            red = ["-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "10"] \
                if url.startswith("http") else []
            cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *red,
                   "-i", url, "-t", str(restante), "-c", "copy", "-map", "0:v:0", "-map", "0:a:0?",
                   "-f", "segment", "-segment_time", str(config.SEGMENTO_SEG),
                   "-reset_timestamps", "1",
                   os.path.join(self.carpeta, f"seg_{int(time.time())}_%04d.ts")]
            print(f"[captura] grabando ({restante // 60} min restantes)")
            subprocess.run(cmd)
            time.sleep(5)
        print("[captura] fin del turno de grabación")
