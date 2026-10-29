# Shared photo journal

Run from this folder with Python 3.11+ (standard library only):

```sh
python run.py import /path/to/photo.jpg --device bench-phone --project robot --captured-at 2026-10-28T12:00:00Z
python run.py list --project robot
```

Replace the input path/time with a real photo. Stores original bytes by SHA-256 and metadata in SQLite; repeated identical imports do not duplicate the metadata entry. Original filenames are metadata, not storage paths. Capture time is explicitly provided rather than inferred from EXIF. Local trusted import only: camera capture, network upload, authentication, captions, and offline queues remain future work. Retrieve an original using its digest under runtime/originals/; use original_name for its file extension.

Use `python run.py --help` for options. See [the garage run guide](../../README.md) for deployment boundaries.
