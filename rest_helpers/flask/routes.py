import sys
from rest_helpers import routes, flask, framework_adapter
# Hack needed until we move to python3.7
sys.modules[__name__] = framework_adapter.Proxy(routes, flask.flask_adapter_builder)

