"""Horarios locales y deduplicación compartida entre páginas."""
import re
import unicodedata


HORAS = (7,8,9,10,11,12,13,15,16,17,18,19,20,21,22)


def turno(fecha, indice):
    minutos = fecha.hour * 60 + fecha.minute
    for hora in HORAS:
        inicio = hora * 60 + 30 * indice
        if inicio <= minutos < inicio + 30:
            return f'{fecha.date()}:{inicio}'
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
