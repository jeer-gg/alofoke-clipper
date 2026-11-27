import unittest
from clipper import aprendizaje as a
class Ranking(unittest.TestCase):
    def test_top(self):
        filas=[dict(pagina='1',fecha=100,plays24=i,titulo=str(i)) for i in range(5)]
        filas.append(dict(pagina='2',fecha=100,plays24=999))
        self.assertEqual([h['plays24'] for h in a.mejores({'historial_clips':filas},'1',200)], [4,3,2])
    def test_rasgos(self):
        c=dict(puntaje=7, inicio=0,fin=50,duracion_real=30,formato='vertical')
        self.assertIn('duracion:25-39s',a.rasgos(c))
        self.assertIn('formato:vertical',a.rasgos(c))
        self.assertGreater(a.prioridad(c,{'formato:vertical':.5}),7)
