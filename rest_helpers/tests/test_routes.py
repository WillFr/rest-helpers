import pytest
import functools
from mock import patch, Mock, MagicMock
from rest_helpers import routes, framework_adapter, binding, responses, jsonapi_objects
from rest_helpers.jsonapi_objects import Resource
from rest_helpers.tests.test_common import TestRequestContext as RequestContext, TestClass, SubTestClass

class TestAdapter(framework_adapter.BaseFrameworkAdapter):
    def __init__(self):
        self.add_url_rule = MagicMock()
        self.get_current_request_full_path = MagicMock()
        self.attach_rest_helper_request_context = MagicMock()
        self.make_json_response = MagicMock(side_effect=lambda *a,**k: a)
        self.get_rest_helper_request_context = MagicMock()

    async def get_current_request_body(self):
        return ""


def _decorator(f):
    @functools.wraps(f)
    def inner(*args, **kwargs):
        return f(*args, **kwargs)
    return inner

@pytest.mark.asyncio
async def test_route():
    adapter = TestAdapter()

    exception = None
    options = {"a":"b"}
    try:
        routes.route(MagicMock(), rule="/test", doc=True, options=options)
    except Exception as ex:
        exception = ex

    assert exception is not None

    class TestExc(Exception):
        pass

    route = routes.route(adapter, "/test", doc=True, options=options, exception_handler=lambda ex: "CDE" if isinstance(ex,TestExc) else None)
    assert route.rule == "/test"

    d = {"return_value": 5}

    # This decorator is here to verrify that stacking work
    @route
    @_decorator
    def test_function(data):
        if d["return_value"] == 5:
            return d["return_value"]
        elif d["return_value"] == 4:
            raise TestExc("This is a test exc")
        else:
            raise Exception("an error occured")

    # functools wrap changes the attributes of the decorator function
    # to make it look like the decorated function : in order to make sure that
    # the fields are setup properly, we need to look at the __code__ and specifically
    # the argument of the function to make sure view_function points to the
    # decorator and real_view_function points to the actual function.
    assert route.real_view_function.__code__.co_varnames == ('data',) and route.real_view_function.__code__.co_name == "test_function"
    assert len(adapter.add_url_rule._mock_call_args_list) == 1
    assert adapter.add_url_rule._mock_call_args[0][0] == route
    assert adapter.add_url_rule._mock_call_args[0][1].__code__.co_name == "_on_request"
    assert routes._swagger_routes[0] == route

    assert await test_function(None) == 5
    d["return_value"] = 4
    response = await test_function(None)
    assert response == "CDE"

    d["return_value"] = None
    route.exception_handler = MagicMock(return_value="ABC")
    response = await test_function(None)
    assert response == "ABC"


@pytest.mark.asyncio
async def test_route_with_versionner():
    from rest_helpers.versioning import UrlRootVersionner
    class TestVersionner(UrlRootVersionner):
        class v1:
            def response(self, response):
                return 2
        class v2:
            pass

    adapter = TestAdapter()
    route = routes.route(adapter, "/test", versionner=TestVersionner)


    # This decorator is here to verrify that stacking work
    @route
    @_decorator
    def test_function(x=None, abc=None):
        return {"a":1, "b":{"c":2}}

    assert route.rule == '/<rest_helper_version>/test'

    assert await test_function(rest_helper_version="v2") == {"a":1, "b":{"c":2}}
    assert await test_function(rest_helper_version="v1") == 2
    assert await test_function() == {"a":1, "b":{"c":2}} == {"a":1, "b":{"c":2}}


@pytest.mark.asyncio
async def test_base_resource_route_resource_id_binding():
    adapter = TestAdapter()
    options = {"a":"b"}
    d = {}
    route = routes.base_resource_route(adapter, TestClass, doc=True, options=options)
    @route
    @_decorator
    def test_function(resource_id):
        d["resource_id"] = resource_id
        return "Ok"

    subroute = routes.base_resource_route(adapter, SubTestClass, doc=True, options=options)
    @subroute
    @_decorator
    def subtest_function(resource_id):
        d["resource_id"] = resource_id
        return "Ok"

    adapter.get_current_request_url = MagicMock(return_value="/tests/test_name")
    await test_function()
    assert d["resource_id"] == "/tests/test_name"

    adapter.get_current_request_url = MagicMock(return_value="/tests/test_name/subtests/subtest_name")
    await subtest_function()
    assert d["resource_id"] == "/tests/test_name/subtests/subtest_name"

@pytest.mark.asyncio
@pytest.mark.parametrize("route, route_kwargs, rule, method, res_id, url",[
    (routes.get_resource_route, { "resource_class":TestClass }, "/tests/<test_name>", "GET", "/tests/test_name", "/tests/test_name"),
    (routes.get_all_resources_route, { "resource_class":TestClass }, "/tests/", "GET", "", "/tests/"),
    (routes.put_resource_route, { "resource_class":TestClass }, "/tests/<test_name>", "PUT", "/tests/test_name", "/tests/test_name"),
    (routes.patch_resource_route, { "resource_class":TestClass }, "/tests/<test_name>", "PATCH", "/tests/test_name", "/tests/test_name"),
    (routes.delete_resource_route, { "resource_class":TestClass }, "/tests/<test_name>", "DELETE", "/tests/test_name", "/tests/test_name"),
    (routes.operation_resource_route ,{ "resource_class":TestClass, "operation_name":"test_op"}, "/tests/<test_name>/test_op", "POST", "/tests/test_name", "/tests/test_name/test_op"),
    (routes.group_operation_resource_route ,{ "resource_class":TestClass, "operation_name":"test_op"}, "/tests/test_op", "POST", "", "/tests/test_op"),

    (routes.get_resource_route, { "resource_class":SubTestClass }, "/tests/<test_name>/subtests/<subtest_name>", "GET", "/tests/test_name/subtests/subtest", "/tests/test_name/subtests/subtest"),
    (routes.get_all_resources_route, { "resource_class":SubTestClass }, "/tests/<test_name>/subtests/", "GET", "/tests/test_name", "/tests/test_name/subtests/"),
    (routes.put_resource_route, { "resource_class":SubTestClass }, "/tests/<test_name>/subtests/<subtest_name>", "PUT", "/tests/test_name/subtests/subtest", "/tests/test_name/subtests/subtest"),
    (routes.patch_resource_route, { "resource_class":SubTestClass }, "/tests/<test_name>/subtests/<subtest_name>", "PATCH", "/tests/test_name/subtests/subtest", "/tests/test_name/subtests/subtest"),
    (routes.delete_resource_route, { "resource_class":SubTestClass }, "/tests/<test_name>/subtests/<subtest_name>", "DELETE", "/tests/test_name/subtests/subtest", "/tests/test_name/subtests/subtest"),
    (routes.operation_resource_route, { "resource_class":SubTestClass, "operation_name":"test_op"}, "/tests/<test_name>/subtests/<subtest_name>/test_op", "POST", "/tests/test_name/subtests/subtest", "/tests/test_name/subtests/subtest/test_op"),
    (routes.group_operation_resource_route, { "resource_class":SubTestClass, "operation_name":"test_op"}, "/tests/<test_name>/subtests/test_op", "POST", "/tests/test_name", "/tests/test_name/subtests/test_op"),
])
async def test_resource_routes(route, route_kwargs, rule, method, res_id, url):
    adapter = TestAdapter()
    d={}
    # This decorator is here to verrify that stacking work
    r = route(adapter, **route_kwargs)
    @r
    @_decorator
    def test_function(resource_id):
        d["resource_id"] = resource_id
        return "Ok"

    assert r.rule == rule
    assert r.options["methods"] == [method]
    assert adapter.add_url_rule.mock_calls[0][1][0] == r
    adapter.get_current_request_url = MagicMock(return_value=url)
    assert await test_function() == "Ok"
    assert d["resource_id"] == res_id

    @route(adapter, **route_kwargs)
    @_decorator
    def test_function2():
        return "Ok"
    assert await test_function2() == "Ok"


@pytest.mark.parametrize("helper_method, kwargs",[
    (routes.add_get_resource_route, { "resource_class": TestClass}),
    (routes.add_get_all_resource_route, { "resource_class": TestClass}),
    (routes.add_put_resource_route, { "resource_class": TestClass}),
    (routes.add_patch_resource_route, { "resource_class": TestClass}),
    (routes.add_operation_route, { "resource_class": TestClass, "operation_name":'test_op'}),
    (routes.add_group_operation_route, { "resource_class": TestClass, "operation_name":'test_group_op'}),
])
def test_add_route_helpers(helper_method, kwargs):
    adapter = TestAdapter()

    @_decorator
    def test_function(): # pragma: no cover : This is a function used within a test
        pass

    helper_method(test_function, adapter, **kwargs)
    adapter.add_url_rule.assert_called_once()
    route_dict = adapter.add_url_rule._mock_call_args[0][0].__dict__
    assert adapter.add_url_rule.call_count == 1
    for k,v in kwargs.items():
        assert route_dict[k] == v

def test_add_swagger_route():
    adapter = TestAdapter()
    routes.add_default_swagger_routes(adapter, {})
    assert adapter.add_url_rule.call_count == 2
    assert adapter.add_url_rule.mock_calls[0][1][0].rule == "/swagger.json"
    assert adapter.add_url_rule.mock_calls[1][1][0].rule == "/"

    routes.add_default_swagger_routes(adapter, {"basePath":"/v3"})
    assert adapter.add_url_rule.call_count == 4
    assert adapter.add_url_rule.mock_calls[2][1][0].rule == "/v3/swagger.json"
    assert adapter.add_url_rule.mock_calls[3][1][0].rule == "/v3/"

    routes.add_default_swagger_routes(adapter, {}, basepath="/v3")
    assert adapter.add_url_rule.call_count == 6
    assert adapter.add_url_rule.mock_calls[4][1][0].rule == "/v3/swagger.json"
    assert adapter.add_url_rule.mock_calls[5][1][0].rule == "/v3/"


#TODO : test get all resources route with paging
