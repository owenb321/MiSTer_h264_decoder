# MiSTer H264

An **H.264 video decoder for the MiSTer FPGA**, built as a core that programs running on
the MiSTer's ARM side can feed. A game-streaming client, a media-server client or a file
player hands the core compressed video and audio; the FPGA decodes it and shows it on
HDMI or an analog display, in sync. The ARM chip cannot decode H.264 at these rates in
software; this core does it in the FPGA fabric instead.

!!! warning "Early development"
    This is a development build: nothing has been released yet, and the interface programs
    use to feed the core may still change. On its own the core shows a test pattern; a
    program on the MiSTer's ARM side plays through it. See
    [Compatibility](reference/compatibility.md) for what works today.

## Who this manual is for

- **If you want to watch something**, start with [Install the core](getting-started/install.md)
  and [What you need](getting-started/what-you-need.md): the core does nothing on its own,
  you need a program that uses it. Two come with it: [Streaming from a PC
  (Moonlight)](using/moonlight.md) and [Watching from a Jellyfin server](using/jellyfin.md).
- **If you are writing such a program**, read
  [Integrating a program](integrating/overview.md).
