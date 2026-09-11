"""README's capabilities table names every top-level, app and pack module,
or excludes it.

X7-drift-law, Wave 7's README requirement: one row per law capability the
affairs build-out plan added, naming the release that shipped it — see
README.md's "Capabilities, and what shipped them". That table does not
re-describe Phase 0-3's foundations (the store, the registry, the queue, the
CLI/server doors nearly every bite grows, the Nestor seam, the citation
extractor, the intake UI) — those predate the build-out plan and have no
single "shipped by" release. So the property this file holds is not "every
module is a capability row"; it is **every module is accounted for
somewhere** — named in the capabilities table, or in this file's own
`FOUNDATION` exclusion tuple, each with a one-line reason. A module in
neither is BUG-6's shape one level up: a thing that exists and is not
enumerated anywhere a reader would think to look.

Scoped to `homestead_law/*.py`, `homestead_law/app/*.py` and
`homestead_law/packs/*.py`. `app/` was originally left out, on the reasoning
that `tests/test_chokepoint.py` already holds it to a narrower contract —
but a chokepoint contract answers "may this module reflect", not "which
release added this", and the omission let the table go a whole release stale
without anything noticing: 0.9.0 (L8-surfaces — the grant and venture panes,
the plan-period line) had no row at all when the X7-drift audit read it,
2026-09-11. Swept now, with the surfaces that predate the build-out plan
named in `FOUNDATION` beside the rest.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
PKG = ROOT / "homestead_law"
CHANGELOG = ROOT / "CHANGELOG.md"

#: Modules the capabilities table deliberately does not name, because they
#: are Phase 0-3 foundations predating the build-out plan, or scaffolding
#: with no capability of their own. Each reason is checked by nothing but a
#: human reader — this tuple exists so a module can leave this list only by
#: being named in the README, never by being quietly forgotten from both.
FOUNDATION: dict[str, str] = {
    "__init__.py": "package marker, not a capability",
    "__main__.py": "the `--smoke`/`--demo` entry point, not a capability itself",
    "store.py": "Phase 1 — the SQLite `Sidecar` binding, predates the build-out plan",
    "registry.py": "Phase 3 — the one matter enumeration (I-23), predates the build-out plan; each pack's own row names when it joined",
    "queue.py": "Phase 3 — the urgent queue (BUG-6's fix), predates the build-out plan",
    "nestor_seam.py": "pre-build-out — the entity-resolution seam (the `entity` extra)",
    "nestor_store.py": "pre-build-out — the Nestor-backed store binding",
    "patterns.py": "Phase 2 — the closed-reporter-set citation extractor (I-18)",
    "intake.py": "Phase 3 — the paste-and-extract intake UI, predates the build-out plan",
    "cli.py": "grown by nearly every bite in this file; no single capability owns it",
    "server.py": "grown by nearly every bite in this file; no single capability owns it",
    "packs/__init__.py": "package marker, not a capability",
    # `app/` — swept in by the X7-drift audit (2026-09-11). Two releases
    # landed here (0.5.0's panes, 0.9.0's grant/venture panes) and the table
    # named neither directory nor module, so it went a release stale with
    # nothing to notice. `panes.py` is a capability row; the rest are
    # foundations or scaffolding, each with its reason.
    "app/__init__.py": "package marker, not a capability",
    "app/advisories.py": "Phase 3 — the surfaced advisory matcher, predates the build-out plan",
    "app/cover.py": "Phase 3 — the cover's re-identification check (I-31); L5-sync replaced the vendored copy with the engine's, which is that bite's row, not a capability of its own",
    "app/demo.py": "the headless `--demo` renderer; it composes the panes rather than adding a capability",
    "app/view.py": "Phase 3 — the tk 'What's due' surface, predates the build-out plan",
    "app/window.py": "Phase 3 — the tk list/detail surface (I-21/I-31), predates the build-out plan",
}

_CODE_SPAN_MODULE = re.compile(r"`((?:app/|packs/)?[A-Za-z_]+\.py)`")

#: The heading the capabilities table lives under. The scan is scoped to this
#: one section, so a module merely *mentioned* elsewhere in the README (the
#: custody walk-through above, say) does not count as "named in the
#: capabilities table" — the same scoping mistake the engine's own drift
#: audit found and narrowed (`keep/paths.py` sitting in both its table and
#: its `FOUNDATION` at once because the scan read the whole file).
_CAPABILITIES_HEADING = "## Capabilities, and what shipped them"

_VERSION_RE = re.compile(r"\d+\.\d+\.\d+")
_RELEASED_RE = re.compile(r"^## \[(\d+\.\d+\.\d+)\]", re.MULTILINE)


def _capabilities_section(readme_text: str) -> str:
    """The README text under `_CAPABILITIES_HEADING`, up to the next `##`
    heading — and a refusal, never an empty string, if the heading is gone.
    An empty section would make every module unaccounted-for and the failure
    would read as twenty-two missing rows rather than one renamed heading."""
    _, sep, rest = readme_text.partition(_CAPABILITIES_HEADING)
    assert sep, (
        f"README.md has no {_CAPABILITIES_HEADING!r} heading — this file "
        "checks a table that no longer exists under the name it was given"
    )
    end = rest.find("\n## ")
    return rest if end == -1 else rest[:end]


def _modules_named_in(text: str) -> set[str]:
    """Every `x.py`, `app/x.py` or `packs/x.py` backtick-quoted path in
    `text`."""
    return set(_CODE_SPAN_MODULE.findall(text))


def _real_modules() -> set[str]:
    """Every module directly under `homestead_law/`, `homestead_law/app/` and
    `homestead_law/packs/`, as the same short form the README and
    `FOUNDATION` both use. The prefixes are written out rather than derived
    from a path, so nothing here depends on the separator the OS uses (the CI
    matrix runs Windows)."""
    modules = {p.name for p in PKG.glob("*.py")}
    for sub in ("app", "packs"):
        modules |= {f"{sub}/{p.name}" for p in (PKG / sub).glob("*.py")}
    return modules


def _unaccounted_for(real_modules: set[str], readme_text: str) -> set[str]:
    """Modules that are neither named in `readme_text` nor in `FOUNDATION`."""
    named = _modules_named_in(_capabilities_section(readme_text)) | set(FOUNDATION)
    return real_modules - named


def test_every_top_level_and_pack_module_is_named_or_excluded():
    unaccounted = _unaccounted_for(_real_modules(), README.read_text("utf-8"))
    assert not unaccounted, (
        f"these modules are named in neither README.md's capabilities table "
        f"nor this file's FOUNDATION tuple: {sorted(unaccounted)}. Add a row "
        "naming the release that shipped it, or add it to FOUNDATION with a "
        "one-line reason it predates the build-out plan."
    )


def test_foundation_entries_are_real_modules_not_a_stale_list():
    """The other half of BUG-6's lesson: an entry in the exclusion tuple for
    a module that no longer exists is exactly as silent a drift as a module
    missing from it."""
    real = _real_modules()
    stale = set(FOUNDATION) - real
    assert not stale, f"FOUNDATION names modules that no longer exist: {sorted(stale)}"


def test_the_coverage_guard_fires_on_a_planted_unaccounted_module():
    """A scan that has never fired has not been shown to check anything. A
    fake module named in neither the README text nor `FOUNDATION` must be
    caught, and the real tree, run through the same helper, must stay
    clean — the plant is additive, not a relaxation of the real check."""
    readme_text = README.read_text("utf-8")
    planted = _real_modules() | {"_planted_uncovered.py"}
    unaccounted = _unaccounted_for(planted, readme_text)
    assert unaccounted == {"_planted_uncovered.py"}
    assert not _unaccounted_for(_real_modules(), readme_text)


def test_the_foundation_exclusions_are_minimal():
    """An exclusion for a module the table names anyway is not an exclusion,
    it is a second, unsynchronised list of the same module."""
    in_table = _modules_named_in(_capabilities_section(README.read_text("utf-8")))
    both = sorted(set(FOUNDATION) & in_table)
    assert not both, (
        f"these modules are in FOUNDATION and in the capabilities table: "
        f"{both}. A module is a capability with a release, or a foundation "
        "with a reason — one list, not two."
    )


def test_the_capabilities_scan_reads_the_section_and_fires_on_a_planted_mention():
    """The plant the scoping needs, both ways round. A module named *only*
    outside the capabilities section must still count as unaccounted, and
    the same name inside the section must count as covered."""
    outside = (
        "# Law\n\n## What is enforced here today\n\n"
        "`_planted_elsewhere.py` is the only module that may do the thing.\n\n"
        f"{_CAPABILITIES_HEADING}\n\n| capability | shipped by | module(s) |\n"
        "|---|---|---|\n| Something | 0.6.0 | `sync.py` |\n\n## Design\n"
    )
    planted = {"_planted_elsewhere.py", "sync.py"}
    assert _unaccounted_for(planted, outside) == {"_planted_elsewhere.py"}

    inside = outside.replace(
        "| Something | 0.6.0 | `sync.py` |",
        "| Something | 0.6.0 | `sync.py`, `_planted_elsewhere.py` |",
    )
    assert _unaccounted_for(planted, inside) == set()


def test_a_missing_capabilities_heading_refuses_rather_than_reading_empty():
    """Fail closed (I-11): a renamed or deleted heading is a refusal that
    names the heading, not a silent empty section that would report every
    module in the package as missing a row."""
    with pytest.raises(AssertionError, match="Capabilities"):
        _capabilities_section("# Law\n\n## Design\n\nnothing here\n")


# ── every "shipped by" version in the table is a release that happened ──────

def _released_versions() -> set[str]:
    return set(_RELEASED_RE.findall(CHANGELOG.read_text("utf-8")))


def _unreleased_since_versions(readme_text: str) -> list[str]:
    """Every version named in the capabilities table that this repo's own
    CHANGELOG never cut — an invented or mistyped number, not a merely
    *wrong* one."""
    section = _capabilities_section(readme_text)
    released = _released_versions()
    return sorted({v for v in _VERSION_RE.findall(section) if v not in released})


def test_every_shipped_by_version_is_a_release_that_happened():
    unreleased = _unreleased_since_versions(README.read_text("utf-8"))
    assert not unreleased, (
        "README.md's capabilities table names these versions, and "
        f"CHANGELOG.md records no such release: {unreleased}"
    )


def test_the_shipped_by_guard_fires_on_a_planted_phantom_release():
    """A version nobody ever cut, planted in the table — the guard must name
    it, and must still clear the real ones beside it."""
    readme_text = README.read_text("utf-8")
    section = _capabilities_section(readme_text)
    assert "| Sync — CLI and Sync tab, the consented-scope envelope | 0.6.0 |" in section, (
        "the plant assumes the sync row's shape"
    )
    planted = readme_text.replace(
        "| Sync — CLI and Sync tab, the consented-scope envelope | 0.6.0 |",
        "| Sync — CLI and Sync tab, the consented-scope envelope | 9.9.9 |",
        1,
    )
    assert _unreleased_since_versions(planted) == ["9.9.9"]
