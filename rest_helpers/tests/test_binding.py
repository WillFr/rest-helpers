import sys
import pytest
import asyncio
import httpretty

from mock import patch, Mock, MagicMock
from rest_helpers import binding, validators, framework_adapter, rest_exceptions
from rest_helpers.tests import test_common

@pytest.fixture
def test_adapter(request):
    adapter = MagicMock(wraps=framework_adapter.BaseFrameworkAdapter())
    adapter.is_in_test = lambda:False
    adapter.get_rest_helper_request_context = lambda:None
    adapter.make_json_response = lambda  obj,status=200, headers=None: (obj, status, headers)
    return adapter

@pytest.mark.asyncio
async def test_bind_hints(counter, test_adapter):
    binding_decorator_1 = binding.base_binder(test_adapter)
    binding_decorator_1.get_value = asyncio.coroutine(lambda:"1")

    binding_decorator_2 = binding.base_binder(test_adapter)
    binding_decorator_2.get_value = asyncio.coroutine(lambda:"true")

    @binding.bind_hints(test_adapter)
    def inner_func(
        abc: (int, binding_decorator_1),
        cde: (bool, binding_decorator_2)):
        counter["inner_func"] += 1
        assert abc == 1
        assert cde == True
        return "success"

    response = await inner_func()

    # This will verify that the function is not called multiple times
    assert counter["inner_func"] == 1

    # This will verify that the assertion in the inner function succeeded
    assert response == "success"

@pytest.mark.asyncio
async def test_bind_hints_with_no_hints(counter, test_adapter):
    """
    This use to cause an infinite recursion when the wrapper was
    added even when no bind hints was used
    """

    @binding.bind_hints(test_adapter)
    def inner_func(
        abc,
        cde):
        counter["inner_func"] += 1
        assert abc == 1
        assert cde == True
        return "success"

    response = inner_func(1, True)

    # This will verify that the function is not called multiple times
    assert counter["inner_func"] == 1

    # This will verify that the assertion in the inner function succeeded
    assert response == "success"

#region base_binder
@pytest.mark.asyncio
@pytest.mark.base_binder
async def test_base_binder_with_default_values(counter, test_adapter):
    binding_decorator = binding.base_binder(test_adapter, field="abc")
    binding_decorator.get_value = asyncio.coroutine(lambda:"value")

    @binding_decorator
    def inner_func(abc):
        counter["inner_func"] += 1
        assert abc == "value"
        return "success"

    response = await inner_func()
    assert counter["inner_func"] == 1
    assert response == "success"

@pytest.mark.asyncio
@pytest.mark.base_binder
async def test_base_binder_with_deserializer(counter, test_adapter):
    binding_decorator = binding.base_binder(test_adapter, field="abc", deserializer=lambda x:test_obj(x))
    binding_decorator.get_value = asyncio.coroutine(lambda:"value")

    class test_obj:
        def __init__(self, dic):
            self.dic = dic

    @binding_decorator
    def inner_func(abc):
        counter["inner_func"] += 1
        assert isinstance(abc, test_obj)
        assert abc.dic == "value"
        return "success"

    response = await inner_func()
    assert counter["inner_func"] == 1
    assert response == "success"


@pytest.mark.asyncio
@pytest.mark.base_binder
@pytest.mark.parametrize("exception,expected", [
    (binding.MissingFieldException("This is a missing field exception."), binding.MissingFieldException),
    (binding.InvalidDataException("This is a invalid data exception."), rest_exceptions.InvalidDataException),
    (Exception("This is a server exception."), Exception),
])
async def test_base_binder_with_exception(counter, test_adapter, exception, expected):
    binding_decorator = binding.base_binder(test_adapter, field="abc")
    binding_decorator.get_value = asyncio.coroutine(lambda:(_ for _ in ()).throw(exception))

    @binding_decorator
    def inner_func(abc): #pragma: no cover
        counter["inner_func"] += 1
        return "success"

    excep = None
    try:
        response = await inner_func()
    except Exception as ex:
        excep = ex

    assert counter["inner_func"] == 0
    assert isinstance(excep, expected)

@pytest.mark.asyncio
@pytest.mark.base_binder
async def test_base_binder_with_default_value_field(counter, test_adapter):
    binding_decorator = binding.base_binder(test_adapter, field="abc")
    binding_decorator.get_value = asyncio.coroutine(lambda:(_ for _ in ()).throw(binding.MissingFieldException))

    @binding_decorator
    def inner_func(abc = None):
        counter["inner_func"] += 1
        return "success"

    response = await inner_func()
    assert counter["inner_func"] == 1
    assert response == "success"


@pytest.mark.asyncio
@pytest.mark.base_binder
@pytest.mark.parametrize("data,expected,inner_func_count", [
    ("valid", "success",1),
    ("not valid", "field1 must have value 1", 0),
])
async def test_base_binder_with_validator(counter, test_adapter, data, expected, inner_func_count):
    def validator(data, post):
        counter["validator"] += 1
        return (data=="valid", "field1 must have value 1.")

    binding_decorator = binding.base_binder(test_adapter, field="abc", validator=validator)
    binding_decorator.get_value = asyncio.coroutine(lambda:data)

    @binding_decorator
    def inner_func(abc):
        counter["inner_func"] += 1
        return "success"

    excep = None
    try:
        response = await inner_func()
    except Exception as ex:
        excep = ex

    assert counter["inner_func"]==inner_func_count
    assert counter["validator"]>=1
    assert expected in str(excep if inner_func_count == 0 else response)


@pytest.mark.asyncio
@pytest.mark.base_binder
async def test_base_binder_in_test_mode(counter, test_adapter):
    test_adapter.is_in_test=lambda:True

    binding_decorator = binding.base_binder(test_adapter, field="abc")

    @binding_decorator
    def inner_func(abc):
        counter["inner_func"] += 1
        assert abc == 'value1'
        return "success"

    response = await inner_func('value1')
    assert counter["inner_func"] == 1
    assert response == "success"


@pytest.mark.asyncio
@pytest.mark.base_binder
async def test_base_binder_on_async_function(counter, test_adapter):
    binding_decorator = binding.base_binder(test_adapter, field="abc")
    binding_decorator.get_value = asyncio.coroutine(lambda:"value")

    @binding_decorator
    async def inner_func(abc):
        counter["inner_func"] += 1
        assert abc == 'value'
        return "success"

    response = await inner_func()
    assert counter["inner_func"] == 1
    assert response == "success"

@pytest.mark.asyncio
@pytest.mark.base_binder
async def test_base_binder_with_improper_field(counter, test_adapter):
    binding_decorator = binding.base_binder(test_adapter, field="foo")
    with pytest.raises(Exception) as ex:
        @binding_decorator
        def inner_func(abc): #pragma: no cover
            counter["inner_func"] += 1
            assert abc == "value"
            return "success"

    assert "Argument foo could not be found in function" in str(ex.value)

async def test_base_binder_default_validator(test_adapter, make_coro):
    with patch("rest_helpers.validators.get_type_validators", MagicMock(return_value= lambda x,y: (1,""))) as get_type_validators:
        binding_decorator = binding.base_binder(test_adapter, field="abc")
        binding_decorator.get_value = lambda : make_coro("1")
        @binding_decorator
        def inner_func(abc:int):
            return "success" #pragma: no cover
        await inner_func()
        get_type_validators._mock_call_args[0][0] == int

        binding_decorator = binding.base_binder(test_adapter, field="abc", type=bool)
        binding_decorator.get_value = lambda : make_coro("True")
        @binding_decorator
        def inner_func(abc):
            return "success" #pragma: no cover
        await inner_func()
        get_type_validators._mock_call_args[0][0] == bool


@pytest.mark.base_binder
async def test_base_binder_default_deserializer(test_adapter, make_coro):
    with patch("rest_helpers.type_deserializers.get_default_deserializer", MagicMock(return_value= lambda x: 1)) as get_default_deserializer:
        binding_decorator = binding.base_binder(test_adapter, field="abc")
        binding_decorator.get_value = lambda : make_coro("1")
        @binding_decorator
        def inner_func(abc:int):
            return "success" #pragma: no cover
        await inner_func()
        get_default_deserializer._mock_call_args[0][0] == int

        binding_decorator = binding.base_binder(test_adapter, field="abc", type=bool)
        binding_decorator.get_value = lambda : make_coro("1")
        @binding_decorator
        def inner_func(abc):
            return "success" #pragma: no cover
        await inner_func()
        get_default_deserializer._mock_call_args[0][0] == bool

@pytest.mark.asyncio
@pytest.mark.base_binder
async def test_base_binder_stacking(test_adapter, counter):
    binding_decorator_abc = binding.base_binder(test_adapter, field="abc")
    binding_decorator_abc.get_value = asyncio.coroutine(lambda:"valueABC")

    binding_decorator_cde = binding.base_binder(test_adapter, field="cde")
    binding_decorator_cde.get_value = asyncio.coroutine(lambda:"valueCDE")

    @binding_decorator_abc
    @binding_decorator_cde
    def inner_func(abc, cde):
        counter["inner_func"] += 1
        assert abc == "valueABC"
        assert cde == "valueCDE"
        return "success"

    response = await inner_func()
    assert counter["inner_func"] == 1
    assert response == "success"

    assert binding_decorator_abc.real_view_function.__name__ == "inner_func"
    assert binding_decorator_cde.real_view_function.__name__ == "inner_func"
#endregion

#region from_json_body
@pytest.mark.asyncio
async def test_from_json_body_with_default_values(counter, test_adapter):
    test_adapter.get_current_request_body = asyncio.coroutine(lambda:'{"field1":"value1", "field2":"value2"}')
    @binding.from_json_body(test_adapter)
    def inner_func(data):
        counter["inner_func"] += 1
        assert data == { 'field1':'value1', 'field2':'value2'}
        return "success"

    response = await inner_func()
    assert counter["inner_func"] == 1
    assert response == "success"


@pytest.mark.asyncio
async def test_from_json_body_with_validator_missing_data(counter, test_adapter):
    test_adapter.get_current_request_body = asyncio.coroutine(lambda:'')

    @binding.from_json_body(test_adapter)
    def inner_func(data): #pragma: no cover
        counter["inner_func"] += 1
        return "success"

    excep = None
    try:
        response = await inner_func()
    except Exception as ex:
        excep = ex

    assert counter["inner_func"] == 0
    assert "The body of the request is not valid: a json object is expected." in str(excep)

@pytest.mark.asyncio
@pytest.mark.parametrize("version, expected", [
    ("v1", {'a': 1}),
    ("v2", {'a': 'b', 'field1': 'value1', 'field2': 'value2'})
])
async def test_from_json_body_with_versionner(test_adapter, version, expected):
    test_adapter.get_current_request_body = asyncio.coroutine(lambda:'{"field1":"value1", "field2":"value2"}')

    from rest_helpers.versioning import UrlRootVersionner
    class TestVersionner(UrlRootVersionner):
        class v1:
            def body(self, body):
                return '{   "a": 1 }'

        class v2:
            def body_dict(self, body):
                body["a"] = "b"
                return body

        class value3:
            pass

    rh_context = MagicMock()
    test_adapter.get_rest_helper_request_context = lambda :rh_context
    rh_context.versionner = TestVersionner()

    @binding.from_json_body(test_adapter)
    def inner_func(data):
        assert isinstance(data, dict)
        return data

    rh_context.versionner.requested_version = version
    response = await inner_func()
    assert response == expected


#endregion

#region field_from_json_body

@pytest.mark.asyncio
@pytest.mark.field_from_json_body
@pytest.mark.parametrize("field, json_field, data", [
    ("fieldA", "field1", '{"field1":"value1", "field2":"value2"}'),
    ('field1/field2/fieldA', None,'{"field1":{"field2":{"fieldA":"value1"}}, "field2":"value2"}')
])
async def test_field_from_json_body_with_specific_json_field(counter, test_adapter, field, json_field, data):
    test_adapter.get_current_request_body = asyncio.coroutine(lambda:data)

    @binding.field_from_json_body(test_adapter, field=field, json_field=json_field)
    def inner_func(fieldA):
        counter["inner_func"] += 1
        assert fieldA == 'value1'
        return "success"

    response = await inner_func()
    assert counter["inner_func"] == 1
    assert response == "success"

@pytest.mark.asyncio
@pytest.mark.field_from_json_body
@pytest.mark.parametrize("data,expected", [
    ('{"field_a":"b"', "request data is not valid JSON"),
    ('{"field_b":"b_value"}', "The field field_a is not present in the content of the request."),
])
async def test_field_from_json_body_invalid_body(counter, test_adapter, data, expected):
    test_adapter.get_current_request_body = asyncio.coroutine(lambda:data)

    @binding.field_from_json_body(test_adapter, "field_a")
    def inner_func(field_a): #pragma: no cover
        counter["inner_func"] += 1
        return "success"

    excep = None
    try:
        response = await inner_func()
    except Exception as ex:
        excep = ex

    assert counter["inner_func"] == 0
    assert expected in str(excep)

#endregion

#region field_from_query_string
@pytest.mark.asyncio
@pytest.mark.field_from_query_string
async def test_field_from_query_string_with_specific_query_field(counter, test_adapter):
    test_adapter.get_current_request_query_string_args = lambda:{"fieldA":["value1"], "field2":["value2"]}

    @binding.from_query_string(test_adapter, field="field1", query_field="fieldA")
    def inner_func(field1):
        counter["inner_func"] += 1
        assert field1 == 'value1'
        return "success"

    response = await inner_func()
    assert counter["inner_func"] == 1
    assert response == "success"

@pytest.mark.asyncio
@pytest.mark.field_from_query_string
async def test_field_from_query_string_with_list(counter, test_adapter):
    test_adapter.get_current_request_query_string_args = lambda:{"field1":["value1", "value3"], "field2":["value2"]}

    @binding.from_query_string(test_adapter, field="field1", as_list=True)
    def inner_func(field1):
        counter["inner_func"] += 1
        assert field1 == ["value1", "value3"]
        return "success"

    response = await inner_func()
    assert counter["inner_func"] == 1
    assert response == "success"

@pytest.mark.asyncio
@pytest.mark.field_from_query_string
async def test_field_from_query_string_with_missing_field(counter, test_adapter):
    test_adapter.get_current_request_query_string_args = lambda:{"field1":["value1"], "field2":["value2"]}

    @binding.from_query_string(test_adapter, field="fieldX")
    def inner_func(fieldX): #pragma: no cover
        counter["inner_func"] += 1
        return "success"

    excep = None
    try:
        response = await inner_func()
    except Exception as ex:
        excep = ex

    assert counter["inner_func"]==0
    assert "The field fieldX is not present in the query string." in str(excep)

@pytest.mark.asyncio
async def test_from_query_string_with_versionner(test_adapter):
    test_adapter.get_current_request_query_string_args = lambda:{"field1":["value1"], "field2":["value2"]}

    from rest_helpers.versioning import UrlRootVersionner
    class TestVersionner(UrlRootVersionner):
        class v1:
            def query_string_args(self, query_string_args):
                query_string_args["a"]="b"
                return query_string_args

        class v2:
            pass

    rh_context = MagicMock()
    test_adapter.get_rest_helper_request_context = lambda :rh_context
    rh_context.versionner = TestVersionner()

    @binding.from_query_string(test_adapter, field="a")
    def inner_func(a):
        return a

    rh_context.versionner.requested_version = "v1"
    response = await inner_func()
    assert response == "b"

#endregion

#region field_from_header

@pytest.mark.asyncio
@pytest.mark.field_from_header
async def test_field_from_header_with_specific_field(counter, test_adapter):
    test_adapter.get_current_request_headers_dict = lambda:{"fieldA":"value1", "field2":["value2"]}

    @binding.from_header(test_adapter, field="field1", header_field="fieldA")
    def inner_func(field1):
        counter["inner_func"] += 1
        assert field1 == 'value1'
        return "success"

    response = await inner_func()

    assert counter["inner_func"] == 1
    assert response == "success"

@pytest.mark.asyncio
@pytest.mark.field_from_header
async def test_field_from_header_with_missing_field(counter, test_adapter):
    test_adapter.get_current_request_headers_dict = lambda:{"field1":["value1"], "field2":["value2"]}

    @binding.from_header(test_adapter, field="fieldX")
    def inner_func(fieldX): #pragma: no cover
        counter["inner_func"] += 1
        return "success"

    excep = None
    try:
        response = await inner_func()
    except Exception as ex:
        excep = ex

    assert counter["inner_func"]==0
    assert "The field fieldX is not present in the requests headers." in str(excep)

@pytest.mark.asyncio
async def test_from_header_with_versionner(test_adapter):
    test_adapter.get_current_request_headers_dict = lambda:{"field1":["value1"], "field2":["value2"]}

    from rest_helpers.versioning import UrlRootVersionner
    class TestVersionner(UrlRootVersionner):
        class v1:
            def headers(self, headers):
                headers["a"]="b"
                return headers

        class v2:
            pass

    rh_context = MagicMock()
    test_adapter.get_rest_helper_request_context = lambda :rh_context
    rh_context.versionner = TestVersionner()

    @binding.from_header(test_adapter, field="a")
    def inner_func(a):
        return a

    rh_context.versionner.requested_version = "v1"
    response = await inner_func()
    assert response == "b"
#endregion


#region oauth

@pytest.mark.asyncio
@pytest.mark.oauth
@pytest.mark.parametrize("get_unverified_header, get_unverified_claims, allowed_domains, expected_exception, decode_side_effect", [
    ({},{}, ["A.com","B.C.org"], rest_exceptions.UnauthorizedException, Exception()),
    ({"kid":"ab129f_Z"}, {"iss": "http://d.ca/my/endpoint"}, ["A.com","B.C.org"], rest_exceptions.UnauthorizedException, Exception()),
    ({"kid":"ab129f_Z"}, {"iss": "http://A.com/my/endpoint"}, ["A.com","B.C.org"], rest_exceptions.UnauthorizedException, Exception()),
    ({"kid":"abc_1"}, {"iss": "http://A.com/my/endpoint"}, None, rest_exceptions.ForbiddenException, Exception()),
    ({"kid":"abc_1"}, {"iss": "http://A.com/my/endpoint"}, ["A.com","B.C.org"], None, lambda *x,**kw: {"A":1, "B":{"C":2}})
])
async def test_oauth_with_invalid_token(counter, test_adapter, get_unverified_header, get_unverified_claims, allowed_domains, expected_exception, decode_side_effect):
    test_adapter.get_current_request_headers_dict = lambda:{"Authorization":"ABC"}

    @binding.from_Oauth(test_adapter, field="field1", allowed_domains=allowed_domains, validate_options={"a":1, "b":2}, client_id="TheClientId")
    def inner_func(field1):
        counter["inner_func"] += 1
        assert field1 == {"A":1, "B":{"C":2}}
        return "success"

    with patch("jose.jws.get_unverified_header") as m_get_unverified_header:
        m_get_unverified_header.return_value = get_unverified_header
        with patch("jose.jwt.get_unverified_claims") as m_get_unverified_claims:
            with patch("jose.jwt.decode") as m_decode:
                m_decode.side_effect = decode_side_effect
                m_get_unverified_claims.return_value = get_unverified_claims
                httpretty.enable()
                httpretty.register_uri(
                    httpretty.GET,
                    "http://A.com/my/endpoint/.well-known/openid-configuration",
                    body='{"jwks_uri": "http://B.com/a/b/c"}'
                )
                httpretty.register_uri(
                    httpretty.GET,
                    "http://B.com/a/b/c",
                    body='{"keys": [ {"kid":"abc-1"}, {"kid":"abc-2"} ]}'
                )

                excep = None
                response = None
                try:
                    response = await inner_func()
                except Exception as ex:
                    excep = ex
                httpretty.disable()

                if response ==  "success":
                    assert counter["inner_func"] == 1
                else:
                    assert isinstance(excep, expected_exception)
                    assert counter["inner_func"] == 0

@pytest.mark.asyncio
@pytest.mark.oauth
async def test_oauth_cache(counter, test_adapter):
    test_adapter.get_current_request_headers_dict = lambda:{"Authorization":"ABC"}

    decorator = binding.from_Oauth(test_adapter, field="field1", allowed_domains=["A.com","B.C.org"], validate_options={"a":1, "b":2}, client_id="TheClientId")
    decorator._public_keys = {"abc1": "abc"}

    @decorator
    def inner_func(field1):
        counter["inner_func"] += 1
        assert field1 == {"A":1, "B":{"C":2}}
        return "success"

    with patch("jose.jws.get_unverified_header") as m_get_unverified_header:
        m_get_unverified_header.return_value = {"kid":"abc_1"}
        with patch("jose.jwt.decode") as m_decode:
            m_decode.return_value = {"A":1, "B":{"C":2}}

            response = await inner_func()

            assert response ==  "success"
            assert counter["inner_func"] == 1

@pytest.mark.asyncio
@pytest.mark.Oauth
async def test_Oauth_hardcoded_valid_tokens(counter, test_adapter):
    test_adapter.get_current_request_headers_dict = lambda:{"Authorization":"ABC"}

    decorator = binding.from_Oauth(test_adapter, field="field1", valid_tokens={"ABC":{"A":1, "B":{"C":2}}})
    decorator._public_keys = {"abc1": "abc"}

    @decorator
    def inner_func(field1):
        counter["inner_func"] += 1
        assert field1 == {"A":1, "B":{"C":2}}
        return "success"

    response = await inner_func()

    assert response ==  "success"
    assert counter["inner_func"] == 1

#endregion