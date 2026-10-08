# What you need

- A MiSTer (DE10-Nano) with an up-to-date MiSTer menu.
- An HDMI display, or an analog display through a MiSTer I/O board.
- **A program that feeds the core.** The core decodes; it does not fetch anything from
  the network or read files by itself. Programs that use it run on the MiSTer's ARM side.

The core comes with two programs:

- **A Moonlight client**: streams a PC running Sunshine -- its desktop or its games, picture
  and sound -- started from MiSTer's Scripts menu
  ([Streaming from a PC](../using/moonlight.md)). The MiSTer's keyboard, mouse and gamepads
  control the PC.
- **A reference player, `h264play`**: plays an H.264 file (Annex-B: `.264` / `.h264`, Main or
  High profile) from the SD card or a network share: copy it to the MiSTer and run it from a
  terminal (ssh).

Other programs -- a media-server client, for example -- are for their authors to build on the
same interface: [Integrating a program](../integrating/overview.md).
