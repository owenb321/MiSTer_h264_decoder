---
name: hil-testing
description: Drive the maintainer's real MiSTer over ssh to test the H264 core — flash a build, load the core, press keys, pull back a screenshot. Use whenever a question would otherwise be answered by asking the user to test something on hardware, or when a change needs confirming on the board.
---

# Hardware-in-the-loop testing

The rig is reachable over ssh and can be driven end to end: flash, load the core, press
keys, screenshot. **Prefer this to asking the user to test something.** Design notes:
`docs/hil_harness.md`. This skill is the operating manual.

⚠ **The rig is the maintainer's, and it is shared** with MiSTer_DVD and MiSTer_UMD_Video
sessions on the same workstation. Run `state` first and say what you found before
touching it. If another core is loaded, find out whether a session is driving it (`ps`
for `mister.py`, walk to the owning claude process, ask THAT session) and wait for a
go. A disturbed run of theirs is void, not salvageable. `restore` when done.

## Setup (once per session)

```bash
cat tools/.mister_host          # e.g. root@<mister-ip>  (gitignored, never commit it)
tools/mister.py state           # core loaded, running Main, key daemon, deployed build
```

`tools/mister.py deploy --rbf releases/H264_x.rbf` flashes a core; `--agent` (re)starts the
key daemon.

**Put the rig back when you are done:** `tools/mister.py restore` (harness files gone,
saved settings restored, the menu reloaded if our core is running).

## The tools

| Command | What it does |
|---|---|
| `mister.py launch --opt "Name=Value"` | write settings and load the core via MGL (no image: the core has no file slot) |
| `mister.py key osd` | press keys (`osd` always; more only if an `h264/kbd_map.sv` ever exists) |
| `mister.py shot -o FILE` | screenshot of the core's raw raster |
| `mister.py shot --scaled -o FILE` | the scaler's output: the width shows the aspect the core reports |
| `mister.py options` | every OSD option, derived from the RTL |
| `mister.py shell -- <cmd>` | run a command on the target |

**Feeding a stream** (Phase 3): build the ARM binaries (`USE_DOCKER=1 hps/build_arm.sh`),
make the clips (`tools/p3/make_clips.sh DIR`: synthetic, never others' media), then

| Command | What it does |
|---|---|
| `mister.py deploy --bin [--clip FILE]...` | `h264play`, `h264stat` (and clips) -> `/media/fat/h264hil/` |
| `mister.py feed CLIP [--bg] [-- h264play options]` | plays through the HPS interface; loads the core by MGL; prints the final status JSON |
| `mister.py stat [--count N --watch S]` | the status block (`h264stat --json`): state, errors, counters, the judder pair |

`restore` kills a running feeder and removes `/media/fat/h264hil/`. The status block IS the
telemetry: no HIL Main (decided 2026-09-27). `docs/hil_harness.md` "Feeding a stream".

## Traps that have cost real time (inherited, same platform)

- **Screenshots are the CORE's raster, upstream of the OSD.** You cannot see the OSD; set
  options by writing the settings file (`launch --opt`), not by navigating menus.
- **HIL latency is part of the instrument.** ssh-paced presses land 1-2 s apart; a timing
  window under ~3 s must be sequenced ON the target in one session.
- **A screenshot burst resolves ~1 s per frame.** Read a missing frame as missing.
- **An interlaced raster's screenshot is the scaler's WOVEN buffer** (both `shot` and
  `shot --scaled`): HDMI Deinterlace = Bob is applied only as ascal reads it out, so a
  screenshot combs whatever Bob is set to (`docs/history.md` §7). Judge Bob, csync and the
  analog pins on the RetroTINK -> capture card (ask the maintainer to plug it in).
- **The MiSTer has no `pkill`**; use `kill_exact()`.
- **Never overwrite a running Main binary** (it reboots the box). This harness never
  touches the Main.
- **`launch` overwrites the user's saved settings**; it backs them up once; `restore`.
- **Run the OLD build through the same script as the control arm** when a defect is
  intermittent, and change ONE thing per hardware round.
- **A step that never reached the state was not measured.** Wait for a readiness signal
  before acting; a clean measurement of the wrong state reads like "did not reproduce".
- **A freeze at a fixed early point that the PREVIOUS build shares is the rig**, not the
  core: an HPS DDR3 port left hung (UMD, 2026-09-26). This core carries UMD's
  `f2sdram_safe_terminator` fix; a stock-terminator core loaded before it can still leave
  the port hung. A reboot clears it -- the maintainer's call.
- **Ask "is the PICTURE frozen or is the MACHINE frozen?"** The idle marker moves every
  frame precisely so one pair of shots answers it.

## Before believing a finding

1. Does it **reproduce**?
2. Would it change if you changed something **unrelated to the core** (settle time, stream)?
3. Is the instrument **validated for the thing being claimed**?
4. Is the control arm **capable of failing**? Prove it with a deliberate mutation.
