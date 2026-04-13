# Core Build Notes

The native module target is `imagegpt_core` and requires:
- OpenImageIO (image I/O)
- LibRaw (RAW decode)
- LittleCMS2 (ICC transforms)
- pybind11 + Python 3.11+

If native dependencies are unavailable, backend falls back to a Python JPEG pipeline for v1 functionality.
