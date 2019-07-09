import sys
import asyncio
import inspect
import functools
from flask import jsonify,request,has_request_context, Blueprint, jsonify, Flask
from flask.globals import _request_ctx_stack as request_context
from multiprocessing.pool import ThreadPool
from rest_helpers.framework_adapter import BaseFrameworkAdapter

def flask_adapter_builder(*args, **kwargs):
    if any(args) and isinstance(args[0], Blueprint):
        adapter = FlaskFrameworkAdapter(args[0])
        args = args[1:]
    else:
        adapter = FlaskFrameworkAdapter()

    return adapter, args, kwargs


_async_handled = False
_async_map = {}
def handle_async_route(loop=None):
    """
    This functions monkey patches the Flask class to transform asynchrnous view functions into
    synchronous ones.

    The async handling should be called only once (which is guarded by the `async_handled` global variable)
    Each route view function will be wrapped in a sync_function only once and this mapping will be stored
    in the `_async_map` variable
    """

    global _async_handled
    if _async_handled is True:
        return
    _async_handled = True

    original = Flask.add_url_rule
    if loop is None:
        try:
            loop = asyncio.get_event_loop()
        except: #pragma: no cover
            loop = asyncio.new_event_loop()

    def replacement(self, rule, endpoint=None, view_func=None, **options):
        global _async_map
        sync_function = _async_map.get(view_func)
        if sync_function is None:
            if view_func is not None :
                def sync_function(*args, **kwargs):
                    result = view_func(*args, **kwargs)
                    return loop.run_until_complete(result) if inspect.iscoroutine(result) else result

                functools.update_wrapper(sync_function, view_func)
                _async_map[view_func] = sync_function
            else:
                sync_function = view_func

        return original(self, rule, endpoint=endpoint or "sync-{}".format(view_func.__name__), view_func=sync_function, **options)

    Flask.add_url_rule = replacement

class FlaskFrameworkAdapter(BaseFrameworkAdapter):
    def __init__(self, blueprint=None):
        self.blueprint = blueprint
        handle_async_route()
        try:
            self.loop = asyncio.get_event_loop()
        except: #pragma: no cover
            self.loop = asyncio.new_event_loop()

    def is_in_test(self):
        return not has_request_context() or request_context.top.app.config["TESTING"] is True

    async def get_current_request_body(self):
        return request.data.decode()

    def get_current_request_query_string_args(self):
        return dict(request.args.lists())

    def get_current_request_query_string(self):
        return request.query_string

    def get_current_request_headers_dict(self):
        return request.headers

    def get_current_request_path(self):
        return request.path

    def attach_rest_helper_request_context(self, context):
        if not hasattr(request, "rest_helper_context"):
            request.rest_helper_context = context

    def get_current_request_full_path(self):
        return request.full_path

    def get_current_request_url(self):
        return request.url

    def add_url_rule(self, route, func):
        endpoint = route.options.pop("endpoint", route.real_view_function.__name__)
        route.rule = (self.blueprint.url_prefix or "") + route.rule
        self.blueprint.add_url_rule(route.rule, endpoint, func, **route.options)

    def get_rest_helper_request_context(self):
        return request.rest_helper_context if hasattr(request, "rest_helper_context") else None

    def get_current_request_method(self):
        return request.method

    def get_current_request_headers(self):
        return {}

    def make_json_response(self, obj, status = 200, headers=None, title=None):
        headers = headers or {}
        response = jsonify(obj)
        if title is not None:
            response._status = str(status)+" "+title
            response._status_code = status
        else:
            response.status_code = status

        for k,v in headers.items():
            response.headers[k] = v
        return response

def add_default_swagger_routes(app, source, **kwargs):
    swagger_ui = Blueprint('swagger_ui', 'swagger_ui', url_prefix='')
    import rest_helpers.routes as native_routes
    native_routes.add_default_swagger_routes(FlaskFrameworkAdapter(swagger_ui), source, **kwargs)
    app.register_blueprint(swagger_ui)
