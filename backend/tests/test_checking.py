from app.content.checking import check_part, parse_number, sanitize_expression


def numeric(canonical, tolerance=None):
    return {"answer_type": "numeric", "canonical": str(canonical), "tolerance": tolerance}


def test_parse_number_forms():
    assert parse_number("7") == 7
    assert parse_number("-2.5") == -2.5
    assert parse_number("3/4").numerator == 3
    assert parse_number("1 3/4") == 1.75
    assert parse_number("-1 1/2") == -1.5
    assert parse_number("1,200") == 1200
    assert parse_number("abc") is None
    assert parse_number("1/0") is None


def test_numeric_exact():
    assert check_part(numeric("0.3"), "0.3")[0]
    assert check_part(numeric("0.3"), "3/10")[0]  # equivalent forms accepted
    assert not check_part(numeric("0.3"), "0.31")[0]
    assert check_part(numeric("12"), " 12 ")[0]


def test_numeric_tolerance():
    assert check_part(numeric("3.14", tolerance=0.01), "3.14159")[0]
    assert not check_part(numeric("3.14", tolerance=0.001), "3.15")[0]


def test_fraction_lowest():
    p = {"answer_type": "fraction_lowest", "canonical": "3/4"}
    assert check_part(p, "3/4")[0]
    ok, feedback = check_part(p, "6/8")
    assert not ok and "reduce" in feedback
    assert not check_part(p, "2/4")[0]
    whole = {"answer_type": "fraction_lowest", "canonical": "3"}
    assert check_part(whole, "3")[0]


def test_multiple_choice():
    p = {"answer_type": "multiple_choice", "canonical": "2", "choices": ["a", "b", "c"]}
    assert check_part(p, "2")[0]
    assert not check_part(p, "0")[0]


def test_expression_equivalence():
    p = {"answer_type": "expression", "canonical": "7*x + 2"}
    assert check_part(p, "7x + 2")[0]
    assert check_part(p, "2 + 7x")[0]
    assert not check_part(p, "7x + 3")[0]


def test_expression_requires_simplification():
    p = {"answer_type": "expression", "canonical": "7*x"}
    ok, feedback = check_part(p, "3x + 4x")
    assert not ok and "simplified" in feedback


def test_expression_sanitization():
    assert sanitize_expression("__import__('os')") is None
    assert sanitize_expression("system(1)") is None
    assert sanitize_expression("2^3 + x") == "2^3 + x"
    ok, feedback = check_part({"answer_type": "expression", "canonical": "x"}, "import x")
    assert not ok


def test_empty_answer():
    ok, feedback = check_part(numeric("5"), "")
    assert not ok and feedback
