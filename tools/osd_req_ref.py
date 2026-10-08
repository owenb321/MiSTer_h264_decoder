#!/usr/bin/env python3
"""osd_req_ref.py -- the settings request's rule (interface 0.4), written from
docs/architecture.md's text, NOT from h264/osd_req.sv: random requests against random menu
states -> the expected result, for bench/h264/osd_req_tb.sv.

    osd_req_ref.py N FILE     one vector a line: status set_word -> want_err want_set want_status_in (hex)
"""
import random, sys

# the request's values in word 27's mirror order, and each option's CONF_STR status bits
OPTS = [  # name, width in the request, status lsb, the number of values the option has
    ("aspect", 2, 1, 3), ("deint", 2, 3, 3), ("video_out", 2, 5, 3), ("hdmi_deint", 1, 7, 2),
    ("analog_aspect", 2, 8, 4), ("refresh", 2, 11, 4), ("anti_twitter", 2, 15, 3)]


def rule(status, word):
    vals, b = {}, 0
    for name, w, _, _ in OPTS:
        vals[name] = (word >> b) & ((1 << w) - 1)
        b += w
    mask = (word >> 13) & 0x7F
    if mask == 0:
        return 3, 0, 0
    if (word >> 20) & 0xF:
        return 2, 0, 0
    for i, (name, w, _, n) in enumerate(OPTS):
        if mask >> i & 1 and vals[name] >= n:
            return 1, 0, 0
    out = status & ~1 & ~(3 << 17)         # never the OSD's Reset, never an OSD action (0.8)
    for i, (name, w, lsb, _) in enumerate(OPTS):
        if mask >> i & 1:
            out = (out & ~(((1 << w) - 1) << lsb)) | (vals[name] << lsb)
    return 0, 1, out


def main():
    n, path = int(sys.argv[1]), sys.argv[2]
    rnd = random.Random(7)
    with open(path, "w") as f:
        for i in range(n):
            status = rnd.getrandbits(128)
            word = rnd.getrandbits(24) | ((i % 255 + 1) << 24)
            if rnd.random() < 0.7:
                word &= ~(0xF << 20)          # most without reserved bits
            if i % 17 == 0:
                word &= ~(0x7F << 13)         # some with an empty mask
            e, st, out = rule(status, word)
            f.write("%032x %08x %x %x %032x\n" % (status, word, e, st, out))
    print("wrote %d vectors" % n)


if __name__ == "__main__":
    main()
