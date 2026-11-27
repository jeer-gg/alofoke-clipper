import unittest
from unittest.mock import patch, Mock
from clipper import elegir, config


def response(code, data):
    r = Mock(status_code=code, ok=200 <= code < 300)
    r.json.return_value = data
    return r


def valid(text='{"clips": []}'):
    return response(200, {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':text}]}}]})


class GeminiTests(unittest.TestCase):
    def setUp(self):
        elegir._gemini_modelo_activo = None
        elegir._gemini_pausa_hasta = 0
        self.key = patch.object(config, 'GEMINI_API_KEY', 'test-only')
        self.key.start()
        self.addCleanup(self.key.stop)

    def call(self):
        return elegir.con_gemini([], [], 100)

    @patch('requests.post')
    def test_empty_valid(self, post):
        post.return_value = valid()
        self.assertEqual(self.call(), [])

    @patch('requests.post')
    def test_valid_clip(self, post):
        post.return_value = valid('{"clips":[{"inicio":"00:10","fin":"00:45","titulo":"UN MOMENTO","descripcion":"Contexto","puntaje":8}]}')
        self.assertEqual(self.call()[0]['puntaje'], 8)

    @patch('requests.post')
    def test_fallback_model(self, post):
        post.side_effect = [response(404, {'error':{'status':'NOT_FOUND'}}), valid()]
        self.assertEqual(self.call(), [])
        self.assertEqual(post.call_count, 2)

    @patch('requests.post')
    def test_quota(self, post):
        post.return_value = response(429, {'error':{'status':'RESOURCE_EXHAUSTED'}})
        self.assertIsNone(self.call())
        self.assertIsNone(self.call())
        self.assertEqual(post.call_count, 1)

    @patch('requests.post')
    def test_bad_key(self, post):
        post.return_value = response(403, {'error':{'status':'PERMISSION_DENIED'}})
        self.assertIsNone(self.call())
        self.assertEqual(post.call_count, 1)

    @patch('requests.post')
    def test_no_candidates(self, post):
        post.return_value = response(200, {})
        self.assertIsNone(self.call())

    @patch('requests.post')
    def test_block(self, post):
        post.return_value = response(200, {'promptFeedback':{'blockReason':'SAFETY'}})
        self.assertEqual(self.call(), [])

    @patch('clipper.elegir.time.sleep')
    @patch('requests.post')
    def test_transient(self, post, sleep):
        post.side_effect = [response(503, {}), valid()]
        self.assertEqual(self.call(), [])
        self.assertEqual(post.call_count, 2)

    def test_invalid_json(self):
        self.assertIsNone(elegir.parsear('{"wrong":[]}', 100))
        self.assertIsNone(elegir.parsear('{"clips":[{"inicio":0,"fin":99,"puntaje":99}]}', 100))

if __name__ == '__main__':
    unittest.main()
