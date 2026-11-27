"""Graba fragmentos del directo de YouTube con recuperación automática."""

import os
import subprocess
import tempfile
import time
import threading
import uuid

from . import config


def _cookies_args():
    if not config.YT_COOKIES.strip():
        return []

    ruta = os.path.join(
        tempfile.gettempdir(),
        "yt_cookies.txt"
    )

    fd = os.open(
        ruta,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        0o600
    )

    with os.fdopen(fd, "w") as f:
        f.write(config.YT_COOKIES)

    os.chmod(ruta, 0o600)

    return ["--cookies", ruta]


def _red_args(url):
    """Configuración de estabilidad de conexión."""

    if not url.startswith(("http://", "https://")):
        return []

    return [
        "-rw_timeout", "30000000",
        "-reconnect", "1",
        "-reconnect_streamed", "1",
        "-reconnect_on_network_error", "1",
        "-reconnect_on_http_error", "5xx",
        "-reconnect_delay_max", "10",
    ]


def url_directo():
    """Obtiene una URL actualizada de la transmisión."""

    cmd = [
        "yt-dlp",
        "--js-runtimes", "deno",
        "--socket-timeout", "30",
        "--retries", "2",
        "--no-warnings",
        "-g",
        "-f", "best[height<=720]/best",
        *_cookies_args(),
        config.CANAL_LIVE_URL
    ]

    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )

    except subprocess.TimeoutExpired:
        print("[captura] yt-dlp excedió el tiempo de espera")
        return None

    if r.returncode != 0:
        print(
            "[captura] yt-dlp falló:",
            r.stderr.strip()[-800:]
        )
        return None

    lineas = [
        l.strip()
        for l in r.stdout.splitlines()
        if l.startswith("http")
    ]

    if lineas:
        print("[captura] URL obtenida correctamente")
        return lineas[0]

    return None


def grabar(destino, segundos=None):
    """Graba un fragmento del directo."""

    segundos = segundos or config.SEGMENTO_SEG

    for intento in range(1, 4):

        print(f"[captura] intento {intento}/3")

        url = url_directo()

        if not url:
            time.sleep(15)
            continue

        cmd = [
            "ffmpeg",
            "-y",
            "-nostdin",
            "-hide_banner",
            "-loglevel", "error",
            *_red_args(url),
            "-i", url,
            "-t", str(segundos),
            "-c", "copy",
            destino
        ]

        try:
            subprocess.run(
                cmd,
                timeout=segundos + 90
            )

        except subprocess.TimeoutExpired:
            print("[captura] tiempo de grabación excedido")

        ok = (
            os.path.exists(destino)
            and os.path.getsize(destino) > 5_000_000
        )

        if ok:
            print(f"[captura] archivo generado: {destino}")
            return True

        print("[captura] sin datos suficientes")
        time.sleep(10)

    return False


def extraer_audio(video, wav, wav_voz):
    """Extrae el audio original y mejora las voces."""

    subprocess.run([
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel", "error",
        "-i", video,
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        wav,
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-af",
        "highpass=f=80,lowpass=f=7500,"
        "dynaudnorm=f=150:g=15:p=0.9:m=20",
        wav_voz
    ], check=True)


class GrabadorContinuo:
    """Graba continuamente y recupera conexiones interrumpidas."""

    def __init__(self, carpeta, fin, avisar=None):

        self.carpeta = carpeta
        self.fin = fin
        self.avisar = avisar or (lambda texto: None)

        os.makedirs(carpeta, exist_ok=True)

        self.hilo = threading.Thread(
            target=self._correr,
            daemon=True
        )

    def iniciar(self):
        self.hilo.start()

    def vivo(self):
        return self.hilo.is_alive()

    def _correr(self):

        fallos = 0

        while time.time() < self.fin - 60:

            url = url_directo()

            if not url:

                fallos += 1

                print(
                    "[captura] directo no disponible; "
                    "reintento en 30 segundos"
                )

                if fallos == 5:
                    self.avisar(
                        "Bot Alofoke: problemas para "
                        "obtener la transmisión."
                    )

                time.sleep(30)
                continue

            restante = int(self.fin - time.time())

            if restante <= 60:
                break

            identificador = (
                f"{int(time.time())}_"
                f"{uuid.uuid4().hex[:8]}"
            )

            salida = os.path.join(
                self.carpeta,
                f"seg_{identificador}_%04d.ts"
            )

            cmd = [
                "ffmpeg",
                "-y",
                "-nostdin",
                "-hide_banner",
                "-loglevel", "warning",
                *_red_args(url),
                "-i", url,
                "-t", str(restante),
                "-c", "copy",
                "-map", "0:v:0",
                "-map", "0:a:0?",
                "-f", "segment",
                "-segment_time", str(config.SEGMENTO_SEG),
                "-reset_timestamps", "1",
                salida
            ]

            print(
                f"[captura] grabando "
                f"({restante // 60} min restantes)"
            )

            inicio = time.monotonic()

            try:

                resultado = subprocess.run(
                    cmd,
                    timeout=restante + 90
                )

                print(
                    f"[captura] FFmpeg terminó "
                    f"con código {resultado.returncode}"
                )

            except subprocess.TimeoutExpired:

                print(
                    "[captura] tiempo máximo excedido; "
                    "reiniciando conexión"
                )

            duracion = time.monotonic() - inicio

            if duracion < 30:
                fallos += 1
            else:
                fallos = 0

            if fallos == 5:
                self.avisar(
                    "Bot Alofoke: interrupciones "
                    "repetidas durante la grabación."
                )

            if time.time() < self.fin - 60:

                print(
                    "[captura] renovando URL "
                    "y reiniciando grabación"
                )

                time.sleep(10 if fallos else 5)

        print("[captura] fin del turno de grabación")
