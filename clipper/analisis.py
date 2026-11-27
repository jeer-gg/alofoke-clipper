"""Transcripción con Whisper (sensible a la voz baja) y medición de volumen."""
import wave

import numpy as np

from . import config


def transcribir(wav):
    """Lista de segmentos: {inicio, fin, texto, palabras:[{inicio, fin, texto}]}."""
    from faster_whisper import WhisperModel
    import os
    modelo = WhisperModel(config.WHISPER_MODELO, device="cpu", compute_type="int8",
                          cpu_threads=os.cpu_count() or 4)
    segmentos, _ = modelo.transcribe(wav, language="es", word_timestamps=True,
                                     vad_filter=True, beam_size=1,
                                     vad_parameters={"threshold": 0.3, "min_silence_duration_ms": 700})
    salida = []
    for s in segmentos:
        palabras = [{"inicio": w.start, "fin": w.end, "texto": w.word.strip()}
                    for w in (s.words or []) if w.word.strip()]
        salida.append({"inicio": s.start, "fin": s.end, "texto": s.text.strip(),
                       "palabras": palabras})
    print(f"[analisis] {len(salida)} segmentos transcritos")
    return salida


def energia_por_segundo(wav):
    """Volumen (RMS) de cada segundo, normalizado como puntaje z."""
    with wave.open(wav, "rb") as w:
        sr = w.getframerate()
        datos = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
    n = len(datos) // sr
    if n == 0:
        return np.zeros(0)
    bloques = datos[: n * sr].reshape(n, sr)
    rms = np.sqrt((bloques ** 2).mean(axis=1)) + 1e-6
    db = 20 * np.log10(rms)
    return (db - db.mean()) / (db.std() + 1e-6)


def picos(z, umbral=2.0, separacion=20):
    """Segundos donde el volumen se dispara, separados al menos `separacion` s."""
    candidatos = sorted(np.where(z > umbral)[0], key=lambda i: -z[i])
    elegidos = []
    for i in candidatos:
        if all(abs(i - j) >= separacion for j in elegidos):
            elegidos.append(int(i))
        if len(elegidos) >= 15:
            break
    return sorted(elegidos)
