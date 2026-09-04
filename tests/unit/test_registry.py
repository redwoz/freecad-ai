"""Tests for tool registry, schema generation, and execution."""

import pytest

from unittest.mock import patch

from freecad_ai.tools.registry import (
    ToolDefinition,
    ToolParam,
    ToolRegistry,
    ToolResult,
    _params_to_json_schema,
    _schema_params,
)


def _make_tool(name="test_tool", params=None, handler=None):
    """Helper to create a ToolDefinition for testing."""
    if handler is None:
        handler = lambda **kw: ToolResult(success=True, output="ok", data=kw)
    if params is None:
        params = [ToolParam("x", "number", "A number")]
    return ToolDefinition(
        name=name,
        description=f"Test tool: {name}",
        parameters=params,
        handler=handler,
    )


class TestToolParam:
    def test_required_by_default(self):
        p = ToolParam("name", "string", "A name")
        assert p.required is True

    def test_optional_param(self):
        p = ToolParam("opt", "string", "Optional", required=False, default="hi")
        assert p.required is False
        assert p.default == "hi"

    def test_enum_param(self):
        p = ToolParam("color", "string", "Color", enum=["red", "blue"])
        assert p.enum == ["red", "blue"]

    def test_array_param_with_items(self):
        p = ToolParam("names", "array", "Names", items={"type": "string"})
        assert p.items == {"type": "string"}


class TestToolResult:
    def test_success_result(self):
        r = ToolResult(success=True, output="Created box")
        assert r.success is True
        assert r.data == {}
        assert r.error == ""

    def test_error_result(self):
        r = ToolResult(success=False, output="", error="Not found")
        assert r.success is False
        assert r.error == "Not found"


class TestToolRegistry:
    def test_register_and_get(self):
        reg = ToolRegistry()
        tool = _make_tool("my_tool")
        reg.register(tool)
        assert reg.get("my_tool") is tool

    def test_get_missing_returns_none(self):
        reg = ToolRegistry()
        assert reg.get("nonexistent") is None

    def test_list_tools(self):
        reg = ToolRegistry()
        reg.register(_make_tool("a"))
        reg.register(_make_tool("b"))
        names = [t.name for t in reg.list_tools()]
        assert "a" in names
        assert "b" in names

    def test_register_overwrites_same_name(self):
        reg = ToolRegistry()
        t1 = _make_tool("x")
        t2 = _make_tool("x")
        reg.register(t1)
        reg.register(t2)
        assert reg.get("x") is t2
        assert len(reg.list_tools()) == 1


class TestToolExecution:
    def test_execute_success(self):
        reg = ToolRegistry()
        reg.register(_make_tool("add", params=[
            ToolParam("a", "number", "A"),
            ToolParam("b", "number", "B"),
        ], handler=lambda a, b: ToolResult(
            success=True, output=str(a + b), data={"sum": a + b}
        )))
        result = reg.execute("add", {"a": 3, "b": 4})
        assert result.success is True
        assert result.data["sum"] == 7

    def test_execute_unknown_tool(self):
        reg = ToolRegistry()
        result = reg.execute("nonexistent", {})
        assert result.success is False
        assert "Unknown tool" in result.error

    def test_execute_wrong_params(self):
        reg = ToolRegistry()
        reg.register(_make_tool("strict", params=[
            ToolParam("required_arg", "string", "Required"),
        ], handler=lambda required_arg: ToolResult(
            success=True, output=required_arg
        )))
        result = reg.execute("strict", {"wrong_arg": "value"})
        assert result.success is False
        assert "Invalid parameters" in result.error

    def test_execute_handler_exception(self):
        def bad_handler(**kw):
            raise ValueError("Something broke")
        reg = ToolRegistry()
        reg.register(_make_tool("bad", handler=bad_handler))
        result = reg.execute("bad", {"x": 1})
        assert result.success is False
        assert "failed" in result.error
        assert "Something broke" in result.error


class TestParamsToJsonSchema:
    def test_empty_params(self):
        schema = _params_to_json_schema([])
        assert schema == {"type": "object", "properties": {}}
        assert "required" not in schema

    def test_required_param(self):
        schema = _params_to_json_schema([
            ToolParam("name", "string", "The name"),
        ])
        assert "name" in schema["properties"]
        assert schema["required"] == ["name"]
        assert schema["properties"]["name"]["type"] == "string"

    def test_optional_param_not_in_required(self):
        schema = _params_to_json_schema([
            ToolParam("x", "number", "X", required=False, default=0.0),
        ])
        assert "required" not in schema
        assert schema["properties"]["x"]["default"] == 0.0

    def test_enum_in_schema(self):
        schema = _params_to_json_schema([
            ToolParam("op", "string", "Operation", enum=["add", "sub"]),
        ])
        assert schema["properties"]["op"]["enum"] == ["add", "sub"]

    def test_array_items_in_schema(self):
        schema = _params_to_json_schema([
            ToolParam("names", "array", "Names", items={"type": "string"}),
        ])
        assert schema["properties"]["names"]["items"] == {"type": "string"}

    def test_mixed_required_optional(self):
        schema = _params_to_json_schema([
            ToolParam("req", "string", "Required"),
            ToolParam("opt", "number", "Optional", required=False),
        ])
        assert schema["required"] == ["req"]
        assert "req" in schema["properties"]
        assert "opt" in schema["properties"]


class TestOpenAISchema:
    def test_schema_structure(self):
        reg = ToolRegistry()
        reg.register(_make_tool("test", params=[
            ToolParam("msg", "string", "Message"),
        ]))
        schema = reg.to_openai_schema()
        assert len(schema) == 1
        assert schema[0]["type"] == "function"
        assert schema[0]["function"]["name"] == "test"
        assert "parameters" in schema[0]["function"]

    def test_empty_registry(self):
        reg = ToolRegistry()
        assert reg.to_openai_schema() == []


class TestAnthropicSchema:
    def test_schema_structure(self):
        reg = ToolRegistry()
        reg.register(_make_tool("test", params=[
            ToolParam("msg", "string", "Message"),
        ]))
        schema = reg.to_anthropic_schema()
        assert len(schema) == 1
        assert schema[0]["name"] == "test"
        assert "input_schema" in schema[0]

    def test_empty_registry(self):
        reg = ToolRegistry()
        assert reg.to_anthropic_schema() == []


class TestMCPSchema:
    def test_schema_structure(self):
        reg = ToolRegistry()
        reg.register(_make_tool("test", params=[
            ToolParam("msg", "string", "Message"),
        ]))
        schema = reg.to_mcp_schema()
        assert len(schema) == 1
        assert schema[0]["name"] == "test"
        assert "inputSchema" in schema[0]

    def test_empty_registry(self):
        reg = ToolRegistry()
        assert reg.to_mcp_schema() == []


class TestBuiltinToolSchemas:
    """Validate that every shipped tool emits a strict-OpenAI-compliant schema.

    Issue #10: GitHub Models rejected create_assembly because part_names was
    declared as 'array' without 'items'. Anthropic and Ollama silently accept
    this; OpenAI's marketplace API enforces the spec. Walk every built-in tool
    so future regressions surface immediately, not from a user bug report.
    """

    def test_every_array_property_has_items(self):
        from freecad_ai.tools.freecad_tools import ALL_TOOLS

        offenders = []
        for tool in ALL_TOOLS:
            schema = _params_to_json_schema(tool.parameters)
            for prop_name, prop in schema.get("properties", {}).items():
                if prop.get("type") == "array" and "items" not in prop:
                    offenders.append(f"{tool.name}.{prop_name}")
        assert not offenders, (
            "Array-typed properties without 'items' (rejected by strict "
            f"providers like GitHub Models): {offenders}"
        )


def _modeling_tool(name="mutate", handler=None, own_document_param=False):
    params = [ToolParam("x", "number", "A number")]
    if own_document_param:
        params.append(ToolParam("document_name", "string", "own param"))
    return ToolDefinition(
        name=name,
        description="Mutates something",
        parameters=params,
        handler=handler or (lambda **kw: ToolResult(success=True, output="ok", data=kw)),
        category="modeling",
    )


class TestDocumentNameInterception:
    """Mutating (category="modeling") tools accept an optional
    document_name that resolves/switches the active document before the
    handler runs, replacing the switch_document-then-mutate two-call dance.
    """

    def test_document_name_resolved_before_handler(self):
        reg = ToolRegistry()
        reg.register(_modeling_tool())
        with patch(
            "freecad_ai.core.active_document.resolve_document_by_name",
            return_value=None,
        ) as mock_resolve:
            result = reg.execute("mutate", {"x": 1, "document_name": "Other"})
        mock_resolve.assert_called_once_with("Other")
        assert result.success is True
        assert "document_name" not in result.data  # stripped before the handler call

    def test_document_name_error_short_circuits_handler(self):
        called = []

        def handler(**kw):
            called.append(kw)
            return ToolResult(success=True, output="ok")

        reg = ToolRegistry()
        reg.register(_modeling_tool(handler=handler))
        with patch(
            "freecad_ai.core.active_document.resolve_document_by_name",
            return_value="Document 'Other' not found. Available: Doc1",
        ):
            result = reg.execute("mutate", {"x": 1, "document_name": "Other"})
        assert result.success is False
        assert "not found" in result.error
        assert called == []  # handler never ran

    def test_no_document_name_skips_resolution(self):
        reg = ToolRegistry()
        reg.register(_modeling_tool())
        with patch(
            "freecad_ai.core.active_document.resolve_document_by_name",
        ) as mock_resolve:
            result = reg.execute("mutate", {"x": 1})
        mock_resolve.assert_not_called()
        assert result.success is True

    def test_own_document_param_not_intercepted(self):
        # A tool that already declares document_name (switch_document) keeps
        # its own semantics — the registry must not pop or resolve for it.
        captured = {}

        def handler(**kw):
            captured.update(kw)
            return ToolResult(success=True, output="ok")

        reg = ToolRegistry()
        reg.register(_modeling_tool(handler=handler, own_document_param=True))
        with patch(
            "freecad_ai.core.active_document.resolve_document_by_name",
        ) as mock_resolve:
            reg.execute("mutate", {"x": 1, "document_name": "Explicit"})
        mock_resolve.assert_not_called()
        assert captured["document_name"] == "Explicit"

    def test_non_modeling_tool_unaffected(self):
        reg = ToolRegistry()
        reg.register(_make_tool("query_tool"))  # category="general"
        with patch(
            "freecad_ai.core.active_document.resolve_document_by_name",
        ) as mock_resolve:
            result = reg.execute("query_tool", {"x": 1, "document_name": "Whatever"})
        mock_resolve.assert_not_called()
        assert result.success is True
        assert result.data["document_name"] == "Whatever"


class TestSchemaParamsInjection:
    """The document_name capability must be advertised in the
    emitted schema for mutating tools, without duplicating it for a tool
    that already declares its own (switch_document)."""

    def test_modeling_tool_gets_document_name_param(self):
        tool = _modeling_tool()
        names = [p.name for p in _schema_params(tool)]
        assert names == ["x", "document_name"]

    def test_non_modeling_tool_unaffected(self):
        tool = _make_tool("query_tool")  # category="general"
        names = [p.name for p in _schema_params(tool)]
        assert names == ["x"]

    def test_own_document_name_param_not_duplicated(self):
        tool = _modeling_tool(own_document_param=True)
        names = [p.name for p in _schema_params(tool)]
        assert names.count("document_name") == 1

    def test_injected_param_is_optional_in_schema(self):
        tool = ToolDefinition(
            name="mutate", description="d", parameters=[],
            handler=lambda **kw: None, category="modeling",
        )
        schema = _params_to_json_schema(_schema_params(tool))
        assert "document_name" not in schema.get("required", [])
