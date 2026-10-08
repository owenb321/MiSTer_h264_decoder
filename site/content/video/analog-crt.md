# Analog and CRT output

The analog outputs carry the core's own signal (see [Video output](output.md)), with the
framework's usual `MiSTer.ini` video options (`vga_scaler`, `composite_sync`, `ypbpr`,
`vga_sog`).

**For a standard-definition CRT (15 kHz)** set **Video Output** to Interlaced -- or leave it
on Auto with `MiSTer.ini` set up for an analog TV (`composite_sync`, `ypbpr` or `vga_sog`
with `vga_scaler=0`, or `direct_video`). The core then generates 480i (576i at 50 Hz) with
standard composite sync: equalizing and serration pulses, so a TV interlaces the two fields
correctly.

- **Analog Aspect** fits pictures that are not 4:3 inside the 4:3 screen: Letterbox (black
  bars, the whole picture), Crop (fills the screen, cuts the sides) or Fit (stretches, for
  a TV in a wide mode).
- **Anti-Twitter** (Interlaced only): a detail one line tall -- small text, a game's HUD, a
  thin horizontal edge -- flickers on an interlaced screen. Anti-Twitter softens the
  picture vertically just enough that it stops. Off by default.
- **Refresh Rate**: 59.94 Hz and 60 Hz are NTSC-rate signals (480 lines); 50 Hz is the PAL
  rate with 576 lines -- your TV must accept 50 Hz. On Auto the rate follows the video.
- A 60p stream at 480i shows each field from its own picture (the broadcast conversion:
  full motion); 24p and 30p pictures span two or more fields and keep their full
  vertical detail.

**For a 31 kHz display** (a VGA monitor, an external scaler) use Video Output Progressive,
and set Analog Aspect to Letterbox or Crop: on Auto the Progressive output fills the screen
for HDMI's benefit and the analog picture would be stretched.
