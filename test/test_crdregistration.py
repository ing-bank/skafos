import unittest
from unittest.mock import MagicMock

from skafos.crdregistration import register


class TestCrdRegistration(unittest.TestCase):
    def test_register(self):
        # API generates ValueError, so we do too. Everything should still progress smoothly
        fake_ext_client = MagicMock()
        fake_ext_client.create_custom_resource_definition.side_effect = ValueError()

        # Actual registration
        register(fake_ext_client, path_to_crd='test/crd.yaml')

        # Make sure API call is valid
        args, _ = fake_ext_client.create_custom_resource_definition.call_args
        create_body = args[0]
        assert create_body['kind'] == 'CustomResourceDefinition'


if __name__ == '__main__':
    unittest.main()
