"""
This file contains the generic EventListener class which should be overridden by
other classes that wish to handle events of the CRD type.
"""
import logging
import traceback
from typing import Union


class EventListener:
    """
    This class is responsible for partially unwrapping events and creating
    references to some shared frequently-used objects (e.g. dyn_client, gauge).
    """

    def __init__(self, api_client, event=None):
        """
        Pre-processes some event data and creates references to `dyn_client` and
        `gauge`.

        :param kubernetes.client.api_client.ApiClient: Kubernetes apiclient
        :param event: (optional) event produced by Kubernetes event stream
        """
        self.logger = logging.getLogger('skafos')
        self.ev_state = None

        self.api_client = api_client
        self.event = None
        self.event_obj = None
        self.metadata = None

        self.process_event(event, self.ev_state)

    def process_event(self, event, ev_state):
        """
        process received event
        :param event: event produced by Kubernetes event stream
        """
        if not event:
            return

        self.ev_state = ev_state
        self.event = event
        self.event_obj = event['object']
        if isinstance(self.event_obj, dict):
            self.metadata = self.event_obj.get('metadata')
        else:
            self.metadata = self.event_obj.metadata

    def process(self, event, ev_state) -> bool:
        """
        This method calls other methods based on the `event['type']`, and does
        some logging.

        :param event: (optional) event produced by Kubernetes event stream
        :return whether the event was processed successfully
        """
        if event:
            self.process_event(event, ev_state)

        process_ok = True
        try:
            if self.event['type'] == 'ADDED':
                process_ok = self.create()
            elif self.event['type'] == 'MODIFIED':
                process_ok = self.update()
            elif self.event['type'] == 'DELETED':
                process_ok = self.delete()
            elif self.event['type'] == 'ERROR':
                process_ok = self.error()
            else:
                self.logger.warning("nothing to do event:")
                self.logger.warning(str(self.event))

            # Compatibility with older versions, empty return will be seen as ok
            if process_ok is None:
                process_ok = True

            status = 'succeeded' if process_ok else 'failed'
            meta_name = str(self.metadata["name"]) if isinstance(self.metadata, dict) else str(self.metadata.name)
            self.logger.info("%s :: %s completed with status: %s", meta_name, self.get_name(), status)

        except Exception:
            self.logger.exception("%s :: failed", self.get_name())
            process_ok = False

        return process_ok

    def create(self) -> Union[bool, None]:
        """
        This method is called when the event['type'] is 'ADDED'. This method should be
        overridden in a child class.

        :return Whether create was successful. False will initiate a rollback. Empty is ok.
        """

    def update(self) -> Union[bool, None]:
        """
        This method is called when the event['type'] is 'MODIFIED'. This method should be
        overridden in a child class.

        :return Whether update was successful. False will initiate a rollback. Empty is ok.
        """

    def delete(self) -> Union[bool, None]:
        """
        This method is called when the event['type'] is 'DELETED'. This method should be
        overridden in a child class.

        :return Whether delete was successful. False will initiate a rollback. Empty is ok.
        """

    def error(self) -> Union[bool, None]:
        """
        This method is called when the event['type'] is 'ERROR'. This method should be
        overridden in a child class.

        :return Whether error was successful. False will initiate a rollback. Empty is ok.
        """

    def rollback(self):
        """
        This method is called when this class or other EventListener classes in the future
        return a failure. It's purpose is to undo any action by create/update/delete/error.
        Rollback occurs in reverse order, that means that the most recent EventListener is
        rolled back first, then the second recent, etc.
        """

    def get_name(self) -> str:
        """
        :return: str, name of module, defaults to ClassName
        """
        return self.__class__.__name__
