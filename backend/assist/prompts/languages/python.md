### Python
- Resources: files, sockets, database connections and cursors, locks and HTTP sessions opened without `with`/`async with` or a guaranteed close.
- Mutable default arguments; mutable class attributes shared across instances.
- Exceptions: bare `except:` or `except Exception` that swallows errors, `raise` inside `except` without `from`, try blocks so broad they hide bugs.
- Async: blocking calls inside `async def` (`time.sleep`, `requests`, sync DB drivers, heavy CPU work), coroutines never awaited, fire-and-forget tasks without a reference, missing timeouts on network calls.
- Memory: unbounded module-level caches, lists or dicts; `functools.lru_cache` on methods (keeps `self` alive).
- Security: SQL or shell commands built with f-strings, `%` or `+`; `subprocess(..., shell=True)` with input; `pickle`/`yaml.load` on untrusted data; `eval`/`exec`; `verify=False`; path traversal from user-supplied paths; `random` used for tokens.
- Correctness: late-binding closures in loops, float instead of `Decimal` for money, naive vs aware `datetime`, `is` vs `==`, mutating a collection while iterating it.
- Style that matters: type hints on public functions, no deprecated APIs for the project's Python version.
- Tests: pytest with fixtures and `parametrize`; no real network or database in unit tests.
