from mock import patch, Mock, MagicMock

from rest_helpers.jsonapi_objects import Resource
from rest_helpers.framework_adapter import BaseFrameworkAdapter


class TestRequestContext(object):#pragma: no cover
    def __init__(self, app, **options):
        self.app = app
        self.options = options
        self.test_ctx = None

    def __enter__(self):
        self.test_ctx = self.app.test_request_context(**self.options)
        self.test_ctx.push()

    def __exit__(self, type, value, traceback):
        self.test_ctx.pop()

class TestClass(Resource):#pragma: no cover
    resource_type = "/tests"
    def __init__(self, id = 1):
        super(TestClass, self).__init__("test_name", "test_type")
        self.id=id
        self.list = ["1",2,"3"]
        self.dic = {
            "entry_1": "value 1",
            "list": [{"x":1,"b":"2"},{"x":2,"b":"3"},{"x":3,"b":"4"}]
        }

class SubTestClass(Resource): #pragma: no cover
    resource_type = "/tests/subtests"
    def __init__(self, id = 1):
        super(SubTestClass, self).__init__("sub_test_name" )
        self.id=id
        self.list = ["1",2,"3"]
        self.dic = {
            "entry_1": "value 1",
            "list": [{"x":1,"b":"2"},{"x":2,"b":"3"},{"x":3,"b":"4"}]
        }