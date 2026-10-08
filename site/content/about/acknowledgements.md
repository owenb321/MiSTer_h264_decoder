# Acknowledgements

- The **MiSTer** project and its contributors: the framework this core is built on
  (Template_MiSTer, Main_MiSTer).
- **MiSTer_UMD_Video**, the PSP UMD Video player core this core's decoder, display path,
  build gates and process come from, and **MiSTer_DVD**, from which that core came.
- **Moonlight** (moonlight-embedded, moonlight-common-c; Iwan Timmer, Cameron Gutman and
  contributors): the game-streaming client the core's Moonlight support is built on, and
  **Sunshine** (LizardByte), the open host it streams from.
- **Jellyfin** and its clients: the server the core's Jellyfin support plays from;
  **jellyfin-mpv-shim**, the cast-only client whose flow the MiSTer's follows; and **MiSTerFin**
  (Pudding Studio), the first Jellyfin client for MiSTer, read for ideas (its Quick Connect flow,
  its transcode request) -- none of its code is used.
- **FFmpeg**: its libraries demux and decode the audio in the Jellyfin client (LGPL); with the
  ITU-T **JM** reference software it is also the decoder's verification oracle.
- **cJSON** (Dave Gamble), **stb_truetype** (Sean Barrett), the **DejaVu** fonts, and Mozilla's
  CA certificate list as **curl** publishes it, in the Jellyfin client.
- The H.264 FPGA literature the decoder was sized against (Agostini et al.; Petrovsky et
  al.; K. Xu's *nova*, ideas only).

Licensing: GPL-3.0-or-later; see [LICENSE](https://github.com/owenb321/MiSTer_h264_decoder/blob/main/LICENSE) and
[NOTICE](https://github.com/owenb321/MiSTer_h264_decoder/blob/main/NOTICE).
