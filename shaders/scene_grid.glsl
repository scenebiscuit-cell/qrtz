// The Grid scene: the crystal's picture is tiled into a pattern that turns with the crystal.
// The pattern can be squares, hexagons, triangles, diamonds or one big kaleidoscope, and
// wedges mirrors each tile around its center, like the mirrors in a kaleidoscope. Every
// few beats the tiles step to a different part of the crystal. Each beat the picture pushes
// in a little and brightens, and the crystal's sparkle lights up its brightest points.
//
// Input 0 is crystal_out.

uniform float uCells;       // how many tiles fit in the picture's height
uniform float uShape;       // the tile shape: see the numbers below
uniform float uWedges;      // how many mirrored wedges fill a tile, 0 for none
uniform float uStep;        // picks each tile's view, and moves on every few beats
uniform float uPulse;       // the beat, fading from 1 to 0
uniform float uTurn;        // how far the grid has turned, radians
uniform float uViewTurn;    // how fast the view inside the tiles turns, compared with the grid
uniform float uSparkle;     // the crystal's sparkle, 0 to 1
uniform float uBeatZoom;    // how much a beat pushes in
uniform float uBeatGlow;    // how much a beat brightens the picture
uniform float uSparkleGlow; // how much sparkle lights up bright points
uniform float uFacetView;   // how much of the crystal one tile shows, 1 is all of it
uniform float uFacetWander; // how far a tile's view moves from the center
uniform float uLineWidth;   // the dark line between tiles, as a fraction of a tile

layout(location = 0) out vec4 fragColor;

// The same numbers as scene_clock.py.
const int SHAPE_HEXAGON = 1;
const int SHAPE_TRIANGLE = 2;
const int SHAPE_DIAMOND = 3;
const int SHAPE_RADIAL = 4;
const float TRIANGLE_HEIGHT = 0.8660254;
const float HEXAGON_ROW = 1.7320508;
const float TWO_PI = 6.2831853;

vec2 hash2(vec2 p) {
    return fract(sin(vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)))) * 43758.5453);
}

// Each tiling takes a position in tile units. It returns where that is inside its tile,
// measured from the tile's center, and sets which tile it's in and how far the nearest
// edge is. Tiles' edges meet exactly, so mirrored wedges flow across them.

vec2 squareTile(vec2 grid, out vec2 id, out float edge) {
    vec2 shifted = grid + 0.5;
    vec2 cell = floor(shifted);
    vec2 inTile = shifted - cell - 0.5;
    vec2 fromEdge = 0.5 - abs(inTile);
    edge = min(fromEdge.x, fromEdge.y);
    // Neighbors mirror each other and share a view, so the pattern stays orderly.
    id = floor(cell / 2.0);
    return inTile * (mod(cell, 2.0) * 2.0 - 1.0);
}

vec2 hexagonTile(vec2 grid, out vec2 id, out float edge) {
    vec2 size = vec2(1.0, HEXAGON_ROW);
    vec2 a = mod(grid, size) - size * 0.5;
    vec2 b = mod(grid - size * 0.5, size) - size * 0.5;
    vec2 inTile = dot(a, a) < dot(b, b) ? a : b;
    id = floor(grid - inTile + 0.5);
    vec2 h = abs(inTile);
    edge = 0.5 - max(h.x, dot(h, vec2(0.5, TRIANGLE_HEIGHT)));
    return inTile;
}

vec2 triangleTile(vec2 grid, out vec2 id, out float edge) {
    float row = floor(grid.y / TRIANGLE_HEIGHT);
    vec2 inRow = vec2(grid.x - 0.5 * mod(row, 2.0), grid.y - row * TRIANGLE_HEIGHT);
    float column = floor(inRow.x);
    vec2 f = vec2(inRow.x - column, inRow.y);

    // Each square of the row holds a triangle pointing up, with half a triangle pointing
    // down on either side of it. The ones pointing down are flipped to match.
    bool up = abs(f.x - 0.5) < 0.5 * (1.0 - f.y / TRIANGLE_HEIGHT);
    vec2 inTile;
    if (up) {
        inTile = f - vec2(0.5, TRIANGLE_HEIGHT / 3.0);
    } else {
        inTile = f - vec2(f.x < 0.5 ? 0.0 : 1.0, TRIANGLE_HEIGHT * 2.0 / 3.0);
        inTile.y = -inTile.y;
    }
    edge = 0.2886751 - max(-inTile.y, TRIANGLE_HEIGHT * abs(inTile.x) + 0.5 * inTile.y);
    id = vec2(column * 2.0 + (up ? 0.0 : (f.x < 0.5 ? -1.0 : 1.0)), row);
    // A quarter turn puts a mirror line through the triangle's point.
    return vec2(inTile.y, -inTile.x);
}

void main() {
    vec2 res = uTDOutputInfo.res.zw;
    float aspect = res.x / res.y;

    // The whole pattern turns with the crystal, and pushes in on the beat.
    vec2 p = (vUV.st - 0.5) * vec2(aspect, 1.0);
    p *= 1.0 - uBeatZoom * uPulse;
    float c = cos(uTurn), s = sin(uTurn);
    p = vec2(c * p.x - s * p.y, s * p.x + c * p.y);

    int shape = int(uShape + 0.5);
    vec2 grid = p * uCells;
    vec2 id = vec2(0.0);
    float edge = 1.0;
    vec2 inTile = grid;
    if (shape == SHAPE_HEXAGON) {
        inTile = hexagonTile(grid, id, edge);
    } else if (shape == SHAPE_TRIANGLE) {
        inTile = triangleTile(grid, id, edge);
    } else if (shape == SHAPE_DIAMOND) {
        inTile = squareTile(vec2(grid.x + grid.y, grid.y - grid.x) * 0.7071068, id, edge);
    } else if (shape != SHAPE_RADIAL) {
        inTile = squareTile(grid, id, edge);
    }

    // Mirrors meeting at the tile's center fold it into wedges. They all look at the same
    // part of the crystal, the way a kaleidoscope does.
    if (uWedges > 0.5) {
        float wedge = TWO_PI / uWedges;
        float around = abs(mod(atan(inTile.y, inTile.x), wedge) - wedge * 0.5);
        float fromCenter = length(inTile);
        inTile = fromCenter * vec2(cos(around), sin(around));
        id = vec2(0.0);
        if (shape == SHAPE_RADIAL) {
            edge = fromCenter * min(sin(around), sin(wedge * 0.5 - around));
        }
    }

    // The view inside the tiles turns too, so the pattern keeps changing as it spins.
    float viewAngle = uTurn * uViewTurn;
    float vc = cos(viewAngle), vs = sin(viewAngle);
    inTile = vec2(vc * inTile.x - vs * inTile.y, vs * inTile.x + vc * inTile.y);

    // Every few beats, each tile looks at a new part of the crystal. Past the picture's edge the
    // crystal's picture mirrors back on itself, so there's never a smear.
    vec2 view = (hash2(id + floor(uStep) * vec2(1.0, 7.0)) - 0.5) * uFacetWander;
    vec2 crystal = 0.5 + view + inTile * uFacetView * vec2(1.0 / aspect, 1.0);
    crystal = 1.0 - abs(1.0 - mod(crystal, 2.0));
    vec3 color = texture(sTD2DInputs[0], crystal).rgb;

    // The crystal's sparkle lights its brightest points.
    float bright = dot(color, vec3(0.3, 0.6, 0.1));
    color += color * pow(bright, 3.0) * uSparkle * uSparkleGlow;

    // A brighter picture on the beat.
    color *= 1.0 + uBeatGlow * uPulse;

    // A soft dark line between tiles.
    color *= mix(0.35, 1.0, smoothstep(0.0, uLineWidth, edge));

    fragColor = TDOutputSwizzle(vec4(color, 1.0));
}
