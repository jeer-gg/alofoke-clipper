import unittest
from unittest.mock import patch
from clipper import elegir, config

class SeleccionTests(unittest.TestCase):
    def test_umbral_y_sin_consultas_extra(self):
        clips = [dict(inicio=0, fin=30, titulo='a', descripcion='', puntaje=6), dict(inicio=40, fin=70, titulo='b', descripcion='', puntaje=7)]
        with patch.object(config, 'ELEGIDORES', ['gemini']), patch.object(config,'PUNTAJE_MINIMO',7), patch.object(elegir,'con_gemini',return_value=clips) as g:
            self.assertEqual([c['puntaje'] for c in elegir.elegir([dict(inicio=10,fin=20,texto="prueba")],[],[],100)], [7])
            g.assert_called_once()
    def test_vacio_no_reintenta(self):
        with patch.object(config,'ELEGIDORES',['gemini','codex']), patch.object(elegir,'con_gemini',return_value=[]), patch.object(elegir,'con_codex') as c:
            self.assertEqual(elegir.elegir([dict(inicio=10,fin=20,texto="prueba")],[],[],100),[])
            c.assert_not_called()
    def test_prompt(self):
        self.assertIn('al menos 7', elegir._armar_prompt([],[],600))
