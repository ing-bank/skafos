import time
from http import client
import unittest

from skafos.healthcheck import start_healthcheck, beat_healthcheck


class TestHealthcheck(unittest.TestCase):
    MIN_BEAT_TIME = 1

    @staticmethod
    def get_health():
        conn = client.HTTPConnection('localhost', port=5000, timeout=1)
        conn.request('GET', '/health')
        response = conn.getresponse()
        conn.close()
        return response.status, response.read()

    def test_all(self):
        start_healthcheck(self.MIN_BEAT_TIME)
        time.sleep(0.1)  # Give threads a moment to spin up

        # First call to HealthCheck without beat should be OK
        status, body = self.get_health()
        self.assertEqual(status, 200)
        self.assertEqual(body, b'Ok')

        # Let MIN_BEAT_TIME go by
        time.sleep(self.MIN_BEAT_TIME)
        status, body = self.get_health()
        self.assertEqual(status, 500)
        self.assertEqual(body[:17], b'Last beat was at ')

        # Beat to be healthy
        beat_healthcheck()
        status, body = self.get_health()
        self.assertEqual(status, 200)
        self.assertEqual(body, b'Ok')


if __name__ == '__main__':
    unittest.main()
