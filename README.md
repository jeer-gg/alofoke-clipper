# Bot clipper 24/7 — La Casa de Alofoke 3

El bot graba **todo** el directo, sin pausas, y lo convierte en Reels sin parar:

1. Graba el directo de YouTube (@AlofokeRadioShow) cortado en pedazos de 1 hora.
2. Cada pedazo se transcribe con Whisper y se miden los picos de volumen (gritos, risas, peleas).
3. La IA elige **todos** los momentos buenos de cada hora (hasta 15) y les escribe el título y la descripción. Es una sola consulta por hora: 24 al día.
4. Convierte cada momento en un Reel 9:16 con fondo difuminado, título arriba y subtítulos grandes.
5. Guarda los clips en la cola, ordenados por puntaje. Cada vez que toca publicar, sube el mejor a Facebook.

Todo esto ocurre mientras el bot sigue grabando. Pueden salir cientos de clips al día.

## Cuántos se publican
**Meta solo permite 30 Reels por API cada 24 horas por página.** El bot publica las 30 permitidas en cada página que le conectes (2 páginas = 60 al día), cada 25 minutos como mínimo, entre las 7 a.m. y la medianoche. Siempre publica los de mayor puntaje y descarta los clips de más de 10 horas.

Para aprovechar el resto de clips:
- Crea la variable `ENVIAR_TODOS_TELEGRAM` con valor `1`. El bot te enviará **todos** los clips por Telegram para que los subas a mano a TikTok, Instagram o X, donde Alofoke también permite monetizarlos.

> Alofoke Media permite publicar y monetizar clips de la Casa 3 en Facebook, Instagram, TikTok y X.
> **En YouTube no.**

## Cómo graba 24/7 con GitHub gratis
Cada turno graba 4 horas. Cada 2 horas se lanza uno nuevo, que espera en fila y arranca justo cuando termina el anterior. Las horas que un turno no alcanzó a procesar se las entrega al siguiente, así que no se pierde nada del directo; entre turno y turno solo hay unos minutos de cambio. La cola de clips también pasa de un turno al siguiente.

## Fuente de video: tus grabaciones en Google Drive
Si creas la variable `DRIVE_CARPETA` con el enlace de una carpeta de Google Drive, el bot deja de grabar YouTube y usa los videos que subas ahí:

1. En la app de Google Drive crea una carpeta (por ejemplo, "Clips Alofoke").
2. Compártela: **Compartir → Acceso general → Cualquier persona con el enlace (Lector)** y copia el enlace.
3. En GitHub crea la variable `DRIVE_CARPETA` con ese enlace.
4. Graba el directo con la grabación de pantalla del iPhone (YouTube a pantalla completa, teléfono de lado, con No molestar activado) y sube cada grabación a la carpeta.

El bot revisa la carpeta cada 3 minutos, procesa cada video nuevo una sola vez y publica los clips como siempre. Borra de vez en cuando las grabaciones viejas: el bot solo lee hasta 50 archivos por carpeta.

## Instalación

### 1. Crea el repositorio
Crea un repositorio **público** (por ejemplo, `alofoke-clipper`) y sube todo, incluida la carpeta `.github`. Tiene que ser público para que GitHub Actions sea gratis sin límite de minutos. Los secretos siguen protegidos.

### 2. Agrega los secretos
Ve a Settings → Secrets and variables → Actions → New repository secret.

| Secreto | Qué es |
|---|---|
| `GEMINI_API_KEY` | Tu clave gratis de Google AI Studio. Gemini elige los momentos primero, para no gastar tu límite de Claude |
| `CODEX_AUTH_JSON` | Tu sesión de ChatGPT Plus para Codex (abajo cómo sacarla). Se usa si Gemini se agota |
| `CLAUDE_CODE_OAUTH_TOKEN` | El token de tu plan Pro (`claude setup-token`). Se usa de último |
| `FB_PAGINAS` | Las páginas donde publica, con el ID y el token de cada una (formato abajo) |
| `TELEGRAM_TOKEN` / `TELEGRAM_CHAT_ID` | Tu bot de Telegram |
| `YT_COOKIES` | Solo si YouTube bloquea al bot (más abajo) |

Por ahora usa Gemini y después Codex (Claude está apagado hasta que se renueve su límite). Si fallan, el bot no se detiene: elige los momentos por volumen y cantidad de palabras.

#### Formato de `FB_PAGINAS`
Pega esto en el secreto, cambiando los nombres, IDs y tokens. Cada token es el token de página de tu app "Videos Plus", con los permisos `pages_manage_posts`, `pages_read_engagement` y `publish_video`:

```
[{"nombre": "Pagina 1", "id": "ID_DE_LA_PAGINA_1", "token": "TOKEN_DE_LA_PAGINA_1"},
 {"nombre": "Pagina 2", "id": "ID_DE_LA_PAGINA_2", "token": "TOKEN_DE_LA_PAGINA_2"}]
```

Cada página tiene su propio límite de 30 Reels en 24 horas: con 2 páginas son 60 al día. El bot reparte los mejores clips entre ellas y nunca sube el mismo clip a las dos. Puedes agregar más páginas en la misma lista.

**Importante:** quita esas páginas del bot de animación, para que no se mezclen los dos tipos de video.

### 3. Haz la primera prueba sin publicar
En la pestaña Variables crea `MODO_PRUEBA` con valor `1`. Para no esperar una hora, crea también `SEGMENTO_SEG` con valor `600` (pedazos de 10 minutos). Ve a Actions → Run workflow. En unos 15 minutos te llega el primer clip por Telegram. Cuando termines de probar, borra `SEGMENTO_SEG`.
Cuando te guste cómo queda, cambia `MODO_PRUEBA` a `0`.

## Qué hace el bot cuando algo falla
| Problema | Qué hace | Qué te avisa por Telegram |
|---|---|---|
| El directo se cae o YouTube bloquea | Reintenta cada 2 minutos | Un aviso por hora como máximo |
| Un momento queda entre dos horas | Repite los últimos 90 s de la hora anterior, así el momento sale completo | — |
| La IA elige dos veces el mismo momento | Se queda con el de mayor puntaje | — |
| Se vence el token de una página | Pausa esa página 6 horas y las demás siguen | Te pide un token nuevo |
| Facebook frena por límite | Pausa esa página 2 horas | Un aviso |
| Facebook rechaza un Reel al procesarlo | Sigue con el siguiente | Te dice cuál fue |
| 3 horas seguidas sin clips buenos | Sigue trabajando | Te pide revisar los registros |
| GitHub falla al guardar la cola | Reintenta 3 veces; si no, guarda el clip en el turno actual | — |
| Cualquier error inesperado | Lo anota y sigue, el turno no se cae | Un aviso por hora como máximo |

Los avisos repetidos se agrupan para no llenarte el Telegram. Los tokens se ocultan en los registros, que son públicos porque el repositorio es público.

**Lo único que no se arregla solo:** la sesión de ChatGPT (Codex) puede vencer, porque OpenAI la renueva de vez en cuando y la copia guardada en GitHub no se actualiza. Si en los registros ves "Codex falló" todo el tiempo, repite `codex login` y pega el `auth.json` nuevo. Mientras tanto, el bot sigue funcionando con Gemini.

## Ajustes (pestaña Variables, todos opcionales)

| Variable | Por defecto | Para qué |
|---|---|---|
| `MAX_POR_DIA` | 30 | Reels en 24 h. No pases de 30: es el límite de Meta |
| `PUNTAJE_MINIMO` | 5 | Más alto = menos clips, pero mejores |
| `ENVIAR_TODOS_TELEGRAM` | 0 | `1` = te manda cada clip que produce |
| `ELEGIDORES` | gemini,codex | El orden en que se usan las IA. Para sumar Claude: `gemini,codex,claude` |
| `SEGMENTO_SEG` | 3600 | Largo de cada pedazo en segundos. Más corto = clips más frescos, pero más consultas de IA |
| `WHISPER_MODELO` | small | `base` es más rápido pero entiende peor |
| `CANAL_LIVE_URL` | youtube.com/@AlofokeRadioShow/live | Si el directo cambia de canal |

## Cómo conectar tu ChatGPT Plus (Codex)
Se hace una sola vez, desde cualquier computadora:

1. Instala Codex con `npm install -g @openai/codex`.
2. Escribe `codex login` y entra con tu cuenta de ChatGPT.
3. Abre el archivo `~/.codex/auth.json` y copia todo su contenido.
4. Pégalo en el secreto `CODEX_AUTH_JSON`.

Ese archivo funciona como una contraseña: no lo compartas ni lo subas al repositorio. Si un día Codex deja de responder en los registros del bot, es que la sesión venció. Repite los pasos 2 a 4.

## Si YouTube bloquea al bot
Si te llega "el directo no está disponible" mientras el reality sigue al aire, YouTube está bloqueando a los servidores de GitHub.
Para arreglarlo:

1. Exporta `cookies.txt` de YouTube desde una computadora, con la extensión "Get cookies.txt LOCALLY". Usa una cuenta de Google secundaria.
2. Pega todo el contenido del archivo en el secreto `YT_COOKIES`.

## Archivos
- `main.py`: el ciclo 24/7 (graba, procesa y publica al mismo tiempo).
- `clipper/captura.py`: grabación continua con yt-dlp y ffmpeg.
- `clipper/analisis.py`: Whisper y picos de volumen.
- `clipper/elegir.py`: Gemini, después Codex, después Claude, y al final el respaldo automático.
- `clipper/editar.py`: el Reel 9:16.
- `clipper/publicar.py`: API de Reels de Meta y Telegram.
- `clipper/cola.py`: la cola, guardada en el release `cola`. No lo borres.


## Diagnóstico de Gemini (actualización)

- `GEMINI_MODELO`: modelo principal, por defecto `gemini-3.5-flash-lite`.
- `GEMINI_ALTERNATIVOS`: lista separada por comas, por defecto `gemini-3.8-flash`. Solo se prueba otro modelo ante HTTP 404. Comprueba acceso y tarifas en Google AI Studio antes de habilitar modelos.
- HTTP 400/401/403: revisar clave, permisos y región; 429: revisar cuota (pausa de cinco minutos dentro del turno); 5xx y errores de red: hasta tres intentos con espera creciente.
- Una respuesta válida con cero clips no activa el respaldo. Una respuesta bloqueada por seguridad tampoco.
- El respaldo sin IA queda exclusivamente para revisión manual en Telegram si `ENVIAR_TODOS_TELEGRAM=1` o `MODO_PRUEBA=1`; no entra a la cola de Facebook.
- El ZIP no instala por sí mismo el workflow: actualizar `.github/workflows/clipper.yml` por separado.
- Pruebas locales simuladas: `python -m unittest discover -s tests -v`. No verifican una clave real ni la cuota de Google.

## Reparto de dos páginas (hora dominicana)
Las dos primeras páginas de FB_PAGINAS reciben hasta 17 clips cada una en 24 horas. Ventanas de 30 minutos cada hora de 7 a 23 inclusive; la segunda página empieza 30 minutos después. Si no hay clip o el proceso está ocupado, la ventana se pierde. Se prioriza puntaje y luego fecha de creación; mínimo 7 y antigüedad de cola 6 horas. Los clips de revisión manual no se publican. El historial compartido se conserva en estado.json del release cola: no borrarlo. La reserva se guarda antes de publicar; si el resultado es ambiguo o falla el envío, se sacrifica ese turno y clip para evitar duplicaciones. La comparación de transcripciones es aproximada, no garantiza detectar toda repetición; los clips antiguos sin huella tienen protección limitada. El workflow fija 17, 7 y envío a Telegram. Si se instala mediante el ZIP, actualizar el workflow por separado.


### Actualización: 17 Reels y control de inicio
Hasta 17 por página (34 entre dos páginas), de 07:00 a 23:00 y 07:30 a 23:30, respectivamente. Las ventanas son máximos, no garantías. El editor decodifica primero el fragmento, analiza la imagen sin textos, recorta el inicio inmóvil, ajusta los subtítulos y vuelve a validar el Reel. La cola antigua se vuelve a verificar antes de publicar; se descartan los archivos dudosos. La detección puede confundir escenas quietas con congelamientos.

### Edición cuadrada dinámica
Los clips nuevos se exportan a 1080×1080, sin fondo borroso ni títulos grandes. OpenCV estima rostros y movimiento localmente, con zoom limitado a 1.25× y transición suave. No identifica hablantes ni reconoce quién está hablando. La marca textual de la página se añade al publicar; Telegram recibe el máster sin marca. `SUBTITULOS=1` activa subtítulos blancos discretos (por defecto apagados). Los clips antiguos no cuadrados de la cola se descartan al intentar publicarlos. No se cambia el selector Gemini ni los turnos de 17 publicaciones por página. El procesamiento local puede aumentar el tiempo de Actions. Revisar encuadre y audio antes de publicar en producción.

## Tres páginas
Agregar History Time como tercer objeto del secreto FB_PAGINAS. Con tres páginas: ventanas de 20 minutos a las :00, :20 y :40 de cada hora de 07 a 23. Con dos se mantienen :00 y :30. Máximo 17 por página en 24 h, mínimo 7/10. Cola hasta 150 y edad hasta 24 h. No se añaden consultas Gemini. No se garantiza llenar todas las ventanas.

### Ranking de aprendizaje
El resumen de Telegram muestra los tres Reels con más reproducciones medidas por página. El aprendizaje incorpora formato, duración real, tema, gancho y puntuación; conserva el filtro mínimo de 7 y ajusta únicamente la prioridad de la cola. Las cifras son reproducciones, no espectadores únicos ni retención. No añade consultas de Gemini.

### Cuatro páginas
Añadir la cuarta al final de FB_PAGINAS. Ventanas de 15 minutos (:00, :15, :30, :45), de 07 a 23. Hasta 17 por página en 24 h; cola 200; edad 24 h. El editor prioriza vertical, conserva cuadrado en escenas amplias persistentes. Sin consultas adicionales a Gemini.
