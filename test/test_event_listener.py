"""
The purpose of this class it to make sure that the methods:
create(), update(), delete() are called when there is a corresponding
event.
"""
import unittest
from unittest.mock import MagicMock, patch

from skafos.event_listener import EventListener


class MyEventListener(EventListener):
    pass


class TestEventListener(unittest.TestCase):
    @staticmethod
    def create_fake_event(event_type):
        return {
            'type': event_type,
            'object': {
                'metadata': {
                    'name': 'MockedEvent'
                }

            }
        }

    def test_init(self):
        fake_dyn_client = MagicMock()
        fake_event = self.create_fake_event('any')

        event_listener = MyEventListener(fake_dyn_client, fake_event)

        # Make sure `fake_event` is parsed correctly
        assert event_listener.event_obj == fake_event['object']
        assert event_listener.metadata == fake_event['object']['metadata']

    def test_event_added(self):
        self.assert_called_on_process('ADDED', 'create')

    def test_event_update(self):
        self.assert_called_on_process('MODIFIED', 'update')

    def test_event_delete(self):
        self.assert_called_on_process('DELETED', 'delete')

    def assert_called_on_process(self, event_type, method_name):
        """
        Makes sure a method with name `method_name` is called when
        event['type'] is `event_type`. A fake event shall be
        constructed automatically.

        :param str event_type: Type of event
        :param str method_name: Name of method which should be called
        """
        fake_event = self.create_fake_event(event_type)

        event_listener = MyEventListener(MagicMock(), fake_event)
        with patch.object(event_listener, method_name) as mock:
            event_listener.process(event=fake_event, ev_state={})
            mock.assert_called()


if __name__ == '__main__':
    unittest.main()
