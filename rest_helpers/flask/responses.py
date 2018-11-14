import sys

from rest_helpers import responses, flask, framework_adapter

# Hack needed until we move to python3.7
sys.modules[__name__] = framework_adapter.Proxy(responses, flask.flask_adapter_builder)

