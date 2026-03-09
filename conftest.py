"""Pytest compatibility shims for this repo's async/script-style tests."""

import asyncio
import inspect
import httpx


def pytest_configure(config):
    """Register custom markers used across the test suite."""
    config.addinivalue_line("markers", "asyncio: mark a test as async")


# Starlette TestClient in this repo expects older httpx.Client(app=...) signature.
# Patch for newer httpx versions that removed the `app` kwarg.
_original_httpx_client_init = httpx.Client.__init__
if "app" not in inspect.signature(httpx.Client.__init__).parameters:
    def _patched_httpx_client_init(self, *args, app=None, **kwargs):
        return _original_httpx_client_init(self, *args, **kwargs)

    httpx.Client.__init__ = _patched_httpx_client_init


def pytest_pyfunc_call(pyfuncitem):
    """Run async test functions without requiring external pytest async plugins."""
    test_func = pyfuncitem.obj
    if inspect.iscoroutinefunction(test_func):
        kwargs = {
            name: pyfuncitem.funcargs[name]
            for name in pyfuncitem._fixtureinfo.argnames
        }
        asyncio.run(test_func(**kwargs))
        return True

    return None
