---
name: release
description: Cut and publish a release of the MiSTer H264 core — gather notes from every PR merged since the previous release, land the one release commit that sets CORE_VERSION and reconciles the manual, build the timing-clean .rbf, and publish it (a GitHub release draft, packaged by the package workflow). Use when the user asks to cut, make, or publish a release.
---

# Cutting a release

One artefact ships: the compressed `.rbf` (plus its `.rbf.json` manifest and the install
zip from `tools/package_release.sh`, which also carries the HPS clients -- Moonlight, Jellyfin,
the video player, the camera viewer -- built by `package.yml` through `clients.yml` from the
release commit). Run the clients' host tests from the release commit first
(`clients/*/tests/run_test.sh --red`, `hps`'s `make test`). The HPS client library (`hps/`) is
versioned by the interface version it speaks, and the release notes state which interface
version this core implements.

## The one-commit invariant

> A bare semver lives in **exactly one commit per release** — the release commit. Any
> build whose OSD shows `v0.1.0` came from that commit and no other.

- `CORE_VERSION` in `h264/emu.sv` carries `dev-<slug>` on branches and whatever the last
  merge left on `main`. The release commit sets `v<semver>`; nothing resets it after.
  `build_release.sh` refuses a `dev-` string on `--release` and a semver on a dev build.
- Tag = `v<semver>`; zip = `MiSTer_h264_decoder_v<semver>.zip`.
- **The `.rbf` stays `H264_YYYYMMDD.rbf` — date only, never a version**: MiSTer's core
  browser and update scripts parse the date out of the filename.
- `CORE_VERSION` and `BUILD_DATE` are inside CONF_STR = inside the netlist, so the version
  edit rides in ONE commit with the docs sweep and the release needs exactly one compile.

## Preconditions

On `main`, clean tree, every intended branch merged (`/merge`). The manual matches what
ships: `.venv/bin/python3 tools/docs_check.py && .venv/bin/mkdocs build --strict`. Decide
the number against the WHOLE unreleased delta (patch / minor / major per `CLAUDE.md`).
An interface change that breaks existing HPS programs is at least a minor bump before
1.0 and a major one after, and the notes say so first.

## Steps

1. **Gather the notes.** Every PR merged since the last release, grouped into human
   sentences; run `docs-sweep` over `<prev_tag>..HEAD` and fix stale pages.
   `gh pr list --state merged --base main --json number,title,mergedAt` and
   `git log <prev_tag>..HEAD --merges --format='%h %s'`. (The first release, 1.0, has no
   previous tag on GitHub: its notes cover the whole Forgejo era, PRs fj#1-fj#45, from
   `docs/roadmap.md` and `docs/history.md`.)
2. **Land ONE release commit** on `main`: `CORE_VERSION` → `"v<semver>"`,
   `extra.released_version` in `mkdocs.yml` → `<semver>`, the "Current as of" line in
   `site/content/reference/compatibility.md`, the docs-sweep edits. Verify the two docs
   checks. Do NOT push until the build is tested (no release-signalling pushes).
3. **Build the core (timing-clean):**
   ```bash
   USE_DOCKER=1 ./build_release.sh --release --compile   # -> releases/H264_YYYYMMDD.rbf + .json
   ```
   `--release` refuses a marginal netlist; re-roll with `tools/seed_sweep.sh` if needed.
   Never ship a `_MARGINAL_` build.
4. **Record the fit** in `H264.qsf`'s SEED LEDGER (`jq . releases/H264_YYYYMMDD.rbf.json`
   has every number) and `docs/history.md`.
5. **Smoke-test on hardware** (`hil-testing`): flash, boot, confirm the OSD About line
   reads `H264 v<semver> <yymmdd>` and, once the input path exists, that the reference
   feeder plays a stream.
6. **Publish.**
   Push `main`, then `tools/publish_draft.sh v<semver> --notes <scratch>/relnotes.md` creates
   the draft and dispatches `.github/workflows/package.yml`; smoke-test the draft, then
   `gh release edit v<semver> --draft=false`. Publishing deploys the manual (`docs.yml`;
   Pages needs the repository public). A later doc fix deploys from a `docs-v<semver>` branch
   cut off the tag, never from `main`.
   `package.yml` builds the HPS clients itself (`clients.yml`, from the manifest's commit, in
   images built from the repository) and packages them: the clients in the zip are the release
   commit's. Build them locally too, for the hardware smoke test (step 5).

⛔ No version-reset step after publishing. The next feature branch sets its own
`dev-<slug>` in its first commit.
