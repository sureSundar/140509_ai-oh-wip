import time
from functools import wraps


def timed_ms(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = fn(*args, **kwargs)
        end = time.perf_counter()
        return result, int((end - start) * 1000)

    return wrapper

