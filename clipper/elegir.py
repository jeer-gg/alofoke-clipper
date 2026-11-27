"""Claude (tu plan Pro, vía Claude Code) elige los mejores momentos.
Si Claude no responde (límite agotado), usa un método automático de respaldo."""
import json
import re
import subprocess

from . import config


def _mmss(s):
    s = int(s)
    return f"{s // 60:02d}:{s % 60:02d}"


def _transcripcion_compacta(segmentos):
    return "\n".join(f"[{_mmss(s['inicio'])}]{' (bajito)' if s.get('bajito') else ''} {s['texto']}"
                     for s in segmentos if s["texto"])


PROMPT = """Eres el editor de una página de Facebook de clips virales de "La Casa de Alofoke 3", \
el reality dominicano que se transmite 24/7. Abajo tienes la transcripción (con marcas mm:ss) \
de {duracion} minutos del directo. Las líneas marcadas (bajito) se dijeron en voz baja.

Elige hasta {n} momentos que funcionen solos como Reel viral: discusiones, chismes, confesiones, \
secretos, estrategias para nominar, indirectas, coqueteos, momentos muy graciosos, reacciones fuertes, \
anuncios o eliminaciones. Reglas:
- Elige por lo que se DICE, no por el volumen. Lo que se habla en voz baja (bajito) suele ser lo \
mejor: secretos, chismes a espaldas de otros, planes y confesiones. Dale la misma prioridad que a una pelea.
- Los picos de volumen son solo una pista extra; un grito sin contenido no vale como clip.
- Cada clip dura entre {min_s} y {max_s} segundos, empieza justo antes de que arranque la acción \
(sin relleno) y termina después del remate. Que se entienda sin contexto.
- Descarta: momentos aburridos, silencios, publicidad o patrocinios leídos, partes donde lo principal \
es una canción sonando (la música genera reclamos de derechos), desnudos, agresiones físicas \
o cualquier cosa contra las normas de Meta.
- No elijas un momento que ya esté empezado en el segundo 00:00 o que siga después del final: \
tiene que estar completo dentro de este pedazo.
- Si nada vale la pena, devuelve una lista vacía. Mejor ningún clip que uno flojo.
- "titulo": gancho corto en MAYÚSCULAS (máx. 8 palabras), estilo farándula dominicana, sin emojis, \
sin inventar cosas que no se dicen. Usa los nombres o apodos que se mencionan.
- "descripcion": 1 o 2 frases que den contexto y una pregunta para que la gente comente. Sin emojis.
- "puntaje": 1 a 10, qué tan viral crees que será.

Responde SOLO con JSON válido, sin texto extra:
{{"clips": [{{"inicio": "mm:ss", "fin": "mm:ss", "titulo": "...", "descripcion": "...", "puntaje": 8}}]}}

PICOS DE VOLUMEN (pista extra, no decisiva): {picos}

TRANSCRIPCIÓN:
{transcripcion}
"""


def _a_segundos(valor):
    if isinstance(valor, (int, float)):
        return float(valor)
    partes = [float(p) for p in str(valor).strip().split(":")]
    total = 0.0
    for p in partes:
        total = total * 60 + p
    return total


def parsear(texto, duracion_total):
    """Extrae y valida la lista de clips del texto que devuelve Claude."""
    m = re.search(r"\{.*\}", texto, re.S)
    if not m:
        return []
    try:
        datos = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    clips = []
    for c in datos.get("clips", []):
        try:
            ini, fin = _a_segundos(c["inicio"]), _a_segundos(c["fin"])
        except (KeyError, ValueError):
            continue
        ini = max(0.0, ini - 0.5)
        fin = min(duracion_total, fin + 0.8)
        if fin - ini < config.CLIP_MIN_SEG:
            fin = min(duracion_total, ini + config.CLIP_MIN_SEG)
        if fin - ini > config.CLIP_MAX_SEG:
            fin = ini + config.CLIP_MAX_SEG
        if fin - ini < config.CLIP_MIN_SEG * 0.8:
            continue
        clips.append({
            "inicio": ini, "fin": fin,
            "titulo": str(c.get("titulo", "")).strip()[:80] or "MIRA LO QUE PASÓ EN LA CASA",
            "descripcion": str(c.get("descripcion", "")).strip()[:400],
            "puntaje": int(c.get("puntaje", 5)),
        })
    return clips


def _armar_prompt(segmentos, picos_seg, duracion_total):
    return PROMPT.format(
        duracion=round(duracion_total / 60), n=config.CLIPS_POR_SEGMENTO,
        min_s=config.CLIP_MIN_SEG, max_s=config.CLIP_MAX_SEG,
        picos=", ".join(_mmss(p) for p in picos_seg) or "ninguno",
        transcripcion=_transcripcion_compacta(segmentos))


def con_claude(segmentos, picos_seg, duracion_total):
    prompt = _armar_prompt(segmentos, picos_seg, duracion_total)
    try:
        r = subprocess.run(["claude", "-p", "--output-format", "text"], input=prompt,
                           capture_output=True, text=True, timeout=600)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print("[elegir] Claude no disponible:", e)
        return None
    if r.returncode != 0:
        print("[elegir] Claude falló:", (r.stderr or r.stdout).strip()[-500:])
        return None
    return parsear(r.stdout, duracion_total)


def con_codex(segmentos, picos_seg, duracion_total):
    """Codex CLI con la sesión de tu ChatGPT Plus (sin clave de API)."""
    import os
    import tempfile
    if not os.path.exists(os.path.expanduser("~/.codex/auth.json")):
        return None
    prompt = _armar_prompt(segmentos, picos_seg, duracion_total)
    salida = os.path.join(tempfile.gettempdir(), "codex_respuesta.txt")
    try:
        r = subprocess.run(["codex", "exec", "--skip-git-repo-check", "--sandbox", "read-only",
                            "--output-last-message", salida, "-"],
                           input=prompt, capture_output=True, text=True, timeout=600)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print("[elegir] Codex no disponible:", e)
        return None
    if r.returncode != 0 or not os.path.exists(salida):
        print("[elegir] Codex falló:", (r.stderr or r.stdout).strip()[-500:])
        return None
    with open(salida) as f:
        return parsear(f.read(), duracion_total)


def con_gemini(segmentos, picos_seg, duracion_total):
    import requests
    if not config.GEMINI_API_KEY:
        return None
    prompt = _armar_prompt(segmentos, picos_seg, duracion_total)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODELO}:generateContent"
    try:
        r = requests.post(url, timeout=180, headers={"x-goog-api-key": config.GEMINI_API_KEY}, json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.4}})
        texto = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print("[elegir] Gemini falló:", type(e).__name__, str(e)[:200])
        return None
    return parsear(texto, duracion_total)


CLAVES = ("mentira", "secreto", "no le digas", "no digas", "chisme", "traici", "nomin", "falsa", "falso",
          "hipócrita", "hipocrita", "me gusta", "te gusta", "beso", "novio", "novia", "celos", "pelea",
          "expuls", "elimin", "votar", "voto", "plan", "estrategia", "por detrás", "a espaldas",
          "me cae mal", "no la soporto", "no lo soporto", "envidia", "llor", "perdón", "perdon")


def respaldo(segmentos, z, duracion_total):
    """Sin IA: ventana de 45 s con más conversación y más palabras clave de chisme.
    El volumen pesa poco para no perder lo que se dice en voz baja."""
    import numpy as np
    n = int(duracion_total) + 1
    if n < 60:
        return []
    puntos = np.zeros(n)
    for s in segmentos:
        texto = s["texto"].lower()
        extra = 3.0 * sum(texto.count(c) for c in CLAVES)
        for w in s["palabras"]:
            i = int(w["inicio"])
            if 0 <= i < n:
                puntos[i] += 1
        i = int(s["inicio"])
        if 0 <= i < n:
            puntos[i] += extra
    if len(z):
        puntos[: len(z)] += 0.3 * np.clip(np.abs(z[:n]), 0, 3)
    largo = 45
    suma = np.convolve(puntos, np.ones(largo), "valid")
    ini = int(suma.argmax())
    return [{"inicio": float(ini), "fin": float(min(ini + largo, duracion_total)),
             "titulo": "ESTO ACABA DE PASAR EN LA CASA DE ALOFOKE 3",
             "descripcion": "Momento del directo de hoy. ¿Qué opinas de lo que pasó?",
             "puntaje": config.PUNTAJE_MINIMO}]


def sin_repetidos(clips):
    """Si dos clips comparten más del 40 % del tiempo, se queda el de mayor puntaje."""
    clips = sorted(clips, key=lambda c: -c["puntaje"])
    quedan = []
    for c in clips:
        repetido = False
        for q in quedan:
            comun = min(c["fin"], q["fin"]) - max(c["inicio"], q["inicio"])
            if comun > 0.4 * min(c["fin"] - c["inicio"], q["fin"] - q["inicio"]):
                repetido = True
                break
        if not repetido:
            quedan.append(c)
    return quedan


def marcar_bajito(segmentos, z):
    """Marca las frases dichas claramente más bajo que el promedio del pedazo."""
    import numpy as np
    for s in segmentos:
        a, b = int(s["inicio"]), max(int(s["inicio"]) + 1, int(s["fin"]))
        tramo = z[a:b] if len(z) else []
        s["bajito"] = bool(len(tramo)) and float(np.mean(tramo)) < -0.6


def elegir(segmentos, z, picos_seg, duracion_total):
    marcar_bajito(segmentos, z)
    clips = None
    for nombre in config.ELEGIDORES:
        funcion = {"claude": con_claude, "gemini": con_gemini, "codex": con_codex}.get(nombre)
        if funcion:
            clips = funcion(segmentos, picos_seg, duracion_total)
            if clips is not None:
                print(f"[elegir] eligió: {nombre}")
                break
    if clips is None:
        print("[elegir] uso el método de respaldo")
        clips = respaldo(segmentos, z, duracion_total)
    clips = sin_repetidos(clips)
    print(f"[elegir] {len(clips)} clips: " + "; ".join(f"{c['puntaje']} {c['titulo']}" for c in clips))
    return clips[: config.CLIPS_POR_SEGMENTO]
