# QRTZ (pronounced "quartz") — project rules for AI assistants

Live visuals in TouchDesigner driven by a small lit crystal on the DJ booth.
A camera on the crystal supplies the texture; the DJ steers it by spinning its
base, hand gestures, MIDI and Ableton; tempo comes from Ableton Link (Rekordbox,
Serato DJ Pro, Traktor Pro, Engine DJ, Ableton Live). Full plan: PLAN.md.

## Environment
- TouchDesigner 2025.32280 or newer, Non-Commercial (max 1280x1280, render 1280x720)
- Windows; give PowerShell commands and Windows paths. Repo lives at C:\Projects\qrtz
- Python inside TouchDesigner (numpy available); GLSL TOP pixel shaders
- Arduino sketch in firmware/ drives an addressable RGB LED ring over USB serial

## Rules
- All Python in scripts/*.py, synced to Text DATs. All GLSL in shaders/.
- Each module is an external .tox in tox/. Never put logic only inside the .toe.
- Module outputs are Null CHOPs/TOPs named *_out (crystal_out, tempo_out, hands_out).
- TouchDesigner only listens to Ableton Link tempo; it never sets it.
- Every gesture needs a hold timer so passing hands don't trigger it.
- Every input has a fallback; losing one never stops the output.
- Tunable numbers go in config/settings.json, never hard-coded.
- Flash rate limited to 3 per second in any scene.
- Never save frames from the live show camera (pre-shot crystal loops in loops/ are fine).
- Owner is a beginner in Python: explain each new TouchDesigner concept
  in 1-2 plain sentences, and end each change with "how to check it worked".
- One small, testable step at a time.
