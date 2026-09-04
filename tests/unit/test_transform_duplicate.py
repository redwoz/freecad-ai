"""Unit tests for transform_object relative mode + duplicate_object definitions."""

from freecad_ai.tools.freecad_tools import TRANSFORM_OBJECT


class TestTransformObjectDefinition:
    def test_relative_param_default_true(self):
        params = {p.name: p for p in TRANSFORM_OBJECT.parameters}
        assert "relative" in params
        assert params["relative"].type == "boolean"
        assert params["relative"].default is True

    def test_no_copy_param(self):
        names = {p.name for p in TRANSFORM_OBJECT.parameters}
        assert "copy" not in names


from freecad_ai.tools.freecad_tools import (
    DUPLICATE_OBJECT, ALL_TOOLS, _duplicate_label,
)


class TestDuplicateObjectDefinition:
    def test_name_and_category(self):
        assert DUPLICATE_OBJECT.name == "duplicate_object"
        assert DUPLICATE_OBJECT.category == "modeling"

    def test_registered_in_all_tools(self):
        assert DUPLICATE_OBJECT in ALL_TOOLS

    def test_array_params_declare_items(self):
        # Consistency guard (issue #10) even though these params are scalar/string.
        for p in DUPLICATE_OBJECT.parameters:
            if getattr(p, "type", None) == "array":
                assert getattr(p, "items", None) is not None, p.name


class TestDuplicateLabel:
    def test_default_label(self):
        assert _duplicate_label("Box", "") == "Box_Copy"

    def test_explicit_label_wins(self):
        assert _duplicate_label("Box", "MyCopy") == "MyCopy"


from freecad_ai.tools.freecad_tools import (
    _rebind_expression_refs, _dedupe_shared_dependencies,
)


class _FakeObj:
    """Minimal stand-in for a FreeCAD DocumentObject: Name/Label/TypeId plus
    an ExpressionEngine list and a setExpression() that records calls."""

    def __init__(self, name, label, type_id, expression_engine=None):
        self.Name = name
        self.Label = label
        self.TypeId = type_id
        self.ExpressionEngine = list(expression_engine or [])
        self.set_calls = []

    def setExpression(self, path, expr):
        self.set_calls.append((path, expr))
        self.ExpressionEngine = [
            (p, expr) if p == path else (p, e) for p, e in self.ExpressionEngine
        ]


class _FakeDupDoc:
    def __init__(self):
        self.removed = []

    def removeObject(self, name):
        self.removed.append(name)


class TestRebindExpressionRefs:
    """TI-024 support: repointing a copied object's expressions off a
    duplicated shared VarSet, back onto the pre-existing original."""

    def test_rebinds_bare_name_reference(self):
        obj = _FakeObj("Pad", "Pad", "PartDesign::Pad",
                        expression_engine=[(".Length", "VarSet001.Height")])
        _rebind_expression_refs(obj, "VarSet001", "VarSet", "VarSet", "VarSet")
        assert obj.set_calls == [(".Length", "VarSet.Height")]

    def test_rebinds_label_bracket_reference(self):
        obj = _FakeObj("Pad", "Pad", "PartDesign::Pad",
                        expression_engine=[(".Length", "<<VarSetCopy>>.Height")])
        _rebind_expression_refs(obj, "VarSet001", "VarSet", "VarSetCopy", "VarSet")
        assert obj.set_calls == [(".Length", "<<VarSet>>.Height")]

    def test_no_reference_no_call(self):
        obj = _FakeObj("Pad", "Pad", "PartDesign::Pad",
                        expression_engine=[(".Length", "OtherVar.Height")])
        _rebind_expression_refs(obj, "VarSet001", "VarSet", "VarSet", "VarSet")
        assert obj.set_calls == []

    def test_no_expression_engine_is_noop(self):
        obj = _FakeObj("Pad", "Pad", "PartDesign::Pad")
        _rebind_expression_refs(obj, "VarSet001", "VarSet", "VarSet", "VarSet")
        assert obj.set_calls == []

    def test_word_boundary_avoids_partial_name_match(self):
        obj = _FakeObj("Pad", "Pad", "PartDesign::Pad",
                        expression_engine=[(".Length", "VarSet0011.Height")])
        _rebind_expression_refs(obj, "VarSet001", "VarSet", "VarSet", "VarSet")
        assert obj.set_calls == []  # VarSet0011 != VarSet001, must not match


class TestDedupeSharedDependencies:
    """TI-024: doc.copyObject(obj, True) recursively copies expression
    dependencies, silently duplicating a shared App::VarSet the source
    references. The duplicate must be removed and every rebound copy
    re-pointed at the pre-existing original."""

    def test_removes_duplicate_varset_and_rebinds_dependents(self):
        orig_varset = _FakeObj("VarSet", "VarSet", "App::VarSet")
        dup_varset = _FakeObj("VarSet001", "VarSet", "App::VarSet")
        copy_body = _FakeObj("Body001", "Body_Copy", "PartDesign::Body",
                              expression_engine=[(".Length", "VarSet001.Height")])
        doc = _FakeDupDoc()
        pre_by_key = {("App::VarSet", "VarSet"): orig_varset}

        reused = _dedupe_shared_dependencies(doc, [copy_body, dup_varset], copy_body, pre_by_key)

        assert reused == ["VarSet"]
        assert doc.removed == ["VarSet001"]
        assert copy_body.set_calls == [(".Length", "VarSet.Height")]

    def test_does_not_remove_the_object_being_duplicated(self):
        # Duplicating a VarSet directly must keep the requested copy.
        varset_copy = _FakeObj("VarSet001", "VarSet", "App::VarSet")
        doc = _FakeDupDoc()
        reused = _dedupe_shared_dependencies(doc, [varset_copy], varset_copy, {})
        assert reused == []
        assert doc.removed == []

    def test_noop_without_shared_singleton_types(self):
        body = _FakeObj("Body001", "Body_Copy", "PartDesign::Body")
        doc = _FakeDupDoc()
        reused = _dedupe_shared_dependencies(doc, [body], body, {})
        assert reused == []
        assert doc.removed == []

    def test_noop_when_no_pre_existing_original(self):
        # VarSet was created fresh by the copy — nothing to dedupe against.
        dup_varset = _FakeObj("VarSet", "VarSet", "App::VarSet")
        doc = _FakeDupDoc()
        reused = _dedupe_shared_dependencies(doc, [dup_varset], None, {})
        assert reused == []
        assert doc.removed == []
