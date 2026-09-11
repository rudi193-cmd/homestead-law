"""X7-drift-law — grep guards for the sentences the build moved past, so a
reintroduction (a copy-paste from an old commit, a docstring reverted by
hand) fails here by name rather than misleading the next reader.

**Fixed, not a general staleness detector.** The sweep read every claim in
README.md, the pack docstrings and `docs/*.md` against the code as it stands
today (2026-09-11, on top of `L8-surfaces`) and found three sentences that had
drifted past what the code now does. Each is guarded below, per the house
rule that a scan without a planted-violation test has not been shown to check
anything.

1. **README.md's top status banner** said "bite 3 — runnable end to end on
   SQLite" and pinned "Suite: 85 passed" — true when bite 3 shipped, five
   packs and four releases ago. Struck and replaced with a status that
   points at the capabilities table (`tests/test_readme_capabilities.py`)
   instead of a number the next added test makes false again.
2. **`homestead_law/packs/custody.py`'s `child_name` `why` string** (and the
   test that pins it, `tests/test_packs.py`) said "L4-surfaces (wave 4) is
   the bite that retires it" as a forward promise. `L4-surfaces` landed and
   left every door naming `child_name` unchanged — the promise was false the
   day the bite it named shipped without keeping it. Struck; the retirement
   is now recorded as a still-open item in `docs/PLAN-affairs-face.md`.
3. **`rules.accept`'s stored instruction** hard-coded `"confirm against the
   court's notice"` for every accepted template, including `L8-venture`'s
   `election-83b` — an IRS filing window under 26 U.S.C. § 83(b), with no
   court. Corrected to `"confirm against the source above"`, which names
   what the instruction already states a sentence earlier and holds
   regardless of whether the source is a court, a trustee's rule, or the tax
   code.

**What this file is not.** Most of the known suspects from the affairs
build-out plan's drift-inventory list ("only custody is registered", the
US-DE/US-OR jurisdiction claims, `validate_value` "not yet called by either
door", the vendored `app/cover.py`) were already corrected by the bites that
built the thing they described, each with its own guard in its own file
(`tests/test_registry.py`, `tests/test_venture.py`, `homestead_law/app/
cover.py`'s own module docstring). Re-guarding those here would be a second,
unsynchronised copy of a check that already exists — the exact failure this
module's docstring warns against.
"""
from __future__ import annotations

import re
from pathlib import Path

from _strikethrough import live

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
CUSTODY = ROOT / "homestead_law" / "packs" / "custody.py"
RULES_PY = ROOT / "homestead_law" / "rules.py"
TEST_PACKS = ROOT / "tests" / "test_packs.py"
TEST_RULES = ROOT / "tests" / "test_rules.py"
TEST_CLI_NO_NESTOR = ROOT / "tests" / "test_cli_without_nestor.py"


def _contains(path: Path, needle: str) -> bool:
    return needle in path.read_text(encoding="utf-8")


def _live_contains(path: Path, needle: str) -> bool:
    """`needle` appears in `path` outside any `~~struck~~` span — a stale
    claim kept for history inside a strike is not a live one."""
    return needle in live(path.read_text(encoding="utf-8"))


# ── 1. the README's pinned bite-3 status banner ──────────────────────────

STALE_SUITE_COUNT = "Suite: **85 passed**"
STALE_BITE_3_STATUS = "Status: bite 3 — runnable end to end on SQLite"

#: The *shape* of a pinned test count, not just the one number this file
#: happened to carry — an exact-string guard alone would clear a README that
#: said "Suite: **905 passed**", a fresh pin of exactly the thing that went
#: stale.
_PINNED_COUNT_RE = re.compile(r"\b\d+\s+passed\b")


def _pinned_test_counts(text: str) -> list[str]:
    return _PINNED_COUNT_RE.findall(text)


def test_readme_does_not_reassert_the_bite_3_status_or_a_pinned_suite_count():
    text = README.read_text("utf-8")
    assert not _live_contains(README, STALE_BITE_3_STATUS), (
        f"README.md must not live-assert {STALE_BITE_3_STATUS!r} — five "
        "matters are registered and four releases have shipped since bite 3"
    )
    assert not _live_contains(README, STALE_SUITE_COUNT), (
        f"README.md must not live-assert {STALE_SUITE_COUNT!r}"
    )
    pinned = _pinned_test_counts(live(text))
    assert not pinned, (
        f"README.md pins a suite count ({pinned}) outside any struck span — "
        "describe the suite qualitatively (as the sentence that replaced "
        f"{STALE_SUITE_COUNT!r} does), not with a literal the next added "
        "test makes false again"
    )


def test_the_status_guard_fires_on_a_planted_regression_and_a_fresh_count(tmp_path):
    """The exact stale sentence, written back into a copy of the real file —
    and, the half an exact-string guard alone would miss, the same shape
    with today's number in it."""
    planted = tmp_path / "README.md"
    base = README.read_text("utf-8")
    planted.write_text(base + f"\n\n> {STALE_BITE_3_STATUS}. {STALE_SUITE_COUNT}.\n", "utf-8")
    assert _live_contains(planted, STALE_BITE_3_STATUS)
    assert _live_contains(planted, STALE_SUITE_COUNT)

    fresh_pin = tmp_path / "README2.md"
    fresh_pin.write_text(base + "\n\nSuite: **905 passed**.\n", "utf-8")
    assert _pinned_test_counts(live(fresh_pin.read_text("utf-8"))) == ["905 passed"]

    # and the sentence that actually replaced it does not fire — or the
    # README could never describe its own suite again.
    assert not _pinned_test_counts(
        "Suite: green on `pytest -q`, on both legs (with and without the "
        "`entity` extra)."
    )


# ── 2. child_name's broken "L4-surfaces retires it" promise ─────────────

STALE_L4_SURFACES_PROMISE = (
    "**L4-surfaces (wave 4) is the "
    "bite that retires it**, because that is the bite that already "
    "rewrites every door naming it"
)


def test_custody_pack_does_not_live_assert_l4_surfaces_retires_child_name():
    assert not _live_contains(CUSTODY, STALE_L4_SURFACES_PROMISE), (
        "homestead_law/packs/custody.py must not live-assert that "
        "L4-surfaces retires child_name — it landed and did not; the "
        f"struck claim must stay struck: {STALE_L4_SURFACES_PROMISE!r}"
    )


def test_test_packs_does_not_repeat_the_broken_promise_as_a_live_docstring():
    assert not _live_contains(TEST_PACKS, "The bite that retires the field is L4-surfaces"), (
        "tests/test_packs.py must not live-assert that L4-surfaces is (still, "
        "in the future) the bite retiring child_name — that promise is "
        "broken and corrected; see docs/PLAN-affairs-face.md"
    )
    assert _contains(TEST_PACKS, "docs/PLAN-affairs-face.md"), (
        "the corrected docstring must point at the open item's real record"
    )


def test_the_l4_surfaces_promise_guard_fires_on_a_planted_regression(tmp_path):
    """The stale sentence, written into a copy of the real module — struck
    or not, the guard's job is to catch it live."""
    live_regression = tmp_path / "custody.py"
    live_regression.write_text(
        CUSTODY.read_text("utf-8") + f"\n\n_PLANTED = '''{STALE_L4_SURFACES_PROMISE}'''\n",
        "utf-8",
    )
    assert _live_contains(live_regression, STALE_L4_SURFACES_PROMISE)

    # struck, it must NOT fire — a struck plant is history, not a live claim.
    struck_only = tmp_path / "custody_struck.py"
    struck_only.write_text(f"_PLANTED = '''~~{STALE_L4_SURFACES_PROMISE}~~'''\n", "utf-8")
    assert not _live_contains(struck_only, STALE_L4_SURFACES_PROMISE)


# ── 3. rules.accept's "confirm against the court's notice" wording ──────

STALE_COURT_NOTICE_INSTRUCTION = "confirm against the court's notice"
CORRECTED_SOURCE_INSTRUCTION = "confirm against the source above"

#: `homestead_law/packs/custody.py`'s own per-template `note` for
#: `nm-registration-contest` legitimately says "confirm against the court's
#: own notice" — a genuine UCCJEA court, named in that one template's prose,
#: not the generic `rules.accept()` instruction every pack's templates share.
#: The extra word "own" keeps the two strings distinct byte-for-byte, so this
#: guard does not fire on that legitimate, still-true sentence.
_CUSTODY_OWN_NOTICE = "confirm against the court's own notice"


def test_rules_py_does_not_hard_code_the_court_specific_instruction():
    for path in (RULES_PY, README, TEST_RULES, TEST_CLI_NO_NESTOR):
        assert not _contains(path, STALE_COURT_NOTICE_INSTRUCTION), (
            f"{path.name} still names the generic accept() instruction as "
            f"{STALE_COURT_NOTICE_INSTRUCTION!r} — wrong for a non-judicial "
            "template (venture's election-83b, an IRS filing with no court); "
            f"it must say {CORRECTED_SOURCE_INSTRUCTION!r}"
        )
    assert _contains(RULES_PY, CORRECTED_SOURCE_INSTRUCTION), (
        "rules.py's accept() must write the corrected, forum-neutral "
        f"instruction: {CORRECTED_SOURCE_INSTRUCTION!r}"
    )
    # the custody pack's own, genuinely court-specific template note is
    # unrelated and must still say what it always said.
    assert _contains(CUSTODY, _CUSTODY_OWN_NOTICE)


def test_the_court_notice_guard_fires_on_a_planted_regression(tmp_path):
    """The stale instruction, written back into a copy of the real module —
    and the negative control: the custody pack's own distinct per-template
    note must not trip the same guard."""
    planted = tmp_path / "rules.py"
    planted.write_text(
        RULES_PY.read_text("utf-8").replace(
            CORRECTED_SOURCE_INSTRUCTION, STALE_COURT_NOTICE_INSTRUCTION
        ),
        "utf-8",
    )
    assert _contains(planted, STALE_COURT_NOTICE_INSTRUCTION)

    # the negative control: custody's own distinct sentence inserts "own"
    # between "court's" and "notice", so the exact generic phrase is not a
    # substring of it — the guard must not fire on custody.py's real,
    # still-true template note.
    assert _CUSTODY_OWN_NOTICE != STALE_COURT_NOTICE_INSTRUCTION
    assert STALE_COURT_NOTICE_INSTRUCTION not in _CUSTODY_OWN_NOTICE
    assert not _contains(CUSTODY, STALE_COURT_NOTICE_INSTRUCTION), (
        "custody.py's real per-template note must not itself match the "
        "exact generic phrase this guard bans"
    )
