import unittest
from unittest.mock import patch, Mock
from clipper import aprendizaje as a
class TestAprendizaje(unittest.TestCase):
    def test_muestras(self):
        h=[dict(pagina='1',fecha=100,plays24=100 if i<10 else 10000,rasgos=['tema:humor' if i<10 else 'tema:confesion'],hora=7) for i in range(20)]
        self.assertEqual(a.perfil({'historial_clips':h[:10]},'1',200)[0],{})
        p,n=a.perfil({'historial_clips':h},'1',200)
        self.assertEqual(n,20); self.assertGreater(p['tema:confesion'],p['tema:humor'])
        self.assertEqual(a.perfil({'historial_clips':h},'2',200)[0],{})
    def test_consulta(self):
        h=dict(pagina='1',fecha=100,video_id='123'); estado={'historial_clips':[h]}
        r=Mock(status_code=200); r.json.return_value={'data':[{'name':a.METRICA,'values':[{'value':250}]}]}
        with patch.object(a.requests,'get',return_value=r) as get:
            self.assertTrue(a.actualizar(estado,[{'id':'1','token':'fake'}],90000)); self.assertEqual(h['plays24'],250)
            self.assertFalse(a.actualizar(estado,[],90001)); self.assertEqual(get.call_count,1)
    def test_filtro(self):
        h=dict(pagina='1',fecha=100,video_id='123',estado_fb='error')
        with patch.object(a.requests,'get') as get:
            a.actualizar({'historial_clips':[h]},[{'id':'1','token':'fake'}],90000); get.assert_not_called()
if __name__=='__main__': unittest.main()
