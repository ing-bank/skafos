"""
The purpose of this test is to make sure EventListeners are called when there is
a new event, except for when there is an error (timeout) event.
"""
import sys
import unittest

from unittest.mock import MagicMock


class FakeEventListener:
    def __init__(self, api_client=None, event=None, watch=None):
        self.api_client = api_client
        self.event = event

        self.watch = watch
        self.counter = 0

        self.rolled_back = False

    def process(self, event):
        # Call a random (mock) method to check how many times events are processed (global var)
        self.api_client.touch()

        # Increment counter to see how many times this class processes an event
        self.counter += 1

        # If we have a reference to the StreamWatch, we stop it
        if self.watch:
            self.watch.stop()
            return False  # Invoke rollback

        return True

    def rollback(self):
        assert not self.rolled_back
        assert self.counter != 0
        self.rolled_back = True


class FakeCrdRegistration(MagicMock):
    @staticmethod
    def get_crd_config(path):
        return None, None, None, None  # We don't care about CrdRegistration here


class TestOperator(unittest.TestCase):
    @staticmethod
    def fake_added_event():
        return {
            'type': 'ADDED',
            'object': {
                'metadata': {
                    'name': 'SampleAddEvent'
                },
                'reason': 'Something was added'
            }
        }

    @staticmethod
    def fake_error_event():
        return {
            'type': 'ERROR',
            'object': {'reason': 'Expired'}
        }

    @unittest.mock.patch('kubernetes.watch')
    def create_stream_watch(self, watch):
        watch.Watch.return_value.stream.return_value = [self.fake_error_event(), self.fake_added_event()]
        sys.modules['skafos.crdregistration'] = FakeCrdRegistration()

        from skafos.stream_watch import StreamWatch
        listeners = [FakeEventListener, FakeEventListener()]
        return StreamWatch('test/crd.yaml', listeners, StreamWatch.create_config(''))


if __name__ == '__main__':
    unittest.main()
