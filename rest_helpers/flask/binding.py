import sys
from rest_helpers import binding, flask, framework_adapter

sys.modules[__name__] = framework_adapter.Proxy(binding, flask.flask_adapter_builder)
