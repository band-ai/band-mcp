"""Pytest configuration for integration tests.

The live-API smoke/error/full-workflow tests that lived here (pre-INT-352)
imported the handwritten handler modules that were deleted in Phase 4.
Their behavior is now covered by `tests/integration/test_forwarding.py`
(in-process registrar dispatch) and `tests/runtime/test_human_tools.py` in
`thenvoi-sdk-python` (SDK-level tool tests).
"""
