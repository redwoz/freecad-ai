"""Unit tests for newly added tools: create_clone, create_subshape_binder, part_join_operation, sweep_sketch, and bspline sketch support."""

import pytest
from freecad_ai.tools.freecad_tools import (
    ALL_TOOLS,
    CREATE_CLONE,
    CREATE_SUBSHAPE_BINDER,
    PART_JOIN_OPERATION,
    SWEEP_SKETCH,
    CREATE_SKETCH,
    EDIT_SKETCH,
)


class TestNewToolsDefinitions:
    def test_registered_in_all_tools(self):
        assert CREATE_CLONE in ALL_TOOLS
        assert CREATE_SUBSHAPE_BINDER in ALL_TOOLS
        assert PART_JOIN_OPERATION in ALL_TOOLS
        assert SWEEP_SKETCH in ALL_TOOLS
        assert CREATE_SKETCH in ALL_TOOLS
        assert EDIT_SKETCH in ALL_TOOLS

    def test_create_clone_params(self):
        assert CREATE_CLONE.name == "create_clone"
        assert CREATE_CLONE.category == "modeling"
        params = {p.name: p for p in CREATE_CLONE.parameters}
        assert "source_object" in params
        assert "body_name" in params
        assert "translate_x" in params
        assert "translate_y" in params
        assert "translate_z" in params
        assert "rotate_axis_z" in params
        assert "rotate_angle" in params

    def test_create_subshape_binder_params(self):
        assert CREATE_SUBSHAPE_BINDER.name == "create_subshape_binder"
        assert CREATE_SUBSHAPE_BINDER.category == "modeling"
        params = {p.name: p for p in CREATE_SUBSHAPE_BINDER.parameters}
        assert "support_object" in params
        assert "body_name" in params
        assert "sub_elements" in params
        assert params["sub_elements"].type == "array"
        assert params["sub_elements"].items == {"type": "string"}

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

    def test_sweep_sketch_enhanced_params(self):
        params = {p.name: p for p in SWEEP_SKETCH.parameters}
        assert "transition" in params
        assert set(params["transition"].enum) == {"Transformed", "RightCorner", "RoundCorner"}
        assert "frenet" in params
        assert params["frenet"].type == "boolean"

    def test_array_params_have_items(self):
        for tool in [CREATE_CLONE, CREATE_SUBSHAPE_BINDER, PART_JOIN_OPERATION, SWEEP_SKETCH, CREATE_SKETCH, EDIT_SKETCH]:
            for p in tool.parameters:
                if p.type == "array":
                    assert p.items is not None, f"Tool {tool.name} param {p.name} missing items dict"

    def test_create_body_and_sketch_aliases(self):
        from freecad_ai.tools.freecad_tools import CREATE_BODY
        body_params = {p.name: p for p in CREATE_BODY.parameters}
        assert "name" in body_params
        assert "label" in body_params

        sketch_params = {p.name: p for p in CREATE_SKETCH.parameters}
        assert "geometry" in sketch_params
        assert "geometries" in sketch_params
        assert "name" in sketch_params
        assert "label" in sketch_params
        assert sketch_params["geometry"].type == "array"
        assert sketch_params["geometry"].items == {"type": "object"}
