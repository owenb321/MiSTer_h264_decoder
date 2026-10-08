# MiSTer H264

An **H.264 decode and presentation core for the MiSTer FPGA** (DE10-Nano), built so that
programs on the MiSTer's ARM side can offload video to it. A Moonlight game-streaming
client, a Jellyfin client or a file player hands the core compressed video (and
audio) with presentation times; the FPGA decodes it and shows it on HDMI and analog, in
sync. The ARM chip cannot decode H.264 at these rates in software.

The target is **High profile video up to 854x480 at 60 or 1280x720 at 30 frames per second**
(any size and aspect up to 3,600 macroblocks a picture), at the bitrate of a 10 Mbit/s game
stream, from any service; **analog
output (480i on a CRT) comes first**. The decoder
is forked from that of MiSTer_UMD_Video, a sibling core for PSP UMD Video discs, which
decodes H.264 Main profile bit-exact at up to 30 frames per second.

## Status

**Early development.** A program on the MiSTer plays H.264 through the core: the
interface programs use (a ring of records in DDR3, version 1.0, frozen), its C client
library and a reference file player (`hps/`) work on the hardware. The decoder does Main
and **High profile** (what a stock Sunshine host sends: the 8x8 transform, 8x8 intra
prediction, scaling matrices), bit-exact in simulation against ffmpeg and the H.264.1
conformance streams; CAVLC streams (Constrained Baseline phone video, x264's `ultrafast`) are
rewritten into CABAC by the library on the ARM, bit for bit, in real time up to about 4-5 Mbit/s;
**720x480 and 854x480 at 60 frames/s are real time** on the hardware (game-stream
bitrates); **1280x720 (720p) at up to 30 frames/s** too, fitted to the screen or, on HDMI with
Video Output Native (what Auto picks when no analog display is set up), shown at its own 1280x720 (real time for game streams, films and transcodes
up to about 8 Mbit/s); **480i analog output** (15 kHz with proper composite sync, for a standard-definition
CRT) and **every picture size fitted to the screen** at its true shape, shrunk by averaging so thin lines and text stay even (letterboxed, cropped
or stretched on a CRT; exact on HDMI, or at the picture's own pixel size with Video Output Native)
work on the hardware, as do **576i / 576p (PAL) at 50 Hz**,
an **exact 60.00 Hz** mode for game streams (chosen automatically from the stream) and an
**anti-twitter** filter for interlaced CRTs. **Audio** (PCM from the program, played in sync
with the pictures; pause and volume) works on the hardware. **A Moonlight client**
(`clients/moonlight/`) streams a PC running Sunshine to the core, picture and sound, started
from MiSTer's Scripts menu; the MiSTer's keyboard, mouse and gamepads reach the PC through the
core, and a game's rumble comes back to the gamepads. **A Jellyfin client** (`clients/jellyfin/`, early) plays a Jellyfin server's films and shows:
pick one in any Jellyfin app and play it on the MiSTer -- direct play when the file suits the core,
the server's transcode otherwise, with text subtitles drawn over the picture. **A video player**
(`clients/player/`, early) plays files from the SD card, a USB drive or a network share, chosen
with the pad: H.264 up to 720p at 30 frames per second (High or Main, 8-bit), and the older formats --
MPEG-2, DivX / Xvid, WMV, Theora, Motion JPEG -- up to DVD size, decoded on the ARM and shown by the core like its
own pictures; anything else is named on screen. Both programs dim the screen when nothing plays,
against burn-in. **A camera viewer** (`clients/uvc/`, early) shows a USB webcam or capture device
(Motion JPEG up to DVD size, 30 frames per second) -- the MiSTer as a 15 kHz screen for another source. A program can draw **its own screens** -- menus, subtitles, a progress bar -- into the
Linux framebuffer, and the core composites them over the video on HDMI and the analog outputs
alike. See the [roadmap](docs/roadmap.md).

## Quick start

There is no release yet. To build from source (Quartus 17.0.2, or the pinned Docker
image):

```bash
USE_DOCKER=1 ./build_release.sh --compile     # -> releases/H264_<slug>_<date>_<time>.rbf
bench/h264/run_scaffold.sh --red              # the simulation gate
```

Copy the `.rbf` to `_Other/` on the SD card and load **H264** from the menu: colour bars
with a moving white square mean it runs. To play a file, build the feeder
(`USE_DOCKER=1 hps/build_arm.sh`), copy `hps/build/arm/h264play` to the MiSTer and run
`h264play clip.264` there (H.264 Constrained Baseline, Main or High profile, Annex-B): it loads the core itself. The
manual's "Integrating a program" pages describe the interface and the library. To stream a PC:
`USE_DOCKER=1 clients/moonlight/build.sh`, copy `clients/moonlight/build/dist/*` to the SD
card's root, and follow the manual's "Streaming from a PC (Moonlight)". To watch from a Jellyfin
server: `USE_DOCKER=1 clients/jellyfin/build.sh`, copy `clients/jellyfin/build/dist/*` likewise,
and follow "Watching from a Jellyfin server". To play video files: `USE_DOCKER=1
clients/player/build.sh`, copy `clients/player/build/dist/*` likewise, and follow "Playing video
files". To show a USB camera: `USE_DOCKER=1 clients/uvc/build.sh`, copy `clients/uvc/build/dist/*`
likewise, and follow "Showing a USB camera".

## Documentation

- **The manual** (for users and for developers of programs that feed the core):
  `site/content/`, built with MkDocs (`mkdocs.yml`).
- **Engineering notes** (why the design is the way it is): `docs/`. Not user documentation.
- Historical note: `fj#NN` references and quoted commit SHAs come from a pre-publication
  private repository and do not resolve here.

## Licence

GPL-3.0-or-later, except `hps/` (the client library programs link, its feeder and
h264stat), which is MIT. See [LICENSE](LICENSE), [hps/LICENSE](hps/LICENSE) and
[NOTICE](NOTICE) (framework licences, verification oracles, patents).
