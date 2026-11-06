"""Band smoothing and drop detection for audio.tox.

Synced into the Text DAT /project1/audio/audio_bands. The Script CHOP "bands"
calls onCook once a frame with one RMS level per band and the manual drop key,
and writes the bass, mids, treble and drop channels that end up in audio_out.

All tunable numbers come from the "audio" section of config/settings.json.
"""

import json
import math

BANDS = ('bass', 'mids', 'treble')
BEATS_PER_BAR = 4


def smooth_step(current, target, dt, attack_sec, release_sec):
    """Move current toward target: quickly when rising, slowly when falling."""
    time_constant = attack_sec if target > current else release_sec
    if time_constant <= 0:
        return target
    return current + (target - current) * (1 - math.exp(-dt / time_constant))


class DropDetector:
    """Flags big and medium drops, which show up in two ways.

    Bass return: the bass goes away for several seconds, then comes back close to
    its earlier strength. Kicks keep resetting the timer, so normal playing never
    arms it.

    Bass jump: the bass suddenly hits far harder than anything recent, which is how
    a track's first drop looks, with nothing earlier to return to.

    Neither counts in the first part of a track, where an intro's kick coming in
    would otherwise look just like a drop.
    """

    def __init__(self):
        self.reference = 0.0
        self.jump_base = 0.0
        self.last_time = None
        self.last_loud = -math.inf
        self.music_since = math.inf
        self.quiet_since = None
        self.armed = False
        self.cooldown_until = -math.inf
        self.flag_until = -math.inf
        self.last_fired = -math.inf

    def update(self, now, bass, rms, cfg, bpm):
        """Add one reading, where bass is the smoothed level and rms holds each
        band's raw level. Returns 1 while the flag is up, else 0."""
        dt = 0.0 if self.last_time is None else max(now - self.last_time, 0.0)
        self.last_time = now

        # Silence means a new track, with nothing yet to compare against. A
        # short pause right before a real drop isn't long enough to count.
        if sum(rms.values()) >= cfg['drop_min_level']:
            if now - self.last_loud > cfg['drop_silence_reset_sec']:
                self.music_since = now
                self.reference = 0.0
                self.jump_base = 0.0
                self.quiet_since = None
                self.armed = False
            self.last_loud = now

        # The recent peak falls slowly, and never below a minimum, so faint
        # sound can't pass for a strong bass.
        decay = 0.5 ** (dt / cfg['drop_reference_halflife_sec'])
        self.reference = max(self.reference * decay, cfg['drop_min_bass'])

        if bass < cfg['drop_breakdown_ratio'] * self.reference:
            if self.quiet_since is None:
                self.quiet_since = now
            if now - self.quiet_since >= cfg['drop_breakdown_sec']:
                self.armed = True
        else:
            self.quiet_since = None

        # The bass coming back uses up the breakdown even if it's too early to
        # count, or the next kick in an ordinary intro would raise the flag.
        returned = self.armed and bass >= cfg['drop_return_ratio'] * self.reference
        if returned:
            self.armed = False

        # Compared with the peak from about a second ago, because the bass takes a
        # few frames to rise and the current peak rises right along with it.
        self.jump_base += ((self.reference - self.jump_base)
                           * (1.0 - math.exp(-dt / cfg['drop_jump_lag_sec'])))
        jumped = (bass >= cfg['drop_jump_min_level']
                  and bass >= cfg['drop_jump_ratio'] * max(self.jump_base, cfg['drop_min_bass']))

        if ((returned or jumped)
                and now - self.music_since >= cfg['drop_min_music_sec']
                and now >= self.cooldown_until):
            self._fire(now, cfg, bpm)

        self.reference = max(self.reference, bass)
        return 1 if now < self.flag_until else 0

    def _fire(self, now, cfg, bpm):
        """Raise the flag, then rest so the same drop can't fire twice."""
        bar_sec = BEATS_PER_BAR * 60.0 / bpm
        self.cooldown_until = now + cfg['drop_cooldown_bars'] * bar_sec
        self.flag_until = now + cfg['drop_flag_hold_sec']
        self.last_fired = now

    def press(self, now, cfg, bpm):
        """The DJ called a drop. It skips the automatic rules and cooldown, and
        uses up any breakdown so the bass returning doesn't fire a second one.
        Presses too close together are ignored, to respect the flash limit."""
        if now - self.last_fired >= cfg['drop_manual_min_gap_sec']:
            self.armed = False
            self._fire(now, cfg, bpm)


# ---- TouchDesigner side -----------------------------------------------------

_settings_text = None
_settings = None
_levels = {band: 0.0 for band in BANDS}
_drop_flag = 0
_key_was_down = False
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


def _key_pressed(scriptOp):
    """True on the one frame the drop key goes down. Holding it does nothing more."""
    global _key_was_down
    key = scriptOp.inputs[1] if len(scriptOp.inputs) > 1 else None
    down = key is not None and key.numChans > 0 and key[0][0] > 0.5
    pressed = down and not _key_was_down
    _key_was_down = down
    return pressed


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
        bpm = _current_bpm(cfg)
        if _key_pressed(scriptOp):
            _detector.press(now, cfg, bpm)
        _drop_flag = _detector.update(now, _levels['bass'], rms, cfg, bpm)
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
