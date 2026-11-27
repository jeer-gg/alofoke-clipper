"""Reencuadre cuadrado: detección facial local y movimiento, no identificación."""
try:
    import cv2
except Exception:
    cv2 = None
import numpy as np
import subprocess


def objetivo(rostros, movimiento, w, h):
    # Con varias caras, mantener el grupo si cabe en un recorte cuadrado.
    base = min(w, h)
    if len(rostros):
        x1 = min(x for x,y,a,b in rostros); x2 = max(x+a for x,y,a,b in rostros)
        y1 = min(y for x,y,a,b in rostros); y2 = max(y+b for x,y,a,b in rostros)
        lado = base if len(rostros)>1 else max(base/1.25, min(base, max(x2-x1,y2-y1)*3.5))
        return (x1+x2)/2, (y1+y2)/2 + lado*.13, lado
    if movimiento is not None:
        return movimiento[0], movimiento[1], base
    return w/2,h/2,base


def recorte(frame, centro):
    h,w = frame.shape[:2]; x,y,lado = centro
    lado = max(2,min(w,h,int(round(lado))))
    x = max(0,min(w-lado,int(round(x-lado/2))))
    y = max(0,min(h-lado,int(round(y-lado/2))))
    return cv2.resize(frame[y:y+lado,x:x+lado], (1080,1080), interpolation=cv2.INTER_LINEAR)


def _renderizar_dinamico(origen, salida):
    cv2.setNumThreads(2)
    detector = cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
    if detector.empty(): raise RuntimeError('detector facial no disponible')
    cap = cv2.VideoCapture(origen)
    if not cap.isOpened(): raise RuntimeError('no se pudo abrir el video')
    cmd = ['ffmpeg','-y','-nostdin','-loglevel','error','-f','rawvideo','-pixel_format','bgr24','-video_size','1080x1080','-framerate','30','-i','-','-an','-c:v','libx264','-threads','2','-preset','veryfast','-crf','18','-pix_fmt','yuv420p',salida]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    anterior = None; actual = None; meta = None; n=0; ultimo_cambio=-60
    try:
        while True:
            ok, frame = cap.read()
            if not ok: break
            h,w = frame.shape[:2]
            if n%10==0:
                escala = min(1, 480/w)
                gris = cv2.cvtColor(cv2.resize(frame, (round(w*escala),round(h*escala))),cv2.COLOR_BGR2GRAY)
                cambio = anterior is not None and np.mean(cv2.absdiff(gris,anterior))>38
                caras = detector.detectMultiScale(cv2.equalizeHist(gris), scaleFactor=1.12,minNeighbors=5,minSize=(22,22))
                caras = [tuple(float(v)/escala for v in r) for r in caras]
                mov = None
                if anterior is not None and not cambio:
                    diferencia = cv2.absdiff(gris,anterior)
                    mascara = (diferencia>25).astype(np.uint8)
                    m = cv2.moments(mascara)
                    if .015*mascara.size < m['m00'] < .35*mascara.size:
                        mov=(m['m10']/m['m00']/escala,m['m01']/m['m00']/escala)
                candidato = np.array(objetivo(caras,mov,w,h))
                if actual is None or cambio:
                    actual = candidato.copy(); meta=candidato; ultimo_cambio=n
                elif n-ultimo_cambio>=30:
                    # Sin detección fiable, mantener la toma y volver a plano amplio.
                    if not caras and mov is None:
                        candidato[:2]=actual[:2]
                    meta=candidato; ultimo_cambio=n
                anterior=gris
            actual += (meta-actual)*.065
            proc.stdin.write(recorte(frame,actual).tobytes()); n+=1
        proc.stdin.close()
        if proc.wait(timeout=60) or not n: raise RuntimeError('falló render cuadrado')
    finally:
        cap.release()
        if proc.poll() is None:
            proc.kill(); proc.wait()
    print(f'[encuadre] {n} cuadros; recorte cuadrado dinámico local')


def verificar_opencv():
    if cv2 is None:
        raise RuntimeError("OpenCV no disponible")
    detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    if detector.empty():
        raise RuntimeError("clasificador facial vacío")
    return cv2.__version__


def _centrado(origen, salida):
    subprocess.run(["ffmpeg", "-y", "-nostdin", "-loglevel", "error",
                    "-i", origen, "-an", "-vf",
                    "crop='min(iw,ih)':'min(iw,ih)',scale=1080:1080,setsar=1,fps=30",
                    "-c:v", "libx264", "-threads", "2", "-preset", "veryfast",
                    "-crf", "18", "-pix_fmt", "yuv420p", salida],
                   check=True, timeout=360)


def renderizar(origen, salida):
    import os
    try:
        verificar_opencv()
        _renderizar_dinamico(origen, salida)
    except Exception as exc:
        print(f"[encuadre] zoom no disponible ({type(exc).__name__}); recorte centrado de respaldo")
        if os.path.exists(salida):
            os.remove(salida)
        _centrado(origen, salida)
