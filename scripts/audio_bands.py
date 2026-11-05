"""Band smoothing and drop detection for audio.tox.

Synced into the Text DAT /project1/audio/audio_bands. The Script CHOP "bands"
calls onCook once a frame with one RMS level per band, and writes the bass,
mids, treble and drop channels that end up in audio_out.

All tunable numbers come from the "audio" section of config/settings.json.
"""

import json
import math
from collections import deque

BANDS = ('bass', 'mids', 'treble')
BEATS_PER_BAR = 4


def smooth_step(current, target, dt, attack_sec, release_sec):
    """Move current toward target: quickly when rising, slowly when falling."""
    time_constant = attack_sec if target > current else release_sec
    if time_constant <= 0:
        return target
    return current + (target - current) * (1 - math.exp(-dt / time_constant))


def _average(values):
    values = list(values)
    return sum(values) / len(values) if values else 0.0


class DropDetector:
    """Flags a sudden, sustained jump in energy.

    Compares the average of the last short window against the average of the
    window before it. The short window is longer than one beat, so a single
    kick can't lift it far above the recent average, while a real drop lifts
    it and keeps it there.
    """

    def __init__(self):
        self.samples = deque()
        self.last_loud = -math.inf
        self.music_since = math.inf
        self.cooldown_until = -math.inf
        self.flag_until = -math.inf

    def update(self, now, energy, cfg, bpm):
        """Add one energy reading and return 1 while the flag is up, else 0."""
        short_sec = cfg['drop_short_window_sec']

        # After a stall the stored readings no longer describe "just before
        # now", so start the comparison again.
        if self.samples and now - self.samples[-1][0] > short_sec:
            self.samples.clear()
        self.samples.append((now, energy))

        horizon = now - short_sec - cfg['drop_window_sec']
        while len(self.samples) > 1 and self.samples[1][0] <= horizon:
            self.samples.popleft()

        # Music has to have been playing across the whole comparison, which
        # rules out room noise and tracks starting from silence. Silence longer
        # than the earlier window restarts the clock, so the short pause right
        # before a real drop doesn't.
        if energy >= cfg['drop_min_level']:
            if now - self.last_loud > cfg['drop_window_sec']:
                self.music_since = now
            self.last_loud = now

        warmed_up = (self.samples[0][0] <= horizon
                     and self.music_since <= horizon)
        if warmed_up and now >= self.cooldown_until:
            split = now - short_sec
            recent_avg = _average(e for t, e in self.samples if t > split)
            earlier_avg = _average(e for t, e in self.samples if t <= split)
            if recent_avg >= cfg['drop_threshold'] * earlier_avg:
                bar_sec = BEATS_PER_BAR * 60.0 / bpm
                self.cooldown_until = now + cfg['drop_cooldown_bars'] * bar_sec
                self.flag_until = now + cfg['drop_flag_hold_sec']

        return 1 if now < self.flag_until else 0


# ---- TouchDesigner side -----------------------------------------------------

_settings_text = None
_settings = None
_levels = {band: 0.0 for band in BANDS}
_drop_flag = 0
_last_cook_sec = None
_detector = DropDetector()


def _audio_settings():
    """Return the audio settings, keeping the last good copy if the file is
    mid-edit and briefly invalid."""
    global _settings_text, _settings
    text = op('settings').text
    if text != _settings_text:
        _settings_text = text
        try:
            _settings = json.loads(text)['audio']
        except (ValueError, KeyError) as e:
            if _settings is None:
                raise
            print('audio_bands: keeping last good settings:', e)
    return _settings


def setting(*path):
    """Read one audio setting. Parameter expressions call this, so they update
    by themselves when settings.json changes."""
    value = _audio_settings()
    for key in path:
        value = value[key]
    return value


def device_menu_name(device_par):
    """Find the device whose label contains settings "device". Falls back to
    the system default input if it isn't there."""
    wanted = setting('device').strip().lower()
    if wanted:
        for name, label in zip(device_par.menuNames, device_par.menuLabels):
            if wanted in label.lower():
                return name
    return 'default'


def _current_bpm(cfg):
    """BPM from tempo_out once M2 exists, otherwise the fallback from settings."""
    tempo_out = op('../tempo/tempo_out')
    bpm = tempo_out['bpm'] if tempo_out is not None else None
    if bpm is not None and bpm[0] > 0:
        return bpm[0]
    return cfg['fallback_bpm']


def _read_rms(scriptOp):
    """Raw level per band. A missing input reads as silence, and so does an
    infinite or NaN reading, which would otherwise stay in the smoothing for
    good. The filters can produce one when the audio device restarts."""
    source = scriptOp.inputs[0] if scriptOp.inputs else None
    levels = {}
    for band in BANDS:
        chan = source[band] if source is not None else None
        value = chan[0] if chan is not None else 0.0
        levels[band] = value if math.isfinite(value) else 0.0
    return levels


def onCook(scriptOp):
    """Update the bands and the drop flag, then write the output channels."""
    global _last_cook_sec, _drop_flag
    now = absTime.seconds
    dt = 0.0 if _last_cook_sec is None else max(now - _last_cook_sec, 0.0)
    _last_cook_sec = now

    scriptOp.clearScriptErrors()
    try:
        cfg = _audio_settings()
        rms = _read_rms(scriptOp)
        for band in BANDS:
            target = min(rms[band] * cfg['band_gain'][band], 1.0)
            _levels[band] = smooth_step(_levels[band], target, dt,
                                        cfg['attack_sec'], cfg['release_sec'])
        _drop_flag = _detector.update(now, sum(rms.values()), cfg,
                                      _current_bpm(cfg))
    except Exception as e:
        # Show the problem on the node, and keep outputting the last values.
        _drop_flag = 0
        scriptOp.addScriptError('audio_bands: {}'.format(e))

    scriptOp.isTimeSlice = False
    scriptOp.clear()
    scriptOp.numSamples = 1
    for band in BANDS:
        scriptOp.appendChan(band)[0] = _levels[band]
    scriptOp.appendChan('drop')[0] = _drop_flag


def onGetCookLevel(scriptOp):
    """Cook every frame, so the drop detector's history never has gaps."""
    return CookLevel.ALWAYS
