"""Convierte un pedazo del directo en un Reel 9:16 con título y subtítulos grandes."""
import subprocess

from . import config

ANCHO, ALTO = 1080, 1920


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
PlayResY: {ALTO}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Titulo,DejaVu Sans,78,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,6,3,2,60,60,0,1
Style: Sub,DejaVu Sans,84,&H0000E5FF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,7,2,5,50,50,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    eventos = [f"Dialogue: 1,{_t(0)},{_t(dur)},Titulo,,0,0,0,,"
               f"{{\\pos({ANCHO // 2},{y_titulo})\\fad(150,0)}}{_partir_titulo(clip['titulo'].upper())}"]

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


def editar(video, clip, segmentos, salida, ancho_fuente=1280, alto_fuente=720):
    alto_video = int(round(ANCHO / (ancho_fuente * config.ZOOM / alto_fuente) / 2) * 2)
    ass = salida.replace(".mp4", ".ass")
    crear_ass(clip, segmentos, ass, alto_video)
    filtro = (
        "[0:v]split[a][b];"
        f"[a]scale={ANCHO}:{ALTO}:force_original_aspect_ratio=increase,crop={ANCHO}:{ALTO},"
        "boxblur=25:2,eq=brightness=-0.18[fondo];"
        f"[b]crop=iw*{config.ZOOM}:ih,scale={ANCHO}:{alto_video}[frente];"
        f"[fondo][frente]overlay=(W-w)/2:(H-h)/2,ass={ass},fps=30,format=yuv420p[v]"
    )
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-ss", f"{clip['inicio']:.2f}", "-t", f"{clip['fin'] - clip['inicio']:.2f}", "-i", video,
           "-filter_complex", filtro, "-map", "[v]", "-map", "0:a?",
           "-af", "dynaudnorm=f=150:g=15:p=0.9:m=10,loudnorm=I=-14:TP=-1.5:LRA=11",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
           "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
           "-t", f"{clip['fin'] - clip['inicio']:.2f}", "-movflags", "+faststart", salida]
    subprocess.run(cmd, check=True)
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
