"""Chooses the tempo source for tempo.tox and writes tempo_out.

Synced into the Text DAT /project1/tempo/tempo_source. The Script CHOP
"tempo_logic" calls onCook once a frame. Its first input is the Ableton Link
CHOP and its second is the lastBeatStanding beat tracker.

Link is preferred. When it has no peers the audio tracker takes over, and if
neither is usable an internal clock keeps running at the last known BPM, so the
output never stops. TouchDesigner only reads the Link tempo and never sets it,
which is why it joins Link only after hearing a peer (see LinkListener).

All tunable numbers come from config/settings.json.
"""

import json
import math
import socket
from collections import deque

CLOCK, AUDIO, LINK = 0, 1, 2
SOURCE_NAMES = ('clock', 'audio', 'link')
MIN_GAPS_FOR_BPM = 4
GAP_OUTLIER_FRACTION = 0.15

# Fixed by the Ableton Link protocol.
LINK_GROUP = '224.76.78.75'
LINK_PORT = 20808
LINK_HEADER = b'_asdp_v\x01'
LINK_ALIVE = b'\x01'
# After leaving, TouchDesigner's own last packets can still arrive. Ignore them
# so it doesn't rejoin because it heard itself.
LINK_OWN_ECHO_SEC = 1.0
LISTENER_REFRESH_SEC = 10.0


class TempoSelector:
    """Keeps track of which source is usable and produces one set of outputs."""

    def __init__(self, start_bpm):
        self.bpm = start_bpm
        self.bar_phase = 0.0
        self.source = CLOCK
        self.last_time = None
        self.last_link_peer = -math.inf
        self.last_audio_beat = -math.inf
        self.last_sound = -math.inf
        self.audio_since = math.inf
        self.beat_times = deque()

    def update(self, now, cfg, link, audio):
        """link and audio are dicts of readings, or None if that input is gone.

        Returns the channels for tempo_out: beat, bpm, bar_phase and source.
        """
        dt = 0.0 if self.last_time is None else max(now - self.last_time, 0.0)
        self.last_time = now

        self.source = self._choose_source(now, cfg, link, audio)
        beats_per_bar = cfg['beats_per_bar']
        last_beat_index = int(self.bar_phase * beats_per_bar)

        if self.source == LINK:
            self.bpm = link['bpm']
            self.bar_phase = link['bar_phase'] % 1.0
            beat = int(self.bar_phase * beats_per_bar) != last_beat_index
        elif self.source == AUDIO:
            self.bpm = self._measured_bpm() or audio['bpm']
            # The tracker counts beats but can't hear which one is the
            # downbeat, so this bar position is a count from where it started.
            beats_into_bar = max(audio['beat_num'], 1) - 1 + audio['phase']
            self.bar_phase = (beats_into_bar / beats_per_bar) % 1.0
            beat = audio['beat']
        else:
            bars_per_sec = self.bpm / 60.0 / beats_per_bar
            self.bar_phase = (self.bar_phase + dt * bars_per_sec) % 1.0
            beat = int(self.bar_phase * beats_per_bar) != last_beat_index

        return {
            'beat': 1 if beat else 0,
            # The multiplier fixes half-time and double-time readings. It
            # changes the reported BPM, not when the beats land.
            'bpm': self.bpm * cfg['bpm_multiplier'],
            'bar_phase': self.bar_phase,
            'source': self.source,
        }

    def _choose_source(self, now, cfg, link, audio):
        if link is not None and link['peers'] >= 1 and link['bpm'] > 0:
            self.last_link_peer = now
        link_ok = (link is not None and link['bpm'] > 0
                   and now - self.last_link_peer <= cfg['link_lost_after_sec'])

        lost_sec = cfg['audio_lost_after_sec']
        if audio is not None and audio['level'] >= cfg['audio_silence_level']:
            self.last_sound = now
        if audio is not None and audio['beat'] and audio['bpm'] > 0:
            if now - self.last_audio_beat > lost_sec:
                self.audio_since = now
                self.beat_times.clear()
            self.last_audio_beat = now
            # After the sound stops, the tracker carries on with made-up beats
            # at its own jumpy BPM. Those keep the beat going, but measuring
            # them would drag the BPM away from what was actually playing. Its
            # "synth" flag can't identify them, because it's also on for most
            # beats during music, so this goes by whether sound is arriving.
            if now - self.last_sound <= cfg['audio_silence_after_sec']:
                self.beat_times.append(now)
            while len(self.beat_times) > cfg['audio_bpm_window_beats'] + 1:
                self.beat_times.popleft()
        audio_ok = (audio is not None and audio['bpm'] > 0
                    and now - self.last_audio_beat <= lost_sec
                    and now - self.audio_since >= cfg['audio_settle_sec'])

        if cfg['prefer'] == 'audio' and audio_ok:
            return AUDIO
        if link_ok:
            return LINK
        return AUDIO if audio_ok else CLOCK

    def _measured_bpm(self):
        """BPM from the gaps between recent beats, or None if there are too few.

        The tracker's own BPM follows single beat gaps and jumps around, which
        would flip between BPM bands. Averaging the gaps is steadier, and
        leaving out the ones far from the median ignores missed beats.
        """
        times = list(self.beat_times)
        gaps = sorted(b - a for a, b in zip(times, times[1:]))
        if len(gaps) < MIN_GAPS_FOR_BPM:
            return None
        median = gaps[len(gaps) // 2]
        close = [g for g in gaps if abs(g - median) <= GAP_OUTLIER_FRACTION * median]
        return 60.0 / (sum(close) / len(close))


class LinkListener:
    """Hears Link peers announce themselves, without joining their session.

    Link has no listen-only mode: an app joining a session TouchDesigner is
    already in takes on TouchDesigner's tempo. So TouchDesigner stays out of
    Link until it hears a peer, and that peer's tempo stands.
    """

    def __init__(self):
        self.sock = None
        self.opened_at = -math.inf

    def heard_peer(self, now):
        """Read everything waiting and return True if a peer said it's alive.

        Call this every frame, so old packets never pile up.
        """
        if now - self.opened_at >= LISTENER_REFRESH_SEC:
            self._reopen(now)
        heard = False
        while self.sock is not None:
            try:
                packet = self.sock.recvfrom(2048)[0]
            except OSError:
                break
            if packet[:len(LINK_HEADER)] == LINK_HEADER:
                heard = heard or packet[len(LINK_HEADER):][:1] == LINK_ALIVE
        return heard

    def _reopen(self, now):
        # Reopening picks up network adapters that appeared since last time,
        # such as a travel router plugged in after the project started.
        self.opened_at = now
        if self.sock is not None:
            self.sock.close()
            self.sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', LINK_PORT))
            group = socket.inet_aton(LINK_GROUP)
            for address in socket.gethostbyname_ex(socket.gethostname())[2]:
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                                group + socket.inet_aton(address))
            sock.setblocking(False)
            self.sock = sock
        except OSError as e:
            print('tempo_source: can\'t listen for Link peers:', e)


# ---- TouchDesigner side -----------------------------------------------------

_settings_text = None
_settings = None
_selector = None
_last_output = None
_listener = LinkListener()
_link_needed_at = -math.inf
_link_left_at = -math.inf


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
            print('tempo_source: keeping last good settings:', e)
    return _settings


def setting(name):
    """Read one tempo setting. Parameter expressions call this, so they update
    by themselves when settings.json changes."""
    return _all_settings()['tempo'][name]


def _last_value(chop, name, default=0.0):
    chan = chop[name]
    return chan[-1] if chan is not None and len(chan) > 0 else default


def _read_link(scriptOp):
    if len(scriptOp.inputs) < 1:
        return None
    chop = scriptOp.inputs[0]
    return {
        'peers': _last_value(chop, 'numpeers'),
        'bpm': _last_value(chop, 'tempo'),
        'bar_phase': _last_value(chop, 'rampbar'),
    }


def _input_level():
    """Loudest sample this frame in the audio going to the tracker."""
    source = op('audio_in')
    if source is None or source.numChans == 0:
        return 0.0
    samples = source.numpyArray()
    return max(float(samples.max()), -float(samples.min()))


def _read_tracker(scriptOp):
    # The tracker lives in its own file, which may be missing on a new machine.
    if len(scriptOp.inputs) < 2:
        return None
    chop = scriptOp.inputs[1]
    return {
        'beat': _last_value(chop, 'beat') > 0.5,
        'level': _input_level(),
        'bpm': _last_value(chop, 'bpm'),
        'phase': _last_value(chop, 'phase'),
        'beat_num': _last_value(chop, 'beat_num'),
    }


def _manage_link(scriptOp, now, cfg):
    """Join Link once a peer is heard, and leave when the last one has gone."""
    global _link_needed_at, _link_left_at
    heard = _listener.heard_peer(now)
    if len(scriptOp.inputs) < 1:
        return
    link = scriptOp.inputs[0]
    if link.par.enable.eval():
        if _last_value(link, 'numpeers') >= 1:
            _link_needed_at = now
        elif now - _link_needed_at > cfg['link_lost_after_sec']:
            link.par.enable = False
            _link_left_at = now
    elif heard and now - _link_left_at > LINK_OWN_ECHO_SEC:
        link.par.enable = True
        _link_needed_at = now


def _configure_tracker(cfg):
    """Apply the tracker's settings. It reloads from its own file and loses
    anything set on it, so these are checked every frame."""
    tracker = op('beat_tracker')
    if tracker is None:
        return
    wanted = {'Singlemodel': cfg['tracker_single_model'],
              'Beatsperbar': cfg['beats_per_bar']}
    for name, value in wanted.items():
        par = getattr(tracker.par, name, None)
        if par is not None and par.eval() != value:
            par.val = value


def _show_source_name(source):
    name_dat = op('source_name')
    if name_dat is not None and name_dat.text != SOURCE_NAMES[source]:
        name_dat.text = SOURCE_NAMES[source]


def onCook(scriptOp):
    """Update the selector, then write the output channels."""
    global _selector, _last_output
    scriptOp.clearScriptErrors()
    try:
        settings = _all_settings()
        if _selector is None:
            _selector = TempoSelector(settings['audio']['fallback_bpm'])
        _configure_tracker(settings['tempo'])
        _manage_link(scriptOp, absTime.seconds, settings['tempo'])
        _last_output = _selector.update(absTime.seconds, settings['tempo'],
                                        _read_link(scriptOp),
                                        _read_tracker(scriptOp))
        _show_source_name(_last_output['source'])
    except Exception as e:
        # Show the problem on the node, and keep outputting the last values.
        scriptOp.addScriptError('tempo_source: {}'.format(e))
        if _last_output is not None:
            _last_output = dict(_last_output, beat=0)

    scriptOp.isTimeSlice = False
    scriptOp.clear()
    scriptOp.numSamples = 1
    if _last_output is not None:
        for name, value in _last_output.items():
            scriptOp.appendChan(name)[0] = value


def onGetCookLevel(scriptOp):
    """Cook every frame, so the clock and source timers never have gaps."""
    return CookLevel.ALWAYS
