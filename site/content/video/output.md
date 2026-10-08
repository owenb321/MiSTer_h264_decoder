# Video output

The core generates one signal for HDMI and the analog outputs alike, chosen by two
settings ([Settings](../using/settings.md)):

| Refresh Rate | Video Output: Progressive | Video Output: Interlaced |
|---|---|---|
| 59.94 Hz | 720x480p (31 kHz) | 720x480i (15 kHz) |
| 60 Hz | 720x480p at exactly 60.000 Hz | 720x480i at exactly 60.000 Hz |
| 50 Hz | 720x576p (PAL, 31 kHz) | 720x576i (PAL, 15 kHz) |

**Refresh Rate** on Auto follows the video: a stream at exactly 60, 30, 24 or 120 frames a
second gets 60 Hz (a Moonlight game stream is exactly 60), one at 50, 25 or 100 gets 50 Hz,
anything else 59.94 Hz. The choice is made when a stream starts and kept until the next
one, so a display may resync once at the start of a stream, never during it.

**Every picture is fitted to the screen** at its true shape -- its cropping and its pixel
shape as the stream declares them -- centred, with black bars where the shapes differ:
640x480, 854x480, a transcode's 720x404, a phone's portrait 480x854 alike, on 480 or 576
lines. On HDMI with the Progressive output and Analog Aspect on Auto, the picture instead
fills the core's screen and the HDMI scaler is told its exact shape; a picture wider than your
HDMI display (a 2.39:1 film on a 16:9 TV) is letterboxed inside the core's screen, so the bars
are part of it and a player can show subtitles there.

**Video Output: Native (HDMI)** goes further for HDMI: the core's signal is the video's own size
-- 852x480, 640x480 (shown 853x480 with its side bars), 720x576, **1280x720** ... -- at the same
refresh rate, and the HDMI scaler makes the only resize to your display, the sharpest HDMI
picture. Every picture the core plays is shown this way, 720p included (any size up to 2,048
pixels on a side). Each new picture size is a brief blip on HDMI (and MiSTer's resolution box, if
`video_info` is set). Native is for HDMI only: the analog output carries the same unusual timing
unless `vga_scaler=1`.

On HDMI the MiSTer's scaler converts the core's signal to your HDMI mode. A 50 Hz signal on
a 60 Hz HDMI mode shows a small judder; to avoid it, let the HDMI output follow the core
(`vsync_adjust=1` or `2` in `MiSTer.ini`). With Interlaced output the HDMI scaler
deinterlaces (**HDMI Deinterlace**).

Between two streams the screen is black and keeps the last stream's shape.
