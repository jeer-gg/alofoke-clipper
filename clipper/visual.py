"""Muestreo visual acotado: contacto regular y pares de movimiento."""
import base64


def partes(video, duracion):
    import cv2
    import numpy as np
    cap = cv2.VideoCapture(video)
    muestras = []
    try:
        if not cap.isOpened():
            return []
        paso = max(3, int(duracion / 200) + 1)
        anterior = None
        for t in range(0, int(duracion), paso):
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ok, frame = cap.read()
            if not ok:
                anterior = None
                continue
            h, w = frame.shape[:2]
            frame = cv2.resize(frame, (480, max(1, round(h * 480 / w))))
            gris = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (64, 36))
            cambio = float(np.mean(cv2.absdiff(gris, anterior))) if anterior is not None else 0
            anterior = gris
            ok, jpg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 72])
            if ok:
                muestras.append((t, cambio, jpg.tobytes()))
    finally:
        cap.release()
    if not muestras:
        return []
    # Cobertura de toda la escena y pares cercanos a cambios intensos.
    indices = set(np.linspace(0, len(muestras)-1, min(20, len(muestras)), dtype=int).tolist())
    picos = []
    for i in sorted(range(1, len(muestras)), key=lambda i: -muestras[i][1]):
        if muestras[i][1] < 5 or any(abs(i-j)<4 for j in picos):
            continue
        picos.append(i)
        indices.update((i-1, i))
        if len(picos) == 8:
            break
    salida = []
    for i in sorted(indices):
        t, _, jpg = muestras[i]
        salida.extend([{'text': f'Fotograma aproximado {t//60:02d}:{t%60:02d}'},
                       {'inline_data': {'mime_type':'image/jpeg','data':base64.b64encode(jpg).decode('ascii')}}])
    print(f'[visual] {len(indices)} fotogramas enviados como máximo por análisis')
    return salida
