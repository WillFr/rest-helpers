import pytest
import asyncio
from collections import defaultdict

@pytest.fixture
def counter(request):
    return defaultdict(int)

@pytest.fixture
def loop(event_loop):
     """Ensure usable event loop for everyone.

     If you comment this fixture out, default pytest-aiohttp one is used
     and things start failing (when redis pool is in place).
     """
     return event_loop

@pytest.fixture
def make_coro():
    def inner(obj):
        mock_return_value = asyncio.Future()
        mock_return_value.set_result(obj)
        return mock_return_value

    return inner