### TypeScript / JavaScript
- Types: `any`, unchecked `as` casts, non-null assertions (`!`) hiding real nulls, untyped exports, external data (API responses, `JSON.parse`) trusted without validation.
- Async: floating promises (neither awaited nor handled), `forEach` with async callbacks, `fetch` without checking `response.ok`, no timeout or `AbortController`, races between overlapping requests.
- Leaks: `setInterval`/`setTimeout`, event listeners, subscriptions, WebSockets and observers never cleaned up; unbounded caches or maps.
- Security: `innerHTML`, `eval` or `new Function` with untrusted data; secrets in client-side code or in env vars bundled into the browser; missing input validation on servers; prototype pollution through object merging.
- Correctness: `==` vs `===`, floating-point money math, mutating shared objects or arrays, `Date` timezone mistakes, off-by-one errors in pagination.
