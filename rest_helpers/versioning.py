import inspect
from rest_helpers.rest_exceptions import InvalidDataException

class BaseVersionner:
    def __init__(self):
        attributes = (getattr(self, a) for a in dir(self))
        innner_classes = (c for c in attributes if inspect.isclass(c) and c != self.__class__)
        self.supported_versions = {c.name if hasattr(c, "name") else c.__name__:c() for c in innner_classes}
        self.requested_version = None

    @staticmethod
    def version_route(route):
        raise NotImplementedError

    def get_specific_versionner(self):
        version = self.requested_version or list(self.supported_versions.keys())[-1] #default version is the latest
        if version not in self.supported_versions:
            raise InvalidDataException("The specified version ({})is not correct: it should be among {}".format(version, str(self.supported_versions.keys())))

        return self.supported_versions[version]

    # The following methods verify if the specific versionner has the corresponding
    # method before calling it instead of using an inheritance mechanism: this is so
    # the definition of inner versionner is clear and looks very readable.
    def body(self, body):
        versionner = self.get_specific_versionner()
        return versionner.body(body) if hasattr(versionner, "body") else body

    def body_dict(self, body):
        """
        If you  want to version a json object, use this hook instead of
        Tthe body hook that would force you to deserialize the json to
        reserialize the versionned one right after

        Arguments:
            body {dict} -- the body of the request aleready deserialized from json.

        Returns:
            {dict} -- the versionned body dictionary.
        """

        versionner = self.get_specific_versionner()
        return versionner.body_dict(body) if hasattr(versionner, "body_dict") else body

    def response(self, response):
        versionner = self.get_specific_versionner()
        return versionner.response(response) if hasattr(versionner, "response") else response

    def headers(self, headers):
        versionner = self.get_specific_versionner()
        return versionner.headers(headers) if hasattr(versionner, "headers") else headers

    def query_string_args(self, query_string_args):
        versionner = self.get_specific_versionner()
        return versionner.query_string_args(query_string_args) if hasattr(versionner, "query_string_args") else query_string_args

    def response_body_dict(self, response_body_dict):
        versionner = self.get_specific_versionner()
        return versionner.response_body_dict(response_body_dict) if hasattr(versionner, "response_body_dict") else response_body_dict

    def set_request_args(self, request_args, request_kwargs):
        if "rest_helper_version" in request_kwargs:
            self.requested_version = request_kwargs["rest_helper_version"]
            request_kwargs.pop("rest_helper_version")

class UrlRootVersionner(BaseVersionner):
    @staticmethod
    def version_route(route):
        route.rule="/<rest_helper_version>"+route.rule