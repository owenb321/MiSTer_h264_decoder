# Loading the core

The core is normally **loaded by the program that feeds it**: the program starts the core
the way MiSTer's own shortcuts (`.mgl` files) do, then starts sending video. You can also
load it by hand from the MiSTer menu under **Other** → **H264**, which is useful to check
that it runs.

On its own the core shows a test pattern: seven colour bars and a small white square
below them that moves steadily from left to right. If the square moves, the core is
running. See [On-screen messages](../using/on-screen-messages.md).

The core has **no file browser entry** and loads no files through the OSD: it accepts no
file types. Video reaches it only from a program -- for example the Moonlight client, which
streams a PC's desktop or games ([Streaming from a PC](../using/moonlight.md)).
