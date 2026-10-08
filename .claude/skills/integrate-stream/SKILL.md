---
name: integrate-stream
description: Feed the H264 core from a new video source — a new client under clients/, or a new service, protocol, container or device in an existing one. Characterise the stream against the core's envelope, pick what to reuse from clients/common/ and the library, write records the way the interface requires, then gate and document the result. Use when asked to "play X through the core", add a streaming service or client, feed the ring from a program, or work out why a source's stream will not play.
---

# Feeding the core from a new source

The job: get video from somewhere the core does not reach yet (a service, a protocol, a
container, a device) onto the screen through the HPS interface. This skill gives the order of
the decisions, what to reuse, and the mistakes this project has already paid for. **It does not
restate the interface.** The manual's `site/content/integrating/*.md` pages are normative (frozen
at 1.0) and `hps/include/h264ring.h` is the API. Read them; do not work from memory or from this
file.

## Read first

| What | Where |
|---|---|
| The model: what the program does, what the core does | `site/content/integrating/overview.md` |
| Records, flags, the session, seeking, time stamps, errors | `integrating/interface.md` |
| Every library call, CAVLC, threads, the lock | `integrating/library.md`, `hps/include/h264ring.h` |
| Loading the core, input, the menu's actions | `integrating/launch.md` |
| PCM, pacing, low latency | `integrating/audio.md` |
| Your own screens on the overlay | `integrating/overlay.md` |
| Video that is not H.264 | `integrating/pictures.md` |
| The smallest complete feeder | `hps/feeder/h264play.c` |

Then pick the **nearest existing client** and read its design note before designing anything:

| The source is like... | Start from | Note |
|---|---|---|
| a live, interactive stream (game, desktop) over RTP | `clients/moonlight/` | `docs/moonlight.md` |
| a server that can transcode for you (HTTP, a URL) | `clients/jellyfin/` | `docs/jellyfin.md` |
| files: MKV / MP4 / TS, any codec | `clients/player/` | `docs/player.md` |
| a device that produces frames (camera, capture) | `clients/uvc/` | `docs/uvc.md` |

## 1. Characterise the stream before writing code

Get a real sample (generate one or cut it from `${H264_REFS_DIR:-~/h264-refs}`; **never commit
other people's media**). `ffprobe` cannot show entropy coding or MBAFF. Read the headers:

```bash
ffprobe -v error -show_streams -select_streams v:0 SAMPLE
ffmpeg -hide_banner -i SAMPLE -c:v copy -bsf:v trace_headers -frames:v 1 -f null - 2>&1 \
  | grep -E 'profile_idc|chroma_format_idc|bit_depth|frame_mbs_only|mb_adaptive|entropy_coding|pic_width|pic_height'
```

Then decide, in this order:

| The stream is | So |
|---|---|
| H.264 Main / High, CABAC, 8-bit 4:2:0, frames or PAFF, ≤ `caps.max_mbs` (3,600), ≤ `caps.mb_rate` (108,000 MB/s) | plays in real time. |
| as above but CAVLC (Baseline, x264 `ultrafast`) | the library's write call rewrites it. **It costs ~11-12 % of an A9 core per Mbit/s at 480p60**, so it plays in real time only up to ~4-5 Mbit/s. If the source can send CABAC, ask it to. |
| above `mb_rate` | plays correctly but late (counted). Ask the source for less. |
| MBAFF, 4:2:2 / 4:4:4, 10-bit, monochrome, > 3,600 MBs | **refused.** Ask the source for a transcode, or decode it on the ARM (next row). |
| not H.264 | decode it on the ARM and send PICTURE records (`clients/common/vdec.c`). **SD and ≤ 30 frames/s only**, because the ARM's store copy and decoder are the limit. |

- **Check before the ring, refuse by name.** `clients/common/h264check.c` gives the verdict
  from the first SPS / PPS, against `h264ring_caps()`. A picture over `max_mbs` is *not* refused
  at its SPS: its slices are dropped silently but for a counter. Never send a stream you
  already know will fail.
- **Live or paced?** A game, a desktop or a camera is LOW_LATENCY (and GRAPHICS when it is
  rendered). A film or a transcode is paced by PTS, with audio.
- **The ARM budget is one A9 core.** Main holds the other. Demux, decryption, FEC, audio
  decode, a CAVLC rewrite and your UI all share it. Estimate early; measure on the rig with
  `taskset -c 0` (step 5).

## 2. Reuse before writing

`clients/common/` already solves the MiSTer side. Read the header before writing your own:

| Module | Gives you |
|---|---|
| `core.c` | launch, attach, a session for the program's life, the heartbeat (another core loaded = gone), a menu Reset's `-ENOTCONN` re-opened, `core_new_stream()` = flush + re-based counters, the refusal named |
| `h264check.c` | the SPS / PPS verdict above |
| `player.c` | libavformat demux: avcC (MP4 / MKV) → Annex-B with `h264_mp4toannexb`, audio → 48 kHz s16 stereo, PTS, seeks |
| `input.c` | the input region: pads, keys, menu open / close, the menu's actions, pad / key → actions (Back + Start is stop) |
| `ui.c` | text and panels on the overlay, sized to the raster (`/dev/fb0` is Main's HDMI-mode size), title-safe on SD rasters, the screensaver |
| `subs.c` | text subtitles (SRT, ASS dialogue) |
| `vdec.c` | other codecs → PICTURE records, the SD budget, refusals as words |

Build in the shared image (`mister-h264-clients:deps3`, `clients/common/docker/`) with a
`build.sh` copied from `clients/player/build.sh`. Output is a static ARM binary (static but for
glibc) and `build/dist/` laid out as the SD card (`Scripts/<name>.sh` + `<name>/`). Copy the
launcher pattern from `clients/player/mister/h264player.sh`: detached with `setsid`, a log
beside the binary, back to the menu on exit **only if `/tmp/CORENAME` is still H264**.

## 3. Writing records

Each of these rules has cost a debugging round in this project. The manual pages hold the
details:

- **One complete Annex-B access unit per VIDEO_AU record**, with start codes. A stream's first IDR
  (a session start, a flush, a DISCONTINUITY) must be preceded by its SPS / PPS. Containers do not hand you that shape: avcC (MP4 / MKV) needs
  `h264_mp4toannexb`, a TS PES can split or merge access units, RTP needs depacketising
  (FU-A / STAP-A). `h264ring_split_annexb()` splits a buffer at access-unit boundaries.
- **The PTS is 90 kHz presentation time**, one per access unit, never a decode-order counter
  (B frames). Use `-1` when there is none. A lone stamp more than 8 ms and at most 0.5 s off the
  timeline is disbelieved once (`disp_lone`).
- **LOW_LATENCY, GRAPHICS and the colour code are taken from each stream's first access unit.**
  Set them on every one. Leave the colour code at 0 (auto) unless the source mislabels it (a
  server that tags every transcode BT.709).
- **To seek or switch now, use `h264ring_flush()`** (~15-40 ms), then write from an IDR.
  DISCONTINUITY waits for everything queued ahead of it, which can be seconds, so use it only
  for the next item of a playlist. After END_OF_STREAM the library adds DISCONTINUITY by itself.
- **Audio:** PCM 48 kHz s16le stereo, records of ≥ 5 ms, each stamped with its *first* frame's
  PTS. Write it interleaved with the video, as a demuxer does. More than 256 unplayed records
  stalls the video behind them.
- **One writer.** The handle has no lock. With video and audio on separate threads, serialise
  every call with your own mutex, and wait on a full ring with `h264ring_try_*` + a sleep
  **outside** the mutex.
- **Paced CAVLC:** call `h264ring_prepare_au()` before the due time. Otherwise an IDR's
  ~25 ms rewrite lands inside the write and the picture arrives late.
- **Bound each loop step's work** (`docs/player.md`: 10 ms a step). A loop that rewrites or
  decodes until the ring is full starves the pad (key delay 1.43 s before that fix).
- **Read the results:** `-ENOTCONN` means the menu's Reset (start a session, resend from an IDR).
  `-EPROTO` means the core refused a record (`h264ring_status` + `h264ring_error_name`).
  `-EOPNOTSUPP` / `-EBADMSG` come from the CAVLC rewrite and are *not* in the status block, so
  log `h264ring_rewrite_why()` yourself. A still heartbeat means the core is gone.
- **Never write the words yourself** and never `memcpy` into the mapping (unaligned uncached
  stores fault). The library covers alignment, the cold-boot write index and versions.

The rest of the program, all in `integrating/launch.md` / `overlay.md` / `interface.md`:

- Main grabs every input device: read the input region, never `/dev/input`. On "menu opened",
  release everything you forwarded. Take the two menu actions (Send Home, Program menu)
  even while ignoring input.
- A settings request stays in word 35 and is applied again at every later session, including
  another program's. Call `h264ring_clear_settings()` on exit.
- Rumble: the keepalive is the program's (`h264ring_rumble_keepalive()` at least once a second).
- A 1280x720 transcode only when `h264ring_video_out()` is NATIVE and `caps.native_h` ≥ 720.
  Otherwise the picture is fitted to an SD raster anyway.

**If the source needs something the interface does not have, stop.** That is interface work: it
is designed in `docs/architecture.md` first, a 1.x minor may only add (`interface.md`
"Versions"), and it changes the `integrating/` pages in the same change. Discuss it with the
maintainer before building.

## 4. Size to the spec, not the sample

A capture shows what is common, not what is possible. Size every buffer and table that holds a
stream structure to the format's maximum (an access unit up to 4 MB, 32 SPS / 256 PPS ids, the
container's own limits). Make a bound that is hit visible: a log line, a refusal, a counter.
`CLAUDE.md` "Design to the spec maximum".

## 5. Gates

**Host test, `clients/<name>/tests/run_test.sh` and `--red`.** It must be able to fail
(`bench/h264/README.md`; `clients/player/tests/README.md` is the model):

- the client's own code built with `-DCLIENT_TEST` against a **fake core** on a thread (copy
  `clients/player/tests/test_player.c`), driven by a script (a pad, a fake server: see
  `clients/jellyfin/tests/fake_server.py`);
- scored by an **independent oracle**: `tools/ring_model.py`'s consumer walks what each session
  received, and the references come from the ffmpeg CLI, never from the client's code;
- `mutations.py`: each mutation applied to a *copy* and compiled from the copy, **each caught by
  its own check**;
- the old binary deleted before every build, and GREEN only on the positive `ALL GREEN` markers
  of both the test and the scorer.

**On the rig** (the `hil-testing` skill; the rig is shared: `state` first, `restore` after):

1. `tools/mister.py feed` the same stream through `h264play` first. If it fails there, the
   problem is the stream or the core, not your client.
2. Run the client and read the status block (`mister.py stat`): errors, refusals, late,
   `fetch_late`, the audio's underruns and A/V offset.
3. **Compare the ARM build's output with the host build's** (record what each wrote).
   x86 and ARM gcc evaluate arguments in different orders, and only the rig shows it
   (`CLAUDE.md`, fj#20).
4. Measure the CPU pinned to the free core (`taskset -c 0`), at the source's highest rate.
5. **Analog first:** check 480i too. Ask the maintainer for the RetroTINK / CRT round.

## 6. Wire it in and write it down

- **CI:** add the build step, the binary to the size list and the `build/dist` to the tar in
  `.github/workflows/clients.yml`. `package.yml` takes `clients-dist` from there.
- **The manual** (`CLAUDE.md` "Keep the user-facing docs current"): `using/<name>.md` + its
  `mkdocs.yml` nav line, the list in `getting-started/install.md`, every new message in
  `using/on-screen-messages.md` **and** `reference/troubleshooting.md`, buttons in
  `using/controls.md`, formats in `reference/compatibility.md`, upstream code credited in
  `about/acknowledgements.md` (and `NOTICE`). No support promises (`CLAUDE.md` "Support
  stance"). Then `.venv/bin/python3 tools/docs_check.py` and `.venv/bin/mkdocs build --strict`.
- **Engineering notes:** `docs/<name>.md` (the decisions, the measurements, the limits, what was
  rejected), `docs/roadmap.md`, `CLAUDE.md`'s status block, and `docs/history.md` for the rig
  results.
- **Licences:** `hps/` is MIT; the clients are GPL-3.0-or-later (SPDX line). Check upstream code
  against both.
- **Nothing personal:** no server names, IPs, accounts, tokens or paths in code, fixtures, tests
  or docs. Use placeholders (`root@<mister-ip>`, `http://<server>:8096`).
- A client-only branch changes no RTL, so it needs no fit (`docs/jellyfin.md`: "ARM-only (no fit)").
