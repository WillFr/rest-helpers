import inspect

# TODO: make generic
from random import randint
from requests_futures.sessions import FuturesSession

from flask import make_response

class BaseValidator():
    def __init__(self, framework_adapter):
        self.framework_adapter = framework_adapter


    def validate(self, untrusted_response, trusted_response):
        return untrusted_response.status_code  == trusted_response.status_code

class BaseRequestAdapter():
    def __init__(self, shadow_to, framework_adapter):
        self.framework_adapter = framework_adapter
        self.shadow_to = shadow_to

    async def _get_request_args(self):
        url = "{}{}".format(
                self.shadow_to,
                self.framework_adapter.get_current_request_full_path())
        return {
            "method":self.framework_adapter.get_current_request_method(),
            "url":url,
            "data": await self.framework_adapter.get_current_request_body(),
            "headers":self.framework_adapter.get_current_request_headers()
        }

class shadow_traffic(object):
    def __init__(self, framework_adapter, shadow_to, ratio, request_adapter=None, validator=None):
        self.framework_adapter = framework_adapter
        self.shadow_to = shadow_to
        self.ratio = ratio
        self.request_adapter = request_adapter if request_adapter is not None else BaseRequestAdapter(self.shadow_to, self.framework_adapter)
        self.validator = validator if validator is not None else BaseValidator(self.framework_adapter)
        self.f = None

    async def _on_request(self, *args, **kwargs):
        should_fork = randint(0, 100)<= (self.ratio * 100)
        if should_fork:
            request_kwargs = await self.request_adapter._get_request_args()
            session = FuturesSession()
            response_future = session.request(**request_kwargs)

        try:
            result = await self.f(*args, **kwargs) if inspect.iscoroutinefunction(self.f) else self.f(*args, **kwargs)
            result = make_response(self.f(*args, **kwargs))
            response = response_future.result()
            if self.validator.validate(result, response):
                return result
            else:
                return _make_flask_response(response)
        except:
            response = response_future.result()
            return _make_flask_response(response)

    def __call__(self, f):
        self.f = f
        return self._on_request

def _make_flask_response(request_result):
    response = make_response(request_result.text, request_result.status_code, request_result.headers.items())
    return response
