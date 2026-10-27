# QRTZ — TouchDesigner Build Plan

QRTZ is pronounced "quartz." Plan as of Oct 26, 2026, by Nick Lax. This file is the source of truth for the project: update it here as decisions change.

## TL;DR

A small lit crystal sits on the DJ booth in full view of the crowd. A camera locked on it turns its refractions into the live visuals. The DJ plays it like an instrument: turning it by hand, gesturing over it, and syncing it to the music through Ableton Link from Rekordbox, Serato DJ Pro, Traktor Pro, Engine DJ or Ableton Live.

**Why the crystal beats crowd tracking:** you control the light, focus and background, so tracking is reliable every night. Crowd cameras struggle in dark, packed rooms. The crystal also gives the show a physical centerpiece nobody else has, and it stays out of the crowd's reach.

**How to build it (no new subscriptions):**

- **Claude Code + TouchDesigner MCP** (covered by Claude Pro) for building node networks and multi-file features. The `touchdesigner-mcp-server` package (repo 8beeeaaat/touchdesigner-mcp) installs with one `claude mcp add` command.
- **Copilot Pro in VS Code** for line-by-line edits to the external `.py`, `.glsl`, `.ino` and `.html` files. The PyPI `touchdesigner-mcp` package also documents a `.vscode/mcp.json` setup, so Copilot's agent mode can drive TouchDesigner too.

**The crowd still plays a part,** just without touching anything: phone votes on the palette, and an optional wide camera for Crowd Sync later on.

## The concept and what makes it different

The crowd watches the DJ touch a glowing crystal, and the room's visuals bend with it. Most TouchDesigner shows hide the source of the visuals; this one puts it on the booth, in light, where everyone can see cause and effect.

**Core loop:** the music sets the tempo and mood (BPM picks the visual world), the crystal supplies the imagery (its live refractions are the texture), and the DJ steers it (turning, gestures, knobs).

**Differentiators, in order of build priority:**

1. **A real object as the image source.** The camera's close-up of the crystal feeds the GLSL scenes directly, so every show looks slightly different and organic.
2. **The crystal's glow matches the screen.** An LED ring under it takes the current palette color, so the crowd sees the booth and the screens move together.
3. **Hands-on control.** The DJ spins the crystal's base by hand and gestures over it; the same camera reads both.
4. **Locked to the DJ's software.** Ableton Link gives exact tempo and bar position from any of the five supported apps, so drops land on the bar.
5. **Hand-painted look.** Scanned paintings and brush strokes layered over the crystal footage. This is hard for anyone else to copy.

**BPM bands (starting point, tune by ear):**

| BPM band | Typical music | Visual world |
| --- | --- | --- |
| Under 100 | Hip-hop, downtempo, ballads | Slow organic shapes, painted washes, wide color fields |
| 100 to 125 | Pop, disco, house warm-up | Flowing ribbons and soft geometry |
| 125 to 135 | House, techno | Hard-edged grids, rings and lines locked to the beat |
| Over 135 | Drum and bass, dubstep, hardstyle | Fractured shards, fast cuts, high contrast |

A 70 BPM track and a 140 BPM track can feel the same (half-time), so keep a "×2 / ÷2" control for when the reading picks the wrong half.

## Cost, licensing and hardware

The software is free until you take paid gigs; the booth rig is a handful of low-cost parts. Check current prices when you shop.

**Software**

| Item | Cost | Notes |
| --- | --- | --- |
| [TouchDesigner Non-Commercial](https://derivative.ca/UserGuide/Licensing) | Free | Output capped at 1280×1280; not allowed for paid work. Render at 1280×720 while prototyping. |
| [TouchDesigner Commercial](https://derivative.ca/UserGuide/Licensing) | $600 one-time | Needed for paid gigs. One key, movable between computers. |
| [Ableton Link CHOP](https://docs.derivative.ca/Ableton_Link_CHOP) | Built in | Tempo, bar ramp and beat pulses from any Link app on the network. |
| [TDAbleton](https://docs.derivative.ca/TDAbleton) | Built in | Deeper Ableton Live control (clips, devices, tracks). Needs Live 11.1.5 or newer. |
| [lastBeatStanding](https://derivative.ca/community-post/asset/last-beat-standing-rocksolid-ai-based-realtime-beat-detection/74246) | Free | Audio beat tracker. Fallback when the DJ isn't using Link. Needs TouchDesigner 2025.32280+. |
| [MediaPipe plugin](https://github.com/torinmb/mediapipe-touchdesigner) | Free, open source | Hand tracking for the DJ's gestures. One person at close range is what it does best. |
| [Open Beat Control](https://github.com/Deep-Symmetry/open-beat-control) | Free, open source | Optional: reads beats from Pioneer CDJ networks and sends OSC, for booths with CDJs and no laptop. |

**Booth rig**

| Part | What to look for |
| --- | --- |
| "Crystal" | A faceted acrylic gem is cheap and won't shatter. A K9 glass prism or crystal ball sparkles more but can break. Fist-sized or smaller. |
| Rotating base | A small lazy-susan bearing the DJ can spin with one finger. |
| Clear dome | An acrylic display dome over the crystal keeps drinks and hands off it. It sits on the rotating base. |
| Light | An addressable RGB LED ring (often sold as NeoPixel or WS2812) under the crystal. |
| Microcontroller | An Arduino-compatible board on USB. TouchDesigner's Serial DAT sends it the colors. |
| Camera | A USB webcam whose autofocus and auto-exposure can be switched off, on a short gooseneck or arm. |
| Backdrop | A matte black card behind the crystal, so the only thing the camera sees is light in glass. |
| Mount plate | Camera, base and backdrop bolted to one board, so the framing survives booth bumps. |
| MIDI controller (optional) | A small knob-and-pad box just for the visuals, so you never fight the DJ software for the DJ's controller. |

**Computers:** TouchDesigner runs on its own machine beside the booth, not the DJ's laptop. Link works over a local network, so bring a small travel router rather than trusting venue Wi-Fi. The RTX 3060 Ti machine is the better show computer (some TouchDesigner features are Nvidia-only); the RX 9070 desktop is fine for building.

## How it works

Eight modules, each its own `.tox`, pass data down through Null operators named `*_out`. The brain is the only module that makes decisions, so every other piece stays simple and swappable.

```
 DJ software          Booth controls          Crystal camera  <------------+
 (Link, 5 apps)       (MIDI, Ableton, phone)  (crystal + DJ's hand)        |
      |                     |                       |                      |
      v                     v                       v                      |
 Tempo                Control                 Crystal + hands              |
 tempo.tox            control.tox             crystal_cam.tox, hands.tox   |
 Link first,          MIDI In CHOP,           texture, sparkle, spin,      |
 audio fallback       TDAbleton, phone+PIN    hand height, pinch, palm     |
      |                     |                       |                      |
      +---------------------+-----------------------+                      |
                            v                                              |
                     Brain (brain.tox)                                     |
   BPM band picks scene - changes land on the bar - 2-bar cross-fades      |
   gestures need a hold - DJ controls win - every input has a fallback     |
                            |                                              |
                            v                                              |
                     Scenes (scenes.tox)                                   |
   crystal footage as texture - 4 GLSL worlds - painted textures           |
                 |                                   |                     |
                 v                                   v                     |
         Output (output.tox)                  LED ring (led.tox)  ---------+
         flash limiter, fullscreen            palette -> Serial -> Arduino
                                              (LED glow lights the crystal)
```

The right-hand loop is physical: the LED ring takes the screen's palette, lights the crystal, and the camera sees that light. If any input drops, the brain carries on with the rest.

### Operator screen: preview and program

The operator gets a control window on the show computer's own screen or a small second monitor, while the venue screens show only the live output. It works like a video switcher.

- **Program:** exactly what the crowd sees right now.
- **Preview:** the next scene, image or palette with your current settings, at half resolution. Tweak it here, press Take, and it crossfades into Program on the next bar.
- **Photo deck strip:** thumbnails of every image in `images/`; click one to load it into Preview.
- **Input monitors:** the crystal camera, tempo source and BPM, spin angle, the gesture being detected, and a red flag when any input has dropped to its fallback.
- **Live controls:** sliders for warp, ripple, intensity and LED brightness, mirrored to the MIDI box.

Preview costs extra GPU, so it renders at 640×360 and pauses when nothing is staged. Later, the phone page can show a small Program thumbnail so you can check the screens from across the room.

## How the DJ plays it

The DJ gets four ways to steer the visuals, and any of them works on its own. Every gesture needs a short hold (about half a second) so a passing hand never fires it by accident.

| Control | How it's read | What it does |
| --- | --- | --- |
| Spin the base | Camera tracks a small colored dot on the base | Rotation angle turns the visuals; spin speed sets motion intensity |
| Hand height over the dome | MediaPipe hand tracking | Higher hand = more bloom and density |
| Pinch and hold | MediaPipe hand tracking | Next palette (screen and LED ring together) |
| Open palm, held 2 seconds | MediaPipe hand tracking | Freeze the current frame until the palm lifts |
| Link tempo and bar | Ableton Link CHOP | Beat pulses, scene changes on the bar, BPM band |
| Ableton clips and knobs | TDAbleton | Launching a clip can switch scenes; a Live macro knob can drive any parameter |
| Knobs and pads | Optional MIDI controller | Scene select, intensity, LED brightness, blackout |
| Phone page | Web Server DAT | Backup controls for you; palette votes for the crowd |

Start with one camera framed on the crystal plus the space just above the dome, so it sees both the crystal and the DJ's hand. If the crystal shot needs to be tighter, add a second webcam for hands.

### Tempo sync per DJ app

All five use Ableton Link, so TouchDesigner needs one Ableton Link CHOP for every setup. TouchDesigner only *listens* to the tempo and never sets it, so it can't fight the DJ.

| App | Link support | What to know |
| --- | --- | --- |
| [Rekordbox](https://rekordbox.com/en/support/faq/ableton-link/) | LINK button in the global section | Check its FAQ for limits when a DJ controller is plugged in. |
| [Serato DJ Pro](https://serato.com/dj/pro/expansions/more/abletonlink) | Since Serato DJ 1.9.3 | A Link toggle sits where each deck's Sync button would be. |
| Traktor Pro | Since [Traktor Pro 2.11](https://synthtopia.com/?p=75959) | Users report decks can't become the Link tempo leader. Fine here, since TouchDesigner only listens. |
| Engine DJ | Since [Engine DJ 2.0](https://djmag.com/news/denon-dj-introduces-engine-dj-20), on standalone hardware too | Works with Denon gear without a laptop. |
| Ableton Live | Built in | Add TDAbleton for clip and knob control beyond tempo. |
| Pioneer CDJs, no laptop | Not Link | Use Open Beat Control to send beats as OSC. It can't share a computer with rekordbox. |

Link only helps when the DJ turns it on. If they don't, the audio beat tracker takes over automatically.

### Later: the optional crowd layer

If you want the crowd involved beyond phone votes, add a second, wide camera on the dance floor and compute *Crowd Sync*: split each beat into 8 slices, add crowd motion to the current slice every frame, and score how unevenly it piles up. A room bouncing together scores high and pushes the crystal visuals harder. Treat this as a phase 2 feature, after the booth rig works.

## Where the art comes from

The visuals are stacked from five layers, and you make or control every one of them. Photos are the fastest way to build a big library; the paintings become the signature layer rather than the only one.

| Layer | Where it comes from | Role in the picture |
| --- | --- | --- |
| Live crystal | The booth camera, every show | The main texture. Its refractions, sparkle and color differ every night. |
| Photo deck | Any JPG, PNG or TIFF dropped into `images/` | Big, varied source material the DJ warps and recolors live. |
| Paintings | Scans of ink, paint and brush strokes | Shapes, masks and overlays that give QRTZ its signature look. |
| Shader structure | GLSL code written with Claude Code or Copilot | The "world" for each BPM band: grids, ribbons, shards, feedback trails. |
| Crystal loops | Macro clips of the crystal filmed at home | Backup when the live camera fails, plus extra variety between scenes. |

**Making the painted layer:**

1. Paint on white paper with strong contrast: ink washes, single brush strokes, splatter, swirls. Variety beats polish; aim for 20 to 30 pieces.
2. Scan at 600 dpi, or photograph them flat in even light.
3. In Photoshop, convert to grayscale and push Levels until the paper is pure black and the paint is white. Export 2048 px PNGs into `textures/`. Grayscale lets TouchDesigner recolor them with any palette.
4. Pull 5 or 6 palettes from color paintings with the eyedropper and save them as hex lists in `config/settings.json`.

**Filming crystal loops:** phone on a tripod in slow motion, crystal on its base under the LED ring cycling colors, black backdrop. Shoot 10 to 20 clips of about 10 seconds each and trim them to loop. Keep them in `loops/` (ignored by Git because video is large).

### Photo deck: any image as art

Drop JPG, PNG or TIFF files into the `images/` folder on the show computer and they join the deck, no restart needed. Convert other formats to PNG first. The folder is ignored by Git, since photos are large and may be private.

**How images get in:**

- A Folder DAT watches `images/`, so new files show up in the deck within seconds.
- Two Movie File In TOPs take turns: one shows the current image while the other loads the next, so switching never stutters.
- A Fit TOP scales every image to 1280×720, so any size or shape works.
- Later option: an upload button on the phone page, operator-only behind the PIN.

**How the DJ distorts it:**

| Effect | What drives it |
| --- | --- |
| Crystal warp: the crystal's light bends the photo (Displace TOP) | Spinning the crystal |
| Liquid ripple (noise displacement) | Hand height over the dome, or a MIDI knob |
| Kaleidoscope and mirror | Spin angle sets the rotation |
| Zoom pulse | Every beat |
| Glitch slices and RGB split | The drop, or a pad (still capped by the flash limiter) |
| Feedback trails | Spin speed |
| Recolor to palette, or keep original colors | A toggle; recoloring makes any photo match the LED ring |
| Next image | Automatically every 8 or 16 bars, or a pad or phone tap; always crossfades on the bar |

**Photos that look best:** strong texture and contrast, such as macro shots, water, smoke, foliage, neon and city lights at night, architecture, rock and crystal close-ups. Busy scenes and faces turn to mush once distorted.

**Rights and privacy:** use photos you took or have the right to use, especially at paid gigs. Skip identifiable people unless they've agreed to appear on a club screen.

### How the crystal changes the visuals

The crystal shapes the picture two ways at once: as an *image* that gets processed, and as *numbers* that steer the scene.

**As an image:**

- **Source.** The camera image is mirrored, kaleidoscoped and recolored through the current palette. A Lookup TOP maps each pixel's brightness to a palette color.
- **Displacement.** The crystal's brightness bends the painted textures (Displace TOP), so the paintings seem to refract as the DJ turns the crystal.
- **Mask.** The brightest highlights reveal the painted layer only where light hits the glass.

**As numbers:**

| Crystal reading | What it drives |
| --- | --- |
| Spin angle | Rotation of the kaleidoscope and scene geometry |
| Spin speed | Trail length (feedback) and motion speed |
| Sparkle count | Particle bursts, bloom and glints on the beat |
| Overall brightness | Density of the painted layer |

**In each scene:**

| Scene (BPM band) | How the crystal shows up |
| --- | --- |
| Organic (under 100) | The crystal image slowly bends large painted washes; long, soft trails |
| Flow (100 to 125) | Each sparkle emits a ribbon that travels along the painted strokes |
| Grid (125 to 135) | The crystal image is tiled into a grid; each beat steps to a new facet; turning the base rotates the grid |
| Shards (over 135) | The crystal frame is cut into shards that burst on the drop and snap to the spin angle |

Because the camera sees the LED ring's color through the glass, the crystal on the booth and the screens always share a color. That shared glow is what tells the crowd the crystal is driving the show.

## Repo structure

The rule: keep everything an AI might edit in plain text files outside the `.toe`. TouchDesigner can link a Text DAT to a file on disk and keep the two in sync, and a component can be saved as its own external `.tox`. That gives Git real diffs and gives Copilot real files to edit.

```
qrtz/
├─ QRTZ.toe                  # main project (binary; commit, but don't expect diffs)
├─ tox/                      # one external .tox per module
│  ├─ crystal_cam.tox        # camera in, crystal texture, sparkle, rotation
│  ├─ hands.tox              # MediaPipe hands → gestures
│  ├─ tempo.tox              # Ableton Link + audio fallback
│  ├─ control.tox            # MIDI, TDAbleton, phone page
│  ├─ brain.tox
│  ├─ scenes.tox
│  ├─ output.tox
│  ├─ ui.tox                 # operator screen: program, preview, deck, monitors
│  └─ led.tox                # palette → Serial DAT → LED ring
├─ scripts/                  # Python, synced into Text DATs
│  ├─ brain_ext.py           # scene choice, smoothing, overrides
│  ├─ crystal_track.py       # marker angle and spin speed
│  ├─ gestures.py            # pinch, palm, hand height, hold timers
│  ├─ led_serial.py          # sends colors to the board
│  └─ web_callbacks.py       # Web Server DAT handlers
├─ shaders/                  # GLSL TOP pixel shaders
│  ├─ scene_organic.glsl
│  ├─ scene_flow.glsl
│  ├─ scene_grid.glsl
│  └─ scene_shards.glsl
├─ firmware/led_ring/led_ring.ino   # Arduino sketch for the LED ring
├─ web/controller.html       # phone page (HTML/CSS/vanilla JS)
├─ images/                   # photo deck: drop JPG/PNG/TIFF here (not in Git)
├─ textures/                 # scanned paintings and brush strokes
├─ loops/                    # pre-shot crystal video loops (camera fallback, not in Git)
├─ config/settings.json      # BPM bands, palettes, gesture thresholds, MIDI map
├─ PLAN.md                   # this file
├─ CLAUDE.md                 # rules for Claude Code
├─ .github/copilot-instructions.md   # same rules for Copilot
└─ .gitignore
```

The phone page and the Arduino sketch are small, self-contained files, which makes them good first tasks for Copilot.

## Build milestones

Thirteen small steps, each testable on its own. Commit to Git after every one that works. M0 to M4 give you a desk demo; M5 to M10 make it booth-ready.

- [ ] **M0 — Setup.** Install TouchDesigner (Non-Commercial key), VS Code, Node.js and the Arduino IDE. Clone this repo to `C:\Projects\qrtz`. Add the TouchDesigner MCP server to Claude Code. *Check:* ask Claude Code for the TouchDesigner build number; it answers from the running project.
- [ ] **M1 — Crystal shot.** Build the rig on the desk: black backdrop, crystal on its base, a desk lamp for now. Video Device In → a Null TOP named `crystal_out`, autofocus and auto-exposure off. *Check:* turn the base slowly; the image stays sharp and the brightness doesn't pump.
- [ ] **M2 — Tempo.** Ableton Link CHOP plus lastBeatStanding as fallback, merged into `tempo_out` (beat, BPM, bar phase, source). Test with Ableton Live or any DJ app on the same machine. *Check:* set the app to 128 BPM; TouchDesigner reads 128 and `source` says link. Turn Link off; it switches to audio within 10 seconds.
- [ ] **M3 — First scene.** One GLSL scene that uses `crystal_out` as its texture, pulses on the beat and changes scene only on the bar. *Check:* with music playing, pulses land on the kick and the crystal's sparkle is visible in the result.
- [ ] **M4 — Palettes and BPM bands.** Palettes in `settings.json`; the brain picks a scene by BPM band and cross-fades over 2 bars. *Check:* move from 90 to 128 BPM; the scene changes within 4 bars with no hard cut.
- [ ] **M4b — Photo deck.** Folder DAT on `images/`, double-buffered loading, Fit TOP, crystal warp and liquid ripple, palette recolor toggle, next image on the bar. *Check:* drop a new JPG into the folder mid-run; it joins the deck within a few seconds, and switching images never drops below 60 FPS.
- [ ] **M5 — Spin tracking.** Stick a small colored dot on the base; `crystal_track.py` outputs angle and spin speed. *Check:* one full turn by hand reads close to 360°; a still base reads spin speed near 0.
- [ ] **M6 — LED ring.** Wire the ring to the board; `led_ring.ino` takes colors over serial; `led.tox` sends the palette. *Check:* changing the palette changes the ring within a quarter second.
- [ ] **M7 — Hand gestures.** MediaPipe hands → `gestures.py` for height, pinch-hold and palm-hold, with hold timers. *Check:* reaching for a drink near the dome triggers nothing; a deliberate pinch-hold changes the palette every time.
- [ ] **M8 — DJ controls.** MIDI In CHOP mapped from `settings.json`, TDAbleton clip-to-scene link, and the phone page with a PIN. *Check:* a knob, a clip launch and a phone tap each change the visuals.
- [ ] **M8b — Operator screen.** A TouchDesigner control panel with Program and Preview windows, photo deck thumbnails, input monitors and a Take button; the venue output stays in its own fullscreen window. *Check:* stage a new image and palette in Preview while Program runs untouched; Take crossfades it in on the next bar, and the output holds 60 FPS.
- [ ] **M9 — Show mode.** Fullscreen output, the flash limiter (see Risks), and fallbacks: no camera → crystal loops, photo deck and painted textures; no Link → audio; no audio → internal clock at the last BPM. *Check:* unplug the camera and the LED board mid-set; visuals keep running and both recover when replugged. Hold 60 FPS.
- [ ] **M10 — Booth test and demo reel.** Build the final mount plate and dome, then run a 2-hour set with a DJ friend. *Check:* no crash, no accidental gestures; 60 seconds of footage showing the DJ's hand, the crystal and the screen together.

## Prompts, one per milestone

Paste into Claude Code (with the TouchDesigner MCP connected) or Copilot agent mode. Rules for both tools live in `CLAUDE.md` and `.github/copilot-instructions.md`.

1. *M1:* "Read PLAN.md. Build M1 in /project1/crystal_cam: Video Device In from my webcam, cropped to the crystal, into a Null TOP named crystal_out. Tell me where to switch off autofocus and auto-exposure, and how to check it worked."
2. *M2:* "Build M2 in /project1/tempo: an Ableton Link CHOP plus lastBeatStanding on Audio Device In. Output beat, bpm, bar_phase and source to tempo_out, preferring Link and switching to audio when Link has no peers."
3. *M5:* "Write scripts/crystal_track.py: find the colored marker in crystal_out, output angle in degrees and spin_speed, smoothed. Colors and thresholds come from config/settings.json."
4. *M6:* "Write firmware/led_ring/led_ring.ino for a WS2812 ring that reads 'R,G,B\n' lines over serial at 115200 baud, and scripts/led_serial.py that sends the current palette color through a Serial DAT no more than 30 times a second."

Write the remaining prompts the same way: point at PLAN.md, name the milestone, name the output, ask for the check.

## Risks, safety and privacy

**Photosensitivity.** Fast flashing can trigger seizures. Cap full-screen flashes at 3 per second, the common accessibility guideline, and avoid saturated red flashes. Build the limiter into the output module so no scene can bypass it.

**Booth hazards.** Drinks get spilled on booths. The dome protects the crystal, but keep the board and USB hub in a closed box off the booth surface. Aim the LED ring up into the crystal, and shade it so it never shines into the DJ's eyes.

**Network security.** The MCP bridge runs any Python it receives. Use it only on your home network and turn it off for shows. Protect the phone page with a PIN, and run it on its own port.

**Privacy.** The booth camera may catch the DJ's face; never save its frames. If you add the crowd camera later, put a small sign up saying motion drives the visuals.

**Market risk, honestly.** The software itself is hard to sell, but the rig is easy to demo and pitch: a DJ touching a glowing crystal while the screens respond is a strong 15-second clip. The likely paths to money are paid gigs and renting the rig with you as the operator. Finish M0–M4 (a few weekends), film a desk demo, and show it to a DJ or venue before building the full booth rig.

**Technical risks:**

- DJs who beatmatch by ear may never turn on Link. The audio fallback has to be solid.
- Some audio drivers block the Ableton Link CHOP on Windows; Derivative's docs suggest the free ASIO4All driver as a fix.
- Booth lights and strobes change what the camera sees. The dome, backdrop and locked exposure keep most of it out; test under real club lighting early.
- A K9 glass crystal can chip or crack if knocked. Carry a spare, or use acrylic for gigs.

## Sources

- [TouchDesigner Licensing comparison](https://derivative.ca/UserGuide/Licensing) — Derivative
- [TouchDesigner FAQ (GPU support)](https://derivative.ca/UserGuide/Frequently_Asked_Questions) — Derivative
- [Ableton Link CHOP](https://docs.derivative.ca/Ableton_Link_CHOP) — Derivative
- [TDAbleton](https://docs.derivative.ca/TDAbleton) — Derivative
- [TouchDesigner MCP Server guide, 2026](https://mcp.directory/blog/touchdesigner-mcp-complete-guide-2026) — mcp.directory
- [touchdesigner-mcp on PyPI (includes Copilot setup)](https://pypi.org/project/touchdesigner-mcp/)
- [lastBeatStanding beat detector](https://derivative.ca/community-post/asset/last-beat-standing-rocksolid-ai-based-realtime-beat-detection/74246) — Derivative community
- [MediaPipe TouchDesigner plugin](https://github.com/torinmb/mediapipe-touchdesigner) — GitHub
- [Rekordbox Ableton Link FAQ](https://rekordbox.com/pt/support/faq/ableton-link/) — rekordbox
- [Ableton Link in Serato DJ Pro](https://serato.com/dj/pro/expansions/more/abletonlink) — Serato
- [Traktor Pro 2.11 adds Ableton Link](https://synthtopia.com/?p=75959) — Synthtopia
- [Traktor Link tempo-leader request](https://community.native-instruments.com/discussion/comment/27272) — Native Instruments community
- [Engine DJ 2.0 adds Ableton Link](https://djmag.com/news/denon-dj-introduces-engine-dj-20) — DJ Mag
- [Open Beat Control](https://github.com/Deep-Symmetry/open-beat-control) — Deep Symmetry
