
import json
import pytest

from mock import patch, Mock, MagicMock
from rest_helpers import responses, framework_adapter, rest_helper_context
from rest_helpers.jsonapi_objects import Resource

# TODO test success response with non Resource object

@pytest.fixture
def test_adapter(request):
    adapter = MagicMock(wraps=framework_adapter.BaseFrameworkAdapter())
    adapter.make_json_response = lambda  obj,status=200, headers=None: (obj, status, headers)
    adapter.get_current_request_path = lambda: "/"
    adapter.get_current_request_query_string_args = lambda:{}
    adapter.get_current_request_query_string = lambda:b""
    rh_context = rest_helper_context.RestHelperContext()
    adapter.get_rest_helper_request_context = lambda: rh_context
    return adapter

def test_bad_request(test_adapter):
    ex = Exception("test exception")
    resp = responses.bad_request(test_adapter, ex)
    assert resp[1]== 400
    assert str(ex) in str(resp[0])
    assert "Bad request" in str(resp[0])

def test_not_found(test_adapter):
    detail_string = "This is the details about the issue."
    resp = responses.not_found(test_adapter, detail_string)
    assert detail_string in str(resp[0])

def test_not_found_with_details(test_adapter):
    resp = responses.not_found(test_adapter)
    assert resp[1]== 404
    assert "Not found" in str(resp[0])
    assert "The requested resource does not exist" in str(resp[0])

def test_internal_server_error(test_adapter):
    resp = responses.internal_server_error(test_adapter, Exception("test exception"), "stack trace")
    assert resp[1]== 500
    assert "Internal server error" in str(resp[0])
    assert "test exception" in str(resp[0])
    assert "stack trace" in str(resp[0])

def test_ok(test_adapter):
    resp = responses.ok(test_adapter, Resource("type", "name"))
    assert resp[1]== 200

def test_ok_id_only(test_adapter):
    resp = responses.ok(test_adapter, [Resource("name1", "type"), Resource("name2", "type"), Resource("name3", "type")], id_only=True)
    assert resp[1]== 200
    assert all("/type/name" in x for x in resp[0]["data"])

def test_created(test_adapter):
    resp = responses.created(test_adapter, Resource("type", "name"))
    assert resp[1]== 201

def test_accepted(test_adapter):
    resp = responses.accepted(test_adapter, Resource("type", "name"))
    assert resp[1]== 202

    resp = responses.accepted(test_adapter)
    assert resp[1]== 202

def test_ok_with_json_path(test_adapter):
    test_adapter.get_current_request_query_string_args = lambda:{"json_path":["/data/attributes/name"]}
    resp = responses.ok(test_adapter, _TestClass())
    assert resp[0]["data"] == "test_name"
    assert resp[1]== 200

    test_adapter.get_current_request_query_string_args = lambda:{"json_path":["/data/attributes/list"]}
    resp = responses.ok(test_adapter, _TestClass())
    assert resp[0]["data"] == ["1",2,"3"]
    assert resp[1]== 200

    test_adapter.get_current_request_query_string_args = lambda:{"json_path":["/data/attributes/list/1"]}
    resp = responses.ok(test_adapter, _TestClass())
    assert resp[0]["data"] == 2
    assert resp[1]== 200

    test_adapter.get_current_request_query_string_args = lambda:{"json_path":["/data/attributes/dic/entry_1"]}
    resp = responses.ok(test_adapter, _TestClass())
    assert resp[0]["data"] == "value 1"
    assert resp[1]== 200

    test_adapter.get_current_request_query_string_args = lambda:{"json_path":["/data/attributes/dic/list/*/x"]}
    resp = responses.ok(test_adapter, _TestClass())
    assert resp[0]["data"] == [1,2,3]
    assert resp[1]== 200

    test_adapter.get_current_request_query_string_args = lambda:{"json_path":["/data/attributes/list/3"]}
    resp = responses.ok(test_adapter, _TestClass())
    assert resp[1]== 400

    test_adapter.get_current_request_query_string_args = lambda:{"json_path":["/data/attributes/list/a"]}
    resp = responses.ok(test_adapter, _TestClass())
    assert resp[1]== 400

    test_adapter.get_current_request_query_string_args = lambda:{"json_path":["/data/attributes/a"]}
    resp = responses.ok(test_adapter, _TestClass())
    assert resp[1]== 400

    test_adapter.get_current_request_query_string_args = lambda:{"json_path":["/data/attributes/dic/list/*:>b~=(2|3)/b"]}
    resp = responses.ok(test_adapter, _TestClass())
    assert resp[0]["data"] == ["2","3"]
    assert resp[1]== 200

    test_adapter.get_current_request_query_string_args = lambda:{"json_path":["/data/attributes/list/*:sfds"]}
    resp = responses.ok(test_adapter, _TestClass())
    assert resp[1]== 400

def _verify_ok_page_1(resp):
    assert resp[1]== 200
    data = resp[0]
    assert set(x["id"] for x in data["data"]) == set([1,2])
    assert "page=2" in data["links"]["next"]["url"]
    assert data["meta"]["total_pages"]==3
    assert "last" not in data["links"]

def _verify_ok_page_2(resp):
    assert resp[1]== 200
    data = resp[0]
    assert set(x["id"] for x in resp[0]["data"]) == set([3,4])
    assert "page=3&x=3" in data["links"]["next"]["url"]
    assert "page=1&x=3" in data["links"]["last"]["url"]

def _verify_ok_page_3(resp):
    assert resp[1]== 200
    data = resp[0]
    assert set(x["id"] for x in resp[0]["data"]) == set([5])
    assert "page=2" in data["links"]["last"]["url"]
    assert "next" not in data["links"]
    return

def test_ok_with_explicit_page_size(test_adapter):
    resp_list = [_TestClass(1), _TestClass(2), _TestClass(3), _TestClass(4), _TestClass(5)]

    test_adapter.get_current_request_query_string_args = lambda:{}
    test_adapter.get_current_request_query_string = lambda:b""
    resp = responses.ok(test_adapter, resp_list, page_size=2)
    _verify_ok_page_1(resp)

    test_adapter.get_current_request_query_string_args = lambda:{"page":["2"], "x":["3"]}
    test_adapter.get_current_request_query_string = lambda:b"page=2&x=3"
    resp = responses.ok(test_adapter, resp_list, page_size=2)
    _verify_ok_page_2(resp)

    test_adapter.get_current_request_query_string_args = lambda:{"page":["3"]}
    test_adapter.get_current_request_query_string = lambda:b"page=3"
    resp = responses.ok(test_adapter, resp_list, page_size=2)
    _verify_ok_page_3(resp)

def test_ok_with_context_page_size(test_adapter):
    resp_list = [_TestClass(1), _TestClass(2), _TestClass(3), _TestClass(4), _TestClass(5)]
    test_adapter.get_current_request_query_string_args = lambda:{}
    test_adapter.get_current_request_query_string = lambda:b""
    test_adapter.get_rest_helper_request_context().page_size = 2
    resp = responses.ok(test_adapter, resp_list)
    _verify_ok_page_1(resp)

    test_adapter.get_current_request_query_string_args = lambda:{"page":["2"], "x":["3"]}
    test_adapter.get_current_request_query_string = lambda:b"page=2&x=3"
    test_adapter.get_rest_helper_request_context().page_size = lambda : 2
    resp = responses.ok(test_adapter, resp_list)
    _verify_ok_page_2(resp)


    test_adapter.get_current_request_query_string_args = lambda:{"page":["3"]}
    test_adapter.get_current_request_query_string = lambda:b"page=3"
    test_adapter.get_rest_helper_request_context().page_size = lambda : 4-2
    resp = responses.ok(test_adapter, resp_list)
    _verify_ok_page_3(resp)

def test_ok_with_query_string_page_size(test_adapter):
    resp_list = [_TestClass(1), _TestClass(2), _TestClass(3), _TestClass(4), _TestClass(5)]
    test_adapter.get_current_request_query_string_args = lambda:{"page_size":"2"}
    test_adapter.get_current_request_query_string = lambda:b"page_size=2"
    test_adapter.get_rest_helper_request_context().page_size = None
    resp = responses.ok(test_adapter, resp_list)
    _verify_ok_page_1(resp)

    test_adapter.get_current_request_query_string_args = lambda:{"page_size":"2", "page":["2"], "x":["3"]}
    test_adapter.get_current_request_query_string = lambda:b"page_size=2&page=2&x=3"
    test_adapter.get_rest_helper_request_context().page_size = None
    resp = responses.ok(test_adapter, resp_list)
    _verify_ok_page_2(resp)

class _TestClass(Resource):
    def __init__(self, id = 1):
        super(_TestClass, self).__init__("test_name", "test_type")
        self.id=id
        self.list = ["1",2,"3"]
        self.dic = {
            "entry_1": "value 1",
            "list": [{"x":1,"b":"2"},{"x":2,"b":"3"},{"x":3,"b":"4"}]
        }

def test_parse_filter():
    filter = responses._parse_filter("*:>a>b==3")
    test_data = [
        {"a":{"b":2}, "c":4},
        {"a":{"b":3}, "c":4},
        {"a":{"b":3, "c":4}},
    ]

    filtered = [x for x in test_data if filter(x)]
    assert filtered == [{'a': {'b': 3}, 'c': 4}, {'a': {'b': 3, 'c': 4}}]