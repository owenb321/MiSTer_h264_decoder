# Controls

The core does nothing with your controls itself. It **passes them on** to the program that feeds
it, such as the [Moonlight client](moonlight.md), which sends them to your PC, or the
[Jellyfin client](jellyfin.md) and the [video player](player.md), which use them to pause, seek
and choose a file, and the [camera viewer](camera.md), which uses them to pause and choose a mode. MiSTer's menu keeps
working as usual: the menu button, or F12 on a keyboard, opens the core's OSD.

## Gamepads

The core asks for an Xbox-style pad. MiSTer's menu maps your own controller onto these buttons:

| Button | |
|---|---|
| D-pad | up, down, left, right |
| A, B, X, Y | the face buttons: A is the bottom one, B the right, X the left, Y the top |
| LB, RB | the shoulder buttons |
| Back, Start | the two centre buttons |
| LS, RS | pressing the left or right stick |
| LT, RT | the triggers (on or off: MiSTer passes no trigger pressure to a core) |

Both analog sticks are passed on as they are. Up to six pads are supported, numbered by
MiSTer the way it numbers players.

MiSTer maps the buttons itself the first time: the face buttons by their position, and for many
controllers (an Xbox controller, for one) all the rest too. **If LS, RS, LT or RT does nothing**,
assign them once with **Define H264 buttons** in the OSD's system settings, the way you would for
any core. MiSTer remembers the mapping for this core.

There is no Guide / Home button: MiSTer uses that button to open its own menu. To send a Home
press to the program playing through the core instead (the Moonlight client makes it the PC's
Guide button), choose **Send Home to the program** in the menu ([Settings](settings.md)); the
Moonlight client also takes Back + Start held for a second
([Moonlight](moonlight.md#controlling-the-pc)).

## Keyboard and mouse

Every key MiSTer gives a core is passed on, and so are the mouse's movement, its wheel and five
buttons (left, right, middle, back and forward). MiSTer keeps some keys for itself; they never
reach the core:

- F12, which opens the menu
- the Menu key
- Win+PrintScreen and Alt+ScrollLock, which take screenshots
- the volume and mute keys
- NumLock and ScrollLock, which switch MiSTer's keyboard-as-joystick modes

## While the menu is open

MiSTer sends nothing to the core while its menu is open. A program forwarding your controls
releases every key, button and stick on the PC when the menu opens, so nothing stays held down
there. Controls resume when the menu closes.
