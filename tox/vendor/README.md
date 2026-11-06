# Third-party components

These files aren't kept in Git. Download them into this folder.

## td_lastBeatStanding.tox

The audio beat tracker used by `tox/tempo.tox` when Ableton Link has no peers. Without this file, tempo still works: it uses Link, then an internal clock.

- **Author:** Ioannis Mihailidis / Studio Farbraum
- **Source:** https://github.com/ioannismihailidis/td_lastBeatStanding
- **Version:** release 2026.05.22
- **Download:** https://github.com/ioannismihailidis/td_lastBeatStanding/releases/download/2026.05.22/td_lastBeatStanding.tox
- **SHA-256:** `86e5d3d5a2b7b232e74bad1c8f7cd712195e7485c92bc319e3e21ac823138d3b`

Also download these four source files from the same release into `beat_detection/` and `src/` here, keeping those folder names. The component runs from its own embedded copies, but shows "file not found" errors without them:

- `beat_detection/beat_detector.py`
- `beat_detection/post_processor.py`
- `src/script_madmom_dnn.py`
- `src/script_madmom_post.py`

In `tox/tempo.tox`, the `beat_tracker` node has **Save Backup of External** turned off. Keep it off, or saving would copy this component into `tempo.tox` and `QRTZ.toe`, and so into this public repo.

**License:** the code is GPL v3. The model weights inside the file come from [madmom](https://github.com/CPJKU/madmom) and are CC BY-NC-SA 4.0, so **commercial use needs permission from the madmom authors**. See the "Cost, licensing and hardware" section of `PLAN.md` before using it at a paid gig.
