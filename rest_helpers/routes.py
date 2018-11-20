import os
import logging
import traceback
import functools
import inspect
from jinja2 import Template
from rest_helpers import responses, swagger, rest_helper_context, binding
from rest_helpers.common import decorators
from rest_helpers.framework_adapter import BaseFrameworkAdapter

LOGGER = logging.getLogger(__name__)

_swagger_routes = []

#TODO: move the url parameter logic to the binding section

class route(object):
    """
    This decorator is to be used to create a route, catching all exceptions in order to return a well formatted 500 response.
    """

    def __init__(self, framework_adapter, rule, options=None, doc=True, versionner=None, exception_handler=None):
        assert isinstance(framework_adapter, BaseFrameworkAdapter)
        self.framework_adapter = framework_adapter
        self.options = options if options else { "methods":["GET"]}
        self.doc = doc
        self.view_function = None
        self.real_view_function = None #The view function might be multiple wrapped, this is the original viewfunction
        self.rule = rule
        self.id = None
        self.versionner = versionner
        self.exception_handler = exception_handler or functools.partial(responses.base_exception_handler, self.framework_adapter)

    async def _on_request(self, *args, **kwargs):
        try:
            rh_context = rest_helper_context.RestHelperContext()
            if self.versionner is not None:
                rh_context.versionner = self.versionner()
                rh_context.versionner.set_request_args(request_args=args, request_kwargs=kwargs)

            self.framework_adapter.attach_rest_helper_request_context(rh_context)

            self._before_fn_call(args, kwargs)
            result = await self._binding_functions(*args, **kwargs) if inspect.iscoroutinefunction(self._binding_functions) else self._binding_functions(*args, **kwargs)
            return result if rh_context.versionner is None else rh_context.versionner.response(result)
        except Exception as ex:
            LOGGER.error("An exception {0} occured: {1}\n stacktrace: {2} \n request url: {3} \n request body: {4}".format(
                ex.__class__.__name__,
                str(ex),
                traceback.format_exc(),
                self.framework_adapter.get_current_request_full_path(),
                await self.framework_adapter.get_current_request_body()))

            return self.exception_handler(ex)

    def _before_fn_call(self, f_arg, f_kwargs):
        pass

    def __call__(self, f):
        self.view_function = f
        self.real_view_function = f

        while hasattr(self.real_view_function, "__wrapped__"):
            self.real_view_function = self.real_view_function.__wrapped__
        self.id = decorators.get_decorated_id(self.real_view_function)

        if self.versionner is not None:
            self.versionner.version_route(self)

        self.framework_adapter.add_url_rule(self, self._on_request)
        if self.doc:
            _swagger_routes.append(self)

        self._binding_functions = binding.bind_hints(self.framework_adapter)(self.view_function)
        return self._on_request

class base_resource_route(route):
    """
    This decorator is the base class to create RESTful api routes. It handles the resource id
    binding, as well as catching all exceptions in order to return a well formatted 500 response.
    """

    def __init__(self, framework_adapter, resource_class, doc=True, options=None, versionner=None, exception_handler=None):
        super(base_resource_route, self).__init__(framework_adapter, rule=None, options=options, doc=doc, versionner=versionner, exception_handler=exception_handler)
        self.resource_class = resource_class

    def _before_fn_call(self, f_arg, f_kwargs):
        if "resource_id" not in self.real_view_function.__code__.co_varnames:
            return

        # We are using the resource type incombination with the url segments to address cases where there is a base path/prefix.
        url_segments = self.framework_adapter.get_current_request_url().strip(" /").split("/")
        type_segments = self.resource_class.resource_type.strip(" /").split('/')
        type_segments_length = len(type_segments)
        f_kwargs["resource_id"] = "".join("/{0}/{1}".format(t,url_segments[-type_segments_length*2+i*2+1]) for i,t in enumerate(type_segments))

class get_resource_route(base_resource_route):
    def __init__(self, framework_adapter, resource_class, doc=True, options=None, versionner=None, exception_handler=None):
        super(get_resource_route, self).__init__(framework_adapter, resource_class, doc, options=options, versionner=versionner, exception_handler=exception_handler)
        self.rule = "".join("/{0}/<{1}_name>".format(x, x[:-3]+'y' if x[-3:] == 'ies' else (x[:-1] if x[-1] == 's' else x)) for x in resource_class.resource_type.strip(" /").split("/"))
        self.options["methods"] = ["GET"]

class get_all_resources_route(get_resource_route):
    def __init__(self, framework_adapter, resource_class, doc=True, page_size=None, options=None, versionner=None, exception_handler=None):
        super(get_all_resources_route, self).__init__(framework_adapter, resource_class, doc, options, versionner=versionner, exception_handler=exception_handler)
        self.rule = self.rule[:self.rule.rindex("/")+1]
        self.page_size = page_size

    def _before_fn_call(self, f_arg, f_kwargs):
        self.framework_adapter.get_rest_helper_request_context().page_size = self.page_size

        if "resource_id" not in self.real_view_function.__code__.co_varnames:
            return

        # We are using the resource type incombination with the url segments to address cases where there is a base path/prefix.
        url_segments = self.framework_adapter.get_current_request_url().strip(" /").split("/")[:-1]
        type_segments = self.resource_class.resource_type.strip(" /").split('/')[:-1]
        type_segments_length = len(type_segments)
        f_kwargs["resource_id"] = "".join("/{0}/{1}".format(t,url_segments[-type_segments_length*2+i*2+1]) for i,t in enumerate(type_segments))

class delete_resource_route(base_resource_route):
    def __init__(self, framework_adapter, resource_class, doc=True, options=None, versionner=None, exception_handler=None):
        super(delete_resource_route, self).__init__(framework_adapter, resource_class, doc, options=options, versionner=versionner, exception_handler=exception_handler)
        self.rule = "".join("/{0}/<{1}_name>".format(x, x[:-3]+'y' if x[-3:] == 'ies' else (x[:-1] if x[-1] == 's' else x)) for x in resource_class.resource_type.strip(" /").split("/"))
        self.options["methods"] = ["DELETE"]

class put_resource_route(get_resource_route):
    def __init__(self, framework_adapter, resource_class, doc=True, options=None, versionner=None, exception_handler=None):
        super(put_resource_route, self).__init__(framework_adapter, resource_class, doc, options=options, versionner=versionner, exception_handler=exception_handler)
        self.options["methods"] = ["PUT"]

class patch_resource_route(get_resource_route):
    def __init__(self, framework_adapter, resource_class, doc=True, options=None, versionner=None, exception_handler=None):
        super(patch_resource_route, self).__init__(framework_adapter, resource_class, doc, options=options, versionner=versionner, exception_handler=exception_handler)
        self.options["methods"] = ["PATCH"]

class operation_resource_route(get_resource_route):
    def __init__(self, framework_adapter, resource_class, operation_name, doc=True, options=None, versionner=None, exception_handler=None):
        super(operation_resource_route, self).__init__(framework_adapter, resource_class, doc, options, versionner, exception_handler)
        self.options["methods"] = ["POST"]
        self.operation_name = operation_name
        self.rule = "{0}/{1}".format(self.rule, self.operation_name)

    def _before_fn_call(self, f_arg, f_kwargs):
        if "resource_id" not in self.real_view_function.__code__.co_varnames:
            return

        # We are using the resource type incombination with the url segments to address cases where there is a base path/prefix.
        url_segments = self.framework_adapter.get_current_request_url().strip(" /").split("/")[:-1]
        type_segments = self.resource_class.resource_type.strip(" /").split('/')
        type_segments_length = len(type_segments)
        f_kwargs["resource_id"] = "".join("/{0}/{1}".format(t,url_segments[-type_segments_length*2+i*2+1]) for i,t in enumerate(type_segments))

class group_operation_resource_route(operation_resource_route):
    def __init__(self, framework_adapter, resource_class, operation_name=None, doc=True, options=None, versionner=None, exception_handler=None):
        super(group_operation_resource_route, self).__init__(framework_adapter, resource_class, operation_name, doc, options, versionner, exception_handler)
        self.rule = "{0}/{1}".format("/".join(self.rule.split("/")[:-2]), operation_name)

    def _before_fn_call(self, f_arg, f_kwargs):
        if "resource_id" not in self.real_view_function.__code__.co_varnames:
            return

        # We are using the resource type incombination with the url segments to address cases where there is a base path/prefix.
        url_segments = self.framework_adapter.get_current_request_url().strip(" /").split("/")[:-2]
        type_segments = self.resource_class.resource_type.strip(" /").split('/')[:-1]
        type_segments_length = len(type_segments)
        f_kwargs["resource_id"] = "".join("/{0}/{1}".format(t,url_segments[-type_segments_length*2+i*2+1]) for i,t in enumerate(type_segments))
#region non decorator helpers

def add_get_resource_route(func, *args, **kwargs):
    get_resource_route(*args, **kwargs)(func)


def add_get_all_resource_route(func, *args, **kwargs):
    get_all_resources_route(*args, **kwargs)(func)

def add_put_resource_route(func, *args, **kwargs):
    put_resource_route(*args, **kwargs)(func)
    
def add_patch_resource_route(func, *args, **kwargs):
    patch_resource_route(*args, **kwargs)(func)
    
def add_operation_route(func, *args, **kwargs):
    operation_resource_route(*args, **kwargs)(func)

def add_group_operation_route(func, *args, **kwargs):
    group_operation_resource_route(*args, **kwargs)(func)

#endregion


#region extras

def add_default_swagger_routes(framework_adapter, source, basepath=None, **kwargs):
    """
    This function adds two default endpoints :
    /swagger.json => swagger spec
    / => swagger ui

    Arguments:
        framework_adapter {BaseFrameworkAdapter} -- The web framework adapter used to setup the routes.
        source {dict|func} -- The dictionary or documented method containing the service documentation.
    """
    service_description = source if isinstance(source,dict) else swagger._get_swagger_part(source, swagger.SWAGGER_DOCUMENTATION_KEY)

    basePath = basepath or service_description.get("basePath","/")
    basePath = basePath + ("/" if basePath[-1]!="/" else "")
    def get_swagger_json():
        return framework_adapter.make_json_response(swagger.get_swagger_service_description(source))

    swagger_json_route = base_resource_route(framework_adapter, None, doc=False, options={ "methods": ["GET"] })
    swagger_json_route.rule = basePath + "swagger.json"
    swagger_json_route(get_swagger_json)

    swagger_ui = None
    swagger_ui_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "templates", "swagger-ui.html")
    with open(swagger_ui_path, "r") as f:
        swagger_ui = Template(f.read()).render(**kwargs)
    def get_swagger_ui():
        return swagger_ui
    swagger_route = base_resource_route(framework_adapter, None, doc=False, options={ "methods": ["GET"] })
    swagger_route.rule = basePath
    swagger_route(get_swagger_ui)

#endregion
