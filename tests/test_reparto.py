import unittest
from datetime import datetime
from clipper import reparto

class TestReparto(unittest.TestCase):
    def test_horarios(self):
        for pagina in (0,1):
            ventanas = {reparto.turno(datetime(2026,11,27,h,m),pagina) for h in range(24) for m in range(60)} - {None}
            self.assertEqual(len(ventanas),17)
        for h in range(24):
            for m in range(60):
                t = datetime(2026,11,27,h,m)
                self.assertFalse(reparto.turno(t,0) and reparto.turno(t,1))
    def test_duplicado(self):
        h = reparto.huella('uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce quince')
        self.assertTrue(reparto.duplicado({'nombre':'a','huella':h},{'nombre':'b','huella':h}))
        self.assertFalse(reparto.duplicado({'nombre':'a','huella':h},{'nombre':'b','huella':[]}))
        self.assertTrue(reparto.duplicado({'nombre':'a','sha256':'x'},{'nombre':'b','sha256':'x'}))
