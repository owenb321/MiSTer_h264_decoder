# Building from source

Requires **Quartus 17.0.2 exactly**. The pinned Docker image `raetro/quartus:mister` is
that version:

```bash
USE_DOCKER=1 ./build_release.sh --compile   # -> releases/H264_<slug>_<date>_<time>.rbf
```

`build_release.sh` also runs the build gates (implicit nets, undriven signals, the
decoder-clock timing gate at both corners, the netlist canary) and packs a **compressed**
`.rbf`, which MiSTer's loader requires.

Simulation benches run under Icarus Verilog and Verilator: `bench/h264/run_scaffold.sh`
(add `--red` to prove each bench can fail).

The Moonlight client (a static ARM program, built in its own pinned Docker image) and its test
on the PC:

```bash
USE_DOCKER=1 clients/moonlight/build.sh     # -> clients/moonlight/build/dist/ (the SD card's layout)
clients/moonlight/tests/run_test.sh --red   # needs gcc, libopus and python3 on the PC
```

`tools/package_release.sh` puts the core and the client into one zip.

The manual is built with MkDocs: `python3 tools/docs_check.py && mkdocs build --strict`.
