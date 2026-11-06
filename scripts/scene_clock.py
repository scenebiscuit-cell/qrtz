"""Turns tempo into a scene's beats and bars.

Synced into the Text DAT /project1/scenes/scene_clock. The Script CHOP "scene_logic"
calls onCook once a frame and writes the numbers the scene's shader uses: pulse (the
beat, as strong as the music is loud, fading out), step (moves the tiles to a new view every few beats), bar (counts
the bars), cells, shape and
wedges (the pattern, which only changes on a new bar) and turn (follows the crystal's
spin).

All tunable numbers come from config/settings.json.
"""

import json
import math
import random

# The numbers scene_grid.glsl uses for each tile shape.
SHAPE_NUMBERS = {'square': 0, 'hexagon': 1, 'triangle': 2, 'diamond': 3, 'radial': 4}
# The longest step anything moves in one go, so a stall doesn't make it jump.
MAX_STEP_SEC = 0.25
# A new bar can't come sooner than this fraction of a bar after the last, so a
# momentary wobble in the bar position can't count as two bars.
MIN_BAR_FRACTION = 0.5


class SceneClock:
    """Keeps the beat pulse and decides when things are allowed to change."""

    def __init__(self):
        self.pulse = 0.0
        self.step = 0
        self.bar = 0
        self.look = 0
        self.last_phase = None
        self.since_bar = math.inf
        self.since_pulse = math.inf
        self.loudness = 0.0
        self.loudness_peak = 0.0
        self.turn = 0.0
        self.last_angle = None

    def _follow_angle(self, angle, gain):
        """Adds up the crystal's turning. Its angle jumps from 360 back to 0, and a
        fraction of that would make the picture jump, so this only counts the change."""
        if self.last_angle is not None:
            change = (angle - self.last_angle + 180.0) % 360.0 - 180.0
            self.turn += math.radians(change) * gain
        self.last_angle = angle

    def _new_bar(self, phase, bars_per_sec):
        """True on the frame the bar position wraps around to a new bar."""
        wrapped = self.last_phase is not None and self.last_phase - phase > 0.5
        self.last_phase = phase
        if not wrapped or self.since_bar * bars_per_sec < MIN_BAR_FRACTION:
            return False
        self.since_bar = 0.0
        return True

    def _beat_strength(self, step, level, cfg):
        """How strong a beat's pulse is, from 0 to 1: the loudest part of the sound compared
        with the song's recent peak. Heavy sections hit fully, quiet ones gently, and
        silence gives exactly 0. The peak never falls below the floor, so faint sound
        can't count as its own peak."""
        time_constant = cfg['pulse_attack_sec'] if level > self.loudness else cfg['pulse_release_sec']
        self.loudness += (level - self.loudness) * (1.0 - math.exp(-step / time_constant))
        decay = 0.5 ** (step / cfg['pulse_peak_halflife_sec'])
        self.loudness_peak = max(self.loudness_peak * decay, self.loudness, cfg['pulse_floor_level'])
        ratio = self.loudness / self.loudness_peak
        return min(max((ratio - cfg['pulse_from']) / (cfg['pulse_full_at'] - cfg['pulse_from']), 0.0), 1.0)

    def _next_look(self, looks):
        """Any look but the current one, so every change is a visible one."""
        others = [i for i in range(len(looks)) if i != self.look % len(looks)]
        return random.choice(others) if others else 0

    def update(self, dt, bpm, beat, bar_phase, angle, level, max_flashes_per_sec, cfg):
        """Returns pulse from 0 to 1, step, bar, the look's cells, shape and wedges, and
        turn in radians."""
        self._follow_angle(angle, cfg['turn_gain'])
        step = min(dt, MAX_STEP_SEC)
        self.since_bar += step
        self.since_pulse += step
        bars_per_sec = bpm / 60.0 / cfg['beats_per_bar']

        # Each pulse brightens the picture, so very fast beats skip some to stay
        # under the flash limit.
        strength = self._beat_strength(step, level, cfg)
        self.pulse *= math.exp(-step / cfg['beat_release_sec'])
        if beat and self.since_pulse >= 1.0 / max_flashes_per_sec:
            self.pulse = max(self.pulse, strength)
            self.since_pulse = 0.0
            self.step += 1

        # The look only ever changes on the first frame of a bar.
        if self._new_bar(bar_phase, bars_per_sec):
            self.bar += 1
            if self.bar % cfg['bars_per_look'] == 0:
                self.look = self._next_look(cfg['looks'])

        look = cfg['looks'][self.look % len(cfg['looks'])]
        return {
            'pulse': self.pulse,
            'step': self.step // cfg['beats_per_view'],
            'bar': self.bar,
            'cells': look['cells'],
            'shape': SHAPE_NUMBERS[look['shape']],
            'wedges': look['wedges'],
            'turn': self.turn,
        }


# ---- TouchDesigner side -----------------------------------------------------

_settings_text = None
_settings = None
_clock = SceneClock()
_last_cook_sec = None
_last_output = None


def _all_settings():
    """Return settings.json, keeping the last good copy if the file is mid-edit
    and briefly invalid."""
    global _settings_text, _settings
    text = op('settings').text
    if text != _settings_text:
        _settings_text = text
        try:
            _settings = json.loads(text)
        except ValueError as e:
            if _settings is None:
                raise
            print('scene_clock: keeping last good settings:', e)
    return _settings


def setting(*path):
    """Read one setting. Parameter expressions call this, so they update by
    themselves when settings.json changes."""
    value = _all_settings()
    for key in path:
        value = value[key]
    return value


def _read(path, name, default):
    """Last value of one channel. A missing module reads as the default."""
    chop = op(path)
    chan = chop[name] if chop is not None else None
    value = chan[-1] if chan is not None and len(chan) > 0 else default
    return value if math.isfinite(value) else default


def onCook(scriptOp):
    """Update the clock, then write the output channels."""
    global _last_cook_sec, _last_output
    now = absTime.seconds
    dt = 0.0 if _last_cook_sec is None else max(now - _last_cook_sec, 0.0)
    _last_cook_sec = now

    scriptOp.clearScriptErrors()
    try:
        settings = _all_settings()
        bpm = _read('../tempo/tempo_out', 'bpm', settings['audio']['fallback_bpm'])
        if bpm <= 0:
            bpm = settings['audio']['fallback_bpm']
        cfg = dict(settings['scene_grid'], beats_per_bar=settings['tempo']['beats_per_bar'])
        _last_output = _clock.update(
            dt, bpm,
            _read('../tempo/tempo_out', 'beat', 0.0) > 0.5,
            _read('../tempo/tempo_out', 'bar_phase', 0.0),
            _read('../virtual_crystal/crystal_numbers_out', 'angle', 0.0),
            max(_read('../audio/audio_out', 'bass', 0.0),
                _read('../audio/audio_out', 'mids', 0.0),
                _read('../audio/audio_out', 'treble', 0.0), 0.0),
            settings['safety']['max_flashes_per_second'], cfg)
    except Exception as e:
        # Show the problem on the node, and keep outputting the last values.
        scriptOp.addScriptError('scene_clock: {}'.format(e))

    scriptOp.isTimeSlice = False
    scriptOp.clear()
    scriptOp.numSamples = 1
    if _last_output is not None:
        for name, value in _last_output.items():
            scriptOp.appendChan(name)[0] = value


def onGetCookLevel(scriptOp):
    """Cook every frame, so a beat or a new bar is never missed."""
    return CookLevel.ALWAYS
