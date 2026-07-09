from app.content.worked_examples import normalize_worked_examples


def test_passes_through_clean_list():
    examples = [{"problem_md": "p", "solution_md": "s"}]
    assert normalize_worked_examples(examples) == examples


def test_drops_malformed_list_entries():
    value = [{"problem_md": "p", "solution_md": "s"}, "bad", {"problem_md": "only"}]
    assert normalize_worked_examples(value) == [{"problem_md": "p", "solution_md": "s"}]


def test_parses_stringified_list():
    value = '[{"problem_md": "p", "solution_md": "s"}]'
    assert normalize_worked_examples(value) == [{"problem_md": "p", "solution_md": "s"}]


def test_salvages_string_with_unescaped_quotes_and_newlines():
    # The field-report crash: the whole array arrived as a JSON string whose
    # values contain unescaped inner quotes and raw newlines (invalid JSON).
    value = (
        '[\n  {\n    "problem_md": "Ask *"where now?"* not *"proven?"*",\n'
        '    "solution_md": "line one\nline two"\n  }\n]'
    )
    out = normalize_worked_examples(value)
    assert len(out) == 1
    assert out[0]["problem_md"] == 'Ask *"where now?"* not *"proven?"*'
    assert out[0]["solution_md"] == "line one\nline two"


def test_unsalvageable_returns_empty():
    assert normalize_worked_examples("total garbage {[") == []
    assert normalize_worked_examples(None) == []
