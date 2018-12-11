import inspect

async def await_if_needed(result):
    return await result if inspect.iscoroutine(result) else result