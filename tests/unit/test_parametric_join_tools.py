"""Unit tests for newly added tools: create_clone, create_subshape_binder, part_join_operation, sweep_sketch, and bspline sketch support."""

import pytest
from freecad_ai.tools.freecad_tools import (
    ALL_TOOLS,
    PART_JOIN_OPERATION,
    SWEEP_SKETCH,
    CREATE_SKETCH,
    EDIT_SKETCH,
)


class TestNewToolsDefinitions:
    def test_sweep_sketch_enhanced_params(self):
        params = {p.name: p for p in SWEEP_SKETCH.parameters}
        assert "transition" in params
        assert set(params["transition"].enum) == {"Transformed", "RightCorner", "RoundCorner"}
        assert "frenet" in params
        assert params["frenet"].type == "boolean"

    def test_part_join_operation_params(self):
        assert PART_JOIN_OPERATION.name == "part_join_operation"
        assert PART_JOIN_OPERATION.category == "modeling"
        params = {p.name: p for p in PART_JOIN_OPERATION.parameters}
        assert "operation" in params
        assert set(params["operation"].enum) == {"connect", "slice", "embed"}
        assert "base_object" in params
        assert "tool_objects" in params
        assert params["tool_objects"].type == "array"
        assert params["tool_objects"].items == {"type": "string"}
