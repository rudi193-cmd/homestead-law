"""`docs/PLAN-affairs-face.md` — every struck bite names a PR *and* a release.

X7-drift-law, Wave 7's plan-tracking requirement: the plan's law bites,
copied into this repo, with each landed one struck through and named for the
PR and release that shipped it. The property worth a test is not "the right
bites are struck" — this repo cannot verify that mechanically without
re-deriving the whole git-log reading the document itself did — it is
narrower and checkable: **a struck bite whose annotation names no PR and no
release is a claim nobody could audit**, the doc-prose equivalent of a scan
that asserts a result with no evidence attached. Ported from the engine's own
`tests/test_plan_affairs_face.py` (X7-drift-engine), which settled the same
two properties for the same reason a copied helper stays copied rather than
reinvented — see `tests/_strikethrough.py`.

* **A PR number alone is not the claim the document makes.** Every strike in
  this file says "landed *and shipped*", two facts with two different
  failure modes: a merged PR that never made a release, and a release named
  from memory. Both halves are required, and each has its own plant below.
* **The evidence window is the bullet, not a fixed number of characters.** A
  fixed lookahead lets a neighbouring bullet's PR number satisfy a strike
  that named none of its own. The window here is the list item the strike
  sits in: from its `- ` to the next one.

Struck text is excluded from its own evidence: a bite whose *original* plan
text predicted "release 0.4.0" must not be allowed to satisfy "which release
shipped it" with the number the plan predicted — that is the claim under
test, not the proof of it — so each item is read through `_strikethrough.
live()` first, exactly as `test_docs_drift.py` reads prose.
"""
from __future__ import annotations

import re
from pathlib import Path

from _strikethrough import live

PLAN_FACE = Path(__file__).resolve().parent.parent / "docs" / "PLAN-affairs-face.md"

_STRUCK_SPAN = re.compile(r"~~.*?~~", re.DOTALL)
_PR_NUMBER = re.compile(r"#\d+")
_RELEASE = re.compile(r"\b\d+\.\d+\.\d+\b")


def _list_items(text: str) -> list[str]:
    """The document's top-level bullets, one string each — the evidence
    window. A bullet runs from its own `- ` at the start of a line to the
    next such line (continuation lines are indented, so they stay with their
    own bullet) or to the end of the section."""
    items: list[str] = []
    current: list[str] | None = None
    for line in text.splitlines():
        if line.startswith("- "):
            if current is not None:
                items.append("\n".join(current))
            current = [line]
        elif current is not None:
            if line.startswith(("#", "|")) or (line and not line.startswith((" ", "\t"))):
                items.append("\n".join(current))
                current = None
            else:
                current.append(line)
    if current is not None:
        items.append("\n".join(current))
    return items


def _struck_items_missing_evidence(text: str) -> dict[str, list[str]]:
    """`{the struck bite, abbreviated: [what its own bullet never names]}`.

    Evidence is read from the bullet with its struck spans removed, so the
    plan's own prediction of a release number cannot stand in for the
    release that actually shipped it."""
    missing: dict[str, list[str]] = {}
    for item in _list_items(text):
        struck = _STRUCK_SPAN.search(item)
        if not struck:
            continue
        evidence = live(item)
        absent = []
        if not _PR_NUMBER.search(evidence):
            absent.append("a PR number")
        if not _RELEASE.search(evidence):
            absent.append("a release")
        if absent:
            missing[struck.group(0)[:80]] = absent
    return missing


def test_every_struck_bite_names_a_pr_number_and_a_release():
    text = PLAN_FACE.read_text("utf-8")
    assert _STRUCK_SPAN.search(text), (
        "no struck-through bite found at all — either nothing has landed "
        "(law is well past its first release) or the strike syntax drifted "
        "from ~~...~~"
    )
    missing = _struck_items_missing_evidence(text)
    assert not missing, (
        f"these struck bites do not name, outside the strike and inside "
        f"their own bullet, what landed them: {missing}"
    )


def test_the_evidence_guard_fires_on_a_planted_strike_with_no_pr():
    """Plant, half one: a strike whose bullet names a release and no PR."""
    planted = (
        "- ~~**L9-fake-bite** does a thing no test covers.~~ **Landed in "
        "release 0.9.0.**\n"
    )
    assert _struck_items_missing_evidence(planted) == {
        "~~**L9-fake-bite** does a thing no test covers.~~": ["a PR number"]
    }


def test_the_evidence_guard_fires_on_a_planted_strike_with_no_release():
    """Plant, half two: a strike whose bullet names a PR and no release — the
    half a weaker guard would have missed, letting a bite merged but never
    shipped read as landed."""
    planted = (
        "- ~~**L9-fake-bite** does a thing no test covers.~~ **Landed: PR "
        "[#99](https://github.com/homestead-affairs/homestead-law/pull/99).**\n"
    )
    assert _struck_items_missing_evidence(planted) == {
        "~~**L9-fake-bite** does a thing no test covers.~~": ["a release"]
    }


def test_the_evidence_guard_reads_neither_the_strike_nor_the_next_bullet():
    """The three negative/positive controls that make the window mean
    something. First: a bullet carrying both halves outside its strike
    passes. Second: a bullet whose *own* text is struck through with a PR
    and a release inside the strike does not — the plan predicted specific
    release numbers for several of these bites, and letting a prediction
    prove itself is the accounting error this document exists to avoid.
    Third: the neighbouring bullet's evidence does not carry over."""
    good = (
        "- ~~**L9-fake-bite** does a thing.~~ **Landed: PR "
        "[#99](https://github.com/homestead-affairs/homestead-law/pull/99), "
        "release 0.9.0.**\n"
    )
    assert _struck_items_missing_evidence(good) == {}

    self_proving = "- ~~**L9-fake-bite**: release 0.4.0, see PR #99.~~ Landed.\n"
    assert _struck_items_missing_evidence(self_proving) == {
        "~~**L9-fake-bite**: release 0.4.0, see PR #99.~~": ["a PR number", "a release"]
    }

    neighbour = (
        "- ~~**L9-fake-bite** does a thing.~~ Landed.\n"
        "- **L10-other-bite** — **Landed: PR [#99](x), release 0.9.0.**\n"
    )
    assert _struck_items_missing_evidence(neighbour) == {
        "~~**L9-fake-bite** does a thing.~~": ["a PR number", "a release"]
    }


def test_every_module_bite_is_listed_and_says_where_it_is_tracked():
    """The other half of "struck through, never deleted", applied to bites
    this repo cannot see: a module bite left *out* of this document is
    indistinguishable from one that does not exist. Each is listed unstruck
    and attributed to the checkout that can answer for it, so a reader with
    that checkout open knows which `git log` to read."""
    text = PLAN_FACE.read_text("utf-8")
    for repo in ("homestead", "homestead-ledger", "homestead-health"):
        assert f"tracked in `{repo}`" in text, (
            f"no bite list is attributed to {repo}; a module bite with no "
            "repository named is a bite nobody can check"
        )
    for bite in ("E1-dates-a", "E4-sync-core", "G2b-account-instances",
                 "G8-business-books", "H6-sealed-reader", "W0-HEALTH"):
        assert f"`{bite}`" in text, (
            f"{bite} is named in the affairs build-out plan and missing from "
            "this document — omission is the one mark this file may not make"
        )


def test_every_law_bite_this_repos_own_history_can_verify_is_named():
    """The half this document owns outright: every law-repo bite the plan
    names must appear here, struck or not, so a reader never has to guess
    whether one was simply left off."""
    text = PLAN_FACE.read_text("utf-8")
    for bite in (
        "W0-LAW", "L2a-pack-contract", "L2c-second-pack-readiness",
        "L2b-instances", "L3-custody-relocation", "L3-bankruptcy-ch13",
        "L3-workers-comp", "L3-deadline-templates", "L4-surfaces", "L5-sync",
        "L8-grant", "L8-venture", "L8-surfaces", "X7-drift-law",
    ):
        assert f"`{bite}`" in text or f"**{bite}**" in text, (
            f"{bite} is a law bite named in the affairs build-out plan and "
            "missing from this document"
        )


def test_l8_surfaces_is_struck_with_its_own_pr_and_release():
    """`L8-surfaces` went through three states while this document was being
    written: in progress on `claude/law-surfaces-8`, merged to `main` (PR
    #46) with no release yet, and finally released as 0.9.0 (PR #47) —
    struck only at the last of those, once `CHANGELOG.md`'s own `[0.9.0]`
    section confirmed it, never ahead of the evidence
    `test_every_struck_bite_names_a_pr_number_and_a_release` requires of
    every other struck bite in this file."""
    for item in _list_items(PLAN_FACE.read_text("utf-8")):
        if "L8-surfaces" in item:
            assert _STRUCK_SPAN.search(item), (
                "L8-surfaces has a release (0.9.0, CHANGELOG.md) and must be "
                "struck like every other landed bite in this document"
            )
            assert "#46" in item and "0.9.0" in item
            return
    raise AssertionError("L8-surfaces is not named in docs/PLAN-affairs-face.md at all")


# ── the open items keep their names, and stay unstruck (audit, 2026-09-11) ──

#: The bites this document tracks as *found and not built*. A strike on one of
#: these would be the same false claim `L4-surfaces`'s own landing made about
#: `child_name` — "the bite that retires it" written before the bite existed.
OPEN_BITES = ("L9-child-name",)


def _struck_spans(text: str) -> list[str]:
    return _STRUCK_SPAN.findall(text)


def test_every_open_bite_is_named_and_none_of_them_is_struck():
    """An open item that names no bite is a to-do nobody can look up, and a
    struck one is a claim that it landed. `L9-child-name` is the retirement
    `L4-surfaces` was wrongly promised to do; it has no PR and no release, so
    it must appear by name and appear unstruck."""
    text = PLAN_FACE.read_text("utf-8")
    struck = " ".join(_struck_spans(text))
    for bite in OPEN_BITES:
        assert bite in text, (
            f"{bite} is the name this document gives an open item and it is "
            "not in the document — an open item with no bite name is a "
            "to-do nobody can look up"
        )
        assert bite not in struck, (
            f"{bite} appears inside a ~~struck~~ span: this document strikes "
            "a bite only once a PR and a release carried it, and there is "
            "neither"
        )


def test_the_open_bite_guard_fires_on_a_planted_strike_and_a_planted_omission():
    """Both halves planted, against the same rule the real check runs. A
    document that struck the open bite, and one that never named it."""
    planted_struck = "- ~~**L9-child-name** retires the field.~~ Landed: PR #99, 0.9.9.\n"
    assert "L9-child-name" in " ".join(_struck_spans(planted_struck))

    planted_absent = "- **L8-surfaces** — nothing about the retirement here.\n"
    assert "L9-child-name" not in planted_absent

    # and the real document satisfies both, which is what makes the plants
    # a check rather than a restatement.
    text = PLAN_FACE.read_text("utf-8")
    assert "L9-child-name" in text
    assert "L9-child-name" not in " ".join(_struck_spans(text))
