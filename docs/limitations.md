# Current Limitations

- Native core compile depends on local installation of OpenImageIO, LibRaw, and LittleCMS2.
- RAW fallback is intentionally limited; full RAW decode requires native core.
- ICC handling in v1 uses a conservative sRGB output path and does not include full camera profile management.
- Tone/finishing algorithms are deterministic approximations rather than advanced local or AI pixel operations.
- Desktop UI is intentionally minimal and optimized for workflow correctness.

