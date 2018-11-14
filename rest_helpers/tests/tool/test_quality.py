import pytest
import httpretty

from flask import Flask
from collections import defaultdict
from rest_helpers.tool import quality
from rest_helpers.flask import FlaskFrameworkAdapter, binding

@pytest.fixture
def app(request):
    app = Flask(__name__)
    ctx = app.test_request_context()
    ctx.push()

    request.addfinalizer(lambda : ctx.pop())

    return app

@pytest.fixture
def counter(request):
    return defaultdict(int)

@httpretty.activate
@pytest.mark.parametrize("trusted_return, untrusted_return, verifier", [
    ((200, "success"), "success", lambda response: response.status_code == 200 and response.data.decode() == "success"),
    ((202, "successful"), "success", lambda response: response.status_code == 202 and response.data.decode() == "successful"),
    ((200, "success"), lambda: (_ for _ in ()).throw(Exception('foobar')), lambda response: response.status_code == 200 and response.data.decode() == "success")
])
def test_shadow_traffic_valid_request(app, counter, trusted_return, untrusted_return, verifier):
    def shadow_server_action(request, uri, headers):
        counter["shadow"] += 1
        assert request.body == b'{"field1":"value1", "field2":"value2"}'
        return (trusted_return[0], headers, trusted_return[1])
    httpretty.register_uri(httpretty.POST, "http://shadow.com/test?", body=shadow_server_action)

    @app.route("/test", methods=['POST'])
    @quality.shadow_traffic(FlaskFrameworkAdapter(), "http://shadow.com", 1)
    @binding.from_json_body()
    def inner_func(data):
        counter["inner_func"] += 1
        assert data == { 'field1':'value1', 'field2':'value2'}
        untrusted_return_value = untrusted_return() if callable(untrusted_return) else untrusted_return
        return untrusted_return_value

    response = app.test_client().post("/test", data='{"field1":"value1", "field2":"value2"}')
    assert counter["inner_func"] == 1
    assert counter["shadow"] == 1
    assert verifier(response) is True
