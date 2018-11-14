import sys
import pytest
import asyncio
import inspect
import flask

from flask import Blueprint
from schematics.models import Model
from schematics import types

from collections import defaultdict
from mock import patch, Mock, MagicMock

from rest_helpers.flask import binding, routes, handle_async_route, responses
from rest_helpers import validators


@pytest.fixture
def counter(request):
    return defaultdict(int)

#region from_json_body
def test_flask_app(counter):
    dic = {}
    blueprint = Blueprint('test_bp', 'test_bp')

    @routes.route(blueprint, "/test/<test_name>", options={"methods": ["POST"]})
    @binding.from_json_body()
    @binding.from_query_string(field="query")
    def inner_func_1(
        test_name,
        data,
        query,
        json_field:(int, binding.field_from_json_body),
        header_field:(bool, binding.from_header)=False
    ):
        counter["inner_func_1"] += 1
        dic.update(inspect.getargvalues(inspect.currentframe()).locals)
        return responses.ok({"outcome": "success"})

    @routes.route(blueprint, "/test2/<test_name>", options={"methods": ["PUT"]})
    @binding.from_query_string(field="query", as_list=True)
    def inner_func_2(
        test_name,
        query:binding.from_query_string(as_list=True),
        header_field:(bool, binding.from_header)=False
    ):
        counter["inner_func_2"] += 1
        dic.update(inspect.getargvalues(inspect.currentframe()).locals)
        return responses.ok({"outcome": "success"})


    app = flask.Flask(__name__)
    app.register_blueprint(blueprint)

    client = app.test_client()
    response = client.post("/test/foo?query=abc", data='{"field1":"value1", "json_field":"2"}', headers={"header_field":"true"})

    assert dic["test_name"] == "foo"
    assert dic["data"] == {'field1': 'value1', 'json_field': '2'}
    assert dic["query"] == "abc"
    assert dic["json_field"] == 2
    assert dic["header_field"] == True

    assert counter["inner_func_1"] == 1
    assert response.status_code == 200
    assert "success" in response.data.decode()

    response = client.put("/test2/foo?query=abc&query=cde", data='{"field1":"value1", "json_field":"2"}')

    assert dic["query"] == ["abc", "cde"]
    assert dic["header_field"] == False

    assert counter["inner_func_2"] == 1
    assert response.status_code == 200
    assert "success" in response.data.decode()

#endregion