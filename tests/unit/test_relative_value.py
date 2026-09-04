"""Tests for _resolve_relative_value and _coerce_property_value used in modify_property."""

import pytest

from freecad_ai.tools.freecad_tools import _resolve_relative_value, _coerce_property_value


class TestResolveRelativeValue:
    def test_absolute_number_passthrough(self):
        assert _resolve_relative_value(50, 100) == 100

    def test_absolute_string_number(self):
        # Non-relative string stays as-is (modify_property handles conversion)
        assert _resolve_relative_value(50, "100") == "100"

    def test_percentage_increase(self):
        result = _resolve_relative_value(100, "+10%")
        assert result == pytest.approx(110.0)

    def test_percentage_decrease(self):
        result = _resolve_relative_value(100, "-20%")
        assert result == pytest.approx(80.0)

    def test_percentage_zero(self):
        result = _resolve_relative_value(50, "+0%")
        assert result == pytest.approx(50.0)

    def test_multiply(self):
        result = _resolve_relative_value(100, "*1.5")
        assert result == pytest.approx(150.0)

    def test_multiply_double(self):
        result = _resolve_relative_value(30, "*2")
        assert result == pytest.approx(60.0)

    def test_add(self):
        result = _resolve_relative_value(50, "+5")
        assert result == pytest.approx(55.0)

    def test_subtract(self):
        result = _resolve_relative_value(50, "-3")
        assert result == pytest.approx(47.0)

    def test_non_numeric_current_returns_expr(self):
        assert _resolve_relative_value("hello", "+10%") == "+10%"

    def test_empty_string(self):
        assert _resolve_relative_value(50, "") == ""

    def test_bool_passthrough(self):
        assert _resolve_relative_value(True, False) is False

    def test_percentage_with_float_current(self):
        result = _resolve_relative_value(2.5, "+10%")
        assert result == pytest.approx(2.75)


class TestCoercePropertyValue:
    """setattr() on an App::PropertyInteger (as any App::VarSet
    integer property is) raises 'type must be int, not str' when the
    resolved value is still the raw wire string — modify_property's
    `value` param is declared "string" in its schema even for absolute
    numeric assignments, so an int/float/bool property's current value
    must drive the coercion.
    """

    def test_int_property_absolute_string(self):
        assert _coerce_property_value(10, "50") == 50
        assert isinstance(_coerce_property_value(10, "50"), int)

    def test_int_property_float_looking_string(self):
        assert _coerce_property_value(10, "50.0") == 50

    def test_float_property_absolute_string(self):
        result = _coerce_property_value(2.5, "7.25")
        assert result == pytest.approx(7.25)
        assert isinstance(result, float)

    def test_bool_property_string_true(self):
        assert _coerce_property_value(False, "true") is True

    def test_bool_property_string_false(self):
        assert _coerce_property_value(True, "false") is False

    def test_string_property_untouched(self):
        assert _coerce_property_value("Box", "Cylinder") == "Cylinder"

    def test_already_numeric_untouched(self):
        assert _coerce_property_value(10, 50) == 50

    def test_relative_expression_result_still_coerced_for_int(self):
        # modify_property calls _resolve_relative_value then _coerce_property_value;
        # a relative result on an int property must round-trip to int.
        resolved = _resolve_relative_value(10, "+5")
        assert _coerce_property_value(10, resolved) == 15

    def test_non_numeric_string_on_int_property_passed_through(self):
        # Can't coerce -> leave alone so the caller's own error path fires.
        assert _coerce_property_value(10, "not-a-number") == "not-a-number"
