import sys
from rest_helpers import binding, aiohttp, framework_adapter

sys.modules[__name__] = framework_adapter.Proxy(binding, aiohttp.aiohttp_adapter_builder)
