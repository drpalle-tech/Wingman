### React
- Effects: `useEffect` without cleanup for listeners, timers, subscriptions, sockets and in-flight requests (`AbortController`); missing dependencies (stale closures) or dependencies that change every render and cause loops.
- State: derived values stored in state, updates based on stale values (use functional updates), direct state mutation, state set after unmount.
- Rendering: `key={index}` in lists that reorder, insert or delete; expensive work in render; new object or function props defeating memoized children; components defined inside components.
- Data fetching: stale responses overwriting newer ones when props change, missing loading or error states.
- Security: `dangerouslySetInnerHTML` with unsanitized input, user-controlled URLs in `href` (`javascript:`), auth tokens in `localStorage`.
- Accessibility: clickable `div`s without role and keyboard support, inputs without labels, images without `alt`.
- Structure: huge components mixing data, logic and presentation; hooks called conditionally; prop drilling where composition or context fits.
