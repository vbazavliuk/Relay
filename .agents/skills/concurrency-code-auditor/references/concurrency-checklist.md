# Concurrency, Race Condition & Edge-Case Checklist

---

## 🧵 1. Threading & Asynchronous Concurrency (`asyncio` / `threading`)
- [ ] **Shared State Mutation**: Are shared dicts, lists, or state objects accessed without mutex locks (`asyncio.Lock()`, `threading.Lock()`)?
- [ ] **Task Cancellation & Cleanup**: Do background tasks catch `asyncio.CancelledError` and cleanly release locks, sockets, and DB connections?
- [ ] **Deadlock Detection**: Are locks acquired in inconsistent ordering across different coroutines?
- [ ] **Event Loop Blocking**: Are blocking CPU-heavy calls (e.g. disk I/O, heavy crypto, synchronous HTTP) executed directly on the event loop instead of `run_in_executor`?
- [ ] **Race Condition in Order Placement**: Is there a possibility of double-submission of orders when market events arrive simultaneously?

---

## ⚠️ 2. Mathematical & Numeric Edge Cases
- [ ] **Zero Division**: Every division (`a / b`) must guard against `b == 0` or `abs(b) < 1e-9`.
- [ ] **`None` / `null` Propagation**: Are optional return types checked before attribute access (`item.value` when `item` can be `None`)?
- [ ] **NaN / Inf in Numerical Code**: Are arrays or pandas series scanned with `np.isnan()`, `np.isinf()` prior to ML inference or order sizing?
- [ ] **Floating Point Rounding**: Financial balances, prices, and quantities must avoid IEEE-754 drift. Use `Decimal` or rounded integer cents/satoshis where exactness is required.

---

## 📦 3. Release Certification & Git Tagging
- [ ] Run full test suite: `pytest -v`.
- [ ] Verify clean git state: `git status`.
- [ ] Tag release commit: `git tag -a v<VERSION>-production-certified -m "Release <VERSION>: Passed zero-tolerance audit"`.
- [ ] Push tags: `git push origin v<VERSION>-production-certified`.
