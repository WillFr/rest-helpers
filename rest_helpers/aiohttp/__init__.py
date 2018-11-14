import sys
import json
import asyncio
import aiotask_context
from aiohttp import web,web_request
from multidict import MultiDict
from rest_helpers.framework_adapter import BaseFrameworkAdapter

def aiohttp_adapter_builder(*args, **kwargs):
    if any(args) and isinstance(args[0], web.Application):
        adapter = AioHttpFrameworkAdapter(args[0])
        args = args[1:]
    else:
        adapter = AioHttpFrameworkAdapter()

    return adapter, args, kwargs


class AioHttpFrameworkAdapter(BaseFrameworkAdapter):
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            app.loop.set_task_factory(aiotask_context.task_factory)

    def is_in_test(self):
        # TODO
        return False #not has_request_context() or request_context.top.app.config["TESTING"] is True

    async def get_current_request_body(self):
        return await self.get_rest_helper_request_context().request.text()

    def get_current_request_query_string_args(self):
        query_multidict=self.get_rest_helper_request_context().request.query
        return dict((k,query_multidict.getall(k)) for k in query_multidict.keys())


    def get_current_request_query_string(self):
        return self.get_rest_helper_request_context().request.query_string

    def get_current_request_headers_dict(self):
        return self.get_rest_helper_request_context().request.headers

    def get_current_request_path(self):
        return self.get_rest_helper_request_context().request.path

    def attach_rest_helper_request_context(self, context):
        current_task = asyncio.Task.current_task()
        if not hasattr(current_task, "context"):
            current_task.context = {}

        aiotask_context.set(key="rest_helper_context", value=context)

    def get_current_request_full_path(self):
        return self.get_rest_helper_request_context().request.path_qs

    def get_current_request_url(self):
        return self.get_rest_helper_request_context().request.url

    def add_url_rule(self, route, func):
        self.app.router.add_route(route.options.get("method",["GET"])[0], route.rule.replace("<","{").replace(">","}"), func)

    def get_rest_helper_request_context(self):
        #return asyncio.Task.current_task().rest_helper_context  if hasattr(asyncio.Task.current_task(), "rest_helper_context") else None
        return aiotask_context.get(key="rest_helper_context", default=None)

    def set_request_args(self, args):
        if len(args)>0 and isinstance(args[0], web_request.Request):
            self.get_rest_helper_request_context().request = args[0]
            return args[1:] if len(args)>1 else []
        return args or []

    def set_request_kwargs(self, kwargs):
        kwargs.update(self.get_rest_helper_request_context().request.match_info)
        return kwargs

    def get_current_request_method(self):
        #TODO :
        raise NotImplementedError()

    def get_current_request_headers(self):
        return {}

    def make_json_response(self, obj, status = 200, headers = {}):
        json_content = json.dumps(obj)
        return web.Response(body=json_content, headers = MultiDict(headers), status=status)

def add_default_swagger_routes(app, source):
    import rest_helpers.routes as native_routes
    native_routes.add_default_swagger_routes(AioHttpFrameworkAdapter(app), source)
