import unittest
from datetime import datetime
from clipper import reparto

class TestReparto(unittest.TestCase):
    def test_horarios(self):
        for total in (1, 2, 3, 4):
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
        for h in range(7,24):
            for i in range(4):
                self.assertIsNotNone(reparto.turno(datetime(2026,11,27,h,i*15),i,4))
        self.assertIsNone(reparto.turno(t,4,4))
    def test_duplicado(self):
        h = reparto.huella('uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce quince')
        self.assertTrue(reparto.duplicado({'nombre':'a','huella':h},{'nombre':'b','huella':h}))
        self.assertFalse(reparto.duplicado({'nombre':'a','huella':h},{'nombre':'b','huella':[]}))
        self.assertTrue(reparto.duplicado({'nombre':'a','sha256':'x'},{'nombre':'b','sha256':'x'}))

    def test_config_cuatro(self):
        import os, json, subprocess, sys
        paginas = [dict(nombre=f"p{i}", id=str(i), token="ficticio") for i in range(1,5)]
        env = dict(os.environ, FB_PAGINAS=json.dumps(paginas), MAX_COLA="")
        salida = subprocess.check_output([sys.executable, "-c", "from clipper import config; assert len(config.FB_PAGINAS)==4; assert config.MAX_COLA==200; assert [p['id'] for p in config.FB_PAGINAS]==['1','2','3','4']"], env=env, text=True)
        self.assertIn("minuto: 45", salida)
