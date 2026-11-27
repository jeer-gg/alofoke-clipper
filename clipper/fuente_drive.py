"""Fuente de video: grabaciones de pantalla que subes a una carpeta de Google Drive.

La carpeta debe estar compartida como "Cualquier persona con el enlace: Lector".
Cada video nuevo se descarga, se pasa a 720p horizontal (respetando la rotación del
iPhone) y queda listo en la carpeta de pedazos para que el bot lo procese."""
import os
import subprocess
import threading
import time

from . import config


def _listar(url_carpeta):
    """Devuelve [(id, nombre)] de los videos de la carpeta pública."""
    import gdown
    try:
        archivos = gdown.download_folder(url=url_carpeta, skip_download=True, quiet=True) or []
    except Exception as e:
        print("[drive] no pude leer la carpeta:", type(e).__name__, str(e)[:200])
        return None
    salida = []
    for a in archivos:
        nombre = os.path.basename(getattr(a, "path", "") or getattr(a, "local_path", ""))
        if nombre.lower().endswith((".mp4", ".mov", ".m4v", ".mkv", ".ts", ".webm")):
            salida.append((a.id, nombre))
    return salida


def _normalizar(origen, destino):
    """Pasa el video a 720p horizontal en H.264 (ffmpeg aplica la rotación del iPhone)."""
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", origen,
                    "-vf", "scale=-2:720", "-r", "30",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
                    "-c:a", "aac", "-b:a", "128k", "-f", "mpegts", destino], check=True)


class FuenteDrive:
    """Revisa la carpeta cada pocos minutos hasta `fin` y deja cada video nuevo
    como seg_<hora>_drive.ts. `vistos` es la lista de ids ya procesados (persistente)."""

    archivos_completos = True  # cada archivo llega entero: no hay que esperar al último

    def __init__(self, carpeta, fin, vistos, avisar=None, cada_seg=180):
        self.carpeta, self.fin, self.vistos = carpeta, fin, vistos
        self.avisar = avisar or (lambda texto: None)
        self.cada_seg = cada_seg
        os.makedirs(carpeta, exist_ok=True)
        self.hilo = threading.Thread(target=self._correr, daemon=True)

    def iniciar(self):
        self.hilo.start()

    def vivo(self):
        return self.hilo.is_alive()

    def _correr(self):
        import gdown
        fallos = 0
        while time.time() < self.fin - 60:
            lista = _listar(config.DRIVE_CARPETA)
            if lista is None:
                fallos += 1
                if fallos == 3:
                    self.avisar("Bot Alofoke: no puedo leer la carpeta de Google Drive. Revisa que esté "
                                "compartida como 'Cualquier persona con el enlace' y que el enlace en "
                                "DRIVE_CARPETA sea el correcto.")
            else:
                fallos = 0
                nuevos = [(i, n) for i, n in lista if i not in self.vistos]
                for fid, nombre in nuevos:
                    if time.time() > self.fin - 300:
                        break
                    print(f"[drive] descargando {nombre}")
                    crudo = os.path.join(self.carpeta, f"crudo_{fid}")
                    try:
                        gdown.download(id=fid, output=crudo, quiet=True)
                        destino = os.path.join(self.carpeta, f"seg_{int(time.time())}_drive.ts")
                        parcial = destino + ".parcial"
                        _normalizar(crudo, parcial)
                        os.rename(parcial, destino)  # aparece completo de una vez
                        print(f"[drive] listo: {nombre}")
                    except Exception as e:
                        print(f"[drive] falló {nombre}:", e)
                        self.avisar(f"Bot Alofoke: no pude descargar o leer el video '{nombre}' de Drive.")
                    finally:
                        if os.path.exists(crudo):
                            os.remove(crudo)
                    self.vistos.append(fid)
                del self.vistos[:-500]  # recuerda los últimos 500
            time.sleep(self.cada_seg)
        print("[drive] fin del turno")
