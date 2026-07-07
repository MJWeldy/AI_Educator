from app.content.latex_repair import repair, repair_tree


def test_repairs_eaten_commands():
    assert repair("P_{\text{train}}") == "P_{\\text{train}}"
    assert repair("\frac{1}{2}") == "\\frac{1}{2}"
    assert repair("\beta + \rho") == "\\beta + \\rho"
    assert repair("x \neq y") == "x \\neq y"
    assert repair("\nabla f") == "\\nabla f"


def test_leaves_legit_text_alone():
    md = "A paragraph.\n\nAnother one with a list:\n- item\n- another"
    assert repair(md) == md
    assert repair("already \\text{fine}") == "already \\text{fine}"
    assert repair("") == ""


def test_repair_tree():
    payload = {"content_md": "\text{x}", "worked_examples": [{"problem_md": "\frac12"}], "n": 3}
    fixed = repair_tree(payload)
    assert fixed["content_md"] == "\\text{x}"
    assert fixed["worked_examples"][0]["problem_md"] == "\\frac12"
    assert fixed["n"] == 3


def test_repairs_katex_incompatibilities():
    assert repair(r"D\textsubscript{te}") == r"D_{\text{te}}"
    assert repair(r"m\textsuperscript{2}") == r"m^{\text{2}}"
    assert repair(r"\bigl\bullet x") == r"\bullet x"
    assert repair(r"\bigl\boldsymbol{h}") == r"\boldsymbol{h}"
    assert repair(r"dangling \bigl") == "dangling "
    # Legitimate delimiter sizing is untouched.
    assert repair(r"\bigl(\frac{a}{b}\bigr)") == r"\bigl(\frac{a}{b}\bigr)"
    assert repair(r"\bigl[\bigr]") == r"\bigl[\bigr]"
    assert repair(r"\bigl\{\bigr\}") == r"\bigl\{\bigr\}"
    assert repair(r"\Bigl|x\Bigr|") == r"\Bigl|x\Bigr|"
    assert repair(r"\bigl\lvert x \bigr\rvert") == r"\bigl\lvert x \bigr\rvert"
