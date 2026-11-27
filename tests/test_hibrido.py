import tempfile, os, unittest, subprocess
from unittest.mock import patch
from clipper import encuadre, editar, elegir

class HibridoTests(unittest.TestCase):
    def test_vertical_y_gancho(self):
        with tempfile.TemporaryDirectory() as d:
            a,b,c,ass=[os.path.join(d,x) for x in ('a.mp4','b.mp4','c.mp4','hook.ass')]
            subprocess.run(['ffmpeg','-y','-loglevel','error','-f','lavfi','-i','testsrc2=size=320x180:rate=30','-t','1','-c:v','libx264',a],check=True)
            with patch.object(encuadre,'_formato',return_value=9/16):
                encuadre.renderizar(a,b)
            self.assertEqual(editar.tamano_video(b),(1080,1920))
            editar.crear_ass(dict(inicio=0,fin=1,gancho_blanco='UNA CONFESIÓN',gancho_amarillo='¿QUÉ DIJO?'),[],ass,1920)
            subprocess.run(['ffmpeg','-y','-loglevel','error','-i',b,'-vf','ass='+ass,'-c:v','libx264','-threads','2',c],check=True)
            self.assertEqual(editar.tamano_video(c),(1080,1920))
    def test_ganchos_parseados(self):
        import json
        c=dict(inicio=0,fin=30,titulo='A',descripcion='B',puntaje=8,gancho_blanco='UNA CONFESIÓN',gancho_amarillo='¿QUÉ DIJO?')
        self.assertEqual(elegir.parsear(json.dumps({'clips':[c]}),60)[0]['gancho_amarillo'],c['gancho_amarillo'])
