"""Guarda los clips pendientes y el estado del día en un 'release' del repo
llamado 'cola', para que sobrevivan entre corridas de GitHub Actions."""
import json
import os
import subprocess

from . import config

TAG = "cola"


def _gh(*args, check=False, intentos=3):
    """Llama a gh con reintentos: un fallo pasajero de GitHub no debe tumbar el bot."""
    import time
    r = None
    for i in range(intentos):
        r = subprocess.run(["gh", *args, "-R", config.REPO], capture_output=True, text=True)
        if r.returncode == 0:
            return r
        time.sleep(5 * (i + 1))
    if check:
        raise RuntimeError(f"gh {' '.join(args[:2])} falló: {r.stderr.strip()[-300:]}")
    return r


def preparar():
    if _gh("release", "view", TAG).returncode != 0:
        _gh("release", "create", TAG, "-t", "Cola del bot", "-n",
            "Clips pendientes y estado. No borrar.", "--latest=false", check=True)


def descargar(carpeta):
    """Baja estado.json y los .json de la cola. Los .mp4 se bajan solo al publicarlos."""
    os.makedirs(carpeta, exist_ok=True)
    _gh("release", "download", TAG, "-D", carpeta, "-p", "*.json", "--clobber")
    estado_ruta = os.path.join(carpeta, "estado.json")
    estado = {}
    if os.path.exists(estado_ruta):
        with open(estado_ruta) as f:
            estado = json.load(f)
    pendientes = []
    for nombre in sorted(os.listdir(carpeta)):
        if nombre.startswith("clip-") and nombre.endswith(".json"):
            with open(os.path.join(carpeta, nombre)) as f:
                pendientes.append(json.load(f))
    return estado, pendientes


def bajar_video(nombre, carpeta):
    _gh("release", "download", TAG, "-D", carpeta, "-p", nombre, "--clobber")
    ruta = os.path.join(carpeta, nombre)
    return ruta if os.path.exists(ruta) else None


def subir(*rutas):
    _gh("release", "upload", TAG, *rutas, "--clobber", check=True)


def borrar(*nombres):
    for n in nombres:
        _gh("release", "delete-asset", TAG, n, "-y")


def entregar_pendientes(rutas):
    """Al terminar un turno, sube los pedazos sin procesar para que el siguiente turno los procese."""
    import os
    nombres = []
    for ruta in rutas:
        destino = os.path.join(os.path.dirname(ruta), "pend-" + os.path.basename(ruta))
        os.rename(ruta, destino)
        if _gh("release", "upload", TAG, destino, "--clobber").returncode == 0:
            nombres.append(os.path.basename(destino))
    return nombres


def recibir_pendientes(carpeta):
    """Al empezar un turno, baja los pedazos que dejó el turno anterior."""
    import os
    r = _gh("release", "view", TAG, "--json", "assets", "-q", ".assets[].name")
    nombres = [n for n in (r.stdout.split() if r and r.returncode == 0 else []) if n.startswith("pend-")]
    recibidos = []
    for n in sorted(nombres):
        _gh("release", "download", TAG, "-D", carpeta, "-p", n, "--clobber")
        origen = os.path.join(carpeta, n)
        if os.path.exists(origen):
            destino = os.path.join(carpeta, n[len("pend-"):])
            os.rename(origen, destino)
            recibidos.append(destino)
        _gh("release", "delete-asset", TAG, n, "-y")
    return recibidos


def guardar_estado(estado, carpeta):
    ruta = os.path.join(carpeta, "estado.json")
    with open(ruta, "w") as f:
        json.dump(estado, f, ensure_ascii=False, indent=1)
    subir(ruta)
