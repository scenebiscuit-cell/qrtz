# QRTZ — TouchDesigner Build Plan

QRTZ is pronounced "quartz." Plan as of Nov 3, 2026, by Nick Lax. This file is the source of truth for the project: update it here as decisions change.

## TL;DR

QRTZ is a music visualizer built in TouchDesigner where every image is light through a crystal. It runs two ways:

- **Standalone (built first, no hardware):** a virtual crystal rendered in TouchDesigner refracts your photos and paintings. The music drives it: BPM spins it and times the changes, bass pushes the facets, treble makes them sparkle, and drops set off bursts.
- **With the physical crystal (added later):** a small lit crystal sits on the DJ booth in full view of the crowd, and a camera locked on it replaces the virtual one. The DJ plays it like an instrument: turning it by hand and gesturing over it. Everything else stays the same.

Either way, tempo comes from the DJ's software through Ableton Link (Rekordbox, Serato DJ Pro, Traktor Pro, Engine DJ or Ableton Live), with beat detection from the audio as the fallback.

**Why a crystal, and why not crowd tracking:** you control the light, focus and background, so the image source is reliable every night. Crowd cameras struggle in dark, packed rooms. The physical crystal also gives the show a centerpiece nobody else has, and it stays out of the crowd's reach.

**How to build it (no new subscriptions):**

- **Claude Code in VS Code + TouchDesigner MCP** (covered by Claude Max) builds everything: node networks, scripts, shaders, the Arduino sketch and the phone page. The `touchdesigner-mcp-server` package (repo 8beeeaaat/touchdesigner-mcp) installs with one `claude mcp add` command.
- Give Claude Code one whole milestone per chat, and use the strongest model for the hard parts (shaders, the virtual crystal, tracking, the brain).

**The crowd still plays a part,** just without touching anything: phone votes on the palette, and an optional wide camera for Crowd Sync later on.

## The concept and what makes it different

Most audio visualizers are spectrum bars, tunnels or particle clouds. QRTZ has one identity: everything on screen is seen through a crystal. In standalone mode that crystal is virtual; on the booth it's a real one the crowd can watch the DJ touch, so they see cause and effect.

**Core loop:** the music sets the tempo and mood (BPM picks the visual world, and bass, mids and treble move it), the crystal supplies the lens (virtual or real), and the DJ steers it (knobs, phone, and with the real crystal, turning and gestures).

**Differentiators, in order of build priority:**

1. **A crystal as the lens.** Photos, paintings and shaders are refracted, split into rainbows and kaleidoscoped by a crystal, virtual or real, so it never looks like a stock visualizer.
2. **Locked to the music.** Ableton Link gives exact tempo and bar position from any of the five supported apps, and the audio split (bass, mids, treble, drops) moves the picture between beats, so drops land on the bar.
3. **Your own pictures.** Any photo dropped into the deck becomes source material that the music warps and recolors live.
4. **A real object on the booth (crystal stage).** The camera's close-up of a physical crystal replaces the virtual one, so every show looks slightly different and organic.
5. **The crystal's glow matches the screen (crystal stage).** An LED ring under it takes the current palette color, so the crowd sees the booth and the screens move together.
6. **Hands-on control (crystal stage).** The DJ spins the crystal's base by hand and gestures over it; the same camera reads both.
7. **Hand-painted look.** Scanned paintings and brush strokes layered over the crystal image. This is hard for anyone else to copy.

**BPM bands (starting point, tune by ear):**

| BPM band | Typical music | Visual world |
| --- | --- | --- |
| Under 100 | Hip-hop, downtempo, ballads | Slow organic shapes, painted washes, wide color fields |
| 100 to 125 | Pop, disco, house warm-up | Flowing ribbons and soft geometry |
| 125 to 135 | House, techno | Hard-edged grids, rings and lines locked to the beat |
| Over 135 | Drum and bass, dubstep, hardstyle | Fractured shards, fast cuts, high contrast |

A 70 BPM track and a 140 BPM track can feel the same (half-time), so keep a "×2 / ÷2" control for when the reading picks the wrong half.

## Standalone mode: the virtual crystal

The virtual crystal is a faceted 3D gem rendered inside TouchDesigner, ray-traced in one GLSL shader rather than built from geometry and a camera, so it takes few operators (about 1.4 ms of GPU per frame in M3 testing). It sits between the viewer and the art (photos, paintings or a shader scene) and bends the image through its facets, the way a real crystal held up to a picture would. It writes its result to the same Null TOP, `crystal_out`, that the crystal camera uses later, and it outputs the same numbers (angle, spin speed, sparkle). So the scenes, light modes and brain never need to know which crystal is live.

**What the music drives:**

| Sound | What it moves |
| --- | --- |
| BPM and bar (Link, or beat detection) | The gem's rotation (one turn every 8 bars by default), the zoom pulse on each beat, scene and photo changes on the bar |
| Bass (kick, sub) | Facet depth and refraction strength, the gem "breathing," image warp, LED ring brightness later |
| Mids (vocals, synths) | Flow and ribbon speed, slow color drift through the palette |
| Treble (hats, cymbals) | Sparkles, glints and rainbow edges, fine grain |
| Drops (a sudden jump in energy) | A kaleidoscope burst, glitch slices or a shard explosion, still under the 3-flashes-per-second limit. The virtual crystal's explosion also fires every 16 bars while the music is hitting hard, and its shards stay out for 4 bars, turning and pulsing on the beat |

**How sound gets in:** an Audio Device In CHOP listens to a line in from the DJ mixer's booth or record output through a USB audio interface. For testing at home, play music on the PC and capture it with the sound card's loopback (on many Windows PCs it's called "Stereo Mix"). `audio.tox` splits the sound into bass, mids and treble with audio filters, measures each band's level, smooths it so it doesn't flicker, and flags a drop when energy jumps well above its recent average. The band edges, band gains and smoothing live in `config/settings.json`, along with the input: `audio.device` is matched against part of the device name ("Stereo Mix" at home, your USB interface at a gig), and an unmatched name falls back to the system default input.

**How a drop is detected:** either of two things raises the flag. *Bass return:* the bass stays below 35% of its recent peak for at least 4 seconds, then returns to 70% of it. Kicks keep resetting that timer, so normal playing never arms it. *Bass jump:* the bass hits at least twice its recent peak, and at least 0.3 on the level meter, which is how a track's first drop looks with nothing earlier to return to. Nothing fires in a track's first 30 seconds, and 3 seconds of near-silence counts as a new track, while a short pause right before a real drop doesn't. The trade-offs: a track whose first drop comes within 30 seconds is missed, and so is any drop where the bass neither returns from a long gap nor jumps, such as a track that's bass-heavy all the way through. A second rule that watched the whole mix stepping up was tried and removed: it caught one unusual track's main drop, but on the typical tracks it only fired false alarms, one of which blocked a real drop. For what the rule can't hear, such as a track that's bass-heavy from start to finish, the DJ can call a drop with the `J` key (`drop_manual_key`, and MIDI note 41 once M9 is built). A press raises the same flag and skips the rule and its cooldown, and it's ignored if it comes within half a second of the last drop. After a flag, the detector rests for `drop_cooldown_bars` (8 bars, using `tempo_out` BPM from M2 on and `fallback_bpm` until then).

**Which crystal is live:** `image_source` in `settings.json` is `auto` by default: the crystal camera when one is connected and showing a crystal, the virtual crystal otherwise. MIDI note 40 or the operator screen can force either one.

## Cost, licensing and hardware

The software is free until you take paid gigs. Standalone mode needs no hardware beyond the computer and a way to get sound in; the booth rig for the crystal stage is a handful of low-cost parts. Check current prices when you shop.

**Software**

| Item | Cost | Notes |
| --- | --- | --- |
| [TouchDesigner Non-Commercial](https://derivative.ca/UserGuide/Licensing) | Free | Use the current official build, 2025.33230 (Sep 2026), or newer. Output capped at 1280×1280; not allowed for paid work. Render at 1280×720 while prototyping. |
| [TouchDesigner Commercial](https://derivative.ca/UserGuide/Licensing) | $600 one-time | Needed for paid gigs. One key, movable between computers. |
| [Ableton Link CHOP](https://docs.derivative.ca/Ableton_Link_CHOP) | Built in | Tempo, bar ramp and beat pulses from any Link app on the network. |
| [TDAbleton](https://docs.derivative.ca/TDAbleton) | Built in | Deeper Ableton Live control (clips, devices, tracks). Needs Live 11.1.5 or newer. |
| [lastBeatStanding](https://derivative.ca/community-post/asset/last-beat-standing-rocksolid-ai-based-realtime-beat-detection/74246) | Free for non-commercial use | Audio beat tracker. Fallback when the DJ isn't using Link. Needs TouchDesigner 2025.32280 or newer, which the current build covers. **Paid gigs need a decision:** its code is GPL v3, but its model weights are CC BY-NC-SA 4.0, so commercial use needs permission from the [madmom](https://github.com/CPJKU/madmom) authors. Before taking paid work, get that permission or replace the fallback. Kept out of Git (see `tox/vendor/README.md`) because this repo is public. |
| [MediaPipe plugin](https://github.com/torinmb/mediapipe-touchdesigner) | Free, open source | Hand tracking for the DJ's gestures (crystal stage). One person at close range is what it does best. |
| [Open Beat Control](https://github.com/Deep-Symmetry/open-beat-control) | Free, open source | Optional: reads beats from Pioneer CDJ networks and sends OSC, for booths with CDJs and no laptop. |

**Getting sound in (standalone and gigs):** at home, the PC's own loopback costs nothing. At a gig, a small USB audio interface fed from the mixer's booth or record output gives a clean signal; you may already own one.

**Booth rig (crystal stage)**

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

## Desk prototype: budget and build

This is for the crystal stage (M10 onward); standalone mode needs none of it, so the parts can wait until the standalone visualizer works. The goal is a demo under $100 that proves the physical loop on a desk, before any booth gear: a crystal on a spinning base, a camera reading its light, the screen responding, and the LED ring matching the palette once M12 is in.

**Budget** (rough US retail estimates from 2026; check current prices before buying):

| Part | Est. cost | Notes |
| --- | --- | --- |
| TouchDesigner Non-Commercial | $0 | Free. Enough for the demo, capped at 1280×1280. |
| Lazy-susan bearing (base) | $8–12 | Small, spins with one finger. |
| Faceted acrylic crystal | $5–15 | Cheap and won't shatter. Skip K9 glass for the prototype. |
| Addressable LED ring (WS2812, 16–24 LEDs) | $8–12 | Needed from M12. |
| Arduino-compatible board (Nano or Uno clone) | $8–12 | Needed from M12. |
| 5V power supply (about 2A) | $6–10 | Powers the LED ring, from M12. |
| USB webcam | $0–25 | $0 if you already have one. |
| Matte black foam board (backdrop) | $3–5 | Keeps the camera seeing only light in the glass. |
| Clear top disc | $0 | A clear plastic lid works. The crystal sits on it and the LED ring shines up through it. |
| Base board | $0 | Scrap wood or thick card, about 30 × 30 cm. |
| Colored marker dot | $0 | A sticker on the bearing's top plate, for spin tracking (M11). |
| Jumper wires, USB cable, tape or glue | $5–10 | Enough for a desk mount. |
| **Total** | **about $45–90** | Under $100 with a new webcam. About $35–65 if you reuse one. |

**To stay under $100:** leave out the LED ring and board until M12 (saves about $15–25), and reuse your webcam and desk lamp. Your lamp is not on the list.

**Build steps:**

1. Fix the bearing to the base board.
2. From M12: fix the LED ring to the base board inside the bearing's open center, so the ring stays still while the bearing turns and its wires never twist. Check that the ring fits the opening before you buy (a 16-LED ring is about 4.5 cm across, a 24-LED ring about 6.6 cm).
3. Lay the clear disc on the bearing and center the crystal on it.
4. Put the black foam board 10–15 cm behind the crystal.
5. Mount the webcam on a gooseneck or a stack of books, 25–40 cm away and a little above, framed on the crystal plus the space just above it, so a hand can enter the shot.
6. Light the crystal with the desk lamp.
7. Stick one small colored dot on the bearing's top plate for spin tracking (M11).
8. Connect the webcam to the laptop and open the project (M10).

A design version of this rig (exploded view, stages and test plan, signal flow) is on the "QRTZ Desk Prototype" canvas.

**Demo clip:** film 15 seconds of a hand turning the base while the screen responds. That clip is what you show DJs and venues. Before the rig exists, a screen recording of the standalone visualizer on a strong track does the same job.

## How it works

Eleven modules, each its own `.tox`, pass data down through Null operators named `*_out`. The brain is the only module that makes decisions, so every other piece stays simple and swappable.

```
 DJ software      Sound in          Booth controls          Crystal (the lens)
 (Link, 5 apps)   (line in, mic,    (MIDI, Ableton, phone)  virtual crystal, or the
      |            or loopback)            |                crystal camera <--------+
      v                v                   v                       |                |
 Tempo            Audio             Control                 virtual_crystal.tox or  |
 tempo.tox        audio.tox         control.tox             crystal_cam.tox +       |
 Link first,      bass, mids,       MIDI In CHOP,           hands.tox: crystal_out, |
 audio fallback   treble, drops     TDAbleton, phone+PIN    sparkle, spin, gestures |
      |                |                   |                       |                |
      +----------------+-------------------+-----------------------+                |
                                    v                                               |
                             Brain (brain.tox)                                      |
   BPM band picks scene - changes land on the bar - 2-bar cross-fades               |
   auto-picks the live crystal - DJ controls win - every input has a fallback       |
                                    |                                               |
                                    v                                               |
                             Scenes (scenes.tox)                                    |
   crystal_out as the lens - 4 GLSL worlds - photo deck - painted textures          |
                  |                    |                         |                  |
                  v                    v                         v                  |
         Output (output.tox)    Operator (ui.tox)         LED ring (led.tox) -------+
         flash limiter,         program, preview,         palette -> Serial -> Arduino
         fullscreen             deck, monitors            (crystal stage only)
```

With the physical crystal, the right-hand loop is physical: the LED ring takes the screen's palette, lights the crystal, and the camera sees that light. If any input drops, the brain carries on with the rest; losing the crystal camera falls back to the crystal loops, then to the virtual crystal.

### Operator screen: preview and program

The operator gets a control window on the show computer's own screen or a small second monitor, while the venue screens show only the live output. It works like a video switcher.

- **Program:** exactly what the crowd sees right now.
- **Preview:** the next scene, image or palette with your current settings, at half resolution. Tweak it here, press Take, and it crossfades into Program on the next bar.
- **Photo deck strip:** thumbnails of every image in `images/`; click one to load it into Preview. Drag image files onto the window to add them to the deck.
- **Input monitors:** tempo source and BPM, the bass, mids and treble levels, which crystal is live (virtual or camera), the crystal camera, spin angle, the gesture being detected, and a red flag when any input has dropped to its fallback.
- **Live controls:** sliders for warp, ripple, intensity, how strongly each audio band moves the picture, and LED brightness, mirrored to the MIDI box.

Preview costs extra GPU, so it renders at 640×360 and pauses when nothing is staged. Later, the phone page can show a small Program thumbnail so you can check the screens from across the room.

## How the DJ plays it

In standalone mode the music itself is the main controller, and the DJ or operator steers with knobs, the phone and the operator screen. The crystal stage adds turning the crystal and gesturing over it. Every gesture needs a short hold (about half a second) so a passing hand never fires it by accident.

| Control | How it's read | What it does |
| --- | --- | --- |
| The music: bass, mids, treble, drops | `audio.tox` on the line in | See "What the music drives" above |
| Link tempo and bar | Ableton Link CHOP | Beat pulses, scene changes on the bar, BPM band |
| Ableton clips and knobs | TDAbleton | Launching a clip can switch scenes; a Live macro knob can drive any parameter |
| Knobs and pads | Optional MIDI controller | Scene select, intensity, LED brightness, blackout, light mode (note 39), which crystal is live (note 40), call a drop (note 41) |
| Phone page | Web Server DAT | Backup controls and photo upload for you (behind the PIN); palette votes for the crowd |
| Spin the base (crystal stage) | Camera tracks a small colored dot on the base | Rotation angle turns the visuals; spin speed sets motion intensity |
| Hand height over the dome (crystal stage) | MediaPipe hand tracking | Higher hand = more bloom and density |
| Pinch and hold (crystal stage) | MediaPipe hand tracking | Next palette (screen and LED ring together) |
| Open palm, held 2 seconds (crystal stage) | MediaPipe hand tracking | Freeze the current frame until the palm lifts |

For the crystal stage, start with one camera framed on the crystal plus the space just above the dome, so it sees both the crystal and the DJ's hand. If the crystal shot needs to be tighter, add a second webcam for hands.

### Tempo sync per DJ app

Ableton Link works the same in every app that supports it, so TouchDesigner needs one Ableton Link CHOP for every setup, with no per-app option or settings. TouchDesigner only *listens* to the tempo and never sets it, so it can't fight the DJ. Link has no listen-only mode, and an app that joins a session TouchDesigner is already in takes on TouchDesigner's tempo (tested: a peer joining at 128 was pulled to 120). So `tempo.tox` stays out of Link and hears peers announce themselves on the network, joining only once one appears and leaving when the last one goes. Rekordbox held its tempo when tested on M2. **Open issue:** one join by a stand-in test peer was still pulled from 128 to 120, cause not yet known, though other joins held. Set the tempo again if a DJ app jumps when Link connects, and re-test this before relying on Link at a gig.

`tempo_out` has `beat` (a one-frame pulse), `bpm`, `bar_phase` (0 to 1 across the bar) and `source` (2 = link, 1 = audio, 0 = clock; the `source_name` DAT shows it as a word). If neither Link nor audio is usable, an internal clock carries on at the last BPM, so the output never stops. Audio has to produce beats for `audio_settle_sec` before it's trusted, and its BPM is measured from the last 16 beat gaps because the tracker's own number jumps around. The tracker counts beats but can't hear the downbeat, so **with audio as the source, `bar_phase` is a count from wherever it started, not the true bar**. Only Link gives the real bar.

| App | Link support | What to know |
| --- | --- | --- |
| [Rekordbox](https://rekordbox.com/en/support/faq/ableton-link/) | LINK button at the top of the screen in PERFORMANCE mode | Tested on M2. With a DJ controller plugged in, its tempo slider can't change the Link BPM; use the Link subscreen (right-click LINK). |
| [Serato DJ Pro](https://serato.com/dj/pro/expansions/more/abletonlink) | Since Serato DJ 1.9.3 | A Link toggle sits where each deck's Sync button would be. |
| Traktor Pro | Since [Traktor Pro 2.11](https://synthtopia.com/?p=75959) | Users report decks can't become the Link tempo leader. Fine here, since TouchDesigner only listens. |
| Engine DJ | Since [Engine DJ 2.0](https://djmag.com/news/denon-dj-introduces-engine-dj-20), on standalone hardware too | Works with Denon gear without a laptop. |
| [VirtualDJ](https://www.ableton.com/en/link/products/) | Yes | A [Bonedo guide](https://www.bonedo.de/artikel/virtualdj-basics-ableton-link-installieren-und-aktivieren/) says it's added once through the effects list, not on by default. |
| [djay Pro](https://help.algoriddim.com/user-manual/djay-pro-windows/dj-tools/performance-tools/ableton-link) | Yes, from the main menu | Mac, Windows and iOS. |
| Mixxx | No native support found | Uses the audio tracker. |
| Ableton Live | Built in | Add TDAbleton for clip and knob control beyond tempo. |
| Logic Pro | [Listed by Ableton](https://www.ableton.com/en/link/products/); Mac since 10.7.5 per a news report | [iPad steps](https://support.apple.com/guide/logicpro-ipad/lpip7da90b7c/ipados) are documented; the Mac menu path isn't confirmed. |
| [Pro Tools](https://cdm.link/all-versions-of-pro-tools-now-support-ableton-link/) | Since 2020.9, all editions | Has a Link button. |
| [Bitwig Studio](https://musicradar.com/news/bitwig-studio-gets-ableton-link-now-you-can-sync-it-with-live-and-other-apps) | Since 2.2 | |
| [Reason](https://www.ableton.com/en/link/products/) | Yes | |
| Cubase | Unclear | Ableton's list includes it, but [Steinberg forum users](https://forums.steinberg.net/t/ableton-link-sync-with-cubase/132247) report no Link. Test before relying on it. |
| Studio One | Unclear | One [user report](https://community.native-instruments.com/discussion/comment/233054) of Link in 7.2.1, another source says no. Test before relying on it. |
| Reaper | Third-party only | Through the [ReaBlink extension](https://www.kvraudio.com/forum/viewtopic.php?p=8918837), per forum reports. |
| FL Studio | No native support found | [Users were still asking in 2026](https://forum.image-line.com/viewtopic.php?p=1863571). Uses the audio tracker. |
| Pioneer CDJs, no laptop | Not Link | Use Open Beat Control to send beats as OSC. It can't share a computer with rekordbox. |

This table comes from published sources, some of them forum posts. Rekordbox is the only one tested with QRTZ so far (on M2).

Link only helps when the DJ turns it on. If they don't, or the app has no Link, the audio beat tracker takes over automatically.

### Later: the optional crowd layer

If you want the crowd involved beyond phone votes, add a second, wide camera on the dance floor and compute *Crowd Sync*: split each beat into 8 slices, add crowd motion to the current slice every frame, and score how unevenly it piles up. A room bouncing together scores high and pushes the crystal visuals harder. Treat this as a phase 2 feature, after the booth rig works.

## Where the art comes from

The visuals are stacked from six layers, and you make or control every one of them. Photos are the fastest way to build a big library; the paintings become the signature layer rather than the only one.

| Layer | Where it comes from | Role in the picture |
| --- | --- | --- |
| Virtual crystal | Rendered in TouchDesigner | The lens in standalone mode: refracts photos and paintings, driven by the music. |
| Live crystal | The booth camera (crystal stage) | Replaces the virtual crystal. Its refractions, sparkle and color differ every night. |
| Photo deck | Any JPG, PNG or TIFF dropped into `images/` | Big, varied source material that the music and the DJ warp and recolor live. |
| Paintings | Scans of ink, paint and brush strokes | Shapes, masks and overlays that give QRTZ its signature look. |
| Shader structure | GLSL code written with Claude Code | The "world" for each BPM band: grids, ribbons, shards, feedback trails. |
| Crystal loops | Macro clips of the crystal filmed at home (crystal stage) | Backup when the live camera fails, plus extra variety between scenes. |

**Making the painted layer:**

1. Paint on white paper with strong contrast: ink washes, single brush strokes, splatter, swirls. Variety beats polish; aim for 20 to 30 pieces.
2. Scan at 600 dpi, or photograph them flat in even light.
3. In Photoshop, convert to grayscale and push Levels until the paper is pure black and the paint is white. Export 2048 px PNGs into `textures/`. Grayscale lets TouchDesigner recolor them with any palette.
4. Pull 5 or 6 palettes from color paintings with the eyedropper and save them as hex lists in `config/settings.json`.

**Filming crystal loops (crystal stage):** phone on a tripod in slow motion, crystal on its base under the LED ring cycling colors, black backdrop. Shoot 10 to 20 clips of about 10 seconds each and trim them to loop. Keep them in `loops/` (ignored by Git because video is large).

### Photo deck: any image as art

Drop JPG, PNG or TIFF files into the `images/` folder on the show computer and they join the deck, no restart needed. Convert other formats to PNG first. The folder is ignored by Git, since photos are large and may be private.

**How images get in:**

- A Folder DAT watches `images/`, so new files show up in the deck within seconds.
- Drag image files onto the operator screen; they're copied into `images/`.
- Upload from your phone through the phone page, operator-only behind the PIN (with M9).
- Two Movie File In TOPs take turns: one shows the current image while the other loads the next, so switching never stutters.
- A Fit TOP scales every image to 1280×720, so any size or shape works.

**How the music and the DJ distort it:**

| Effect | What drives it |
| --- | --- |
| Refraction: the photo seen through the crystal's facets | The virtual crystal's rotation and bass, or spinning the real crystal |
| Liquid ripple (noise displacement) | Bass, hand height over the dome, or a MIDI knob |
| Kaleidoscope and mirror | BPM (virtual crystal) or spin angle (real crystal) sets the rotation |
| Rainbow dispersion on edges | Treble |
| Zoom pulse | Every beat |
| Glitch slices and RGB split | The drop, or a pad (still capped by the flash limiter) |
| Feedback trails | Mids, or spin speed with the real crystal |
| Recolor to palette, or keep original colors | A toggle; recoloring makes any photo match the show (and the LED ring) |
| Next image | Automatically every 8 or 16 bars, or a pad or phone tap; always crossfades on the bar |

**Photos that look best:** strong texture and contrast, such as macro shots, water, smoke, foliage, neon and city lights at night, architecture, rock and crystal close-ups. Busy scenes and faces turn to mush once distorted.

**Rights and privacy:** use photos you took or have the right to use, especially at paid gigs. Skip identifiable people unless they've agreed to appear on a club screen.

### How the crystal changes the visuals

The crystal, virtual or real, shapes the picture two ways at once: as an *image* that gets processed, and as *numbers* that steer the scene. Both crystals write to the same `crystal_out` and the same numbers, so this section applies to either.

**As an image:**

- **Source.** The crystal image is mirrored, kaleidoscoped and recolored through the current palette. A Lookup TOP maps each pixel's brightness to a palette color.
- **Displacement.** The crystal's brightness bends the painted textures and photos (Displace TOP), so they seem to refract as the crystal turns.
- **Mask.** The brightest highlights reveal the painted layer only where light hits the glass.

**As numbers:**

| Crystal reading | What it drives | Virtual crystal | Real crystal |
| --- | --- | --- | --- |
| Spin angle | Rotation of the kaleidoscope and scene geometry | From BPM: one turn every 8 bars | From the marker dot |
| Spin speed | Trail length (feedback) and motion speed | From BPM and mids | How fast the DJ turns it |
| Sparkle count | Particle bursts, bloom and glints on the beat | From treble | Bright points in the camera image |
| Overall brightness | Density of the painted layer | From bass | Camera brightness |

**In each scene:**

| Scene (BPM band) | How the crystal shows up |
| --- | --- |
| Organic (under 100) | The crystal image slowly bends large painted washes; long, soft trails |
| Flow (100 to 125) | Each sparkle emits a ribbon that travels along the painted strokes |
| Grid (125 to 135) | The crystal image is tiled into a grid; each beat steps to a new facet; the crystal's turn rotates the grid |
| Shards (over 135) | The crystal frame is cut into shards that burst on the drop and snap to the spin angle |

With the real crystal, the camera sees the LED ring's color through the glass, so the crystal on the booth and the screens always share a color. That shared glow is what tells the crowd the crystal is driving the show.

### Light modes: hanging crystal and kaleidoscope

Two alternate looks sit on top of the scenes. The DJ picks one with MIDI note 39, the operator screen, or the phone page. They use `crystal_out`, so they work with either crystal.

- **Scene (default):** the BPM-band worlds described above.
- **Hanging crystal:** the picture imagines the crystal hanging from a thread above a light. Light passing through its facets forms caustics (bright, curved lines where light focuses), rainbow dispersion at the edges, and a slow pendulum sway. The shader finds edges in `crystal_out` (brightness gradients) and reads the red, green and blue channels at slightly different offsets along them, which splits the light into color. A damped sway offsets the sampling point, and each beat kicks it.
- **Kaleidoscope:** the crystal image is mirrored into 3 to 12 wedges around the center. The spin angle rotates the wedges. Each beat gives a small zoom pulse, still held under the flash limiter.

| Mode | Crystal reading | Beat | DJ control |
| --- | --- | --- | --- |
| Hanging crystal | Spin angle turns the light direction; sparkle adds glints | Pendulum kick | Dispersion (how strong the rainbows are) |
| Kaleidoscope | Spin angle rotates the wedges; brightness sets wedge glow | Zoom pulse | Wedge count, 3 to 12 |

Switching modes lands on the bar and cross-fades over one bar.

## Repo structure

The rule: keep everything an AI might edit in plain text files outside the `.toe`. TouchDesigner can link a Text DAT to a file on disk and keep the two in sync, and a component can be saved as its own external `.tox`. That gives Git real diffs and gives Claude Code real files to edit.

```
qrtz/
├─ QRTZ.toe                  # main project (binary; commit, but don't expect diffs)
├─ tox/                      # one external .tox per module
│  ├─ vendor/                # third-party components, downloaded, not in Git (see its README)
│  ├─ audio.tox              # line in → bass, mids, treble, drops (audio_out)
│  ├─ tempo.tox              # Ableton Link + audio fallback (tempo_out)
│  ├─ virtual_crystal.tox    # 3D gem that refracts the art → crystal_out
│  ├─ crystal_cam.tox        # camera in, crystal texture, sparkle, rotation → crystal_out
│  ├─ hands.tox              # MediaPipe hands → gestures
│  ├─ control.tox            # MIDI, TDAbleton, phone page
│  ├─ brain.tox              # scene choice, live crystal, fallbacks
│  ├─ scenes.tox
│  ├─ output.tox
│  ├─ ui.tox                 # operator screen: program, preview, deck, monitors
│  └─ led.tox                # palette → Serial DAT → LED ring
├─ scripts/                  # Python, synced into Text DATs
│  ├─ brain_ext.py           # scene choice, smoothing, overrides, live crystal
│  ├─ audio_bands.py         # band smoothing and drop detection
│  ├─ tempo_source.py        # chooses Link, audio or clock; joins Link only after hearing a peer
│  ├─ crystal_motion.py      # virtual crystal: tempo and audio to angle, spin speed, sparkle
│  ├─ crystal_track.py       # marker angle and spin speed
│  ├─ scene_clock.py         # scenes: beat pulse, and changes that only land on a new bar
│  ├─ gestures.py            # pinch, palm, hand height, hold timers
│  ├─ led_serial.py          # sends colors to the board
│  └─ web_callbacks.py       # Web Server DAT handlers
├─ shaders/                  # GLSL shaders
│  ├─ crystal_gem.glsl       # virtual crystal: shared ray-traced gem, refraction and dispersion through facets
│  ├─ crystal_refract.glsl   # virtual crystal: draws the main gem
│  ├─ crystal_small.glsl     # virtual crystal: draws the small gem into its own small image
│  ├─ crystal_figure.glsl    # virtual crystal: draws the small figures (melting smiley, dolphin tablet)
│  ├─ dolphin_field.glsl     # virtual crystal: works out the dolphin's distances once, for the pill
│  ├─ crystal_blobs.glsl     # virtual crystal: small lava-lamp blobs that morph out and drift away
│  ├─ crystal_layers.glsl    # virtual crystal: puts the main gem and small one together by depth
│  ├─ crystal_shatter.glsl   # virtual crystal: shards on a drop, gem over the dimmed image
│  ├─ test_pattern.glsl      # grid test image until the photo deck arrives in M5
│  ├─ scene_organic.glsl
│  ├─ scene_flow.glsl
│  ├─ scene_grid.glsl
│  ├─ scene_shards.glsl
│  ├─ light_hanging.glsl     # hanging-crystal caustics and dispersion
│  └─ light_kaleido.glsl     # kaleidoscope wedges
├─ firmware/led_ring/led_ring.ino   # Arduino sketch for the LED ring
├─ web/controller.html       # phone page (HTML/CSS/vanilla JS)
├─ images/                   # photo deck: drop JPG/PNG/TIFF here (not in Git)
├─ textures/                 # scanned paintings and brush strokes
├─ loops/                    # pre-shot crystal video loops (camera fallback, not in Git)
├─ config/settings.json      # BPM bands, audio bands, palettes, crystals, gestures, MIDI map
├─ PLAN.md                   # this file
├─ CLAUDE.md                 # rules for Claude Code
├─ .github/copilot-instructions.md   # older copy of the rules; treat as project notes
└─ .gitignore
```

The phone page and the Arduino sketch are small, self-contained files, which makes them good first tasks for Claude Code.

## Build milestones

Seventeen small steps in four stages, each testable on its own. Commit to Git after every one that works.

- **Stage A, standalone visualizer (M0–M9):** no hardware needed. At the end you have a working music visualizer with your photos and a virtual crystal.
- **Stage B, add the crystal (M10–M13):** the desk prototype, camera, spin tracking, LED ring and gestures.
- **Stage C, show-ready (M14–M15):** show mode, fallbacks and a booth test.
- **Stage D, share it (M16):** a demo people can try without installing anything, to help get gigs and test interest in selling QRTZ.

**Stage A: standalone visualizer**

- [x] **M0 — Setup.** Install TouchDesigner 2025.33230 or newer (Non-Commercial key), VS Code, Node.js and the Arduino IDE. Clone this repo to `C:\Projects\qrtz`. Add the TouchDesigner MCP server to Claude Code. *Check:* ask Claude Code for the TouchDesigner build number; it answers from the running project.
- [x] **M1 — Audio.** Audio Device In from loopback or a line in; `audio.tox` splits it into bass, mids and treble, smooths each band, and flags drops, into `audio_out`. Band edges and smoothing come from `settings.json`. *Check:* play a track with a clear kick; bass jumps on every kick, treble follows the hats, and a drop raises the drop flag once, not on every beat.
- [x] **M2 — Tempo.** Ableton Link CHOP plus lastBeatStanding as fallback, fed from `audio_raw_out` in `audio.tox` and merged into `tempo_out` (beat, BPM, bar phase, source). Test with Ableton Live or any DJ app on the same machine. *Check:* with music playing, set the app to 128 BPM and turn on Link; the app stays at 128, TouchDesigner reads 128 and `source` says link. Turn Link off; it switches to audio within 10 seconds.
- [x] **M3 — Virtual crystal.** `virtual_crystal.tox`: a faceted gem rendered over a test image, with `crystal_refract.glsl` bending the image through the facets and splitting edges into color. It turns once every 8 bars, sways, breathes on bass, kicks on the beat, sparkles on treble, explodes into shards that reform on a drop, and changes crystal shape every 90 seconds, taking turns between morphing in place and shrinking away to return as the next shape. Every few bars, the gem glides to a new way of moving: a different spin speed, sometimes reversed, with a different sway and lean. With no music it just turns steadily. Every so often a blob buds off, becomes a small crystal, orbits the main gem in 3D, passing in front and behind, then returns to be absorbed. It makes many passes on a smooth, tempo-following orbit that glides to a new plane every few bars and sometimes reverses, never lingers over the main gem, moves like the main gem with its own timing and a little more of each motion, and on each beat swells softly and melts part of the way back to a blob. Every few seconds a small lava-lamp blob morphs out of the main gem or the small object, wobbles and drifts out of the picture, in the color of whatever it came from. Without music it still spins and refracts but doesn't pulse: the pulse follows the loudest band compared with the song's recent peak, so a sound at the front of the mix drives it, with or without bass, and quiet sounds behind the mix don't. It writes `crystal_out` plus angle, spin speed and sparkle. *Check:* with music playing, the gem turns in time, the facets push on the kick, the edges glint on the hats, and a drop blows it apart and brings it back; stop the music and the pulsing stops; every 90 seconds the shape changes smoothly; the output holds 60 FPS.
- [x] **M4 — First scene.** One GLSL scene that uses `crystal_out` as its lens, pulses on the beat and changes scene only on the bar. This is the Grid scene in `scenes.tox`, output to `scenes_out`. With only one scene so far, its pattern is what changes: square, hexagon, triangle, diamond or one big kaleidoscope, listed as `looks` in settings, every 4 bars and always on a new bar. The tiles move to a new view every 8 beats, while the push-in and brightening stay on every beat, as strong as the music is loud compared with its recent peak. M5 adds the cross-fades and other scenes. The blobs form into hearts (`droplet_shape`), which for now applies to `crystal_out` as a whole. *Check:* with music playing, pulses land on the kick and the crystal's sparkle is visible in the result.
- [ ] **M5 — Palettes and BPM bands.** Palettes in `settings.json`; the brain picks a scene by BPM band and cross-fades over 2 bars. *Check:* move from 90 to 128 BPM; the scene changes within 4 bars with no hard cut.
- [ ] **M6 — Photo deck.** Folder DAT on `images/`, double-buffered loading, Fit TOP, refraction through the crystal, liquid ripple on bass, dispersion on treble, palette recolor toggle, next image on the bar. *Check:* drop a new JPG into the folder mid-run; it joins the deck within a few seconds, the music visibly moves it, and switching images never drops below 60 FPS.
- [ ] **M7 — Light modes.** `light_hanging.glsl` (caustics, rainbow dispersion, pendulum sway kicked on each beat) and `light_kaleido.glsl` (3 to 12 wedges, rotated by the crystal's angle), selected from `settings.json` with MIDI note 39. *Check:* the hanging mode shows rainbow edges that sway on the kick; the kaleidoscope with 6 wedges turns in time with the virtual crystal; switching lands on the bar.
- [ ] **M8 — Operator screen.** A TouchDesigner control panel with Program and Preview windows, photo deck thumbnails (drag files in to add them), audio and tempo monitors, the live-crystal indicator and a Take button; the venue output stays in its own fullscreen window. *Check:* stage a new image and palette in Preview while Program runs untouched; Take crossfades it in on the next bar, and the output holds 60 FPS.
- [ ] **M9 — DJ controls.** MIDI In CHOP mapped from `settings.json`, TDAbleton clip-to-scene link, and the phone page with a PIN (backup controls, photo upload, palette votes). *Check:* a knob, a clip launch and a phone tap each change the visuals, and a photo uploaded from the phone joins the deck.

**Stage B: add the crystal**

- [ ] **M10 — Crystal shot.** Build the desk prototype (see "Desk prototype" above): black backdrop, crystal on its bearing, a desk lamp for now. Video Device In → `crystal_cam.tox` → `crystal_out`, autofocus and auto-exposure off. With `image_source` on `auto`, the camera takes over from the virtual crystal when connected. *Check:* turn the base slowly; the image stays sharp and the brightness doesn't pump; unplugging the camera brings back the virtual crystal; your parts receipts total under $100.
- [ ] **M11 — Spin tracking.** Stick a small colored dot on the base; `crystal_track.py` outputs angle and spin speed, replacing the virtual crystal's BPM-driven numbers. *Check:* one full turn by hand reads close to 360°; a still base reads spin speed near 0.
- [ ] **M12 — LED ring.** Wire the ring to the board; `led_ring.ino` takes colors over serial; `led.tox` sends the palette. *Check:* changing the palette changes the ring within a quarter second.
- [ ] **M13 — Hand gestures.** MediaPipe hands → `gestures.py` for height, pinch-hold and palm-hold, with hold timers. *Check:* reaching for a drink near the dome triggers nothing; a deliberate pinch-hold changes the palette every time.

**Stage C: show-ready**

- [ ] **M14 — Show mode.** Fullscreen output, the flash limiter (see Risks), and fallbacks: no camera → crystal loops, then the virtual crystal; no Link → audio beat tracking; no audio → internal clock at the last BPM. *Check:* unplug the camera, the LED board and the audio mid-set; visuals keep running and each recovers when replugged. Hold 60 FPS.
- [ ] **M15 — Booth test and demo reel.** Build the final mount plate and dome, then run a 2-hour set with a DJ friend. *Check:* no crash, no accidental gestures; 60 seconds of footage showing the DJ's hand, the crystal and the screen together.

**Trying now: figures for the small crystal.** Besides a crystal, the small crystal can come out as a shape with dents and gaps, which the flat-facet method can't draw. These are built in the shader from distance math, and cut like crystal, with flat edges, rings of facets, refraction and rainbow edges, so they melt out of the glass sphere and stay part of the same world as the gems. They only appear with the virtual crystal, because the real camera crystal can't change shape. `satellite_figures` lists which ones take turns: a yellow crystal melting smiley, a teal crystal tablet with a smooth top and a dolphin recessed into it, and the plain crystal. The small object draws in its own small image, which keeps the frame rate up. This isn't a milestone yet: it depends on how they look. The smiley is drawn from scratch. The dolphin's outline is traced from an image the owner supplied, so check that image's license before selling QRTZ or using it publicly.

**Stage D: share it**

- [ ] **M16 — Shareable demo.** A demo video, plus a page that runs in a web browser, so a potential client can play with QRTZ without installing anything. It's a separate small build, not the TouchDesigner project: the crystal shaders are ported to WebGL (graphics that run in the browser), and the drop and crystal motion logic to JavaScript, with sound analyzed in the browser. Visitors get a bundled demo track or their own audio file, a drop button, and shape and palette controls. Decide before starting: whether the demo video and page count as commercial use under the Non-Commercial license (ask Derivative), and that the demo track is cleared for use. *Check:* on a computer that has never had TouchDesigner, open the link, press play, and see the crystal react and explode on the track's drop within a few seconds of the page loading.

**Later option: drops from Rekordbox's cues.** Rekordbox's automatic hot cue C landed on the drop in the 5 songs the owner has tested so far. To fire on it, QRTZ needs the cue times, plus the current track and position, which Rekordbox doesn't offer officially. [rkbx_link](https://github.com/grufkork/rkbx_link) reads them from Rekordbox's memory, needs a paid license for current versions, and only supports listed Rekordbox versions, so an update could break it. This would be an extra layer for Rekordbox only, with the automatic rule and the `J` key as the fallback. Before building: test more songs, and confirm where the automatic cues are stored and that a tool can read them.

**Later decision: selling QRTZ.** Only if the demo draws interest. Buyers could run the project with TouchPlayer, which needs a license for each paid use and doesn't make a double-click app, or QRTZ could be rebuilt as its own app. Derivative's pages don't cover reselling a project, so ask them first. The beat tracker's weights also need commercial permission or a replacement.

## Prompts, one per milestone

Paste into Claude Code with the TouchDesigner MCP connected, one milestone per chat. Its rules live in `CLAUDE.md`.

1. *M1:* "Read PLAN.md. Build M1 in /project1/audio: an Audio Device In CHOP from my loopback device, split into bass, mids and treble with band edges from config/settings.json, smoothed, plus a drop flag, all into a Null CHOP named audio_out. Explain each new operator, then tell me how to check it worked."
2. *M2:* "Build M2 in /project1/tempo: an Ableton Link CHOP plus lastBeatStanding on the raw audio from audio_raw_out in /project1/audio. Output beat, bpm, bar_phase and source to tempo_out, preferring Link and switching to audio when Link has no peers."
3. *M3:* "Build M3 in /project1/virtual_crystal: a faceted gem rendered over a test image, with shaders/crystal_refract.glsl doing refraction and dispersion through the facets. Drive rotation from tempo_out (one turn per 8 bars), facet depth from bass and sparkle from treble in audio_out. Output a Null TOP named crystal_out and a Null CHOP with angle, spin_speed and sparkle."
4. *M10:* "Build M10 in /project1/crystal_cam: Video Device In from my webcam, cropped to the crystal, into crystal_out, with the brain switching between it and the virtual crystal by image_source in settings.json. Tell me where to switch off autofocus and auto-exposure, and how to check it worked."
5. *M11:* "Write scripts/crystal_track.py: find the colored marker in crystal_out, output angle in degrees and spin_speed, smoothed. Colors and thresholds come from config/settings.json."
6. *M12:* "Write firmware/led_ring/led_ring.ino for a WS2812 ring that reads 'R,G,B\n' lines over serial at 115200 baud, and scripts/led_serial.py that sends the current palette color through a Serial DAT no more than 30 times a second."

Write the remaining prompts the same way: point at PLAN.md, name the milestone, name the output, ask for the check.

## Risks, safety and privacy

**Photosensitivity.** Fast flashing can trigger seizures. Cap full-screen flashes at 3 per second, the common accessibility guideline, and avoid saturated red flashes. Build the limiter into the output module so no scene, drop or audio spike can bypass it.

**Booth hazards.** Drinks get spilled on booths. The dome protects the crystal, but keep the board and USB hub in a closed box off the booth surface. Aim the LED ring up into the crystal, and shade it so it never shines into the DJ's eyes.

**Network security.** The MCP bridge runs any Python it receives. Use it only on your home network and turn it off for shows. Protect the phone page with a PIN, and run it on its own port.

**Privacy.** The booth camera may catch the DJ's face; never save its frames. If you add the crowd camera later, put a small sign up saying motion drives the visuals.

**Market risk, honestly.** Music visualizers are a crowded field, so standalone mode has to stand out on the crystal look and your own art, not on features. The physical rig is the easier pitch: a DJ touching a glowing crystal while the screens respond is a strong 15-second clip. The likely paths to money are paid gigs and renting the rig with you as the operator. Finish Stage A (a few weekends), record the standalone visualizer on a strong track, and show it to a DJ or venue before buying the booth parts.

**Technical risks:**

- DJs who beatmatch by ear may never turn on Link. The audio fallback has to be solid.
- A loud room or a mic picks up crowd noise; a line in from the mixer gives cleaner bass and treble readings than a microphone.
- Some audio drivers block the Ableton Link CHOP on Windows; Derivative's docs suggest the free ASIO4All driver as a fix.
- The audio beat tracker runs in Python on TouchDesigner's main thread. In M2 testing it held 60 FPS with one model (`tracker_single_model`, the default here), but only with the rest of the project still small. Re-check the frame rate once scenes exist, and try the slower 8-model ensemble only if there's headroom.
- TouchDesigner stopped cooking when its window was minimized in testing, and audio operators don't run while the timeline is paused. Never minimize it during a show, and check the timeline is playing. M14's show mode should guard against both.
- In M2 testing, a second Audio Device In on Stereo Mix read pure silence while the first one worked, with no error shown. So only `audio.tox` opens the audio device, and anything else that needs the raw signal reads `audio_raw_out`.
- The virtual crystal is a 3D render plus a refraction shader every frame. Keep the gem low-poly and watch the frame rate on the RX 9070 and the 3060 Ti.
- Booth lights and strobes change what the camera sees. The dome, backdrop and locked exposure keep most of it out; test under real club lighting early.
- A K9 glass crystal can chip or crack if knocked. Carry a spare, or use acrylic for gigs.

## Sources

- [TouchDesigner Licensing comparison](https://derivative.ca/UserGuide/Licensing) — Derivative
- [TouchDesigner FAQ (GPU support)](https://derivative.ca/UserGuide/Frequently_Asked_Questions) — Derivative
- [TouchDesigner release notes](https://docs.derivative.ca/Release_Notes) — Derivative
- [Ableton Link CHOP](https://docs.derivative.ca/Ableton_Link_CHOP) — Derivative
- [TDAbleton](https://docs.derivative.ca/TDAbleton) — Derivative
- [TouchDesigner MCP Server guide, 2026](https://mcp.directory/blog/touchdesigner-mcp-complete-guide-2026) — mcp.directory
- [touchdesigner-mcp on PyPI](https://pypi.org/project/touchdesigner-mcp/)
- [lastBeatStanding beat detector](https://derivative.ca/community-post/asset/last-beat-standing-rocksolid-ai-based-realtime-beat-detection/74246) — Derivative community
- [MediaPipe TouchDesigner plugin](https://github.com/torinmb/mediapipe-touchdesigner) — GitHub
- [Rekordbox Ableton Link FAQ](https://rekordbox.com/pt/support/faq/ableton-link/) — rekordbox
- [Ableton Link in Serato DJ Pro](https://serato.com/dj/pro/expansions/more/abletonlink) — Serato
- [Traktor Pro 2.11 adds Ableton Link](https://synthtopia.com/?p=75959) — Synthtopia
- [Traktor Link tempo-leader request](https://community.native-instruments.com/discussion/comment/27272) — Native Instruments community
- [Engine DJ 2.0 adds Ableton Link](https://djmag.com/news/denon-dj-introduces-engine-dj-20) — DJ Mag
- [Open Beat Control](https://github.com/Deep-Symmetry/open-beat-control) — Deep Symmetry
