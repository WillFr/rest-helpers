import sys
import pytest
import asyncio
import inspect

from schematics.models import Model
from schematics import types

from collections import defaultdict
from mock import patch, Mock, MagicMock

import aiohttp
from aiohttp.test_utils import TestClient, TestServer, loop_context
from aiohttp import request, web
from rest_helpers.aiohttp import binding, routes, responses
from rest_helpers import validators
import aiotask_context


@pytest.fixture
def counter(request):
    return defaultdict(int)



#region from_json_body
@pytest.mark.asyncio
async def test_asyncio_app(counter, aiohttp_client, loop):
    dic = {}
    app = web.Application(loop = loop)

    @routes.route(app, "/test/<test_name>", options={"method": ["POST"]})
    @binding.from_json_body()
    @binding.from_query_string(field="query")
    def inner_func_1(
        test_name,
        data,
        query,
        json_field:(int, binding.field_from_json_body()),
        header_field:(bool, binding.from_header())=False
    ):
        counter["inner_func_1"] += 1
        dic.update(inspect.getargvalues(inspect.currentframe()).locals)
        return responses.ok({"outcome": "success"})

    @routes.route(app, "/test2/<test_name>", options={"method": ["PUT"]})
    @binding.from_query_string(field="query", as_list=True)
    def inner_func_2(
        test_name,
        query:binding.from_query_string(as_list=True),
        header_field:(bool, binding.from_header())=False
    ):
        counter["inner_func_2"] += 1
        dic.update(inspect.getargvalues(inspect.currentframe()).locals)
        return responses.ok({"outcome": "success"})


    client = await aiohttp_client(app)
    response = await client.post("/test/foo?query=abc", data='{"field1":"value1", "json_field":"2"}', headers={"header_field":"true"})
    response_text = await response.text()

    assert dic["test_name"] == "foo"
    assert dic["data"] == {'field1': 'value1', 'json_field': '2'}
    assert dic["query"] == "abc"
    assert dic["json_field"] == 2
    assert dic["header_field"] == True

    assert counter["inner_func_1"] == 1
    assert response.status == 200
    assert "success" in response_text

    response = await client.put("/test2/foo?query=abc&query=cde", data='{"field1":"value1", "json_field":"2"}')
    response_text = await response.text()

    assert dic["query"] == ["abc", "cde"]
    assert dic["header_field"] == False

    assert counter["inner_func_2"] == 1
    assert response.status == 200
    assert "success" in response_text

#endregion