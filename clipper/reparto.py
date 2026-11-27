"""Horarios locales y deduplicación compartida entre páginas."""
import re
import unicodedata


HORAS = tuple(range(7, 24))


def turno(fecha, indice, total=3):
    """17 ventanas por página; 20 min para tres, 30 para dos."""
    if total not in (1, 2, 3) or not 0 <= indice < total:
        return None
    if fecha.hour not in HORAS:
        return None
    ancho = 60 // total
    if indice * ancho <= fecha.minute < (indice + 1) * ancho:
        # Identificador estable por hora incluso si cambia el número de páginas.
        return f'{fecha.date()}:{fecha.hour * 60 + indice * ancho}'
    return None


def huella(texto):
    texto = unicodedata.normalize('NFKD', texto.lower())
    palabras = re.findall(r'\w+', ''.join(c for c in texto if not unicodedata.combining(c)))
    return sorted(set(' '.join(palabras[i:i+4]) for i in range(len(palabras)-3)))


def duplicado(a, b):
    if a['nombre'] == b['nombre'] or (a.get('sha256') and a.get('sha256') == b.get('sha256')):
        return True
    x, y = set(a.get('huella', [])), set(b.get('huella', []))
    return min(len(x), len(y)) >= 8 and len(x & y) / min(len(x),len(y)) >= .6
