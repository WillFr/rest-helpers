import  json
import functools

class Proxy(object):
    def __init__(self, proxied, adapter_builder):
        self.proxied = proxied
        self.adapter_builder = adapter_builder

    def __getattr__(self, name):
        def _call(*args, **kwargs):
            adapter, a_args, a_kwargs = self.adapter_builder(*args, **kwargs)
            return getattr(self.proxied, name)(adapter, *a_args, **a_kwargs)
        functools.update_wrapper(_call, getattr(self.proxied, name))
        return _call

    __file__ = ""

class BaseFrameworkAdapter(object):  # pragma: no cover
    """
    Adapter pattern: the framework adapter is here to isolate
    framework specific logic from the rest helper business logic.
    The framework adapter goal is to provide a thin adapter layer
    so that rest helpers can be used with several different web
    frameworks such as flask or aiohttp.
    """

    #region mandatory
    async def get_current_request_body(self):
        raise NotImplementedError()

    def get_current_request_query_string_args(self):
        raise NotImplementedError()

    def get_current_request_headers_dict(self):
        raise NotImplementedError()

    def get_current_request_query_string(self):
        raise NotImplementedError()

    def get_current_request_path(self):
        raise NotImplementedError()

    def attach_rest_helper_request_context(self, context):
        raise NotImplementedError()

    def get_current_request_full_path(self):
        raise NotImplementedError()

    def get_current_request_url(self):
        raise NotImplementedError()

    def add_url_rule(self, route, func):
        raise NotImplementedError()

    def get_rest_helper_request_context(self):
        raise NotImplementedError()

    def get_current_request_method(self):
        raise NotImplementedError()

    def get_current_request_headers(self):
        raise NotImplementedError()

    def make_json_response(self, obj, status = 200, headers = {}):
        raise NotImplementedError()
    #endregion

    #region optional
    def is_in_test(self):
        return False

    def set_request_args(self, args):
        return args

    def set_request_kwargs(self, kwargs):
        return kwargs
    #endregion