# QRTZ (pronounced "quartz") — project rules for AI assistants

A music visualizer in TouchDesigner where every image is light through a crystal.
Standalone (built first): a virtual crystal refracts photos and paintings, driven
by BPM, bass, mids, treble and drops. Crystal stage (added later): a camera on a
small lit crystal on the DJ booth replaces the virtual one, and the DJ steers it
by spinning its base and hand gestures. Tempo comes from Ableton Link (Rekordbox,
Serato DJ Pro, Traktor Pro, Engine DJ, Ableton Live). Full plan: PLAN.md.

## Environment
- TouchDesigner 2025.33230 (current official build, Sep 2026) or newer, Non-Commercial (max 1280x1280, render 1280x720)
- Windows; give PowerShell commands and Windows paths. Repo lives at C:\Projects\qrtz
- Python inside TouchDesigner (numpy available); GLSL TOP pixel shaders
- Arduino sketch in firmware/ drives an addressable RGB LED ring over USB serial
- TouchDesigner MCP server connects Claude Code to the running project

## Rules
- All Python in scripts/*.py, synced to Text DATs. All GLSL in shaders/.
- Each module is an external .tox in tox/. Never put logic only inside the .toe.
- Module outputs are Null CHOPs/TOPs named *_out (audio_out, tempo_out, crystal_out, hands_out).
- Both crystals write the same crystal_out and the same numbers (angle, spin_speed, sparkle);
  nothing downstream may care which crystal is live.
- TouchDesigner only listens to Ableton Link tempo; it never sets it.
- Every gesture needs a hold timer so passing hands don't trigger it.
- Every input has a fallback; losing one never stops the output.
- Tunable numbers go in config/settings.json, never hard-coded.
- Flash rate limited to 3 per second in any scene.
- Never save frames from the live show camera (pre-shot crystal loops in loops/ are fine).

## How to work with the owner
- Owner knows HTML/CSS and some terminal; beginner in Python and TouchDesigner.
  Explain each new TouchDesigner concept in 1-2 plain sentences, when it first comes up.
- One small, testable step at a time. Work on one milestone from PLAN.md per session.
- End every change with "how to check it worked."
- After the owner confirms a check passed, tick that milestone's box in PLAN.md
  and suggest a short Git commit message.
- When a decision changes the plan, update PLAN.md in the same change.
