import unittest
from datetime import datetime
from clipper import reparto

class TestReparto(unittest.TestCase):
    def test_horarios(self):
        for total in (1, 2, 3):
            for pagina in range(total):
                ventanas = {reparto.turno(datetime(2026,11,27,h,m),pagina,total) for h in range(24) for m in range(60)} - {None}
                self.assertEqual(len(ventanas),17)
            for h in range(24):
                for m in range(60):
                    t = datetime(2026,11,27,h,m)
                    self.assertLessEqual(sum(reparto.turno(t,i,total) is not None for i in range(total)),1)
        t = datetime(2026,11,27,23,40)
        self.assertIsNotNone(reparto.turno(t,2,3))
        self.assertIsNone(reparto.turno(t,3,3))
    def test_duplicado(self):
        h = reparto.huella('uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce quince')
        self.assertTrue(reparto.duplicado({'nombre':'a','huella':h},{'nombre':'b','huella':h}))
        self.assertFalse(reparto.duplicado({'nombre':'a','huella':h},{'nombre':'b','huella':[]}))
        self.assertTrue(reparto.duplicado({'nombre':'a','sha256':'x'},{'nombre':'b','sha256':'x'}))
