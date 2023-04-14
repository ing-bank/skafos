"""Creating CRD in kubernetes/openshift"""
import logging

import yaml


def register(ext_client, path_to_crd='crd.yaml'):
    """
    Registering new CRD to the kubernetes apiserver.

    :param ext_client:
    :param str path_to_crd: (optional) Path to crd file in yaml format
    """
    with open(path_to_crd) as data:
        body = yaml.load(data, Loader=yaml.SafeLoader)
    try:
        ext_client.create_custom_resource_definition(body)
    except ValueError:
        logging.getLogger('skafos').warning("Encountered API error, but it was expected")


def get_crd_config(path_to_crd='crd.yaml'):
    """

    :param str path_to_crd: location of the yaml containting the crd
    :return: str ApiGroup, str Version of Api, str Plural version of CRD, str singular version of CRD
    """
    with open(path_to_crd) as data:
        body = yaml.load(data, Loader=yaml.SafeLoader)

    spec = body['spec']
    return spec["group"], spec["version"], spec["names"]["plural"], spec["names"]["singular"]
