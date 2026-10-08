---
name: docs-sweep
description: Audit README.md and the site/ user manual against the changes in a diff range, update whatever went stale, and report what changed. Use before merging a feature branch, before cutting a release, or whenever asked to check whether the docs match the code.
---

# Sweeping the user docs against a change

The manual is built as a check on every merge and **deployed only on a release**, from
that release's tagged commit. So a stale page merged to `main` does not go live at once,
but it is exactly what the next release ships. This sweep is what stops that.

This core has two audiences, and the manual serves both: **users** (install, what the
screen shows, settings, troubleshooting) and **integrators** (developers of HPS programs
that feed the core: the interface, its versions, its limits). A change to the interface
is user-visible to the second group.

Default range is `main...HEAD`. A release sweep passes `<prev_tag>..HEAD`.

## 1. Mechanical checks first

```bash
.venv/bin/python3 tools/docs_check.py     # OSD options/buttons/extensions <-> manual parity
.venv/bin/mkdocs build --strict           # broken cross-link = failure
grep -on "](#[a-z0-9-]*)" README.md       # README self-anchors, checked by nothing else
```

## 2. Signal pass

`git diff --stat <range>`, then map what changed to what must be reviewed:

| Changed | Review |
|---|---|
| `h264/emu.sv` CONF_STR | `using/settings.md` (normative), `using/controls.md`, `getting-started/loading.md` |
| an on-screen message string (HUD, idle screen) | `using/on-screen-messages.md` **and** `reference/troubleshooting.md` |
| a decoder capability or refusal (`h264/dec/`) | `reference/compatibility.md`, `video/output.md`; README if headline |
| the HPS interface (ring layout, records, control block, `hps/`) | `integrating/*.md` (normative for integrators); bump the interface version if the layout changed |
| an audio path or codec | `integrating/audio.md`, `reference/compatibility.md` |
| `build_release.sh`, `tools/package_release.sh` | `about/building.md`, `getting-started/install.md` |
| video output paths (`sync_gen`, csync, aspect) | `video/output.md`, `video/analog-crt.md` |
| `README.md` changed but `site/content/` did not, or the reverse | **drift flag** |
| `docs/*.md` changed | harvest check: did user-facing material land in an engineering note? |

## 3. Semantic pass

Read the range's commit messages. For each user-visible claim, ask **which page currently
states the old truth**. The highest-value case is a **removed limitation**: the
compatibility page and the README's headline bullets both assert things a branch may have
just fixed. Also: a new message needs rows on two pages; a changed default is stated on
the settings page and often repeated where the feature is explained; a feature that lands
should lose its "not yet implemented" admonition.

## 4. Apply, verify, report

Make the edits, re-run step 1. Report a table of page / signal / verdict (`current`,
`updated`, `needs a decision`). Apply what is unambiguous; **stop and ask** on judgement
calls rather than editing on a guess.
