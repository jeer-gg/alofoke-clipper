"""Aprendizaje local a partir de reproducciones comparables por página y edad."""
import math
import re
import time
from collections import defaultdict
from statistics import median
from datetime import datetime
import requests
from . import config, publicar

METRICA = 'fb_reels_total_plays'
CATEGORIAS = {'humor': r'\b(risa|risas|gracioso|broma|chiste|riendo)\b', 'discusion': r'\b(discusi[oó]n|pelea|careo|discuten|enfrenta|critican)\b', 'confesion': r'\b(confiesa|confesi[oó]n|revela|secreto|admite)\b', 'romance': r'\b(beso|amor|pareja|romance|coqueteo)\b', 'reaccion': r'\b(reacci[oó]n|reacciona|sorpresa|sorprende)\b'}


def rasgos(clip):
    texto = (clip.get('titulo','') + ' ' + clip.get('descripcion','')).lower()
    cat = next((k for k,v in CATEGORIAS.items() if re.search(v,texto)), 'otros')
    dur = clip.get('duracion_real', clip.get('fin',0)-clip.get('inicio',0))
    gancho = clip.get('gancho_blanco','')+' '+clip.get('gancho_amarillo','')
    return ['estilo:'+clip.get('tipo_gancho','tradicional'), 'tema:'+cat, 'duracion:'+('25-39s' if dur<40 else '40-59s' if dur<60 else '60-80s'), 'gancho:'+('pregunta' if '?' in gancho else 'afirmacion'), 'formato:'+clip.get('formato','desconocido'), 'puntaje:'+str(int(clip.get('puntaje',7)))]


def registrar(estado, reserva, clip):
    reserva['rasgos'] = rasgos(clip)
    reserva['hora'] = datetime.fromtimestamp(reserva['fecha'], config.ZONA).hour
    reserva['puntaje'] = clip['puntaje']
    reserva['titulo'] = clip.get('titulo','')[:100]
    reserva['duracion_real'] = clip.get('duracion_real',clip.get('fin',0)-clip.get('inicio',0))


def actualizar(estado, paginas, ahora=None, max_consultas=12):
    ahora = time.time() if ahora is None else ahora
    if ahora - estado.get('insights_ultima',0) < 1800: return False
    estado['insights_ultima'] = ahora
    tokens = {p['id']:p['token'] for p in paginas}
    pendientes=[]
    for h in estado.get('historial_clips',[]):
        edad=ahora-h.get('fecha',ahora)
        if not h.get('video_id') or h.get('pagina') not in tokens or h.get('estado_fb')=='error': continue
        if 86400 <= edad <= 36*3600 and 'plays24' not in h and ahora-h.get('insights_intento',0)>=3600:
            pendientes.append(h)
    bloqueadas=set()
    for h in sorted(pendientes,key=lambda h:h['fecha'])[:max_consultas]:
        pid=h['pagina']
        if pid in bloqueadas: continue
        h['insights_intento']=ahora
        try:
            r=requests.get(publicar._graph(str(h['video_id'])+'/video_insights'), params={'metric':METRICA}, headers={'Authorization':'Bearer '+tokens[pid]},timeout=12)
            data=publicar._ok(r,'insights')
            valores=[v['value'] for d in data.get('data',[]) if d.get('name')==METRICA for v in d.get('values',[]) if isinstance(v.get('value'),(int,float)) and not isinstance(v['value'],bool) and math.isfinite(v['value']) and v['value']>=0]
            if valores:
                h['plays24']=int(valores[-1]); h['edad_medicion_h']=round((ahora-h['fecha'])/3600,2)
                print('[insights] medición guardada', h['video_id'],h['plays24'])
        except publicar.ErrorFacebook as e:
            print('[insights] API rechazó consulta; código',e.codigo)
            bloqueadas.add(pid)
            if e.limite: break
        except (requests.RequestException,ValueError,TypeError,KeyError):
            print('[insights] respuesta no disponible; se reintentará')
    return True


def perfil(estado, pid, ahora=None):
    ahora=time.time() if ahora is None else ahora
    filas=[h for h in estado.get('historial_clips',[]) if h.get('pagina')==pid and 'plays24' in h and h.get('rasgos') and 0<=ahora-h['fecha']<=30*86400]
    if len(filas)<20: return {},len(filas)
    base=median(math.log1p(h['plays24']) for h in filas)
    grupos=defaultdict(list)
    for h in filas:
        for r in h['rasgos']+['hora:'+str(h['hora'])]: grupos[r].append(math.log1p(h['plays24']))
    return {k:max(-.5,min(.5,(median(v)-base)*len(v)/(len(v)+15)*.25)) for k,v in grupos.items() if len(v)>=5},len(filas)


def prioridad(clip, ajustes):
    return clip['puntaje'] + max(-1.5, min(1.5, sum(ajustes.get(r,0) for r in rasgos(clip))))


def mejores(estado, pid, ahora=None, limite=3):
    """Ranking de Reels medidos en una ventana de edad comparable."""
    ahora = time.time() if ahora is None else ahora
    filas = [h for h in estado.get('historial_clips', [])
             if h.get('pagina') == pid and 'plays24' in h
             and h.get('estado_fb') != 'error' and 0 <= ahora-h['fecha'] <= 30*86400]
    return sorted(filas, key=lambda h: h['plays24'], reverse=True)[:limite]


def resumen(estado,paginas):
    partes=['Estadísticas de Reels (medición a 24-36 h; últimos 30 días)']
    for p in paginas:
        ajustes,n=perfil(estado,p['id'])
        top=sorted(((k,v) for k,v in ajustes.items() if v>0),key=lambda x:-x[1])[:3]
        partes.append(p['nombre']+': '+str(n)+' muestras; '+(', '.join(k for k,v in top) or 'aprendizaje inicial'))
        for i,h in enumerate(mejores(estado,p['id']),1):
            partes.append(f"#{i} {h.get('titulo') or h.get('video_id','Reel')}: {h['plays24']:,} reproducciones")
    return '\n'.join(partes)
