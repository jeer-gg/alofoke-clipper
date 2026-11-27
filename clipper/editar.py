"""Edición cuadrada adaptativa local, sin consultas adicionales de IA."""
import subprocess
import os
import re
import tempfile

from . import config

ANCHO, ALTO = 1080, 1080


def _t(seg):
    seg = max(0.0, seg)
    h, r = divmod(seg, 3600)
    m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _limpio(texto):
    return texto.replace("{", "(").replace("}", ")").replace("\\", "").replace("\n", " ")


def _partir_titulo(titulo, max_chars=20):
    """Parte el título en líneas cortas para que se lea grande."""
    lineas, actual = [], ""
    for p in titulo.split():
        if len(actual) + len(p) + 1 > max_chars and actual:
            lineas.append(actual)
            actual = p
        else:
            actual = f"{actual} {p}".strip()
    if actual:
        lineas.append(actual)
    return r"\N".join(_limpio(l) for l in lineas[:3])


def crear_ass(clip, segmentos, ruta, alto_video):
    ini, fin = clip["inicio"], clip["fin"]
    dur = fin - ini
    y_video_arriba = (ALTO - alto_video) // 2
    y_titulo = max(160, y_video_arriba - 40)          # justo encima del video
    y_subs = y_video_arriba + alto_video + 230         # debajo del video

    cab = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {ANCHO}
PlayResY: {alto_video}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Titulo,DejaVu Sans,78,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,6,3,2,60,60,0,1
Style: Sub,DejaVu Sans,48,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,5,50,50,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    eventos = []
    y_subs = int(alto_video*.78)
    blanco = str(clip.get("gancho_blanco") or clip.get("titulo") or "").upper()
    amarillo = str(clip.get("gancho_amarillo") or "¿QUÉ PASÓ DESPUÉS?").upper()
    def linea(texto):
        return _limpio(" ".join(texto.split()[:8]))[:80]
    for i, (texto, color) in enumerate(((blanco, "FFFFFF"), (amarillo, "00FFFF"))):
        texto = linea(texto)
        if texto:
            tam = min(68, max(12, int(930 / max(1,len(texto)) / .72)))
            y = int(alto_video*.085) + i*76
            eventos.append(f"Dialogue: 1,0:00:00.00,{_t(dur)},Titulo,,0,0,0,,"
                           + r"{\an8\pos(" + f"540,{y}" + r")\fs" + str(tam) + r"\1c&H" + color + r"&}" + texto)
    if not config.SUBTITULOS:
        segmentos = []

    palabras = [w for s in segmentos for w in s["palabras"] if w["fin"] > ini and w["inicio"] < fin]
    grupo = []
    for i, w in enumerate(palabras):
        grupo.append(w)
        siguiente = palabras[i + 1] if i + 1 < len(palabras) else None
        corta = (len(grupo) >= 3 or siguiente is None
                 or siguiente["inicio"] - w["fin"] > 0.6
                 or w["texto"].endswith((".", "?", "!", ",")))
        if corta:
            a = grupo[0]["inicio"] - ini
            b = (min(siguiente["inicio"], grupo[-1]["fin"] + 0.5) if siguiente else grupo[-1]["fin"] + 0.3) - ini
            texto = " ".join(x["texto"] for x in grupo).upper()
            eventos.append(f"Dialogue: 0,{_t(a)},{_t(min(b, dur))},Sub,,0,0,0,,"
                           f"{{\\pos({ANCHO // 2},{y_subs})}}{_limpio(texto)}")
            grupo = []
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(cab + "\n".join(eventos) + "\n")



def _congelamiento_inicial(video, bruto=False):
    """Detecta inmovilidad inicial en la imagen, no en los textos animados."""
    import numpy as np
    # En el Reel se analiza toda la franja central, sin título ni subtítulos.
    region = "" if bruto else "crop=iw:ih*0.55:0:ih*0.30,"
    r = subprocess.run([
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-i", video, "-t", "12", "-an",
        "-vf", region + "fps=10,scale=320:96,format=gray",
        "-f", "rawvideo", "-pix_fmt", "gray", "-"
    ], capture_output=True, timeout=90, check=True)
    n = 320 * 96
    if len(r.stdout) < n * 6 or len(r.stdout) % n:
        raise RuntimeError("no hay suficientes fotogramas para verificar el inicio")
    frames = np.frombuffer(r.stdout, dtype=np.uint8).reshape(-1, 96, 320).astype(np.int16)
    # Diferencia con el primer cuadro en bloques: tolera ruido de compresión
    # y detecta movimiento localizado aunque el resto de la escena sea estático.
    diff = np.abs(frames - frames[0]).reshape(-1, 6, 16, 10, 32).mean(axis=(2,4))
    movimiento = (diff.max(axis=(1,2)) >= 2.5) | (diff.mean(axis=(1,2)) >= 0.65)
    for i in range(1, len(frames)-2):
        if movimiento[i:i+3].all():
            return 0.0 if i < 6 else i / 10
    raise RuntimeError("inicio inmóvil sin recuperación verificable en 12 s")


def corregir_inicio(video, minimo=1.0):
    """Recorta audio, imagen y subtítulos incrustados juntos; verifica el resultado."""
    corte = _congelamiento_inicial(video)
    if not corte:
        return 0.0
    if duracion(video) - corte < minimo:
        raise RuntimeError("eliminar el congelamiento dejaría un clip demasiado corto")
    fd, temporal = tempfile.mkstemp(suffix=".mp4", dir=os.path.dirname(os.path.abspath(video)))
    os.close(fd)
    try:
        subprocess.run([
            "ffmpeg", "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
            "-i", video, "-ss", f"{corte:.6f}",
            "-map", "0:v:0", "-map", "0:a:0?",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart", temporal
        ], check=True, timeout=180)
        if duracion(temporal) < minimo or _congelamiento_inicial(temporal):
            raise RuntimeError("el clip sigue defectuoso después de corregir el inicio")
        os.replace(temporal, video)
        print(f"[editar] congelamiento inicial eliminado: {corte:.2f} s")
        return corte
    finally:
        if os.path.exists(temporal):
            os.remove(temporal)

def editar(video, clip, segmentos, salida, ancho_fuente=1280, alto_fuente=720):
    # Primero se decodifica el fragmento sin overlays. El seek de salida evita
    # depender de un fotograma clave anterior para el comienzo exacto.
    alto_video = ALTO
    ass = salida.replace(".mp4", ".ass")
    minimo = config.CLIP_MIN_SEG * 0.7
    inicio, fin = float(clip["inicio"]), float(clip["fin"])
    try:
        with tempfile.TemporaryDirectory(dir=os.path.dirname(os.path.abspath(salida))) as tmp:
            bruto = os.path.join(tmp, "bruto.mp4")
            # Seek grueso 10 s antes, seguido de seek preciso al decodificar.
            grueso = max(0, inicio - 10)
            subprocess.run([
                "ffmpeg", "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
                "-fflags", "+genpts", "-ss", str(grueso), "-i", video,
                "-ss", str(inicio-grueso), "-t", str(fin-inicio),
                "-map", "0:v:0", "-map", "0:a:0?", "-vf", "scale=iw*sar:ih,setsar=1,fps=30",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", bruto
            ], check=True, timeout=240)
            corte = _congelamiento_inicial(bruto, bruto=True)
            disponible = min(fin-inicio, duracion(bruto))
            if disponible - corte < minimo:
                raise RuntimeError("fragmento demasiado corto después de validar inicio")
            ajustado = dict(clip, inicio=inicio+corte, fin=inicio+disponible)
            if corte:
                print(f"[editar] congelamiento fuente eliminado: {corte:.2f} s")
            from . import encuadre
            limpio = os.path.join(tmp, "limpio.mp4")
            subprocess.run([
                "ffmpeg", "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
                "-i", bruto, "-ss", str(corte), "-t", str(disponible-corte),
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
                "-c:a", "aac", limpio
            ], check=True, timeout=240)
            # Confirmar movimiento real antes de que el zoom pueda ocultar un fallo.
            if _congelamiento_inicial(limpio, bruto=True):
                raise RuntimeError("la fuente todavía empieza congelada")
            visual = os.path.join(tmp, "visual.mp4")
            encuadre.renderizar(limpio, visual)
            filtro = "setsar=1"
            alto_video = tamano_video(visual)[1]
            crear_ass(ajustado, segmentos, ass, alto_video)
            filtro += ",ass=" + ass
            subprocess.run([
                "ffmpeg", "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
                "-i", visual, "-i", limpio, "-map", "0:v:0", "-map", "1:a:0?",
                "-vf", filtro, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                "-ar", "48000", "-shortest", "-movflags", "+faststart", salida
            ], check=True, timeout=360)
            corregir_inicio(salida, minimo=minimo)
            print("[editar] inicio verificado: " + os.path.basename(salida))
    except Exception:
        if os.path.exists(salida):
            os.remove(salida)
        raise
    finally:
        if os.path.exists(ass):
            os.remove(ass)
    return salida


def tamano_video(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height", "-of", "csv=p=0", video],
                       capture_output=True, text=True)
    try:
        w, h = r.stdout.strip().split("\n")[0].split(",")[:2]
        return int(w), int(h)
    except ValueError:
        return 1280, 720


def duracion(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", video], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def marcar_pagina(video, salida, nombre):
    """Marca textual propia, sin reutilizar logos ajenos."""
    with tempfile.TemporaryDirectory() as tmp:
        texto = os.path.join(tmp, 'marca.txt')
        with open(texto, 'w', encoding='utf-8') as f:
            f.write(str(nombre).replace('\n', ' ')[:60])
        filtro = ('drawtext=font=DejaVu Sans:fontcolor=white:fontsize=32:'
                  f'textfile={texto}:expansion=none:x=36:y=h-th-85:'
                  'box=1:boxcolor=black@0.65:boxborderw=12')
        subprocess.run(['ffmpeg','-y','-nostdin','-loglevel','error','-i',video,
                        '-vf',filtro,'-c:v','libx264','-preset','veryfast','-crf','20',
                        '-c:a','copy','-movflags','+faststart',salida],check=True,timeout=240)
