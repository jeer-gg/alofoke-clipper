"""Bot clipper 24/7 de La Casa de Alofoke 3.

Cada turno de GitHub Actions graba el directo SIN PARAR durante 4 horas, en pedazos de 1 hora.
Mientras graba, procesa cada pedazo terminado:
  transcribe -> la IA elige los momentos -> edita Reels 9:16 -> cola -> publica el mejor cuando toca.
Al final del turno, los pedazos que no alcanzó a procesar se le entregan al siguiente turno,
que ya está en fila. Así no hay huecos en la grabación."""
import glob
import json
import os
import shutil
import subprocess
import time
import traceback
from datetime import datetime

from clipper import analisis, captura, cola, config, editar, elegir, publicar

TRABAJO = "trabajo"
SEG_DIR = os.path.join(TRABAJO, "segmentos")
COLA_DIR = os.path.join(TRABAJO, "cola")
SOLAPE_SEG = 90  # se repiten los últimos 90 s de la hora anterior para no partir momentos


def ahora():
    return datetime.now(config.ZONA)


def descripcion(clip):
    return f"{clip['titulo']}\n\n{clip['descripcion']}\n\n{config.HASHTAGS}".strip()


def _ffmpeg(*args):
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args], check=True)


class Bot:
    def __init__(self):
        cola.preparar()
        self.estado, self.cola = cola.descargar(COLA_DIR)
        self.estado.pop("publicaciones", None)  # formato viejo (una sola página)
        self.producidos = 0
        self.sin_clips_seguidos = 0
        self.cola_previa = None  # últimos segundos del pedazo anterior

    # ---------- producción ----------
    def _unir_con_previa(self, video):
        """Pega los últimos 90 s del pedazo anterior al inicio de este."""
        if not (self.cola_previa and os.path.exists(self.cola_previa)):
            return video, 0.0
        unido = os.path.join(TRABAJO, "unido_" + os.path.basename(video))  # fuera de SEG_DIR
        try:
            _ffmpeg("-i", f"concat:{self.cola_previa}|{video}", "-c", "copy",
                    "-fflags", "+genpts", unido)
            return unido, editar.duracion(self.cola_previa)
        except subprocess.CalledProcessError:
            return video, 0.0

    def _guardar_cola_previa(self, video):
        previa = os.path.join(TRABAJO, "previa.ts")
        try:
            _ffmpeg("-sseof", f"-{SOLAPE_SEG}", "-i", video, "-c", "copy", previa)
            self.cola_previa = previa
        except subprocess.CalledProcessError:
            self.cola_previa = None

    def procesar_segmento(self, original):
        if editar.duracion(original) < 60:
            return
        video, solape = self._unir_con_previa(original)
        self._guardar_cola_previa(original)
        dur = editar.duracion(video)
        wav = video.replace(".ts", ".wav")
        wav_voz = video.replace(".ts", "_voz.wav")
        try:
            captura.extraer_audio(video, wav, wav_voz)
            segmentos = analisis.transcribir(wav_voz)
            if not segmentos:
                return
            z = analisis.energia_por_segundo(wav)
            elegidos = elegir.elegir(segmentos, z, analisis.picos(z), dur)
            # Un clip que termina dentro del solape ya lo vio la hora anterior.
            elegidos = [c for c in elegidos if c["fin"] > solape + 5]
            ancho, alto = editar.tamano_video(video)
            sello = int(time.time())
            nuevos = 0
            for i, clip in enumerate(elegidos):
                if clip["puntaje"] < config.PUNTAJE_MINIMO:
                    continue
                nombre = f"clip-{sello}-{i}"
                salida = os.path.join(TRABAJO, nombre + ".mp4")
                try:
                    editar.editar(video, clip, segmentos, salida, ancho, alto)
                    if editar.duracion(salida) < config.CLIP_MIN_SEG * 0.7:
                        raise RuntimeError("el clip salió demasiado corto")
                except Exception as e:
                    print(f"[main] no se pudo editar {nombre}: {e}")
                    continue
                clip.update({"nombre": nombre, "creado": sello})
                meta = os.path.join(TRABAJO, nombre + ".json")
                with open(meta, "w") as f:
                    json.dump(clip, f, ensure_ascii=False)
                try:
                    cola.subir(salida, meta)
                except RuntimeError as e:
                    print("[main] no se pudo guardar en la cola (queda solo en este turno):", e)
                clip["ruta"] = salida
                self.cola.append(clip)
                self.producidos += 1
                nuevos += 1
                if config.ENVIAR_TODOS_TELEGRAM:
                    publicar.telegram(f"[{clip['puntaje']}/10] {descripcion(clip)}", salida)
            self.sin_clips_seguidos = 0 if nuevos else self.sin_clips_seguidos + 1
            if self.sin_clips_seguidos >= 3:
                publicar.telegram("Bot Alofoke: van 3 horas seguidas sin clips buenos. Revisa los "
                                  "registros en Actions por si la IA o la transcripción fallan.",
                                  clave="sin_clips", cada_min=180)
            self.podar_cola()
        finally:
            for f in (wav, wav_voz, video if video != original else None):
                if f and os.path.exists(f):
                    os.remove(f)

    def podar_cola(self):
        """Bota lo viejo y deja solo los MAX_COLA mejores."""
        limite = time.time() - config.MAX_EDAD_HORAS * 3600
        vivos = [c for c in self.cola if c["creado"] >= limite]
        vivos.sort(key=lambda c: (-c["puntaje"], -c["creado"]))
        quedan, sobran = vivos[: config.MAX_COLA], vivos[config.MAX_COLA:]
        sobran += [c for c in self.cola if c["creado"] < limite]
        for c in sobran:
            cola.borrar(c["nombre"] + ".mp4", c["nombre"] + ".json")
            if c.get("ruta") and os.path.exists(c["ruta"]):
                os.remove(c["ruta"])
        self.cola = quedan

    # ---------- publicación ----------
    def _pagina(self, pid):
        return self.estado.setdefault("paginas", {}).setdefault(pid, {"publicaciones": []})

    def puede_publicar(self, pagina):
        """Cada página tiene su propio límite de 30 Reels en 24 h."""
        t = time.time()
        p = self._pagina(pagina["id"])
        p["publicaciones"] = [x for x in p["publicaciones"] if t - x < 86400]
        if t < p.get("reintentar_desde", 0):
            return False
        if not (config.HORA_INICIO <= ahora().hour < config.HORA_FIN):
            return False
        if len(p["publicaciones"]) >= config.MAX_POR_DIA:
            return False
        return t - max(p["publicaciones"], default=0) >= config.MIN_ENTRE_POSTS * 60

    def total_24h(self):
        return sum(len(self._pagina(pg["id"])["publicaciones"]) for pg in config.FB_PAGINAS)

    def _guardar_estado(self):
        try:
            cola.guardar_estado(self.estado, COLA_DIR)
        except Exception as e:
            print("[main] no se pudo guardar el estado (se reintenta luego):", e)

    def intentar_publicar(self):
        # Recorre las páginas: a cada una le toca el mejor clip que quede (nunca el mismo).
        for pagina in config.FB_PAGINAS:
            if not self.cola or not self.puede_publicar(pagina):
                continue
            self.podar_cola()
            if not self.cola:
                return
            clip = self.cola[0]
            ruta = clip.get("ruta") if clip.get("ruta") and os.path.exists(clip["ruta"]) else \
                cola.bajar_video(clip["nombre"] + ".mp4", COLA_DIR)
            if not ruta:
                self.cola.pop(0)
                continue
            datos = self._pagina(pagina["id"])
            nombre = pagina["nombre"]
            try:
                if config.MODO_PRUEBA:
                    vid, estado_fb = "prueba", "ready"
                else:
                    vid = publicar.reel(ruta, descripcion(clip), pagina["id"], pagina["token"])
                    estado_fb = publicar.estado_reel(vid, pagina["token"])
            except publicar.ErrorFacebook as e:
                print(f"[main] error al publicar en {nombre}:", e)
                if e.token_malo:
                    datos["reintentar_desde"] = time.time() + 6 * 3600
                    publicar.telegram(f"Bot Alofoke: el token de {nombre} venció o perdió permisos. "
                                      f"Pausé esa página 6 horas. Saca un token nuevo y cámbialo en "
                                      f"el secreto FB_PAGINAS. Detalle: {e.mensaje}",
                                      clave=f"token_{pagina['id']}", cada_min=360)
                elif e.limite:
                    datos["reintentar_desde"] = time.time() + 2 * 3600
                    publicar.telegram(f"Bot Alofoke: Facebook frenó a {nombre} por límite. "
                                      f"Pauso 2 horas. Detalle: {e.mensaje}",
                                      clave=f"limite_{pagina['id']}", cada_min=120)
                else:
                    datos["reintentar_desde"] = time.time() + 15 * 60
                    publicar.telegram(f"Bot Alofoke: error al publicar en {nombre}: {e}",
                                      clave=f"error_{pagina['id']}", cada_min=60)
                self._guardar_estado()
                continue
            except Exception as e:  # red caída, etc.
                print(f"[main] fallo de red publicando en {nombre}:", e)
                datos["reintentar_desde"] = time.time() + 10 * 60
                continue

            datos["publicaciones"].append(time.time())
            self.cola.pop(0)
            cola.borrar(clip["nombre"] + ".mp4", clip["nombre"] + ".json")
            self._guardar_estado()
            n = len(datos["publicaciones"])
            if estado_fb == "error":
                publicar.telegram(f"Bot Alofoke: Facebook rechazó el Reel '{clip['titulo']}' en {nombre} "
                                  f"al procesarlo (video {vid}). Sigo con el siguiente.",
                                  clave=f"rechazo_{pagina['id']}", cada_min=30)
            aviso = (f"Publicado en {nombre} ({n}/{config.MAX_POR_DIA} en 24 h, "
                     f"puntaje {clip['puntaje']}): {clip['titulo']} [{vid}]")
            print("[main]", aviso)
            publicar.telegram(aviso, None if config.ENVIAR_TODOS_TELEGRAM else ruta)
            if os.path.exists(ruta):
                os.remove(ruta)

    # ---------- ciclo ----------
    def correr(self):
        inicio = time.time()
        fin = inicio + config.DURACION_TRABAJO
        os.makedirs(SEG_DIR, exist_ok=True)
        if not config.FB_PAGINAS and not config.MODO_PRUEBA:
            publicar.telegram("Bot Alofoke: no hay páginas configuradas (revisa el secreto FB_PAGINAS). "
                              "Sigo grabando y guardando clips en la cola.", clave="sin_paginas")

        recibidos = cola.recibir_pendientes(SEG_DIR)
        if recibidos:
            print(f"[main] recibí {len(recibidos)} pedazos del turno anterior")

        grabador = captura.GrabadorContinuo(
            SEG_DIR, fin, avisar=lambda t: publicar.telegram(t, clave="directo_caido", cada_min=60))
        grabador.iniciar()
        hechos = set()
        tiempo_proceso = 0.0  # cuánto tardó el último pedazo
        while True:
            try:
                archivos = sorted(glob.glob(os.path.join(SEG_DIR, "seg_*.ts")))
                grabando = grabador.vivo()
                # El último pedazo se sigue grabando; solo se procesan los cerrados.
                listos = [a for a in (archivos[:-1] if grabando else archivos) if a not in hechos]

                if not grabando:
                    # Se acabó el turno: lo que falte, al siguiente turno.
                    if listos:
                        entregados = cola.entregar_pendientes(listos)
                        print(f"[main] entregué {len(entregados)} pedazos al siguiente turno")
                    break

                if len(listos) > 3:  # muy atrasado: salta lo más viejo
                    for a in listos[:-3]:
                        print("[main] me atrasé, salto", os.path.basename(a))
                        hechos.add(a)
                        os.remove(a)
                    listos = listos[-3:]

                # Solo empieza un pedazo si le da tiempo de terminarlo antes del cierre.
                if listos and time.time() + tiempo_proceso * 1.15 < fin:
                    a = listos[0]
                    print("[main] procesando", os.path.basename(a))
                    t0 = time.time()
                    try:
                        self.procesar_segmento(a)
                    except Exception as e:
                        print("[main] falló el pedazo:", e)
                        traceback.print_exc()
                    tiempo_proceso = time.time() - t0
                    print(f"[main] pedazo listo en {tiempo_proceso / 60:.1f} min")
                    hechos.add(a)
                    if os.path.exists(a):
                        os.remove(a)
                else:
                    time.sleep(20)

                self.intentar_publicar()
            except Exception as e:  # nada debe tumbar el turno
                print("[main] error inesperado:", e)
                traceback.print_exc()
                publicar.telegram(f"Bot Alofoke: error inesperado (sigo trabajando): {str(e)[:300]}",
                                  clave="inesperado", cada_min=60)
                time.sleep(30)

        for pagina in config.FB_PAGINAS:
            self.puede_publicar(pagina)  # limpia publicaciones de más de 24 h
        self._guardar_estado()
        resumen = (f"Turno terminado: {self.producidos} clips nuevos, {len(self.cola)} en cola, "
                   f"{self.total_24h()} publicados en 24 h entre {len(config.FB_PAGINAS)} páginas.")
        print("[main]", resumen)
        publicar.telegram("Bot Alofoke: " + resumen)


if __name__ == "__main__":
    os.makedirs(TRABAJO, exist_ok=True)
    try:
        Bot().correr()
    finally:
        shutil.rmtree(TRABAJO, ignore_errors=True)
