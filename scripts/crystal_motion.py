"""Turns tempo and audio into the virtual crystal's motion.

Synced into the Text DAT /project1/virtual_crystal/crystal_motion. The Script
CHOP "crystal_logic" calls onCook once a frame and writes angle, spin_speed and
sparkle, the numbers both crystals share, plus channels that only the virtual
crystal's shaders use, such as breathe, explode, morph and the sat_ channels for
the small crystal that drifts off the main one.

All tunable numbers come from config/settings.json.
"""

import json
import math
import random

# The longest step anything moves in one go, so a stall doesn't make it jump.
MAX_STEP_SEC = 0.25
# The numbers crystal_refract.glsl uses for each shape.
SHAPE_NUMBERS = {'brilliant': 0, 'quartz': 1, 'octahedron': 2, 'emerald': 3}
FIGURE_NUMBERS = {'crystal': 0, 'laughing_face': 1, 'pill': 2}
# Where the smiley's drips end, in its own space. Same places as crystal_figure.glsl.
SMILEY_DRIP_TIPS = ((-0.34, -0.62), (-0.09, -0.52), (0.13, -0.86), (0.38, -0.56))
# A gem can't be drawn at size zero, so "gone" is this small.
MIN_SCALE = 0.001


def _ease(x):
    """Turn a steady 0 to 1 into one that starts and stops gently."""
    return x * x * (3.0 - 2.0 * x)


def _keep_on_screen(position, room, to_screen):
    """Eases a position back so it never passes room, measured on screen. to_screen
    converts a position to its place on screen at the object's depth."""
    room = max(room, 0.05)
    return room * math.tanh(position * to_screen / room) / to_screen


class LevelFollower:
    """Compares a level with its own recent peak. It holds steady from one hit to
    the next, so what it drives doesn't pump."""

    def __init__(self):
        self.level = 0.0
        self.peak = 0.0

    def update(self, step, value, cfg, floor):
        """Returns the level as a fraction of its peak. The peak never falls
        below the floor, so faint sound can't count as its own peak."""
        time_constant = (cfg['motion_attack_sec'] if value > self.level
                         else cfg['motion_release_sec'])
        self.level += (value - self.level) * (1.0 - math.exp(-step / time_constant))
        decay = 0.5 ** (step / cfg['motion_peak_halflife_sec'])
        self.peak = max(self.peak * decay, self.level, floor)
        return self.level / self.peak


class MoveVariation:
    """Keeps a gem from settling into one repeating motion. Every few bars it picks
    a new way of moving, and glides there so there's never a visible jolt. Each gem
    has its own, so they don't change together."""

    def __init__(self):
        self.bars_left = 0.0
        self.spin = 1.0
        self.sway_size = 1.0
        self.sway_speed = 1.0
        self.tilt = 0.0
        self.roll = 0.0
        self.targets = {}

    def _pick(self, cfg):
        spin = random.uniform(*cfg['move_spin_range'])
        if random.random() < cfg['move_spin_reverse_chance']:
            spin = -spin
        self.targets = {
            'spin': spin,
            'sway_size': random.uniform(*cfg['move_sway_size_range']),
            'sway_speed': random.uniform(*cfg['move_sway_speed_range']),
            'tilt': random.uniform(-cfg['move_tilt_deg'], cfg['move_tilt_deg']),
            'roll': random.uniform(-cfg['move_roll_deg'], cfg['move_roll_deg']),
        }
        self.bars_left = random.choice(cfg['move_change_bars'])

    def update(self, step, bars_per_sec, cfg):
        bars = bars_per_sec * step
        self.bars_left -= bars
        if self.bars_left <= 0.0:
            self._pick(cfg)
        glide = 1.0 - math.exp(-bars / cfg['move_glide_bars'])
        for name, target in self.targets.items():
            setattr(self, name, getattr(self, name) + (target - getattr(self, name)) * glide)


class OrbitPlane:
    """Keeps the small crystal's orbit changing. Every few bars it picks a new plane
    to circle in and sometimes reverses, gliding there so it never jumps. Reversing
    means slowing to a stop and heading back the other way."""

    def __init__(self):
        self.tilt = 0.0
        self.roll = 0.0
        self.way = 1.0
        self.goals = (0.0, 0.0, 1.0)
        self.bars_left = 0.0
        self.reverse_wanted = False

    def _pick_plane(self, cfg):
        tilt = math.radians(cfg['satellite_orbit_tilt_deg'])
        roll = math.radians(cfg['satellite_orbit_roll_deg'])
        return random.uniform(-tilt, tilt), random.uniform(-roll, roll)

    def start(self, cfg):
        """A new trip goes straight to its first plane and direction."""
        self.tilt, self.roll = self._pick_plane(cfg)
        self.way = random.choice((-1.0, 1.0))
        self.goals = (self.tilt, self.roll, self.way)
        self.bars_left = random.choice(cfg['satellite_orbit_change_bars'])
        self.reverse_wanted = False

    def update(self, bars, can_reverse, cfg):
        self.bars_left -= bars
        if self.bars_left <= 0.0:
            self.goals = (*self._pick_plane(cfg), self.goals[2])
            self.bars_left = random.choice(cfg['satellite_orbit_change_bars'])
            if random.random() < cfg['satellite_orbit_reverse_chance']:
                self.reverse_wanted = True
        # A reversal waits for a clear moment, so it can't stop over the main gem.
        if self.reverse_wanted and can_reverse:
            self.goals = (self.goals[0], self.goals[1], -self.goals[2])
            self.reverse_wanted = False
        glide = 1.0 - math.exp(-bars / cfg['satellite_orbit_turn_bars'])
        self.tilt += (self.goals[0] - self.tilt) * glide
        self.roll += (self.goals[1] - self.roll) * glide
        self.way += (self.goals[2] - self.way) * glide


class Droplets:
    """Lava-lamp blobs that morph out of a crystal, then wobble and drift out of the
    picture.

    A blob starts small and hidden behind whatever it comes from, so it swells out past
    that crystal's real edge whatever shape it is at the moment. Until it's clear, it's
    tied to two points on the crystal, so it follows it around.

    Positions are in the same space as the small crystal: a negative z is nearer the
    viewer. There's a fixed number of slots, and crystal_blobs.glsl has the same limit.
    """

    SLOTS = 8
    EMPTY_ROW = (0.0, 0.0, 0.0, 1e4, 0.0, 1.0, 0.0, 0.0)

    def __init__(self):
        self.balls = []
        self.rows = [self.EMPTY_ROW] * self.SLOTS
        self.since_last = 1e6

    def can_emit(self, cfg):
        """Keeps the picture from filling up: only so many at once, and never two
        starting close together."""
        return (len(self.balls) < cfg['droplet_max_at_once']
                and self.since_last >= cfg['droplet_min_gap_sec'])

    def emit(self, source, start, clear, lift, kind, cfg):
        """Start one. source says what it comes from. start is where it begins, hidden,
        and clear is where it has reached once it's out, both in the source's own
        space. lift pulls it up afterwards when positive, and down when negative."""
        self.since_last = 0.0
        self.balls.append({
            'source': source, 'start': start, 'clear': clear,
            'x': 0.0, 'y': 0.0, 'z': 0.0, 'vx': 0.0, 'vy': 0.0,
            'last_start': None, 'emerging': True, 'free_for': 0.0,
            'lift': lift, 'kind': kind, 'age': 0.0,
            'phase': random.uniform(0.0, 2.0 * math.pi),
            'size': random.uniform(*cfg['droplet_size_range']),
            'emerge_sec': random.uniform(*cfg['droplet_emerge_sec_range']),
        })

    def _emerge(self, ball, locate, cfg):
        """Moves one that's still coming out of its source. Returns how far along it
        is, 0 to 1."""
        start = locate(ball['source'], ball['start'])
        clear = locate(ball['source'], ball['clear'])
        progress = ball['age'] / ball['emerge_sec']
        if start is None or clear is None or progress >= 1.0:
            # It's out, and carries on the way it was heading.
            origin = ball['last_start'] or (ball['x'], ball['y'] - 1.0)
            away_x, away_y = ball['x'] - origin[0], ball['y'] - origin[1]
            length = max(math.hypot(away_x, away_y), 1e-4)
            ball['vx'], ball['vy'] = away_x / length, away_y / length
            ball['emerging'] = False
            return 1.0
        along = _ease(progress)
        ball['x'], ball['y'], ball['z'] = (start[i] + (clear[i] - start[i]) * along for i in range(3))
        ball['vx'], ball['vy'] = clear[0] - start[0], clear[1] - start[1]
        ball['last_start'] = start
        return progress

    def update(self, step, flow, locate, cfg):
        """Move them all. flow slows them down when the music is quiet, and locate
        finds a point on a source, or None if it's gone."""
        lens, camera = cfg['camera_lens'], cfg['camera_distance']
        self.since_last += step * flow
        rows, alive = [], []
        for ball in self.balls:
            ball['age'] += step * flow
            age = ball['age']
            grown = _ease(min(age / ball['emerge_sec'], 1.0))

            progress = self._emerge(ball, locate, cfg) if ball['emerging'] else 1.0
            if not ball['emerging']:
                # Eases into a slow drift toward its lift, swaying from side to side.
                ball['free_for'] += step * flow
                ball['vy'] += ball['lift'] * cfg['droplet_lift'] * step * flow
                speed = cfg['droplet_speed'] * flow * _ease(min(ball['free_for'] / cfg['droplet_settle_sec'], 1.0))
                heading = math.atan2(ball['vy'], ball['vx'])
                sway = math.sin(age * cfg['droplet_sway_rate'] + ball['phase']) * cfg['droplet_sway']
                ball['x'] += (ball['vx'] - math.sin(heading) * sway) * speed * step
                ball['y'] += (ball['vy'] + math.cos(heading) * sway) * speed * step

            depth = camera + ball['z']
            radius = ball['size'] * grown * lens / depth
            screen_x, screen_y = ball['x'] * lens / depth, ball['y'] * lens / depth
            if not ball['emerging'] and (abs(screen_x) > cfg['picture_half_width'] + radius + 0.03
                                         or abs(screen_y) > 0.5 + radius + 0.03
                                         or age > cfg['droplet_max_sec']):
                continue
            alive.append(ball)

            # Slightly long as it comes out, then a slow wobble between tall and wide.
            ripple = age * cfg['droplet_ripple_rate'] + ball['phase']
            stretch = 1.0 + cfg['droplet_emerge_stretch'] * (1.0 - progress) + 0.16 * math.sin(ripple)
            rows.append((screen_x, screen_y, radius,
                         math.sqrt(ball['x'] ** 2 + ball['y'] ** 2 + depth ** 2),
                         math.atan2(ball['vy'], ball['vx']), stretch, ripple, float(ball['kind'])))
        self.balls = alive
        self.rows = rows + [self.EMPTY_ROW] * (self.SLOTS - len(rows))


class CrystalMotion:
    """Keeps the gem's angle, beat kick, sway and explosion."""

    def __init__(self):
        self.angle = 0.0
        self.kick = 0.0
        self.sway_phase = 0.0
        self.moves = MoveVariation()
        self.sat_moves = MoveVariation()
        self.sat_sway_phase = 0.0
        self.explode_time = None
        self.drop_was_up = False
        self.bass_follower = LevelFollower()
        self.loudness_follower = LevelFollower()
        self.shape_index = 0
        self.change_clock = 0.0
        self.change_time = None
        self.change_style = None
        self.change_count = 0
        self.shape_swapped = False
        self.shrink_angle = 0.0
        self.sat_clock = 0.0
        self.sat_time = None
        self.sat_angle = 0.0
        self.sat_orbit = 0.0
        self.orbit = OrbitPlane()
        self.sat_orbit_speed = 0.0
        self.sat_from_middle = 1.0
        self.droplets = Droplets()
        self.gem_drop_clock = 0.0
        self.sat_drop_clock = 0.0
        self.sat_last_from_middle = 1.0
        self.sat_pulse = 0.0
        self.sat_figure = 0
        self.sat_trips = 0

    def change_shape_now(self, cfg):
        """Start the next shape change, unless one is already running. The
        styles take turns."""
        if self.change_time is not None:
            return
        styles = cfg['shape_change_styles'] or ['morph']
        self.change_style = styles[self.change_count % len(styles)]
        self.change_count += 1
        self.change_time = 0.0
        self.change_clock = 0.0
        self.shape_swapped = False
        self.shrink_angle = random.uniform(0.0, 2.0 * math.pi)

    def _shape(self, step, cfg):
        """Returns the shape channels for this frame. Time passes with or without
        music."""
        names = [name for name in cfg['shapes'] if name in SHAPE_NUMBERS] or ['brilliant']
        self.shape_index %= len(names)

        self.change_clock += step
        if self.change_clock >= cfg['shape_change_interval_sec']:
            self.change_shape_now(cfg)

        morph, scale, away = 0.0, 1.0, 0.0
        if self.change_time is not None:
            self.change_time += step
            if self.change_style == 'shrink':
                # Shrinks away in one direction with the old shape, then comes
                # back from the opposite side as the next one.
                out_sec, in_sec = cfg['shrink_out_sec'], cfg['shrink_in_sec']
                if self.change_time < out_sec:
                    eased = _ease(self.change_time / out_sec)
                    scale, away = 1.0 - eased, eased
                else:
                    if not self.shape_swapped:
                        self.shape_index = (self.shape_index + 1) % len(names)
                        self.shape_swapped = True
                    x = (self.change_time - out_sec) / in_sec
                    if x >= 1.0:
                        self.change_time = None
                    else:
                        eased = _ease(x)
                        scale, away = eased, eased - 1.0
            else:
                x = self.change_time / cfg['morph_sec']
                if x >= 1.0:
                    self.shape_index = (self.shape_index + 1) % len(names)
                    self.change_time = None
                else:
                    morph = _ease(x)

        next_index = (self.shape_index + 1) % len(names)
        distance = away * cfg['shrink_distance']
        return {
            'shape_a': SHAPE_NUMBERS[names[self.shape_index]],
            'shape_b': SHAPE_NUMBERS[names[next_index]],
            'morph': morph,
            'scale': max(scale, MIN_SCALE),
            'offset_x': math.cos(self.shrink_angle) * distance,
            'offset_y': math.sin(self.shrink_angle) * distance,
        }

    def release_satellite(self, cfg):
        """Send a small crystal off the main one, unless one is already out. It
        leaves toward the left or right, where it's easy to see, and each trip
        picks its own direction and orbit tilt. The figures take turns."""
        if self.sat_time is None:
            self.sat_time = 0.0
            self.sat_clock = 0.0
            figures = [name for name in cfg['satellite_figures'] if name in FIGURE_NUMBERS] or ['crystal']
            self.sat_figure = FIGURE_NUMBERS[figures[self.sat_trips % len(figures)]]
            self.sat_trips += 1
            side = random.choice((0.0, math.pi))
            self.sat_orbit = side + random.uniform(-0.6, 0.6)
            self.orbit.start(cfg)

    def _satellite(self, step, bars_per_sec, spin, intensity, punch, motion, cfg):
        """Returns the small crystal's channels. It leaves as a blob and forms
        facets as it spirals out, circles the main gem, then melts back as it
        returns. It turns and sways like the main gem, with its own timing and a
        little more of each. Its path stays smooth: the orbit follows the tempo, and
        each beat is a soft swell that melts it part of the way back to a blob."""
        # The pulse rises fast but never in one frame, so a beat can't look like a jump.
        target = 1.0 if self.kick * punch > self.sat_pulse else self.kick * punch
        time_constant = (cfg['satellite_pulse_attack_sec'] if target > self.sat_pulse
                         else cfg['satellite_pulse_release_sec'])
        self.sat_pulse += (target - self.sat_pulse) * (1.0 - math.exp(-step / time_constant))

        moves = self.sat_moves
        moves.update(step, bars_per_sec, cfg)
        ratio = cfg['satellite_move_ratio']
        spin_speed = (360.0 * bars_per_sec / cfg['turn_bars'] * spin
                      * (1.0 + (moves.spin - 1.0) * intensity) * ratio)
        self.sat_angle = (self.sat_angle + spin_speed * step) % 360.0
        self.sat_sway_phase = (self.sat_sway_phase + bars_per_sec / cfg['sway_bars']
                               * moves.sway_speed * step) % 1.0
        sway = 2.0 * math.pi * self.sat_sway_phase
        tilt = (math.sin(sway) * cfg['sway_deg'] * moves.sway_size + moves.tilt) * motion * ratio
        roll = (math.cos(sway) * cfg['sway_deg'] * 0.7 * moves.sway_size + moves.roll) * motion * ratio
        is_crystal = self.sat_figure == FIGURE_NUMBERS['crystal']
        if is_crystal:
            angle = self.sat_angle
            tilt += cfg['gem_tilt_deg']
            melt = cfg['satellite_beat_melt']
        else:
            # A figure has a front, so it looks around instead of spinning, and
            # nods on the beat.
            angle = math.sin(math.radians(self.sat_angle)) * cfg['satellite_figure_turn_deg']
            tilt += self.sat_pulse * cfg['satellite_figure_nod_deg']
            melt = cfg['satellite_figure_melt']
        size = cfg['satellite_size'] * (1.0 if is_crystal else cfg['satellite_figure_size'])
        if self.sat_figure == FIGURE_NUMBERS['pill']:
            size *= cfg['satellite_pill_size']
        turning = {
            'sat_figure': self.sat_figure,
            'sat_pulse': self.sat_pulse,
            'sat_breathe': self.sat_pulse * cfg['satellite_beat_swell'],
            'sat_angle': angle,
            'sat_tilt': tilt,
            'sat_roll': roll,
        }

        self.sat_clock += step
        if self.sat_clock >= cfg['satellite_interval_sec']:
            self.release_satellite(cfg)

        blank = {'sat_x': 0.0, 'sat_y': 0.0, 'sat_z': 0.0, 'sat_scale': 0.0,
                 'sat_blob': 1.0, **turning}
        if self.sat_time is None:
            return blank
        self.sat_time += step
        out_sec, float_sec, back_sec = (cfg['satellite_out_sec'], cfg['satellite_float_sec'],
                                        cfg['satellite_back_sec'])
        t = self.sat_time
        if t < out_sec:
            distance = _ease(t / out_sec)
            blob = 1.0 - _ease(max((t / out_sec - 0.4) / 0.6, 0.0))
        elif t < out_sec + float_sec:
            distance, blob = 1.0, 0.0
        elif t < out_sec + float_sec + back_sec:
            x = (t - out_sec - float_sec) / back_sec
            distance = 1.0 - _ease(x)
            blob = _ease(min(x / 0.6, 1.0))
        else:
            self.sat_time = None
            self.sat_clock = 0.0
            return blank

        orbit_target = 360.0 * bars_per_sec / cfg['satellite_orbit_bars'] * spin
        self.sat_orbit_speed += ((orbit_target - self.sat_orbit_speed)
                                 * (1.0 - math.exp(-step / cfg['satellite_orbit_glide_sec'])))
        # It never lingers over the main gem. It only starts to turn back while heading
        # away from it, so it stops out in the open, and any slowdown is gone by the time
        # it's over the gem. In quiet passages it also keeps at least a moderate speed.
        near_middle = 1.0 - _ease(min(self.sat_from_middle / cfg['satellite_middle_radius'], 1.0))
        heading_away = self.sat_from_middle > self.sat_last_from_middle
        self.orbit.update(bars_per_sec * step, near_middle <= 0.0 and heading_away, cfg)
        way = self.orbit.way + (self.orbit.goals[2] - self.orbit.way) * near_middle
        slowest = 360.0 * bars_per_sec / cfg['satellite_orbit_bars'] * cfg['satellite_middle_min_spin']
        speed = self.sat_orbit_speed + max(slowest - self.sat_orbit_speed, 0.0) * near_middle
        self.sat_orbit += math.radians(speed) * step * way
        bob = math.sin(t * 2.0 * math.pi / cfg['satellite_bob_sec']) * cfg['satellite_bob'] * distance
        reach = distance * cfg['satellite_distance']

        # A flat circle around the main gem, tipped toward the viewer and then
        # leaned to one side. A negative z is nearer the viewer.
        flat_x = math.cos(self.sat_orbit) * reach
        flat_z = math.sin(self.sat_orbit) * reach
        tipped_y = flat_z * math.sin(self.orbit.tilt)
        sat_y = flat_x * math.sin(self.orbit.roll) + tipped_y * math.cos(self.orbit.roll) + bob
        sat_z = flat_z * math.cos(self.orbit.tilt)

        # Ease it back in as it nears the edges of the picture, leaving room for its size.
        lens = cfg['camera_lens']
        depth = cfg['camera_distance'] + sat_z
        radius = size * cfg['gem_size'] * lens / depth
        sat_y = _keep_on_screen(sat_y, 0.5 - radius, lens / depth)
        # Width stays the same however steep the orbit, because a narrow orbit would
        # spend its whole lap over the main gem.
        sat_x = _keep_on_screen(flat_x - tipped_y * math.sin(self.orbit.roll),
                                cfg['picture_half_width'] - radius, lens / depth)
        self.sat_last_from_middle = self.sat_from_middle
        self.sat_from_middle = math.hypot(sat_x, sat_y) * lens / depth

        return {
            'sat_x': sat_x,
            'sat_y': sat_y,
            'sat_z': sat_z,
            'sat_scale': size * (0.5 + 0.5 * distance),
            'sat_blob': max(blob, self.sat_pulse * melt),
            **turning,
        }

    def _tile(self, shape, sat, cfg):
        """Returns which small-crystal image to show and what part of the picture
        it covers, in image heights. sat_kind is 0 for none, 1 for a faceted gem and
        2 for a figure. A generous margin keeps its edges from ever being cut off."""
        if sat['sat_scale'] <= 0.0:
            return {'sat_kind': 0, 'tile_x': 0.0, 'tile_y': 0.0, 'tile_half': 1.0}
        scale = shape['scale']
        depth = cfg['camera_distance'] + sat['sat_z'] * scale
        reach = sat['sat_scale'] * cfg['gem_size'] * scale * 1.25
        lens = cfg['camera_lens']
        return {
            'sat_kind': 1 if sat['sat_figure'] == FIGURE_NUMBERS['crystal'] else 2,
            'tile_x': sat['sat_x'] * scale * lens / depth,
            'tile_y': sat['sat_y'] * scale * lens / depth,
            'tile_half': reach * lens / max(depth - reach, 0.5),
        }

    def _small_crystal_point(self, sat, shape, local, cfg):
        """Where a point on the small crystal is. local is in the figure's own space,
        the same as crystal_figure.glsl, where 1 is about the main gem's size."""
        angle, tilt, roll = (math.radians(sat[name]) for name in ('sat_angle', 'sat_tilt', 'sat_roll'))
        x, y, z = (value * cfg['gem_size'] * shape['scale'] * sat['sat_scale'] for value in local)
        # Undoes the turns crystal_gem.glsl applies, in the opposite order.
        x, z = x * math.cos(angle) + z * math.sin(angle), z * math.cos(angle) - x * math.sin(angle)
        y, z = y * math.cos(tilt) + z * math.sin(tilt), z * math.cos(tilt) - y * math.sin(tilt)
        x, y = x * math.cos(roll) + y * math.sin(roll), y * math.cos(roll) - x * math.sin(roll)
        return (x + sat['sat_x'] * shape['scale'], y + sat['sat_y'] * shape['scale'],
                z + sat['sat_z'] * shape['scale'])

    def _emit_from_small(self, sat, shape, cfg):
        """A blob out of the small crystal: yellow and falling from a drip on the
        smiley, teal and rising from the rim of the pill, clear from the plain one."""
        behind = cfg['droplet_behind']
        figure = sat['sat_figure']
        # The same short distance on screen, whatever size the object is.
        past_edge = cfg['droplet_clearance'] / (cfg['gem_size'] * shape['scale'] * sat['sat_scale'])
        if figure == FIGURE_NUMBERS['laughing_face']:
            x, y = random.choice(SMILEY_DRIP_TIPS)
            start, clear, lift = (x, y + 0.25, behind), (x, y - past_edge, behind), -1.0
        else:
            a = random.uniform(0.0, 2.0 * math.pi)
            c, s = math.cos(a), math.sin(a)
            far = 0.88 + past_edge
            start, clear, lift = (0.45 * c, 0.45 * s, behind), (far * c, far * s, behind), 1.0
        self.droplets.emit('small', start, clear, lift, figure, cfg)

    def _emit_from_gem(self, shape, cfg):
        """A clear blob out of the main gem, rising."""
        a = random.uniform(0.0, 2.0 * math.pi)
        c, s = math.cos(a), math.sin(a)
        behind = cfg['droplet_behind']
        far = cfg['droplet_gem_reach'] + cfg['droplet_clearance'] / (cfg['gem_size'] * shape['scale'])
        self.droplets.emit('main', (0.4 * c, 0.4 * s, behind), (far * c, far * s, behind),
                           1.0, FIGURE_NUMBERS['crystal'], cfg)

    def _update_droplets(self, step, shape, sat, flow, cfg):
        """Sends off new blobs on their own schedules, then moves them all. A crystal
        only sends one when it's fully formed and in view."""
        lens = cfg['camera_lens']

        def locate(source, local):
            if source == 'main':
                x, y, z = (value * cfg['gem_size'] * shape['scale'] for value in local)
            elif sat['sat_scale'] > 0.0:
                x, y, z = self._small_crystal_point(sat, shape, local, cfg)
            else:
                return None
            scale = (cfg['camera_distance'] + z) / lens
            return x + shape['offset_x'] * scale, y + shape['offset_y'] * scale, z

        self.gem_drop_clock += step * flow
        if (self.gem_drop_clock >= cfg['droplet_gem_interval_sec'] and shape['scale'] > 0.9
                and self.explode_time is None and self.droplets.can_emit(cfg)):
            self.gem_drop_clock = 0.0
            self._emit_from_gem(shape, cfg)

        out_sec = cfg['satellite_out_sec']
        formed = (self.sat_time is not None and out_sec <= self.sat_time <= out_sec + cfg['satellite_float_sec']
                  and sat['sat_blob'] < 0.5 and self.explode_time is None)
        if formed:
            self.sat_drop_clock += step * flow
            interval = {FIGURE_NUMBERS['laughing_face']: cfg['droplet_smiley_interval_sec'],
                        FIGURE_NUMBERS['pill']: cfg['droplet_pill_interval_sec']}.get(
                            sat['sat_figure'], cfg['droplet_gem_interval_sec'])
            if self.sat_drop_clock >= interval and self.droplets.can_emit(cfg):
                self.sat_drop_clock = 0.0
                self._emit_from_small(sat, shape, cfg)
        self.droplets.update(step, flow, locate, cfg)
        count = len(self.droplets.balls)
        return {'droplet_count': count, 'droplets_on': 1 if count else 0}

    def _intensity(self, step, bass, cfg):
        """How hard the music is hitting, from 0 to 1: the bass compared with
        its recent peak. Silence and bass-less build-ups read low."""
        ratio = self.bass_follower.update(step, bass, cfg, cfg['motion_floor_bass'])
        return min(ratio / cfg['motion_full_at'], 1.0)

    def _punch(self, step, bass, mids, treble, cfg):
        """How much the beat pulses, from 0 to 1. It goes by the loudest part of
        the sound compared with the song's recent peak, so anything at the front
        of the mix drives it, such as a lead vocal with no bass. Quiet sounds
        behind the mix don't, and silence gives exactly 0."""
        ratio = self.loudness_follower.update(step, max(bass, mids, treble), cfg,
                                              cfg['punch_floor_level'])
        amount = (ratio - cfg['punch_from']) / (cfg['punch_full_at'] - cfg['punch_from'])
        return min(max(amount, 0.0), 1.0)

    def start_explosion(self):
        """Start the explosion, unless one is already running."""
        if self.explode_time is None:
            self.explode_time = 0.0

    def _explode_amount(self, step, beat_sec, cfg):
        """How far apart the shards are: 0 is whole, 1 is fully blown apart.
        They burst out quickly, then ease back together."""
        if self.explode_time is None:
            return 0.0
        self.explode_time += step
        out_sec = cfg['explode_out_beats'] * beat_sec
        back_sec = cfg['explode_reform_beats'] * beat_sec
        if self.explode_time < out_sec:
            return 1.0 - (1.0 - self.explode_time / out_sec) ** 3
        if self.explode_time < out_sec + back_sec:
            x = (self.explode_time - out_sec) / back_sec
            return 1.0 - x * x * (3.0 - 2.0 * x)
        self.explode_time = None
        return 0.0

    def update(self, dt, bpm, beats_per_bar, bass, mids, treble, beat, drop, cfg):
        """Returns angle in degrees, spin_speed in degrees per second, sparkle
        from 0 to 1, and the channels the virtual crystal's shaders use."""
        step = min(dt, MAX_STEP_SEC)
        intensity = self._intensity(step, max(bass, 0.0), cfg)
        motion = cfg['idle_motion'] + (1.0 - cfg['idle_motion']) * intensity
        punch = self._punch(step, max(bass, 0.0), max(mids, 0.0), max(treble, 0.0), cfg)
        spin = cfg['idle_spin'] + (1.0 - cfg['idle_spin']) * intensity

        bars_per_sec = bpm / 60.0 / beats_per_bar
        moves = self.moves
        moves.update(step, bars_per_sec, cfg)
        # The changes fade out with the music, so a quiet gem just turns steadily.
        spin_speed = (360.0 * bars_per_sec / cfg['turn_bars'] * spin
                      * (1.0 + (moves.spin - 1.0) * intensity))
        self.angle = (self.angle + spin_speed * step) % 360.0

        if beat:
            self.kick = 1.0
        else:
            self.kick *= math.exp(-step / cfg['beat_kick_release_sec'])

        self.sway_phase = (self.sway_phase + bars_per_sec / cfg['sway_bars']
                           * moves.sway_speed * step) % 1.0
        sway = 2.0 * math.pi * self.sway_phase

        # Only the moment the flag goes up counts, not the whole time it's up.
        if drop and not self.drop_was_up:
            self.start_explosion()
        self.drop_was_up = drop

        shape = self._shape(step, cfg)
        sat = self._satellite(step, bars_per_sec, spin, intensity, punch, motion, cfg)
        flow = cfg['droplet_idle_flow'] + (1.0 - cfg['droplet_idle_flow']) * intensity
        return {
            **shape,
            **sat,
            **self._tile(shape, sat, cfg),
            **self._update_droplets(step, shape, sat, flow, cfg),
            'angle': self.angle,
            'spin_speed': spin_speed,
            'sparkle': min(max(treble * cfg['treble_sparkle'], 0.0), 1.0),
            'breathe': max(bass, 0.0) * cfg['bass_breathe'] + self.kick * cfg['beat_pulse'] * punch,
            'twist': self.kick * cfg['beat_twist_deg'] * punch,
            'sway_tilt': (math.sin(sway) * cfg['sway_deg'] * moves.sway_size + moves.tilt) * motion,
            'sway_roll': (math.cos(sway) * cfg['sway_deg'] * 0.7 * moves.sway_size + moves.roll) * motion,
            'explode': self._explode_amount(step, 60.0 / bpm, cfg),
        }


# ---- TouchDesigner side -----------------------------------------------------

_settings_text = None
_settings = None
_motion = CrystalMotion()
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
            print('crystal_motion: keeping last good settings:', e)
    return _settings


def setting(*path):
    """Read one setting. Parameter expressions call this, so they update by
    themselves when settings.json changes."""
    value = _all_settings()
    for key in path:
        value = value[key]
    return value


def explode_now():
    """Set off the explosion by hand, for testing it without waiting for a drop."""
    _motion.start_explosion()


def change_shape_now():
    """Start the next shape change by hand, for testing it without the wait."""
    _motion.change_shape_now(_all_settings()['virtual_crystal'])


def droplet_rows():
    """The blobs' numbers for droplet_table to pass on to the shader."""
    return _motion.droplets.rows


def satellite_now():
    """Send off a small crystal by hand, for testing it without the wait."""
    _motion.release_satellite(_all_settings()['virtual_crystal'])


def _read(path, name, default):
    """Last value of one channel. A missing module reads as the default."""
    chop = op(path)
    chan = chop[name] if chop is not None else None
    value = chan[-1] if chan is not None and len(chan) > 0 else default
    return value if math.isfinite(value) else default


def onCook(scriptOp):
    """Update the motion, then write the output channels."""
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
        _last_output = _motion.update(
            dt, bpm, settings['tempo']['beats_per_bar'],
            _read('../audio/audio_out', 'bass', 0.0),
            _read('../audio/audio_out', 'mids', 0.0),
            _read('../audio/audio_out', 'treble', 0.0),
            _read('../tempo/tempo_out', 'beat', 0.0) > 0.5,
            _read('../audio/audio_out', 'drop', 0.0) > 0.5,
            settings['virtual_crystal'])
    except Exception as e:
        # Show the problem on the node, and keep outputting the last values.
        scriptOp.addScriptError('crystal_motion: {}'.format(e))

    scriptOp.isTimeSlice = False
    scriptOp.clear()
    scriptOp.numSamples = 1
    if _last_output is not None:
        for name, value in _last_output.items():
            scriptOp.appendChan(name)[0] = value


def onGetCookLevel(scriptOp):
    """Cook every frame, so the gem keeps turning without gaps."""
    return CookLevel.ALWAYS
