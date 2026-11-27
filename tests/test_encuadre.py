import os
import tempfile
import subprocess
import unittest
from unittest.mock import patch
from clipper import encuadre

class EncuadreTests(unittest.TestCase):
    def test_detector(self):
        self.assertTrue(encuadre.verificar_opencv())

    def test_render_y_respaldo(self):
        with tempfile.TemporaryDirectory() as tmp:
            fuente = os.path.join(tmp, 'fuente.mp4')
            salida = os.path.join(tmp, 'salida.mp4')
            subprocess.run(['ffmpeg','-y','-loglevel','error','-f','lavfi','-i','testsrc2=size=320x180:rate=30','-t','1','-c:v','libx264',fuente],check=True)
            for fallo in (False, True):
                if fallo:
                    with patch.object(encuadre, 'cv2', None):
                        encuadre.renderizar(fuente,salida)
                else:
                    encuadre.renderizar(fuente,salida)
                info = subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height','-of','csv=p=0',salida],text=True)
                self.assertEqual(info.strip(),'1080,1080')
