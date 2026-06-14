"""Tools package for band-mcp.

The handwritten per-tool handlers that lived under ``tools/agent/`` and
``tools/human/`` were deleted in Phase 4 (INT-352) after the SDK-driven
registrar (Phase 3, INT-351) subsumed them. Tool definitions now live in
``band-sdk-python`` and are consumed via ``iter_tool_definitions()``.
"""

from band_mcp.tools.registrar import register_tools

__all__ = ["register_tools"]
