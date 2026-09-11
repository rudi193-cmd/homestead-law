"""The tkinter view that draws a `Window` (bite 4).

Thin by construction (I-29): it turns `Window` state into widgets and clicks into
`Window` calls, and holds no domain logic. It draws `Row.text` and
`Served.value` — what the gate handed back — and reaches no `.payload`; the
chokepoint (`test_invariants_chokepoint.py`) makes that a build failure and also
forbids reflection here, so this file only ever renders what it was served.

It rests on the **cover** (I-21): nothing is drawn until the operator asks. The
list shows a rung and a line per item; opening one shows the detail.

**The window opens on the household's own records.** `compose_store()` binds the
real store (`HOMESTEAD_HOME`, else `~/.homestead`) and, if it holds anything at
all for any registered matter, draws that — what `homestead-law put`, `deadline`
and the browser UI wrote. Only an empty store falls back to a throwaway demo
(a fresh tmpdir, seeded by `app.demo`, announced on the cover by `DEMO_BANNER`)
so a first run is never a blank window; the real root is never seeded. The
decision is factored out of `run()` so it can be driven headlessly.

**The look is the engine's, not this module's.** `homestead.app.theme` — the
shared stdlib `ttk.Style` theme — is applied once to the root, and the list panes
colour their rows by rung (`theme.rung_color`), so this window and
`homestead-ledger`'s read as one product. There is no second copy of the palette
to drift.

`tkinter` is imported inside `run()` so the module stays importable on a headless
box (the suite reads this file; it does not open a display).
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from datetime import date

from homestead.app import theme
from homestead.keep.rungs import Disposition
from homestead_law import queue as queue_mod
from homestead_law.app import advisories, demo
from homestead_law.app.window import Window
from homestead_law.registry import all_matters
from homestead_law.store import Sidecar

__all__ = ["run", "compose_store", "LawContext", "DEMO_BANNER", "ENTRY_HINT"]

#: Shown on the cover in place of the ordinary subheading whenever `run()` fell
#: back to the throwaway demo store, so demonstration records are never mistaken
#: for a household's own.
DEMO_BANNER = (
    "demonstration data — enter your own with `homestead-law put` or `homestead-law ui`"
)

#: Where a record is entered. The window reads; the browser UI and the CLI write.
ENTRY_HINT = "Enter or change records: `homestead-law ui` (browser) or `homestead-law put`."


@dataclass(frozen=True)
class LawContext:
    """Which store `run()` opened the window on, and why. `demo=True` means the
    real store was empty and this is a throwaway fallback seeded by `app.demo`;
    `demo=False` means `store` is the household's own. `today` is `date.today()`
    for the real store and `demo.TODAY` for the fallback, so the demo's urgency
    stays stable."""

    store: Sidecar
    today: str
    demo: bool


def _has_real_data(store: Sidecar) -> bool:
    """True the moment the real sidecar holds one record for any registered
    matter — iterating the registry (I-23), not a hand-kept list."""
    return any(store.records(name) for name in all_matters())


def compose_store() -> LawContext:
    """Decide which store the window opens on, and bind it.

    Opens `Sidecar()` against whatever `HOMESTEAD_HOME` (or its `~/.homestead`
    default) resolves to. If it holds anything, it wins and is returned
    untouched — this function never seeds the real store. Only a completely
    empty store falls back to a fresh throwaway tmpdir, seeded as `app.demo`
    always has, with `HOMESTEAD_HOME` redirected there *before* seeding so the
    real root, checked and found empty just above, is never written to.
    """
    store = Sidecar()
    if _has_real_data(store):
        return LawContext(store=store, today=date.today().isoformat(), demo=False)

    os.environ["HOMESTEAD_HOME"] = tempfile.mkdtemp(prefix="homestead-law-demo-")
    demo_store = Sidecar()
    demo.seed(demo_store)
    demo.seed_deadlines(demo_store)
    return LawContext(store=demo_store, today=demo.TODAY, demo=True)


def run() -> int:
    import tkinter as tk
    from tkinter import ttk

    context = compose_store()
    store = context.store
    window = Window()
    today = context.today

    root = tk.Tk()
    root.title("Homestead")
    root.minsize(600, 420)
    theme.apply(root)
    content = ttk.Frame(root, padding=24)
    content.pack(fill="both", expand=True)

    def clear() -> None:
        for child in content.winfo_children():
            child.destroy()

    def show_cover() -> None:
        window.close()
        clear()
        ttk.Label(content, text="Homestead", style="Heading.TLabel").pack(anchor="w")
        subheading = DEMO_BANNER if context.demo else "The affairs you handle yourself."
        ttk.Label(content, text=subheading, style="Subheading.TLabel").pack(anchor="w", pady=(4, 24))
        # The resting cover shows only counts that survive the re-identification
        # check (I-31). Over a single matter that is nothing, so the cover rests
        # on "Nothing is open" — the queue is there when the operator asks.
        resting = queue_mod.cover(store, today=today)
        summary = ", ".join(f"{n} {k.replace('_', ' ')}" for k, n in resting.items())
        ttk.Label(content, text=summary or "Nothing is open.", style="Muted.TLabel").pack(anchor="w")
        ttk.Button(content, text="What's due", command=show_queue).pack(anchor="w", pady=(24, 0))
        ttk.Button(
            content, text="Open custody matter", style="Secondary.TButton", command=show_list,
        ).pack(anchor="w", pady=(8, 0))
        # The window reads; entry happens in the browser UI or on the command
        # line. Said once, on the cover, so a first-time operator knows where.
        ttk.Label(content, text=ENTRY_HINT, style="Muted.TLabel", wraplength=520).pack(
            anchor="w", pady=(24, 0)
        )

    def show_queue() -> None:
        clear()
        # Load the matter's records into the window so a queue item opens through
        # the same gated detail path as the list (the demo is one matter; a
        # multi-matter app would load each matter the queue spans).
        window.open_list(store.records(demo.MATTER))
        ttk.Label(content, text="What's due", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(
            content, text="showing derived · L4 present", style="Subheading.TLabel"
        ).pack(anchor="w", pady=(0, 12))

        items = queue_mod.queue(store, today=today)
        listbox = tk.Listbox(content, height=12)
        theme.style_listbox(listbox)
        listbox.pack(fill="both", expand=True)
        for item in items:
            if item.gap:
                mark = "date unreadable"
            elif item.overdue:
                mark = f"overdue by {abs(item.days_until)}d"
            else:
                mark = f"in {item.days_until}d"
            listbox.insert("end", f"[{item.rung.value}]  {item.shown}  ·  {mark}")
            listbox.itemconfig("end", foreground=theme.rung_color(item.rung))

        def on_open(_event: object = None) -> None:
            selection = listbox.curselection()
            if selection:
                show_detail(items[selection[0]].ref, back=show_queue)

        listbox.bind("<Double-Button-1>", on_open)
        ttk.Button(content, text="Open", command=on_open).pack(anchor="w", pady=(12, 0))
        ttk.Button(
            content, text="Close", style="Secondary.TButton", command=show_cover,
        ).pack(anchor="w", pady=(4, 0))

    def show_list() -> None:
        clear()
        window.open_list(store.records(demo.MATTER))
        ttk.Label(content, text="custody", style="Heading.TLabel").pack(anchor="w")
        # one indicator per surface, not per row (I-33): the pane says an L4 is
        # present in its derived form, never a badge on every line — each row's
        # own colour (`theme.rung_color`) is the per-row signal.
        has_l4 = any(row.rung.value == "L4" for row in window.rows)
        ttk.Label(
            content,
            text="showing derived · L4 present" if has_l4 else "showing",
            style="Subheading.TLabel",
        ).pack(anchor="w", pady=(0, 12))

        listbox = tk.Listbox(content, height=12)
        theme.style_listbox(listbox)
        listbox.pack(fill="both", expand=True)
        rows = window.rows
        for row in rows:
            listbox.insert("end", f"[{row.rung.value}]  {row.text}")
            listbox.itemconfig("end", foreground=theme.rung_color(row.rung))

        def on_open(_event: object = None) -> None:
            selection = listbox.curselection()
            if selection:
                show_detail(rows[selection[0]].ref, back=show_list)

        listbox.bind("<Double-Button-1>", on_open)
        ttk.Button(content, text="Open", command=on_open).pack(anchor="w", pady=(12, 0))
        ttk.Button(
            content, text="Close", style="Secondary.TButton", command=show_cover,
        ).pack(anchor="w", pady=(4, 0))

    def show_detail(ref, back) -> None:
        # `back` is the pane this detail was opened from — the custody list or the
        # queue — so "Back" returns where the operator came from rather than always
        # the list (the ledger's two-pane view fixed the same assumption).
        served = window.open_detail(ref)
        clear()
        ttk.Label(content, text=f"{ref[1]}", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(content, text=served.rung.value, style="Muted.TLabel").pack(anchor="w", pady=(0, 12))
        body = (
            str(served.value)
            if served.disposition is Disposition.RENDER
            else "This record is sealed and is not shown here."
        )
        ttk.Label(content, text=body, wraplength=520, justify="left").pack(anchor="w")
        # A non-blocking advisory: if the stored content is shaped for a higher
        # rung than it was declared at (an SSN in an L4 note), say so where the
        # operator is already looking. A muted note, never a dialog and never a
        # block — the record is open regardless. Silence draws nothing (no "clean"
        # line): an empty result is *no pattern matched*, not a safety claim.
        for line in advisories.advisory_lines(store, ref):
            ttk.Label(
                content, text=line, style="Muted.TLabel", wraplength=520, justify="left"
            ).pack(anchor="w", pady=(8, 0))
        ttk.Button(
            content, text="Back", style="Secondary.TButton", command=back,
        ).pack(anchor="w", pady=(24, 0))

    show_cover()
    root.mainloop()
    return 0
