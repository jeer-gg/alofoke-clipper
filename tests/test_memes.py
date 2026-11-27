import json
import unittest
from unittest.mock import patch
from clipper import elegir, config, aprendizaje

class Memes(unittest.TestCase):
    def clip(self, **kwargs):
        c = dict(inicio=10, fin=45, titulo='REACCION', descripcion='Contexto', puntaje=8,
                 gancho_blanco='ORIGINAL', gancho_amarillo='MIRA ESTO', puntaje_meme=9,
                 meme_blanco='Cuando llega la cuenta', meme_amarillo='Y nadie tiene dinero',
                 evidencia_meme='Mira fijamente la mesa', momento_meme=25)
        c.update(kwargs)
        return elegir.parsear(json.dumps({'clips':[c]}), 100)[0]
    def test_meme(self):
        c = self.clip()
        self.assertEqual(c['tipo_gancho'], 'meme')
        self.assertIn('estilo:meme', aprendizaje.rasgos(c))
    def test_weak(self):
        self.assertEqual(self.clip(puntaje_meme=7)['gancho_blanco'], 'ORIGINAL')
    def test_outside(self):
        self.assertEqual(self.clip(momento_meme=46)['tipo_gancho'], 'tradicional')
    def test_disabled(self):
        with patch.object(config,'MEMES_SELECTIVOS',False):
            self.assertEqual(self.clip()['tipo_gancho'],'tradicional')
    def test_empty_evidence(self):
        self.assertEqual(self.clip(evidencia_meme='')['tipo_gancho'],'tradicional')
    def test_silent_visual(self):
        with patch.object(config,'ELEGIDORES',['gemini']), patch('clipper.visual.partes', return_value=[{'text':'frame'}]), patch.object(elegir,'con_gemini',return_value=[self.clip()]) as call:
            self.assertEqual(len(elegir.elegir([], [], [], 100, video='fake')),1)
            self.assertEqual(call.call_args.args[3],[{'text':'frame'}])
