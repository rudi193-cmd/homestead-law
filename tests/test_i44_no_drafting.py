"""Provisional I-44 — this face models, and does not draft or file.

Decision 8 of the build-out plan: the bankruptcy pack (and everything else
under `homestead_law/`) tracks dates and references for a Chapter 13 case; it
never drafts, never files, never says which chapter fits. Three guards — two
AST-based (a grep over rendered text would miss a fragment split across
concatenated string literals; walking the parsed tree does not), and one over
the README, which the parsed tree cannot reach at all:

1. no `Purpose.DRAFTING` or `Purpose.FILING` reference anywhere under
   `homestead_law/` — the engine's own closed set has both members, and
   nothing here may invoke either;
2. no advice-shaped phrase ("you should", "file by", "which chapter", "we
   recommend") in any string literal anywhere under `homestead_law/` — help
   text, page copy, a `why`, a `derived` form, or a `NOTICE` are exactly the
   places advice would first slip in, so the scan does not try to guess which
   strings are "content" and instead reads every one;
3. the same phrase list over `README.md`, because I-44 binds what the
   operator reads and not only what the interpreter parses.

All three are planted, per house style: a scan that has never fired has not
been shown to check anything.
"""
from __future__ import annotations

import ast
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent / "homestead_law"

#: Case-insensitive; matched as a substring of any string literal's text.
#:
#: Every entry is a **phrase**, not a word, and that is a constraint rather
#: than a stylistic choice: this tree legitimately says "should" (in prose
#: about what a guard should catch), "advise" (`Sidecar.advise`, an engine
#: method name), "qualify" (`plan_period.flag`'s own docstring) and
#: "eligible" ("mail-eligible"). A bare-word list would fire on all four and
#: be turned off within a week, which is worse than a narrower list that
#: stays on. So each entry names the *grammatical shape* advice takes — an
#: imperative aimed at the operator, or a claim about which chapter or
#: filing suits them — and the shapes are grouped below by what they would
#: be advising.
#:
#: "which chapter" rather than "chapter" alone — "chapter" bare would flag
#: `chapter` the field name and `Chapter 13` in ordinary prose, neither of
#: which is advice.
BANNED_PHRASES = (
    # telling the operator to act
    "you should", "you must", "you need to", "you have to", "you can file",
    "we recommend", "i recommend", "we suggest", "we advise",
    "you are advised", "it is recommended", "ought to", "be sure to",
    # telling the operator when to act — a date this app computed is always a
    # reference to confirm, never an instruction ("confirm against the
    # court's notice" is the sanctioned wording; "file by" is not)
    "file by", "must file", "should file", "deadline to file",
    "make sure you file", "before the deadline you",
    # telling the operator which relief or chapter suits them (decision 8)
    "which chapter", "right chapter", "chapter is right",
    "convert to chapter", "switch to chapter", "qualify for chapter",
    "eligible for chapter", "best option", "your best",
)

#: The one sanctioned shape "which chapter" may appear in: the pack-level
#: `NOTICE` sentence this bite's own brief hands down verbatim — "...and does
#: not say which chapter fits" — is the disclaimer the phrase ban exists to
#: protect, not a violation of it. Stripped out of a string *before* the scan
#: runs, so every other occurrence — including a rephrased attempt at the same
#: recommendation — is still caught.
_SAFE_NEGATIONS = (
    "does not say which chapter",
    "doesn't say which chapter",
    "never says which chapter",
    "never say which chapter",
)


def _modules() -> list[Path]:
    return sorted(p for p in PKG.rglob("*.py") if "__pycache__" not in p.parts)


# ── guard 1 — no Purpose.DRAFTING / Purpose.FILING ───────────────────────────

def _purpose_local_names(tree: ast.AST) -> set[str]:
    """Every local name bound to the engine's `Purpose` class in this module —
    `Purpose` itself, and whatever `import ... as` renamed it to
    (`from homestead.keep.rungs import Purpose as P` binds `P`). Attribute
    access through any of these names is `Purpose.<member>` under a different
    spelling, and the scan must not lose it to an alias."""
    names = {"Purpose"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "Purpose":
                    names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.rpartition(".")[2] == "Purpose":
                    names.add(alias.asname or alias.name)
    return names


def _purpose_drafting_filing_refs(tree: ast.AST) -> list[tuple[int, str]]:
    """Every `Attribute` node named `DRAFTING` or `FILING` whose immediate
    base is a name bound to `Purpose` (see `_purpose_local_names`, which
    follows an `as` alias) or itself an attribute literally named `Purpose`
    (`rungs.Purpose.FILING`) — `Purpose.DRAFTING`, `P.FILING` after `import
    Purpose as P`, and `keep.rungs.Purpose.DRAFTING` all match; an unrelated
    object's own `.DRAFTING` attribute (there is none in this package) does
    not, since the base must resolve to `Purpose` one way or the other."""
    purpose_names = _purpose_local_names(tree)
    hits: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Attribute) and node.attr in ("DRAFTING", "FILING")):
            continue
        base = node.value
        based_on_purpose = (
            (isinstance(base, ast.Name) and base.id in purpose_names)
            or (isinstance(base, ast.Attribute) and base.attr == "Purpose")
        )
        if based_on_purpose:
            hits.append((node.lineno, node.attr))
    return hits


def test_no_purpose_drafting_or_filing_anywhere_under_homestead_law():
    offenders: list[str] = []
    for mod in _modules():
        for lineno, name in _purpose_drafting_filing_refs(ast.parse(mod.read_text("utf-8"))):
            offenders.append(f"{mod.relative_to(PKG.parent)}:{lineno} Purpose.{name}")
    assert not offenders, (
        f"a Purpose.DRAFTING/FILING reference exists at {offenders}. "
        "Provisional I-44: this face models a case, it does not draft or "
        "file one."
    )


def test_the_purpose_guard_fires_on_a_planted_reference(tmp_path):
    for member, source in (
        ("DRAFTING", "from homestead.keep.rungs import Purpose\nP = Purpose.DRAFTING\n"),
        ("FILING", "from homestead.keep.rungs import Purpose as P\nQ = P.FILING\n"),
    ):
        planted = tmp_path / f"leak_{member}.py"
        planted.write_text(source, "utf-8")
        hits = _purpose_drafting_filing_refs(ast.parse(planted.read_text()))
        assert hits and hits[0][1] == member, f"the guard missed {member}"

    clean = tmp_path / "clean.py"
    clean.write_text(
        "from homestead.keep.rungs import Purpose\nP = Purpose.EXPORT\n", "utf-8"
    )
    assert not _purpose_drafting_filing_refs(ast.parse(clean.read_text())), (
        "a different Purpose member must not be flagged"
    )

    unrelated = tmp_path / "unrelated.py"
    unrelated.write_text(
        "class Form:\n    DRAFTING = 'not the engine enum'\nx = Form.DRAFTING\n",
        "utf-8",
    )
    assert not _purpose_drafting_filing_refs(ast.parse(unrelated.read_text())), (
        "an unrelated object's own .DRAFTING attribute must not be flagged — "
        "only a base literally named Purpose"
    )


# ── guard 2 — no advice-shaped phrase in any string literal ─────────────────

def _banned_phrase_hits(tree: ast.AST) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        lowered = node.value.lower()
        for safe in _SAFE_NEGATIONS:
            lowered = lowered.replace(safe, "")
        for phrase in BANNED_PHRASES:
            if phrase in lowered:
                hits.append((node.lineno, phrase))
    return hits


def test_no_advice_shaped_phrase_anywhere_under_homestead_law():
    """Every string literal in the tree — docstrings, `why`, `derived`,
    `NOTICE`, CLI help text and page copy alike; the scan does not try to
    tell them apart, because any of them is a place advice could slip in."""
    offenders: list[str] = []
    for mod in _modules():
        for lineno, phrase in _banned_phrase_hits(ast.parse(mod.read_text("utf-8"))):
            offenders.append(f"{mod.relative_to(PKG.parent)}:{lineno} {phrase!r}")
    assert not offenders, (
        f"an advice-shaped phrase exists at {offenders}. This face tracks "
        "dates and references; it never tells the operator what to do or "
        "which chapter fits."
    )


def test_the_phrase_guard_fires_on_each_planted_phrase(tmp_path):
    for phrase in BANNED_PHRASES:
        planted = tmp_path / f"leak_{BANNED_PHRASES.index(phrase)}.py"
        planted.write_text(f'MSG = "{phrase.capitalize()} the form."\n', "utf-8")
        hits = _banned_phrase_hits(ast.parse(planted.read_text()))
        assert hits, f"the guard missed {phrase!r}"
        assert hits[0][1] == phrase

    clean = tmp_path / "clean.py"
    clean.write_text('MSG = "Chapter 13 tracks dates and references."\n', "utf-8")
    assert not _banned_phrase_hits(ast.parse(clean.read_text())), (
        "'Chapter 13' in ordinary prose must not be flagged — only 'which "
        "chapter'"
    )


def test_the_negation_exemption_is_narrow_not_a_blanket_pass_for_the_phrase():
    """Only the exact disclaiming shape is exempt. A recommendation that
    happens to sit near the word "not" — but does not actually negate "which
    chapter" — must still be caught, or the exemption is a hole wide enough
    to drive the banned phrase through."""
    still_caught = ast.parse(
        '"MSG = not sure, but here is which chapter fits your case."'
    )
    assert _banned_phrase_hits(still_caught), (
        "a recommendation must not be waved through just because the word "
        "'not' appears somewhere earlier in the same string"
    )

    exempt = ast.parse(
        'MSG = "This pack does not say which chapter fits."'
    )
    assert not _banned_phrase_hits(exempt)


def test_the_real_pack_notice_and_why_strings_are_clean():
    """The positive side, pointed directly at the bankruptcy pack's own
    NOTICE and every `why`/`derived` string — the exact fields the module
    docstring names as where advice would first slip in."""
    from homestead_law.packs import bankruptcy

    assert not _banned_phrase_hits(
        ast.parse(f"NOTICE = {bankruptcy.NOTICE!r}")
    )
    for field, spec in bankruptcy.SCHEMA.items():
        for key in ("why", "derived"):
            text = spec.get(key)
            if text is None:
                continue
            assert not _banned_phrase_hits(ast.parse(f"X = {text!r}")), (
                f"{field}.{key} carries an advice-shaped phrase"
            )


# ── guard 2b — the same phrases, over the README's own page copy ────────────

README = PKG.parent / "README.md"


def _banned_phrase_lines(text: str) -> list[tuple[int, str]]:
    """The same phrase test as `_banned_phrase_hits`, over plain prose rather
    than parsed string literals — the README is page copy a reader sees, and
    an AST walk cannot reach it. Same `_SAFE_NEGATIONS` stripping, applied
    per line, so the disclaiming sentence the guard exists to protect reads
    the same here as it does in the pack's `NOTICE`."""
    hits: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.split("\n"), 1):
        lowered = line.lower()
        for safe in _SAFE_NEGATIONS:
            lowered = lowered.replace(safe, "")
        for phrase in BANNED_PHRASES:
            if phrase in lowered:
                hits.append((lineno, phrase))
    return hits


def test_no_advice_shaped_phrase_in_the_readme():
    """I-44 binds what the operator reads, not only what the interpreter
    parses. The plan's own audit line for this bite — no "you should"/"file
    by"/"which chapter" in help, page copy or derived forms — names page
    copy, and the README's bankruptcy section is page copy that the AST
    guard above is structurally unable to see."""
    offenders = [
        f"README.md:{lineno} {phrase!r}"
        for lineno, phrase in _banned_phrase_lines(README.read_text("utf-8"))
    ]
    assert not offenders, f"an advice-shaped phrase exists at {offenders}"


def test_the_readme_guard_fires_on_a_planted_line():
    planted = "\n".join([
        "## The pack",
        "You should file by the claims bar date.",
        "It does not say which chapter fits.",
    ])
    hits = _banned_phrase_lines(planted)
    assert {"you should", "file by"} <= {phrase for _, phrase in hits}, hits
    assert all(lineno == 2 for lineno, _ in hits), (
        "the disclaiming sentence on line 3 must not be flagged"
    )


def test_every_banned_phrase_is_a_phrase_not_a_bare_word():
    """The list's own constraint, held as a check. A single word ("should",
    "advise", "eligible") fires on this tree's ordinary prose and on the
    engine's own `Sidecar.advise`, and a guard that fires on ordinary prose
    is a guard somebody switches off. Every entry is at least two words, or
    the list has started to drift toward being unusable."""
    singles = [p for p in BANNED_PHRASES if " " not in p]
    assert not singles, (
        f"bare words in BANNED_PHRASES: {singles} — a phrase guard stays on "
        "only while it does not fire on ordinary prose"
    )
