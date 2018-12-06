import pytest
from rest_helpers import swagger, routes, framework_adapter, binding, versioning
from rest_helpers.tests import test_common


def test_update_none():
    d1 = {"a": 1, "b":2}
    swagger._update(d1, None)

    assert d1 == {"a": 1, "b":2}

def test_update_simple():
    d1 = {"a": 1, "b":2}
    d2 = {"c": 3, "b":5}

    swagger._update(d1, d2)

    assert d1 == {"a": 1, "b":5, "c":3}

def test_update_nested():
    d1 = {"a": 1, "b":{"A":"I","B":"II"}}
    d2 = {"c": 3, "b":{"A":"I","B":"V"}}

    swagger._update(d1, d2)

    assert d1 == {"a": 1, "b":{"A":"I","B":"V"}, "c":3}

def test_update_by_index():
    d1 = {"a": 1, "b":[1,2,3,4,5]}
    d2 = {"c": 3, "b":{1:"A"}}

    swagger._update(d1, d2)

    assert d1 == {"a": 1, "b":[1,"A",3,4,5], "c":3}

def test_update_list():
    d1 = {"a": 1, "b":[1,2,3]}
    d2 = {"c": 3, "b":[3,4,5]}

    swagger._update(d1,d2)

    assert d1 == {"a": 1, "b":[3,4,5], "c":3}

def test_update_list_append():
    d1 = {"a": 1, "b":[1,2,3]}
    d2 = {"c": 3, "b>+":[5]}

    swagger._update(d1,d2)

    assert d1 == {"a": 1, "b":[1,2,3,5], "c":3}

def test_update_list_delete_by_elem():
    d1 = {"a": 1, "b":[1,2,3]}
    d2 = {"c": 3, "b>-":[3]}

    swagger._update(d1,d2)

    assert d1 == {"a": 1, "b":[1,2], "c":3}

def test_update_list_delete_by_index():
    d1 = {"a": 1, "b":[1,2,3]}
    d2 = {"c": 3, "b>-":["[1]"]}

    swagger._update(d1,d2)

    assert d1 == {"a": 1, "b":[1,3], "c":3}

@pytest.mark.parametrize("type, expected",
[
    (int, "integer"),
    (str, "string"),
    (bool, "boolean")
])
def test_get_parameter_type(type, expected):
    assert swagger._get_parameter_type(type) == expected

def test_get_parameters_simple_route():
    route = routes.route(framework_adapter.BaseFrameworkAdapter(), "/test_<param1>/hello_<param2>", options=None, doc=True, versionner=None, exception_handler=None)
    parameters = swagger._get_parameters(route)

    assert parameters == [
        {
            'description': '',
            'in': 'path',
            'name': 'param1',
            'required': True,
            'type': 'string'
        },
        {
            'description': '',
            'in': 'path',
            'name': 'param2',
            'required': True,
            'type': 'string'
        }
    ]

def test_get_parameters_resource_route():
    original_binding_input_decorators = binding._input_decorators
    fw_adapter = framework_adapter.BaseFrameworkAdapter()
    try:
        route = routes.get_resource_route(fw_adapter, test_common.TestClass, options=None, doc=True, versionner=versioning.UrlRootVersionner, exception_handler=None)
        route.rule = "<rest_helper_version>/" + route.rule
        binding_list = [
                binding.from_json_body(fw_adapter, field="data", validator=None, deserializer=None),
                binding.field_from_json_body(fw_adapter, field="json_field", json_field="a/b/c", validator=None, deserializer=None),
                binding.from_header(fw_adapter, field="header_field", header_field="in_header", validator=None, deserializer=None),
                binding.from_query_string(fw_adapter, field="query_field", query_field="in_query", validator=None, deserializer=None, as_list=False),
            ]
        for i,b in enumerate(binding_list):
            b.has_default = i % 2 == 0
            b.default = "X"+str(i) if i % 2 == 0 else None

        binding._input_decorators = {
            route.id: binding_list
        }
        parameters = swagger._get_parameters(route)

        assert parameters == [
                {
                    'description': 'Version of the api to use.',
                    'enum': [],
                    'in': 'path',
                    'name': 'rest_helper_version',
                    'required': True,
                    'type': 'string'
                },
                {
                    'description': 'Name of the /tests to get.',
                    'in': 'path',
                    'name': 'test_name',
                    'required': True,
                    'type': 'string'
                },
                {
                    'in': 'query',
                    'name': 'in_query',
                    'required': True,
                    'type': 'string'
                },
                {
                    'description': None,
                    'in': 'header',
                    'name': 'in_header',
                    'required': False,
                    'type': 'string'
                },
                {
                    'in': 'body',
                    'name': 'body',
                    'required': True
                }
            ]
    finally:
        binding._input_decorators = original_binding_input_decorators
