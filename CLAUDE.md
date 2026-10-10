# MiSTer H264 core — Claude Code Context

## Project overview

An **H.264 decode and presentation accelerator for HPS-side programs on the MiSTer**
(DE10-Nano / Cyclone V). A Linux program on the ARM (a Moonlight client, a Plex /
Jellyfin client, a file player) does networking, demux, decryption and FEC and hands the
core H.264 access units and audio with presentation times through a ring in DDR3; the
fabric decodes, presents audio and video against one clock, and scans out on HDMI and
analog. Nothing decoded returns to the ARM. Target (D1, decided 2026-09-27,
re-expressed 2026-09-28 as a service-neutral budget): **High profile, any picture up to
1,620 macroblocks (any size / aspect, cropped), real time up to 97,200 macroblocks a
second (854x480 at 60 frames/s; covers 640x480p60 and 720x480p60), at the bitrate of a
Moonlight session requesting 10 Mbit/s**, every picture fitted to the output raster
(480i analog first). Not tied to one service: Moonlight, Jellyfin / Plex transcodes,
Chiaki all arrive in these terms (`docs/roadmap.md` D1). Higher rates decode correctly
and fall behind visibly, never silently. **Widened 2026-10-02 (the maintainer, roadmap Phase
5c): Level 3.1's MaxFS -- any picture up to 3,600 macroblocks (1280x720), designed for 108,000
a second (720p30 / 480p60)** (since Phase 5c part 2, PR fj#29: real time for game streams, films and
transcodes up to ~8 Mbit/s -- x264 720p30 8 Mbit/s 1.13x, 720p24 1.27x on the rig; still fitted to
the 720-wide rasters -- an HD raster is part 3).

**Analog first** (the maintainer, 2026-09-28): many MiSTer users want only analog
output, typically interlaced (composite / component, 15 kHz). HDMI streaming is trivial
for modern devices; analog is what sets this project apart, so **the 480i raster + csync
is a main goal** (`docs/roadmap.md` "Analog first"). Weigh display decisions for the
15 kHz interlaced case first.

**Forked, not shared** (the maintainer, 2026-09-27): the decoder, display path, framework
edits, gates and process come from **MiSTer_UMD_Video** (`../MiSTer_UMD_Video`), which
built them for UMD discs (Main, Level 3.0, ≤ 30 frames/s), and through it from
MiSTer_DVD. This repository owns its copy and grows it; fixes are ported by hand both
ways and recorded in `docs/harvest.md` "Fixes exchanged".

`docs/roadmap.md` is the canonical plan, with the **decisions** (D1 profile / throughput
scope, D2 where audio is decoded -- **on the ARM, decided 2026-09-29: the core presents PCM**,
D3 a developer input path, D4 the interface details, D5 the name: **"H264" kept, decided 2026-10-06** -- generic, not tied to a service). `docs/architecture.md` holds the draft HPS interface.

**Current status: P0 scaffold ✅ MERGED (PR fj#1), ✅ HW-CONFIRMED on HDMI. P1 (measure the
gap) ✅ MERGED (PR fj#2): `docs/p1_measurements.md`; D1 decided 2026-09-27: High profile in
the fabric** (a stock Sunshine host always sends it, the 8x8 tools on ~3-4 % of coded
macroblocks), **real time at 10 Mbit/s requested** (≤ ~935 cycles a macroblock in the
cosim; 1,186 on Main today). **P2 (the fork) ✅ MERGED (PR fj#3, 2026-09-27):**
UMD `cc595c6` harvested -- the decoder in `h264/dec/`, the display path in `h264/`, 19
runners in `bench/h264/`, the models in `tools/` (`docs/harvest.md`); every disc fixture
replaced by x264 / H.264.1 streams; wired in `emu` behind the **ioctl stand-in** (hps_io's
download path, no OSD slot, so the fit keeps the decoder: `docs/architecture.md`), the DPB
on ram1 (`ddr_mux2` A; B tied off for Phase 3's ring), the display on ram2; CONF_STR gains
Deinterlace. UMD's four spec deviations re-decided (kept) and the 1,620-MB picture bound
added (`docs/spec_hardening.md`). No on-screen HUD (decided: telemetry at Phase 3).
Fit 2026-09-27: SEED 1, **23,331 ALM (56 %), 230 M10K, 69 DSP, clk_dec 91.43 / 88.67**,
every gate PASS (`H264_p2harvest_20260927_1801.rbf`). **P3 (the HPS interface) ✅ MERGED (PR fj#4), ✅ HW-CONFIRMED:** D3 / D4 decided (`docs/architecture.md` "The HPS interface, v0.1": an
8 MB ring and a control block at `0x3140_0000`, a nonce session, polling, the status block
as the telemetry, DISCONTINUITY = the stream reset); `h264/ring_rd.sv` + `ring_stat.sv` on
ram1's master B; `hps/` (the client library, `h264play`, `h264stat`); **first pictures on the
rig through the interface** (`docs/history.md` §3); early output under
`max_num_reorder_frames` and a LOW_LATENCY display; the ioctl stand-in removed. 480p60 is
decoded at ~44 frames/s on the rig at P3 (real time since P5b's 96.43 MHz clock). **P5a (High profile) ✅ MERGED
(PR fj#5), ✅ HW-CONFIRMED** (`docs/high_profile.md`): the 8x8 transform, Intra_8x8, the 8x8 CABAC
syntax and scaling matrices (every SPS / PPS set stored as coded) through the front end,
the units and the reconstruction; every runner GREEN and RED on x264 High and the FRExt
CIF streams, pixel-exact. Monochrome stays refused (`REF_CHROMA`; decided 2026-09-28).
Fit SEED 1, clk_dec 87.60 / 87.37, 27,318 ALM, 315 M10K (`H264_p5high_20260928_0459.rbf`);
✅ HW-CONFIRMED: the real 10 and 3 Mbit/s Sunshine captures decode on the rig, every
picture, errors 0 (`docs/history.md` §4); the real captures run 986 cycles a macroblock in
the cosim at 10 Mbit/s. **P5b part 1 (throughput) ✅ MERGED (PR fj#6), ✅ HW-CONFIRMED:** clk_dec
**96.43 MHz** (fit 104.69 / 101.46 at the 101.4 gate; the retime playbook in
`docs/hw_budget_and_lessons.md` §5), the deblock pre-pass, the residual overlap, the
streaming start; **720x480p60 real time ✅ HW-CONFIRMED** (the 81,000 macroblocks/s gate:
`sun_high_8M` 300 / 300, late 0, errors 0, ~1.04x on the rig; `docs/history.md` §5).
**P5b part 2 ✅ MERGED (PR fj#7), ✅ HW-CONFIRMED:** two interpolation lanes, the fetch
run-ahead, the writeback overlapped; fit 102.74 / 102.90; **854x480p60 real time on the rig
at 8 Mbit/s** (97,200 macroblocks/s, ~1 % margin; `docs/history.md` §6). **P6 part 1 (analog
first) ✅ MERGED (PR fj#8), ✅ HW-CONFIRMED:** the 480i raster (MiSTer_DVD's N64 model) with SMPTE
composite sync and Video Output (Auto / Interlaced / Progressive), field selection (a refresh
is a field), and every picture fitted to the raster -- `disp_fit` + the fitting
`disp_reader` (decimated rows, tagged slots, 2-tap blends), Analog Aspect (both modes),
HDMI's exact aspect, the interface 0.2 (word 30: the fit) -- `docs/analog.md`; on a
RetroTINK 1716x525i at 15.73 kHz, field order measured correct; fit 103.96 / 103.56, 30,471
ALM (73 %). **P6 part 2 ✅ MERGED (PR fj#9), ✅ HW-CONFIRMED 2026-09-29:** Anti-Twitter
(Off by default, 480i-only: sliding luma boxes in the fetch, `analog.md` §9), `Refresh Rate:
Auto / 59.94 / 60 / 50 Hz` (Auto from the stream's VUI rate; 60.00 exact by line length;
576p / 576i PAL; `disp_ctl`'s events from a refresh-grid counter, §10), interface 0.3 (word 30
reports the raster). On the rig (`history.md` §9): 60.00 / 50 Hz measured, the LL skips gone at
60.00, PAL clean, anti-twitter applied; on the RetroTINK V 60.00 / 50.00 Hz locked, 576i field order
correct, the (1, 2, 1) through the pins; on a CRT (S-Video 480i) anti-twitter a clear
improvement on every test clip, controls unaffected. **Interface 0.4 ✅ MERGED (PR fj#11), ✅ HW-CONFIRMED:** the GRAPHICS content flag
(Anti-Twitter Auto / Off / On), word 27's OSD mirror, and the settings request (program word 35:
a program changes the core's OSD settings through hps_io's status_set; Main adopts them, does
not save them -- `architecture.md`, `history.md` §10). **Phase 4 audio ✅ MERGED (PR fj#12), ✅ HW-CONFIRMED (interface 0.5)** -- settled
2026-09-29 (`architecture.md` "Audio (Phase 4)"): PCM 48 kHz s16 stereo from the ARM;
**the ring IS the audio's buffer** (the maintainer's decision after the harvest showed
MiSTer_DVD's DDR3 audio path was retired): the parser queues a descriptor per AUDIO record,
`h264/aud_play.sv` fetches the samples through `ring_rd`'s engine a few ms before they play
and holds the published read index behind them; paced against the STC (DVD's clk_sys tick
and gate at the FIFO's exit, a per-record 10 ms re-time, the audio anchor when no picture
starts the clock) or, on LOW_LATENCY, a queue target with counted single-frame slips; word
34 pause + ATTEN (+ UMD P6b3i's `disp_frz`); status words 40-47 (a fifth burst before
seq_tail). Built and benched (GREEN and `--red`), fit SEED 7 (102.80 / 102.07,
`H264_p4audio_20260929_2240.rbf`), **on the rig** (`history.md` §11: every record at its PTS,
pause / volume / audio only / low latency; the capture chain's absolute calibration deferred
by the maintainer: the Hagibis declares no audio to a PC). **The Moonlight client ✅ MERGED (PR fj#13), ✅ HW-CONFIRMED 2026-09-30, watch only**
(`clients/moonlight/`, `docs/moonlight.md`): moonlight-embedded + a `mister` backend, a Scripts-menu
launcher, the automatic size, a static ARM binary; host test `clients/moonlight/tests/run_test.sh
--red`; fit SEED 7, clk_dec 108.12 / 104.32. **Main holds every input device while a core runs**
(EVIOCGRAB), so **Moonlight input through the core (interface 0.6) ✅ MERGED (PR fj#14), ✅
HW-CONFIRMED 2026-09-30**: designed with the maintainer 2026-09-29 (`docs/moonlight.md` §7 M7-M10,
`docs/architecture.md` "Input (interface 0.6)": words 48-71), built and GREEN in simulation
(`bench/h264/run_ring_in.sh --red`, the client's `tests/run_test.sh --red`), fit SEED 7 104.07 /
104.08 (`H264_mlinput_20260930_0429.rbf`), keys / OSD / mouse verified on the rig through Main
(`docs/history.md` §13); ✅ **HW-CONFIRMED 2026-09-30** with the maintainer (keys, mouse, an Xbox
pad and both quit combos through a stream into the PC). UMD's lone-PTS rules A and B
(PR fj#25 + fj#26) ✅ MERGED (PR fj#15) (`docs/display.md` §10, interface 0.7's `disp_lone`):
`run_disp_sched.sh --red` ALL GREEN (32 mutations), fit SEED 7 105.49 / 106.0, smoke-tested on the
rig (`docs/history.md` §14). **Reaching the program from the pad ✅ MERGED (PR fj#16), ✅ HW-CONFIRMED:** the OSD's two actions ("Send Home to the program", "Program menu": `R[17]` /
`R[18]` -> input event type 3, interface 0.8; `docs/architecture.md` "The OSD's actions (0.8)") and
the client's Back + Start chord (held 1 s -> the host's Guide; `docs/moonlight.md` M11 / M12, "As
built"); GREEN and `--red` in simulation and the client's host test; fit SEED 7 109.59 / 108.46 (`H264_padhome_20260930_1641.rbf`); on the rig both actions arrive before the OSD's closing
(`docs/history.md` §15); ✅ HW-CONFIRMED 2026-09-30 with the maintainer (Send Home and the chord
open the host's Guide). **Phase 6b, the overlay plane ✅ MERGED (PR fj#21) (interface 0.9), ✅ HW-CONFIRMED 2026-10-01 (the
RetroTINK, a CRT and an HDMI capture, with the maintainer)** (decided 2026-09-30: the identity mapping, centred; `1555` / `4444` / `8888`
straight alpha -- `docs/architecture.md` "The overlay plane"): the program draws into `/dev/fb0`,
describes its page in program words 72-79 (a generation pair), and `h264/ovl_plane.sv` reads it
on `ram2` (a second `ddr_mux2`) and composites it on the core's raster (`ovl_blend.sv`; the output
stage LAT 6), anti-twittered at 480i, shown only during a session; status words 46-47; `hps/`
`h264ring_overlay_*`, `h264ring_fb_map` (which quiets fbcon's cursor -- found writing the region
on the rig); `h264play --overlay`. GREEN and `--red`: `run_ovl_plane.sh` (O1-O32),
`run_scaffold.sh` (W60-W68), `run_ring_rd.sh`, `tools/tests` (4 library arms). Fit SEED 7, clk_dec
110.74 / 110.25 before the signed-address fix; after it (`bf951cf`) SEED 7 re-rolled to 105.81 /
104.0 -- MARGINAL at the 108.8 gate, positive at 103.85, merged so at the maintainer's word (the passing
seed it owed came with PR fj#22); ALM 33,493 (80 %), DSP 103; on the rig every format composited, a full 8888
canvas costs ~1 % and fits D1's densest case (`docs/history.md` §17). On the analog chain and an HDMI capture (`docs/history.md` §20): sync
unchanged at 480i / 576i, the (1, 2, 1) through the pins (Off one line, Auto three), each Bob field
equally bright on HDMI (Off blinks at 30 Hz), 4444 translucent over video; on a CRT On / Auto steady,
Off flickers.
**The macroblock pipeline ✅ MERGED (PR fj#22), ✅ HW-CONFIRMED (2026-10-01; `docs/mb_pipeline.md`,
roadmap Phase 5 part 3):** two front stages, the back engine split, the streamed writeback, the
front end's emission queue -- cosim 985 -> 711 cycles a macroblock at 103.85 MHz, bit-exact; +1,400
ALM; carries the fixes for fj#18 and #19. Rebased on main; fit SEED 5 109.06 / 108.18 (34,943 ALM, 83 %,
`H264_mbpipe_MARGINAL_20261001_0620.rbf`); **on the rig 854x480p60 at 8 Mbit/s 1.06x -> 1.51x real
time**, every picture, errors 0 (`docs/history.md` §18). No seed closed 103.85's 108.8 gate at
83 % ALM, so **clk_dec is back to 96.43 MHz on this branch** (gate 101.4; `docs/mb_pipeline.md`
§4f): SEED 6 105.71 / 103.22 PASS (`H264_mbpipe_20261001_1223.rbf`), on the rig 854x480p60 at 8
Mbit/s **1.43x** (`docs/history.md` §19); fj#18 / fj#19 closed. **D1 is met with ~40 % to spare.**
**The headroom clock ✅ MERGED (PR fj#17), ✅ HW-CONFIRMED, reverted by PR fj#22 (clk_dec 96.43 again):**
clk_dec 96.43 -> **103.85 MHz** (VCO 1,350 / 13, gate 108.8; four retime rounds + a sweep, SEED 9
111.77 / 110.41), on the rig 854x480p60 at 8 Mbit/s ~6 % to spare (was ~1 %; `docs/throughput.md`
§7, `docs/history.md` §16). **The Jellyfin client ✅ MERGED (PR fj#24), ✅ HW-CONFIRMED 2026-10-01 with the maintainer (Phase 7,
`docs/jellyfin.md`, `docs/history.md` §21):** J1-J6 decided 2026-10-01 (v1 a cast target; an LVGL browse UI is v2; the
interface NOT frozen by it -- 1.0 waits for a public release); R1-R3 measured (a QSV server's
transcodes: High CABAC 852x480, I/P, 1.64-1.75x real time in the cosim; 5.1 audio ~7 % of an A9 core;
an idle session raises nothing); `clients/jellyfin/` built and working on .201 against the
maintainer's server (Quick Connect, cast, pause / seek / stop, the overlay's panel and subtitles);
library fixes `h264ring_refusal_name` (F3) and `h264ring_overlay_wait` "at or past" (F6); the ARM
binary is static but for glibc (F7); host test `clients/jellyfin/tests/run_test.sh --red` GREEN (10
mutations, each by its own check); the maintainer's rounds: casting, the pad (seeks add up, held
buttons repeat), a seek holding the old picture, text subtitles without a restart. Not yet: a CRT at
480i with this client. Recorded for the next RTL branch: A' + F8 (`jellyfin.md` F8 / F9), Phase 6c -- **designed together on
`feature/hdmi-raster` (`docs/hdmi_raster.md`, 2026-10-01): stage 1 A', stage 2 the native raster on 27 MHz; F8 not
reproduced on the rig; §9's choices decided 2026-10-01 (display-shaped, a `Native (HDMI)` Video Output value,
the overlay's identity on any raster, word 80 in stage 1). **Stage 1 built** (A' in `disp_fit`, interface 0.10's word
80, the Jellyfin client), GREEN and `--red`, fit SEED 6 107.83 / 106.16, 35,483 ALM (85 %); on the rig a scope film
letterboxed inside the raster and the overlay drawn in its bars (`history.md` §22). F8 found and fixed (0 : 0 between
streams, §23). **Stage 2 built** (`raster_geom`, `sync_gen`'s native raster, Video Output **Native (HDMI)**, the overlay up
to 1,024 x 2,047), every runner GREEN and `--red`, fit SEED 6 106.0 / 104.73, 35,896 ALM (86 %); on the rig four shapes
native, a size change held, the overlay centred; a library bug in the settings request across programs fixed (§24).
✅ HW-CONFIRMED with the maintainer 2026-10-02 (films look good in Native; a size change is a small blip + Main's
resolution box). ✅ MERGED (PR fj#26).**
**CAVLC through the HPS (fj#20) ✅ MERGED (PR fj#25, 2026-10-02, interface 0.10)** (`docs/cavlc.md`): a
lossless CAVLC -> CABAC rewrite in the client library (`hps/include/h264ring_cavlc.h`), no RTL change;
`h264play` uses it; `bench/h264/run_cavlc.sh` GREEN and `--red` (30 mutations; 70 AVCv1 CAVLC streams +
x264 / JM / synthetic bit-exact, refusals by name); on the rig the core decodes rewritten streams, errors
0. **Step 1's gate does not pass at 8 Mbit/s: ~12-13 % of one A9 core per Mbit/s at 480p60** (Main
holds the other core), so CAVLC plays up to ~4-5 Mbit/s. **Decided 2026-10-01** (`cavlc.md` §8):
CAVLC supported through the rewrite, on by default in `h264play` and the Moonlight client; the Jellyfin
client left as it is. The rewrite moved into `h264ring_write_au()` (programs send CABAC or CAVLC as
they have it, §9); the hot loops reworked: -8 % on the A9 (~11-12 % a Mbit/s), not 2x -- the bin
chain is serial (§8a); the ~4-5 Mbit/s limit is accepted (maintainer, 2026-10-01).
**The file player ✅ MERGED (PR fj#27), ✅ HW-CONFIRMED 2026-10-02 with the maintainer (.236)** (`docs/player.md`, ARM-side, no RTL): `h264player`
plays files from the SD card / USB / shares through the core -- a folder browser on the overlay,
text subtitles (embedded or an .srt), the refresh rate from the file (P4, accepted 2026-10-02); **only the
core's envelope plays** (SD H.264 CABAC 8-bit 4:2:0), the rest refused by name before the ring;
the Jellyfin client's modules moved to `clients/common/` (P1) and the shared build image is
`mister-h264-clients:deps2`; host tests GREEN and `--red`; on the rig (`history.md` §26). Also on
it: the Jellyfin fixes from the maintainer's round (`jellyfin.md` §11) and **P5, a screensaver**
for both clients (`clients/common/ui.c`: dim 5 min, black 30). Rebased onto interface 0.10
(2026-10-02): `ui.c` draws for the raster's own width (Native (HDMI)), and CAVLC files play through
the library's rewrite (P6, up to ~4-5 Mbit/s). The maintainer's round: every test successful, the
screensaver included; the 8 Mbit/s CAVLC clip's sluggish controls fixed (a 10 ms budget a step:
worst key delay 1.43 -> 0.067 s, `history.md` §26). ⏳ The Jellyfin fixes and its screensaver on
the maintainer's server (host-tested); a CRT at 576i.
**720p (roadmap Phase 5c part 1) ✅ MERGED (PR fj#28), ✅ HW-CONFIRMED 2026-10-04 (`dev-720p`), interface 0.11:** 2 MiB DPB
stores at `0x3200_0000` (above the ring; control block and ring unmoved), `recon_top`'s bound
3,600 (Level 3.1's MaxFS: `spec_hardening.md`'s picture-size row closed; the 128-macroblock side
limit now its own row, accepted 2026-10-05), `H264_BIG_STORES` retired; word 81 `cap_max_mbs` /
`cap_mb_rate` / `cap_native_h` + `h264ring_caps()` (`docs/architecture.md` "The capabilities
(interface 0.11)"); the clients read it (`h264check` refuses above the rate: a 720p60 file "too
fast"; Moonlight refuses past it; Jellyfin direct-plays 720p <= 30 frames/s, its transcode box
1280x720 only on Native (HDMI) with `cap_native_h` >= 720 -- never yet). Benches GREEN / `--red`:
`run_disp_reader.sh` (four 1280x720 fit arms, H1 / H2), the library / Moonlight / player host
tests, `run_recon_top.sh` (hd / big, S1-S6: a refused picture no longer opens a store -- the
unwritten store was emitted to the display), `run_ring_rd.sh` (S8), `run_scaffold.sh`, the Jellyfin
host test, `run_disp_fit` / `run_raster_geom` (3,600-MB vectors), `run_disp_sched` (74 scenarios, 33
mutations), `run_cosim` (the ring mode with the DPB above the ring) and `--red`, `tools/tests`; the
cosim on seven 720p proxies bit-exact (`docs/mb_pipeline.md` §4g). Fit SEED 6 105.62 /
101.4 PASS, 36,109 ALM (86 %), `H264_720p_20261002_2329.rbf`; **on the rig** (`docs/history.md` §27):
NVENC 720p30 1.16x, x264 720p24 4M 1.29x / 8M 1.12x, x264 720p30 4M 1.12x / 8M ~1.00x, errors / late
0; the player plays 720p files, refuses 720p60 / 1080p by name. Moonlight at 1280x720p30 and Jellyfin
720p direct play with the maintainer (§30), the analog chain at 480i on the RetroTINK (720p letterboxed, 1.13x,
§31).
**Phase 5c part 2, throughput ✅ MERGED (PR fj#29), ✅ HW-CONFIRMED on the rig 2026-10-03** (`docs/mb_pipeline.md`
§4i-§4k, `docs/history.md` §28): step 1 (a two-entry A -> B hand-off) built and PARKED (~2-3 % for +622
ALM: the stages' imbalance is per picture type -- `cosim_prof.py --by-type`); `dequant_itrans8` a
pipeline over blocks (~285 -> ~80 cycles an 8x8 block); `recon_inter` fetches only the window rectangle
each position class reads, overlaps its items (`mc_interp` two parameter sets, per-lane writers) and
reads the next item's weights ahead. Cosim x264 720p30 8M 856 -> 755, bit-exact; every runner GREEN and
`--red`. Fit SEED 6 104.32 / 102.05 PASS, 36,709 ALM (88 %), `H264_resovlp_20261003_2016.rbf`; on the rig
x264 720p30 8 Mbit/s ~1.00x -> **1.13x**, 720p24 8M 1.27x, NVENC 720p30 1.29x, 854x480p60 1.57x, errors 0.
Further levers if wanted (not planned): stage B's intra prediction (P pictures), a fetch across
macroblocks (B pictures). Part 3 (the HD raster) follows.
**Phase 5c part 3, the HD raster ✅ MERGED (PR fj#30), ✅ HW-CONFIRMED 2026-10-04 (`dev-hd-raster`, `docs/hd_raster.md`):**
designed and decided with the maintainer 2026-10-03 (§10: a second PLL, `clk_vid` 81 MHz = 3 x 27; every
native raster on the 81 MHz dot; native up to 2,048 wide; two stages, each fitted and on the rig). `clk_sys`
closes at only ~44 MHz, so only the raster side moves (sync_gen, the reader's and overlay's read-outs,
`idle_bars`, the output stage `h264/vid_out.sv`), every register on a dot enable (one clock in three at
27 MHz: the SD rasters bit-identical at the pins -- `run_vid_equiv.sh`, the new SD equivalence gate against
main). **Stage A** (the domain move alone) fitted (SEED 6: clk_dec 104.30 / 103.71, clk_vid 92.16 /
92.05) and on the rig 2026-10-04 -- HDMI and the analog chain exactly as main's (`history.md` §29).
**Stage B** (the native raster on the 81 MHz dot, up to 2,048 x 2,048; interface 0.12: `cap_native_h` 720,
the overlay to 2,048 x 2,048) fitted (SEED 3: 105.21 / 103.79, clk_vid 98.86 / 96.39; 36,736 ALM, RAM 411)
and on the rig: 1280x720 native, x264 720p30 8 Mbit/s 1.13x as fitted (§30); a full 1280x720 overlay over it
`4444` 1.11x, `8888` 1.08x. **`/dev/fb0` is Main's HDMI mode's size** (1.4 / 3.7 / 8.3 MB at 480p / 720p /
1080p), not the 8 MB region: `ui.c`'s rows now the raster's width (stage B's 2,048 row left a 720p mode no
UI; `hd_raster.md` §13). Moonlight at 1280x720p30 in Native ✅ with the maintainer (clean, responsive, errors
0); Jellyfin in Native ✅ with the maintainer (720p direct play, a 1080p film transcoded to 1280x720: both
good on HDMI). Not tested: a direct-video DAC (none at hand), S-Video on a CRT.
**Rumble through the core ✅ MERGED (PR fj#31), ✅ HW-CONFIRMED (interface 0.13; asked 2026-10-04):** program
words 36-38 (two pads a u32, `{large, small}`) read with every poll (a burst of seven) and passed to `hps_io`'s
`joystick_N_rumble` during a session (Main plays them); core words 82-83 the rumble applied + `rum_changes`;
**the keepalive is the program's** (decided 2026-10-04: Main's 32.767 s length stops a dead program's pad) --
`h264ring_rumble` / `_keepalive`; the Moonlight client's callback (patch 0005, which also sets upstream's trigger
handler: its `rumble_triggers()` tests the wrong pointer) and its 1 ms timer (`docs/moonlight.md` §8,
`docs/architecture.md` "Rumble (interface 0.13)"). Built and benched; fit SEED 3 first roll 104.11 / 104.8, 36,988
ALM (88 %), `H264_rumble_20261004_2256.rbf`; on the rig the core passes each value on during a session and 0 after
(`docs/history.md` §32); `h264play --rumble P,L,S`. ✅ HW-CONFIRMED 2026-10-04 with the maintainer (a game through the Moonlight client: "rumble works and feels good"; the keepalive's 10 s step not yet exercised by a sustained rumble). Found on the way: `run_ring_rd.sh` was RED on main since PR fj#30 (its
word 81 check still expected `cap_native_h` 480): fixed here. And `run_ring_in.sh` is RED on main too (I1 / I2
`[frames]`: a frame's 48-word status job skipped when it lands while an input job's 24 words are still in
`ring_stat`'s 64-word FIFO -- `ring_stat` counts a skip rather than waiting for room; since 0.10's 48 words):
fixed on `fix/cleanup` (2026-10-05: a frame with no room now waits for it -- the engine drains it in microseconds --
and only a frame pulse landing on one still waiting is lost and counted; `run_ring_in.sh` S9); its A6 arm, which only a
timing coincidence in I1 caught, moved to a deterministic lone action in I5.
**Phase 6d, the picture's quality ✅ MERGED (PR fj#32), ✅ HW-CONFIRMED 2026-10-05 (the maintainer's comparison on .201;
asked 2026-10-04; `docs/analog.md` §11, roadmap Phase 6d):** Moonlight 854x480 / 720p looked pixelated in Progressive. Found: the host's 3:1 downscale
(Sunshine's one-tap CUDA sampler: advice only), and the fit's 2-tap blend between 1:1 and 2:1 (beading) plus the
1,024-column floor. Decided with the maintainer: **Video Output's Auto is Native (HDMI)** unless the ini sets up an
analog TV (Interlaced) or a 31 kHz VGA monitor (Progressive) -- interface 0.14, word 80's `video_out` /
`h264ring_video_out()`, the Jellyfin client's 720p box asks it; and **the Area pre-filter, always on** (2026-10-05,
after comparing an evaluation option Sharp / Area / Smooth on the rig: Area better on 720p, Smooth too soft): weights
`(8 - A, A)` on the decimated grid in the fetch, Interlaced and Progressive alike, every column kept; anti-twitter's
sliding rows are its code 4; `disp_fit`'s `area` tied high, low the benches' Sharp control (bit-identical to main).
The weights as shift-adds (DSP 103; the first fit took all 112). ascal's own filter left alone (the maintainer). The
three-mode build: fit SEED 6 103.62 / 102.8, bit-exact on the rig (`history.md` §33). **Area always: fit SEED 6 103.49 /
102.79 PASS, 37,549 ALM (90 %), DSP 102, `H264_fitfilter_20261005_1611.rbf`; every runner it touches GREEN and `--red`;
on .201 bit-exact (1280x720 480p / 480i, 2048x448, 720x1280), `fetch_late` 0; installed with the 0.14 clients (the 0.13
ones kept as `*.iface0_13`).**
**Other codecs decoded on the ARM (P7, interface 0.15) ✅ MERGED (PR fj#35), ✅ HW-CONFIRMED 2026-10-06 (the maintainer: .236's CRT and .201) (`dev-arm-codecs`;
`docs/player.md` P7, `docs/architecture.md` "Pictures from the program"):** decided with the maintainer 2026-10-05 -- a
raw-picture record (the ARM writes the decoded picture into a DPB store, planar 4:2:0 as the decoder's; a 32-byte PICTURE
record, type 5; `h264/pic_in.sv` drives `recon_out` through a mux; word 84 `pic_held` / `pic_emitted` for the program's
store rule; errors 11-16), the measured-comfortable codecs (MPEG-1/2, MPEG-4 Part 2, DivX 3, WMV7/8, Theora, MJPEG, H.263)
in the file player only (`clients/common/vdec.c`, `player_cfg.arm_video`; Jellyfin unchanged), **SD only** (step 0 on
.201: `/dev/mem` maps the stores strongly ordered, the copy ~97 MB/s CPU-bound -- `experiments.md`). GREEN and `--red`:
`run_ring_rd.sh` (R28-R33), `test_ring` / `test_hps_lib`, the player's host test (p1-p3 byte-exact vs ffmpeg, T10 the
store rule), the Jellyfin and library tests, `run_ring_in`, `run_cosim` (with the refs). Fit SEED 6 102.95 / 102.9 PASS,
37,923 ALM (90 %), `H264_arm-codecs_20261005_1936.rbf` (and `h264.sdc`'s reader bound gained 6d's `m_hpf` / `m_vpf`). **On
.201** (`history.md` §35): every store byte-exact against the ARM's own decode (MPEG-4, interlaced MPEG-2 as pairs, MJPEG
4:2:2 full range), nine codecs in real time at 13-75 % of a core, late / starved 0, refusals by name. **Then, from the
maintainer's rounds (`history.md` §35-§36):** the 480i / 576i field order of woven pairs fixed (UMD's V6 ported, word 85
`disp_fhold`; no back-steps on .236's CRT); the player's UI inside title-safe on SD rasters; DTS 5.1 downmixed with its
centre; the library's cold-boot write index (nothing played after a power-up); **Analog Dither** (OSD, Off by default:
the DE10-Nano's 18-bit analog I/O board bands in 6 bits, a SuperStation's 24-bit DAC does not -- `analog.md` §12; on .236
it smooths the ramps); `disp_reader` retimed on clk_mem. Fit SEED 5 PASS 103.11 / 103.46, every clock positive, 37,944 ALM
(91 %), `H264_arm-codecs_20261006_0327.rbf` (on .201 and .236). ⏳ Moonlight / Jellyfin 0.15 through a whole session;
interlaced MPEG-2 at 480i by eye.
**The USB camera viewer ✅ MERGED (PR fj#37), ✅ HW-CONFIRMED 2026-10-06 (.201 and .236)** (roadmap "A USB capture / webcam viewer", proposed 2026-10-06;
`docs/uvc.md`, ARM-side, no RTL, no interface change): the MiSTer kernel has no V4L2, so `clients/uvc/` reads UVC
through libusb with its own UVC layer (`uvc.c`: PROBE / COMMIT, the payload assembler, every loss counted) and shows
each frame as a PICTURE (0.15), LOW_LATENCY. Step 1 measured on .201 with a C270: MJPEG 640x480 at 30 fits CPU0 at
**0.724** (Main holds CPU1; run pinned with `taskset -c 0`) after **the library's full-range / 4:2:2 store copy was sped
up 14.3 -> 8.15 ms** (`put_row`'s NEON interior, same bytes: `hps/tests/run_copy_arm.sh --red` on the rig, four new
`red_h264.py` mutations). **The USB host carries ~6 MB/s of isochronous video** (light MJPEG on any setting; uncompressed
only up to 6 MB/s). The viewer (`Scripts/h264cam.sh`, `src/cam.c`): the best mode, a mode list, pause, unplug / replug,
refusals by name; `clients/uvc/tests/run_test.sh --red` GREEN (15 checks, 21 mutations); the manual's "Showing a USB
camera"; on .201 (`history.md` §37); ✅ HW-CONFIRMED with the maintainer on .236 (unplug / replug, a CRT at 480i).
**The dither's matrix, a Latin square ✅ MERGED (PR fj#38), ✅ HW-CONFIRMED 2026-10-06 (.236's CRT)** (from MiSTer_DVD PR #164; `docs/analog.md` §12 "The matrix",
`docs/harvest.md`): Analog Dither's first matrix (a Bayer's top two bits = 2 x 2 `{0 2; 3 1}`) was exact over 4 x 4 but not
per line -- alternate lines half a DAC step apart at `v % 4 = 1` / `3`, a line texture; now DVD's Latin square, every line
and column exact. No interface or OSD change. `run_dac_dither.sh --red` GREEN (`[lines]` / `[cols]`, T1-T9). Fit SEED 5 first roll 103.61 / 102.79 PASS (`H264_ditherlatin_20261006_2313.rbf`); on .201 a smoke at 480i, dither On: 600 / 600, errors 0; clk_mem -0.099 in `disp_reader` (seed placement), its output pixel-exact against main's
build on .201. On .236's CRT at 480i A/B'd against main's build (`history.md` §38): the crosshatching on main's
build gone, gradients better, blue no worse (the maintainer).
**Then:** nothing planned. Moonlight's automatic size stays 480p60 (decided 2026-10-04: frame rate over
resolution; 720p30 by `moonlight.ini`). A Plex client was dropped (the maintainer, 2026-10-04: Jellyfin is enough). Candidates
(`docs/roadmap.md`): the Jellyfin client's v2 browse UI, the interface frozen at 1.0 with the first public release (GitHub; **the first release is 1.0**, decided 2026-10-06 -- the open interface findings settled first, roadmap Phase 7). **F2, the colour matrix
(interface 0.16) ✅ MERGED (PR fj#41), ✅ HW-CONFIRMED** (`docs/colour.md`, `docs/architecture.md` "The colour", `docs/history.md` §39):
the VUI's matrix and range honoured (untagged: SD 601, HD 709 by size), BT.601 / 709 / 2020 x limited / full, a 3-bit
`colour` override in record header word 1 [35:33], error 17, words 80 / 86, `h264ring_set_colour()`; the Jellyfin client
sends a transcode's SOURCE colour (R4: the server labels every transcode 709, converts nothing). Every bench GREEN and
`--red`, the SD equivalence gate exact; fit SEED 13 103.52 / 101.71 PASS after `recon_hdr`'s retime
(`H264_colour_20261007_1245.rbf`, 37,888 ALM); **on .201 every code pixel-exact** against `tools/colour_ref.py`. Every
runner GREEN and `--red` (`run_disp_sched.sh`, `run_cosim.sh` included). ✅ HW-CONFIRMED 2026-10-07 (the maintainer's
round on .201 with the 0.16 set; the 0.15 set kept as `*.iface0_15`); the ready card's clipped line fixed (ui.c wraps).
**F5, the fit word before any picture (interface 0.17) ✅ MERGED (PR fj#42), verified on .201**: word 30's `fit_valid`, the fit's
fields and word 80's place 0 while no picture is shown; fit SEED 2 102.18 / 102.35 PASS
(`H264_fitword_20261007_2343.rbf`); on .201 the Jellyfin ready screen reads 0 (`docs/history.md` §40); .201 runs the
0.17 set (0.16 kept as `*.iface0_16`). No open interface question remains before 1.0 (F1 / F4 left to later additive minors).
**The interface frozen at 1.0 ✅ MERGED (PR fj#43, 2026-10-07; `docs/architecture.md` "Version 1.0", the manual's
`integrating/interface.md` "Versions")**: word 1 `0x0100`, the 0.17 layout unchanged; **a minor only adds** (no
word or field moves or changes meaning, 0 keeps 1.0's behaviour; anything else is 2.0); the library attaches to a core
of the same major and a minor >= its own (`h264ring_version_ok()` in `h264ring.h`; exact below 1.0); the integrator
pages normative. Fit SEED 2 104.68 / 104.28 PASS (`H264_iface1_20261008_0042.rbf`); on .201 word 1 `0x0100`, a capture
plays as on main's build (control arm equal), 0.17 <-> 1.0 refused both ways (`docs/history.md` §41). **Release 1.0.0 drafted
2026-10-09** (GitHub draft `v1.0.0`, release commit `fdecab5`, SEED 12; the zip packaged by CI, PR #6; tested on .201,
`docs/history.md` §42) -- published with the move to public (Pages needs it). **Chroma reconstruction (roadmap Phase 6e) ✅ MERGED
(PR #8)**: the maintainer's bands beside red in Native (HDMI) were the reader's NEAREST chroma. First an
identity-only fix (fit SEED 5, verified on .201: `docs/history.md` §43), then **the full version** (decided 2026-10-10,
`docs/chroma.md`): the SPS's `chroma_sample_loc_type` carried to the display, chroma rows in their own 8 slots, bilinear
chroma at the siting on every output (fields within their field); benches GREEN / `--red`; fit SEED 2 102.15 / 102.45 PASS
(`H264_chromafull_20261010_1752.rbf`, 93 % ALM, 3 DSP left); on .201 every output matches the golden 99.99-100 %
(`docs/history.md` §44); ✅ HW-CONFIRMED 2026-10-10 (the maintainer on .201: "this looks better"). Parked (the session memory, not yet in docs/): the Jellyfin freeze and no-audio fixes. 91 % ALM, 9 DSP left.
---

## Documentation discipline (read before starting work)

Every non-trivial design decision **must** be written down, in this file or under
`docs/`. Code without recorded rationale is treated as incomplete.

- **Where:** `CLAUDE.md` — durable, project-wide rules and the decisions an agent needs
  *before* touching code. `docs/*.md` — subject-specific design notes, measurements, FSM
  descriptions, rejected alternatives. A short per-module status lives here; full detail
  in `docs/`.
- **When:** at the same time as the code, not later. Commit docs with the change.
- **What:** the *why*, known limitations/TODOs, alternatives rejected and why, and
  anything that surprised you.

### Leave a trail to resume work in a new session

Sessions are stateless. Before finishing any feature: update the status block and
checklists, record the **next concrete step**, list **known limitations** explicitly,
cross-reference the relevant `docs/` section and the files/benches, and keep
`docs/roadmap.md` current.

### ★ Keep the user-facing docs current (mandatory)

Three documentation surfaces with three different jobs. Putting text in the wrong one is
a documentation bug:

- **`README.md`** — the landing page. What the core is, honest status, quick start,
  licensing. Deliberately short. **Not the manual.**
- **`site/content/`** — the **manual** (MkDocs, `mkdocs.yml`, `site/README.md` for the
  authoring rules), for two audiences: **users** (install, settings, what the screen
  shows) and **integrators** (developers of HPS programs: `integrating/`, normative for
  the interface, frozen at 1.0). Deployed only on a release publish
  (`.github/workflows/docs.yml`); built as a check on every PR and push to `main` otherwise.
  Write pages in the present tense as a feature lands; an unbuilt feature carries a short
  "not yet implemented" admonition.
- **`docs/`** — engineering design notes. **Not published, not user documentation.**
  Harvest user-facing sentences into the manual; never send a user into `docs/`.

| Change | Update |
|---|---|
| New or changed OSD option | `using/settings.md` — **enforced by `tools/docs_check.py`** |
| New gamepad button | `using/controls.md` — **enforced** |
| New accepted file extension | `getting-started/loading.md` — **enforced** |
| New on-screen message | `using/on-screen-messages.md` **and** `reference/troubleshooting.md` |
| The HPS interface (ring, records, control block, `hps/`) | `integrating/*.md`; the interface version if the layout changed |
| New format / limitation removed or found | `reference/compatibility.md`; README if headline |
| New install step or release asset | `getting-started/install.md`, README quick start |
| New external reference worth crediting | `about/acknowledgements.md` |

Two checks, run both before committing anything under `site/content/` or touching
`CONF_STR`:

```bash
.venv/bin/python3 tools/docs_check.py    # OSD options/buttons/extensions <-> manual parity
.venv/bin/mkdocs build --strict          # broken cross-link = build failure
```

(`python3 -m venv .venv && .venv/bin/pip install -r site/requirements.txt` once.)

⚠ `docs_check.py` parses the `CONF_STR` block by walking to its terminator and stripping
comments. Do not "simplify" it to a grep: commented-out CONF_STR history would invent
options that do not exist.

### ★ Update status markers when a feature completes (mandatory)

A stale marker is a bug. When work merges, flip `🔧`/`❌`/`[ ]` → `✅ MERGED (PR #n)` (the GitHub number;
`fj#n` only for the Forgejo era: "Historical `fj#NN` references" below) and,
after the board test, `✅ HW-CONFIRMED` (or `⏳ HW-confirm pending`) in `docs/roadmap.md`
and the feature's own note, in the SAME change. Retire dead branch names. When in doubt,
reconcile against `gh pr list --repo owenb321/MiSTer_h264_decoder --state merged` (and, for
the Forgejo era, the `fj#NN` numbers already in the prose), not the prose.

---

## ★ Before adding a feature: read `docs/hw_budget_and_lessons.md`

Inherited from MiSTer_DVD through UMD. Three things in it change how the next feature is
designed: the scarce memory resource is **arbitration occupancy, not bandwidth** (give a
new master its own port before shrinking its data; this core's display owns `ram2`, the
ring and the DPB share `ram1`); the fabric budget and what is left for throughput; and
how a feature with a fully green gate shipped as a visible regression — the verification
rules in its §4 apply to every bench in this tree.

---

## ★ The HPS interface is a published contract

Programs other people write will depend on it. Every change to the ring, the records,
the control block or `hps/` is an interface change: it is designed in
`docs/architecture.md` first, versioned (the control block's interface version, the
client library's version), documented in the manual's `integrating/` pages in the same
change, and announced in the release notes. Every field a program writes is
**range-checked on arrival** and a violation is visible in the status block; the core
never trusts the ARM side (`docs/spec_hardening.md`).

---

## ★ Design to the spec maximum (mandatory)

Every table, counter, index width and loop bound that holds a format structure is sized
for **the maximum the format allows** (H.264 at the level and profile `docs/roadmap.md`
D1 settles, and the HPS interface's field widths), not for what a sample of streams
contained. Size to the spec unless there is a **hard limitation** (M10K/ALM, timing);
then **discuss it with the user before deciding**, record the limit and what breaks past
it beside the code and in `docs/`. **Never truncate silently**: a bound that is hit must
be visible (a counter, a status-block code, an on-screen flag).

**Why:** MiSTer_DVD shipped this mistake twice (a 64-entry VOB table a disc exceeded with
91; 7-bit cell indices a "measured unreachable" note justified until 47 PGCs exceeded
them). A capture says what is *common*; it cannot say what is *possible*.

🚩 **Every deviation from the spec maximum that was decided is listed in
`docs/spec_hardening.md` "Known deviations".** None yet here; UMD's four arrive with the
decoder in Phase 2 and are **re-decided, not inherited silently** (the table there lists
them). Scoping decisions (CAVLC, MBAFF refused) hold only because the unsupported cases
are **refused loudly**, never decoded as garbage.

---

## Repository structure

```
MiSTer_h264_decoder/
├── CLAUDE.md                  ← you are here
├── README.md                  ← landing page (not the manual)
├── NOTICE, LICENSE            ← GPL-3.0-or-later; component notes
├── H264.qpf, H264.qsf         ← Quartus project; the qsf carries the SEED LEDGER
├── build_release.sh           ← the only sanctioned way to build a loadable .rbf
├── mkdocs.yml                 ← docs_dir=site/content, site_dir=.site-build
├── h264/                      ← ALL core RTL (emu.sv, sys_pll, sync_gen, idle_bars, dec_stub)
│   └── dec/                   ← the decoder, forked from UMD's umd/h264/ at cc595c6 (Phase 2)
├── hps/                       ← the ARM-side client library, h264play, h264stat (Makefile, build_arm.sh)
├── sys/                       ← MiSTer framework; edit only as marked UMD-FORK / H264-FORK
├── bench/h264/                ← benches + run_*.sh runners (README.md = the rules)
├── tools/                     ← build gates, docs_check, check_emu_wiring, the HIL harness
├── docs/                      ← ENGINEERING NOTES — not published, not the manual
├── site/                      ← MANUAL source (content/, overrides/, README.md)
├── releases/                  ← built .rbf + .json manifests (gitignored, .gitkeep only)
├── .claude/                   ← skills (release, hil-testing, docs-sweep, field-report, integrate-stream), /merge
└── .github/                   ← workflows (the manual's check + Pages, release packaging) + issue forms
```

> **`docs/` and `site/` are not the same thing and must not be merged.** MkDocs' default
> output directory is also called `site/`, which is why `mkdocs.yml` sets
> `site_dir: .site-build` — never let a build write into `site/`, and **never add a bare
> `site/` line to `.gitignore`**.

`sys/` is byte-identical to UMD's `main` at the fork (`75e3f37` there); its `UMD-FORK`
comments name UMD paths (read `umd/` as `h264/`). This core's own `sys/` edits are marked
`H264-FORK`, additive where possible, and listed in `docs/architecture.md`. The `emu`
port list must match `sys/sys_top.v`'s instance exactly; `tools/check_emu_wiring.py` pins
it (as a set, preprocessed with the qsf's macros).

---

## Toolchain

- **Quartus 17.0.2 exactly.** Native, or the pinned Docker image `raetro/quartus:mister`
  via `USE_DOCKER=1` (`tools/docker_reexec.sh`, wired into `build_release.sh` and
  `tools/seed_sweep.sh`). Fitter SEEDs are tied to the exact netlist a given Quartus
  version produces. The Docker daemon may not be running after a reboot
  (`systemctl is-active docker`); ask the user to start it, and run the sim gates
  meanwhile.
- **Device:** Cyclone V 5CSEBA6U23I7 — 41,910 ALM, 553 M10K, 112 DSP.
- **HDL:** SystemVerilog for new modules. **Simulation:** Icarus (`iverilog -g2012`);
  Verilator for `tools/lint_undriven.sh` and cosims (UMD's `run_cosim.sh` comes in
  Phase 2).
- **Manual:** MkDocs Material pinned in `site/requirements.txt`, in a local `.venv`.
- **Oracles:** ffmpeg/ffprobe (H.264 pixels, header traces, libx264 for fixtures), the JM
  reference decoder and the H.264.1 conformance streams in `${H264_REFS_DIR:-~/h264-refs}`
  (the same set UMD reads as `$UMD_REFS_DIR`; `docs/references.md`). Never commit media or
  captured streams of others' content; fixtures are generated or cut from the reference
  set.
- **The Bash tool's shell is zsh**: an unquoted `$VAR` holding several words is ONE
  argument. Use arrays, or write a bash script to the scratchpad.

---

## Hardware status

- ✅ **P0 scaffold — MERGED (PR fj#1, 2026-09-27).** `h264/emu.sv` + `sys_pll` /
  `sync_gen` / `idle_bars` / `dec_stub`; `bench/h264/run_scaffold.sh --red` GREEN (14
  mutations, each caught by its own arm); `lint_undriven`, `netlist_canary`, docs parity
  and `mkdocs build --strict` PASS. ✅ First fit 2026-09-27: SEED 1 first roll, 6,779 ALM
  (16 %), 60 M10K, 33 DSP, clk_dec 297.62 / 291.89, `H264_scaffold_20260927_1219.rbf`
  (2.4 MB), ledgered. ✅ HW-CONFIRMED on HDMI 2026-09-27: `CORENAME` H264, two shots
  pixel-exact with the marker moved (x 4 → 400), Auto 16:9 at idle on a 1080p display,
  forced 4:3 1440 wide. ⏳ Analog not exercised.
- ✅ **P2 the fork — MERGED (PR fj#3, 2026-09-27).** Decoder + display from UMD
  `cc595c6`, fed by the ioctl stand-in; every runner GREEN and `--red`
  (`docs/roadmap.md` "Phase 2 gates"). Fit: SEED 1, 23,331 ALM, 230 M10K, clk_dec
  91.43 / 88.67 MHz, `H264_p2harvest_20260927_1801.rbf`. No HW gate of its own (nothing
  feeds the decoder until Phase 3).
- ✅ **P5a High profile -- MERGED (PR fj#5), ✅ HW-CONFIRMED (2026-09-28)**: SEED 1,
  clk_dec 87.60 / 87.37, 27,318 ALM, 315 M10K, 75 DSP, `H264_p5high_20260928_0459.rbf`;
  the Sunshine captures on the rig, every picture, errors 0 (`docs/high_profile.md` §8,
  `docs/history.md` §4).
- ✅ **P6 part 1 analog first -- MERGED (PR fj#8), ✅ HW-CONFIRMED (2026-09-29)**:
  `H264_p6analog_20260929_0709.rbf` + the Analog Aspect change (refit before merge, below):
  480i on a RetroTINK over RGBS (1716x525i, field order by one-line markers), HDMI Bob by
  capture, every shape fitted (`docs/history.md` §7 / §8). Known: pll_hdmi -2.3 ns inside
  ascal (the framework's scaler at 73 % ALM), clean on the rig; a scaled field-coded picture
  shows woven.
- ✅ **P4 audio -- MERGED (PR fj#12), ✅ HW-CONFIRMED (2026-09-29)**: SEED 7, clk_dec 102.80 /
  102.07, 31,810 ALM (76 %), 341 M10K, 95 DSP, `H264_p4audio_20260929_2240.rbf`; on the original
  rig through the HDMI capture: every record at its PTS, the capture moving with the timestamps,
  pause / volume / audio only / low latency (`docs/history.md` §11).
- ✅ **The Moonlight client (watch only) -- MERGED (PR fj#13), ✅ HW-CONFIRMED (2026-09-30)**:
  `H264_moonlight_20260930_0247.rbf` (SEED 7, clk_dec 108.12 / 104.32, no RTL change); run by the
  maintainer from the Scripts menu, 3,288 access units, 0 errors (`docs/history.md` §12).
  Input: next branch (`docs/moonlight.md` §7).
- ✅ **P3 the HPS interface -- MERGED (PR fj#4), ✅ HW-CONFIRMED on HDMI (2026-09-27).**
  `H264_p3ring_20260927_2129.rbf` (SEED 1, clk_dec 88.21 / 88.24, 26,112 ALM): `h264play`
  plays through the ring (film 240 / 240, errors 0, judder equal), switch / EOS-then-new
  / flush-seek (14 ms vs 11.2 s in order), low latency (skips counted), the lock, ten
  reloads mid-stream. 480p60 ~44 frames/s then (real time since P5b). Every gate `docs/roadmap.md` "Phase 3
  gates".

---

## ★ There is a real MiSTer you can drive — use it instead of asking

`tools/mister.py` (skill: `.claude/skills/hil-testing/`, note: `docs/hil_harness.md`)
flashes a build, loads the core, presses keys and pulls back a screenshot over ssh.
**Prefer measuring to asking.** The rig is the maintainer's **and shared with MiSTer_DVD
and MiSTer_UMD_Video sessions on this workstation**: run `state` first; if another core is
loaded, find the session driving it and ask it before loading; `restore` after; never
overwrite their running Main or settings.

---

## Building a MiSTer-loadable core

**Use `./build_release.sh` — never bare `quartus_cpf`.** MiSTer's loader needs a
**compressed** `.rbf`; an uncompressed pack (~7 MB) silently fails to configure the FPGA
(no video on any output). `build_release.sh` runs the gates (Quartus 10236 implicit-net,
`tools/lint_undriven.sh`, `tools/fmax_check.sh` at **both** slow corners,
`tools/netlist_canary.sh`), packs, and writes a `.rbf.json` provenance manifest.

```bash
USE_DOCKER=1 ./build_release.sh --compile     # -> releases/H264_<slug>_<date>_<time>.rbf
tools/seed_sweep.sh                            # when a fit is marginal
```

**Always build after completing a requested feature**, in the background, and report.
**Record every fit** in `H264.qsf`'s SEED LEDGER (seed, clk_dec both corners, ALM %,
build name, commit) and milestone fits in `docs/history.md`.

Timing note: negative slack on PLL-reconfig / HPS-bridge paths is shared MiSTer
infrastructure; validate empirically. `clk_dec` is the gated domain.

### Versioning

`` `CORE_VERSION `` in `h264/emu.sv` (shown in the OSD as `H264 <version> <yymmdd>`):

> A bare semver lives in **exactly one commit per release**. Every other commit carries
> `dev-<slug>`, set in the branch's **FIRST commit**. Nothing resets it after a merge or a
> release; `build_release.sh` refuses a bare semver on a dev build and a `dev-` string on
> `--release`, so a branch that forgets fails fast.

Limits, enforced: **≤ 18 characters, none of `, ; "`** ("H264 " + " " + "yymmdd" leaves
exactly 18 of the About line's 30). Both `CORE_VERSION` and `BUILD_DATE` are inside
`CONF_STR` = inside the netlist: **any change re-rolls the fitter seed**, so change it once
per branch, never per commit, and never derive it from a SHA. Bump rules: patch =
fixes/docs; minor = any new user-visible capability **or any interface change**; major
reserved (1.0 = the interface frozen). Judge against the whole unreleased delta on
`main`. Builds for testers: the slug names the build (`dev-slug2` for a second one the
same day); never a release.

Publishing: the `release` skill -- a GitHub release draft (`tools/publish_draft.sh`), packaged
by `.github/workflows/package.yml` (which builds the HPS clients from the release commit through
`clients.yml`), smoke-tested, then published.

---

## Source control

**Support stance (decided 2026-10-08, the maintainer): a proof of concept, not supported.** No help
with setups, no fixes on request, no promised features; others are encouraged to fork it and do
whatever they want with it. Said in the README (its callout and "Status"), the manual's home page and
"Reporting a bug", and the issue chooser (`.github/ISSUE_TEMPLATE/config.yml`). Never write a support
promise ("please report", "we will fix") into a user-facing page.

**Hosting: GitHub** (`github.com/owenb321/MiSTer_h264_decoder`; private while it is staged,
public with the first release). The Forgejo repository holds the bring-up history (PRs fj#1 to
fj#45) and is not imported. Write everything as if it were public already (below).

- **Never commit directly to `main`.** Branch first (`feature/<slug>`, `fix/<slug>`).
- **Set `` `CORE_VERSION `` to `dev-<slug>` in that branch's first commit.**
- **Never push a branch or open a PR until explicitly asked.** A merge request is
  authorisation to publish THAT branch (push → PR → merge, the `/merge` command).
- PRs via `gh` (`--repo owenb321/MiSTer_h264_decoder`; the `/merge` command picks `gh` or `tea`
  from `origin`'s URL). Write PR bodies to a file, never inline.
- Commit often, with messages that say what and why.

**The move to GitHub (decided 2026-10-06, the maintainer; made 2026-10-08): a fresh history.**
The GitHub repository starts from one import commit, as MiSTer_DVD's did; the Forgejo history
is not pushed (its commits carry a personal e-mail address). **This repository's `user.email` is
the GitHub noreply address (`owenb321@users.noreply.github.com`)**: never commit with another,
and never push a Forgejo-era commit, branch or tag to GitHub.

### ⚠ Historical `fj#NN` references — do not "fix" them

`docs/` and the code's comments cite this project's Forgejo PRs and issues heavily. GitHub's
numbering restarts at 1, so a bare `#22` would one day point at an unrelated GitHub PR -- a
reference that looks right and is wrong. Every Forgejo-era reference is therefore written
**`fj#NN`** (`PR fj#22`, `issue fj#20`), and so are MiSTer_UMD_Video's (also Forgejo-numbered:
`UMD PR fj#25`). These numbers have no GitHub equivalent: leave them alone, do not renumber
them, do not strip the prefix. MiSTer_DVD's references are its GitHub numbers and stay plain,
always named with the repository (`MiSTer_DVD PR #164`). **Since the move, a new reference is
this repository's GitHub number, plain `#NN`** -- the two namespaces distinguishable on sight.
Commit SHAs quoted in `docs/` before the move refer to the Forgejo history and will not resolve
on GitHub.

### ★ Never publish personal or workstation-specific information

No absolute paths from a machine, no hostnames/IPs/usernames/e-mails, no private
infrastructure. Repo-relative paths; environment variables with generic fallbacks
(`${H264_REFS_DIR:-~/h264-refs}`, `root@<mister-ip>`); generic placeholders in examples.
`tools/.mister_host` and `tools/.notify_url` are gitignored for this reason.

---

## Lessons carried from MiSTer_UMD_Video and MiSTer_DVD

Each earned by a shipped defect in one of the two sibling projects; each names what enforces it
here. Numbers quoted are from THOSE netlists.

- **Bench that cannot fail.** A test whose setup makes failure impossible is not evidence.
  Every runner has `--red`; every arm is proven able to go RED.
- **RED/GREEN + per-arm mutation gating.** Each deliberate mutation must be caught by
  *its own* arm; one caught by everything says nothing (`bench/h264/run_*.sh --red`).
- **Score with `!==`, never `!=`.** X passes `!=` vacuously; a bench once printed PASS
  with 12,028 X pixels in it.
- **`$fatal` on failure, a positive PASS marker, never `$finish` on the failure path**
  (vvp exits 0). Runners never score on the absence of "FAIL".
- **A new port floats Z in every bench that instantiates the module** without it. Tie it
  off everywhere in the same commit.
- **Measure, don't ask.** Drive the rig (`tools/mister.py`) instead of asking the user to
  test.
- **An instrument derived from its subject reports health when the subject is absent.**
  Prefer instruments that can say "nothing real happened" (liveness, history).
- **Async-read arrays at many sites explode into LUT-RAM** (one design went 226 % ALM):
  one synchronous M10K read port and a pipeline. And after editing near a memory's
  writes, grep the map report for its "Inferred altsyncram" line before spending a fit.
  **A byte-enabled array of non-power-of-two depth (48 words) is left in registers
  with NO message** (neither inferred nor "uninferred"): size such memories to a power
  of two (UMD P4's sample banks: 6,144 registers until 64). `tools/synth_unit.sh` checks one
  module in minutes.
- **`vec[K*idx +: W]` with a variable index and a constant K that is not a power of two
  synthesises as a barrel shifter over the whole vector** (~200 LUTs per use at 437 bits:
  three such selects were 1,400 LUTs of UMD's reconstruction). Select with a `case` on the
  index. Grep for it after touching wide records.
- **Quartus 17 silently miscompiles some `function automatic` helpers and `N'(expr)`
  size casts** (sim exact, silicon wrong). Use case blocks / part-selects; when sim says
  correct and silicon says broken, A/B two of your own builds first.
- **iverilog resolves `` `include "h264/..." `` against the working directory BEFORE any
  `-I`.** A mutation runner that copies the RTL and compiles from the repo root mutates
  the copy's `.svh` and compiles the repo's: three UMD P4 arms "survived" that way. Compile a
  mutant from inside its copy.
- **iverilog leaves the old binary on a failed build**: a runner that only checks the
  file exists runs the previous netlist and reports GREEN (`run_intra_pred.sh`, P5b).
  Every runner deletes its sim before building; a new runner must too.
- **`tools/netlist_canary.sh` + `tools/lint_undriven.sh`** catch the declared-but-undriven
  and constant-folded data path that no bench and no telemetry could see. Advisory on a
  dev build, fatal on `--release`.
- **Never edit `H264.qsf` while a build runs, and check `git diff H264.qsf` after one.** A
  quartus_map that died of low memory rewrote it (sys.tcl inlined, the ledger's new
  lines lost) and it was committed so; `build_release.sh` restores such a rewrite, and
  `tools/seed_sweep.sh` restores its pre-sweep snapshot (since UMD P5g, after a sweep
  inlined 170 pin lines): after a sweep, re-apply only the SEED line by hand.
  Simulations and a fit at once exhaust this workstation's memory (UMD's P4 chain bench
  took ~0.7 GB a simulation, eight at a time): sequence them.
- **A deployed build is not the running build, and a swept build is not the swept source**
  (Phase 4, 2026-09-29: a fix "failed" on the rig twice for these alone). `tools/seed_sweep.sh`
  re-runs only the FITTER: after an RTL change, compile first (it now refuses a stale netlist).
  `mister.py deploy --rbf` replaces a file; a loaded core keeps its old bitstream unless
  reloaded (deploy now reloads it). Check `state` / the manifest's sha against what you meant
  to test before reading a rig result.
- **The `.qsf` file list gates everything.** A new `h264/*.sv` is invisible to Quartus AND
  to the lint until `H264.qsf` names it. And `build_release.sh` once exited 0 on a failed
  compile: read the log.
- **The fitter SEED is tied to the netlist**; any CONF_STR change re-rolls it. Ledger
  every fit in `H264.qsf`. **The cold corner (−40 °C) usually binds**; pass
  `TIMING_TEMP=-40` to `tools/timing_paths.sh` or you retime the wrong path (the knob
  existed only in this file until 2026-09-27: the tcl hardcoded 100 C). Check BOTH: the
  first 96.43 MHz fit missed only at 100 C.
- **Retiming for a faster clock: `docs/hw_budget_and_lessons.md` §5 "the P5b playbook"**
  -- count failing endpoints per module (`TIMING_BELOW` + `tools/timing_census.py`),
  read the cells before fixing (`TIMING_PAIRS` + `tools/timing_chain.py`), the fix
  shapes that worked, judging a batch by the census rather than one fmax.
- **Gate at the register, not inside the producing cone**: a suppress-only term belongs
  at the capture register.
- **Occupancy, not bandwidth**: a new DDR3 master that hurts the decoder gets its own port.
- **HIL latency is part of the instrument**: ssh-paced presses cannot test a window under
  ~3 s; sequence on the target. **Control arm first** for intermittent defects; **one
  change per hardware round**; **a step that never reached the state was not measured**
  (wait for a readiness signal, then act).
- **Independent oracle.** A golden model written from the RTL shares its bugs; use
  ffmpeg/JM/the spec.
- **Fixture range and metric blindness.** Ask what inputs a fixture spans and what the
  metric structurally cannot see before trusting a verdict. When halving work, score
  WHICH half.
- **Derive a predicate from what it SELECTS, not from the cases it was written for.**
- **A coverage counter must count what the path CHANGES, not that it ran.** UMD P4's list
  modification dropped 129 duplicates on a conformance stream and 15 on a JM fixture with
  a broken removal and no bench could tell: none of those drops changed an index in use.
  Counting partitions predicted from an index the removal changed found the bug
  (`tools/jm_fixtures.py`, `docs/h264_recon.md` §5).
- **C's argument evaluation order is unspecified, and x86's and ARM's gcc differ** (fj#20,
  2026-10-01): `bw_put(w, br_u(r, n), to - r->pos)` -- ARM read `r->pos` after `br_u()` advanced
  it and dropped every slice header's tail; the host was right, and sanitisers cannot see it. In
  `hps/` code that runs on the rig, never put two side-effecting reads (or a read and a field it
  moves) in one expression's operands; **compare the ARM build's output with the host's on the
  rig** before trusting a host-only GREEN.
- **Papercuts:** declaration after use; an `input` port driven internally (only the fitter
  sees it, 30 s into a 40-minute compile); `pgrep -f` matching its own shell — manage
  Quartus by the Docker container name; the MiSTer has no `pkill`.
- **Check the polarity of any active-low signal shown as a flag** before concluding a
  watchdog is firing.

---

## Simulation quick reference

```bash
bench/h264/run_scaffold.sh            # raster + idle screen + emu wiring + lint
bench/h264/run_scaffold.sh --red      # ...and prove every arm can fail
```

Benches follow `bench/h264/README.md` (the runner table). The decoder's and display's
runners came with the Phase 2 fork: `run_h264_top.sh`, `run_recon_top.sh`,
`run_cosim.sh` (Verilator), `run_disp_sched.sh` (Verilator, ~7 min a scenario), ... Set
`H264_REFS_DIR` or the conformance arms SKIP; never run several heavy ones beside a fit.
