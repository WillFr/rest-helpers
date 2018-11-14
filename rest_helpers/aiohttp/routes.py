import sys
from rest_helpers import routes, aiohttp, framework_adapter
# Hack needed until we move to python3.7
sys.modules[__name__] = framework_adapter.Proxy(routes, aiohttp.aiohttp_adapter_builder)


