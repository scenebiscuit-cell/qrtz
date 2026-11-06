// The small crystal when it's a figure with dents and gaps, which the flat facets
// in crystal_gem can't make. Figures are cut crystal too, with flat cuts around their
// edges and a smooth front.

#include <crystal_gem>

// A figure is a function that says how far any point is from its surface, and the
// ray walks forward by that distance until it arrives. In these functions, a
// figure's front faces the viewer along negative z, and a radius of 1 is about the
// main gem's size.

const int FIGURE_FACE = 1;
const float FIGURE_REACH = 1.25;    // nothing in a figure reaches beyond this
const int MARCH_STEPS = 56;
const int INSIDE_STEPS = 14;

float segment(vec2 p, vec2 a, vec2 b) {
    vec2 along = b - a;
    return length(p - a - along * clamp(dot(p - a, along) / dot(along, along), 0.0, 1.0));
}

// Wavy eyes and a thin smile with a tick across each end. Negative is on the line.
float smileyFeatures(vec2 p) {
    vec2 left = vec2(p.x + 0.21 + 0.025 * sin(p.y * 17.0), p.y - 0.28);
    vec2 right = vec2(p.x - 0.19 + 0.025 * sin(p.y * 15.0 + 1.5), p.y - 0.26);
    float eyes = min(length(vec2(left.x, max(abs(left.y) - 0.17, 0.0))) - 0.055,
                     length(vec2(right.x, max(abs(right.y) - 0.17, 0.0))) - 0.055);

    // The smile is one arc of a circle, so its line stays even all the way along.
    const float RADIUS = 0.54;
    const vec2 CORNER = vec2(0.47, -0.27);  // right end of the smile, from the circle's center
    vec2 q = p - vec2(0.0, 0.24 - 0.03 * uSatPulse);
    vec2 mirrored = vec2(abs(q.x), q.y);
    bool onArc = mirrored.y < 0.0 && mirrored.x * CORNER.y > mirrored.y * CORNER.x;
    float smile = (onArc ? abs(length(q) - RADIUS) : length(mirrored - CORNER)) - 0.024;

    // A short tick straight across each end, joined to the line.
    vec2 across = normalize(CORNER) * 0.075;
    float ticks = segment(mirrored, CORNER - across, CORNER + across) - 0.024;
    return min(eyes, min(smile, ticks));
}

// Flat sides for a shape whose outline is a circle, so its edge reads as cut.
float polygonRadius(vec2 q, float sides) {
    float wedge = 6.28318 / sides;
    float a = mod(atan(q.y, q.x) + wedge * 0.5, wedge) - wedge * 0.5;
    return length(q) * cos(a);
}

// One drip: straight sides with a rounded end, running down to endY.
float dripOutline(vec2 p, float x, float endY, float width) {
    float across = abs(p.x - x);
    float height = endY + width;
    float body = p.y < height ? length(vec2(across, p.y - height)) - width : across - width;
    return max(body, p.y + 0.1);
}

// A slab in the outline's shape, with its edges cut at an angle.
float cutSlab(float outline, float z, float thick, float chamfer) {
    return max(max(outline, abs(z) - thick), (outline + abs(z) - thick + chamfer) * 0.707);
}

// The drips' outline, seen from the front. They stretch on the beat. Negative is inside.
float smileyDrips(vec2 p) {
    float stretch = 0.07 * uSatPulse;
    float d = dripOutline(p, -0.34, -0.62 - stretch, 0.1);
    d = min(d, dripOutline(p, -0.09, -0.52 - stretch * 0.5, 0.085));
    d = min(d, dripOutline(p, 0.13, -0.86 - stretch, 0.105));
    return min(d, dripOutline(p, 0.38, -0.56 - stretch * 0.7, 0.09));
}

// The melting smiley: a smooth dome on the front of the head, with cut facets around
// its rim, on its back and all over the drips.
float smileyDistance(vec3 p) {
    const vec2 CENTER = vec2(0.0, 0.17);
    float head = cutSlab(polygonRadius(p.xy - CENTER, 14.0) - 0.68, p.z, 0.36, 0.28);
    if (p.z < 0.0) {
        head = max(head, length(p - vec3(CENTER, 0.85)) - 1.19);
    }
    return min(head, cutSlab(smileyDrips(p.xy), p.z, 0.16, 0.1));
}

const float DOLPHIN_SIZE = 1.12;     // bigger numbers make the dolphin bigger
const float PILL_THICK = 0.27;
const float RECESS_DEPTH = 0.07;
const vec3 PILL_COLOR = vec3(0.33, 0.70, 0.69);

// The dolphin's outline at its size on the pill. dolphin_field worked out every
// distance once, because doing it here costs far too much for every step of a ray.
const float DOLPHIN_FIELD_SPAN = 1.6;
float pillDolphin(vec2 p) {
    vec2 uv = p / DOLPHIN_SIZE / DOLPHIN_FIELD_SPAN + 0.5;
    return texture(sTD2DInputs[1], uv).r * DOLPHIN_SIZE;
}

// A chunky round tablet cut like a gem, with a smooth top and the dolphin sunk into it.
float pillDistance(vec3 p) {
    float tablet = cutSlab(polygonRadius(p.xy, 12.0) - 0.88, p.z, PILL_THICK, 0.16);
    if (p.z < -0.05 && tablet < 0.12) {
        float recess = max(pillDolphin(p.xy), p.z + PILL_THICK - RECESS_DEPTH);
        tablet = max(tablet, -recess);
    }
    return tablet;
}

float figureDistance(vec3 p) {
    float figure = int(uSatFigure + 0.5) == FIGURE_FACE ? smileyDistance(p) : pillDistance(p);
    return mix(figure, length(p) - 0.62, uSatBlob);
}

vec3 figureNormal(vec3 p) {
    const vec2 e = vec2(0.004, -0.004);
    return normalize(e.xyy * figureDistance(p + e.xyy) + e.yyx * figureDistance(p + e.yyx)
                   + e.yxy * figureDistance(p + e.yxy) + e.xxx * figureDistance(p + e.xxx));
}

// Scattered flecks, like the bits in a pressed tablet: 1 on a fleck, else 0.
float flecks(vec3 p) {
    vec3 cell = floor(p * 26.0);
    float pick = fract(sin(dot(cell, vec3(12.9898, 78.233, 37.719))) * 43758.5453);
    if (pick < 0.68) return 0.0;
    vec3 spot = fract(cell.yzx * 0.37 + pick) * 0.5 + 0.25;
    return 1.0 - smoothstep(0.16, 0.3, length(fract(p * 26.0) - spot));
}

// What a fully formed figure adds to the glass at a point on its surface. tint
// colors the crystal, dim is low where features are drawn so they read at a distance,
// and frost is high where the crystal is etched pale, as the dolphin is.
void figureLook(vec3 p, out vec3 tint, out float dim, out float sparkles, out float frost) {
    dim = 1.0;
    sparkles = 0.0;
    frost = 0.0;
    if (int(uSatFigure + 0.5) == FIGURE_FACE) {
        tint = vec3(1.0, 0.8, 0.12);
        if (p.z < 0.0) {
            dim = mix(0.04, 1.0, smoothstep(0.0, 0.012, smileyFeatures(p.xy)));
        }
    } else {
        tint = PILL_COLOR * 1.25;
        if (p.z < 0.0) {
            // The wall nearest the light shadows the floor below it, and the far edge
            // catches the light, which is what makes it read as sunk in.
            const vec2 TOWARD_LIGHT = vec2(0.5, 0.86);
            float inside = pillDolphin(p.xy);
            float wallSide = pillDolphin(p.xy + TOWARD_LIGHT * 0.05);
            float floorShade = mix(0.48, 0.2,smoothstep(-0.02, 0.02, wallSide));
            dim = mix(floorShade, 1.0, smoothstep(-0.004, 0.004, inside));
            frost = 0.6 * (1.0 - smoothstep(0.0, 0.016, inside)) * step(0.0, inside)
                  * (1.0 - smoothstep(-0.02, 0.0, wallSide));
        }
        sparkles = flecks(p);
    }
}

// Follows light through a figure and returns its direction on the way out.
vec3 figureExit(vec3 pos, vec3 dir, float ior) {
    float t = 0.03;
    for (int i = 0; i < INSIDE_STEPS; i++) {
        float d = -figureDistance(pos + dir * t);
        if (d < 0.004) break;
        t += d;
    }
    vec3 exitNormal = figureNormal(pos + dir * t);
    vec3 outside = refract(dir, -exitNormal, ior);
    return dot(outside, outside) > 0.0 ? outside : reflect(dir, exitNormal);
}

// Draws a figure, like shadeGem. Its space is scaled so the functions above can
// use the same sizes at any size on screen.
vec4 shadeFigure(vec2 uv, vec3 ro, vec3 rd, mat3 toView, float aspect, float unit, out float hitDist) {
    hitDist = FAR;
    vec3 start = ro / unit;

    // Jump straight to the sphere the figure fits inside.
    float along = dot(start, rd);
    float under = along * along - dot(start, start) + FIGURE_REACH * FIGURE_REACH;
    if (under < 0.0) return vec4(0.0);
    float root = sqrt(under);
    float t = max(-along - root, 0.0);
    float tEnd = -along + root;

    // A ray that only just misses still covers part of its pixel, which keeps the
    // outline from looking jagged.
    float pixelSize = 3.0 * uTileHalf / (uLens * uTDOutputInfo.res.w);
    float cover = 0.0;
    float nearestRatio = 1.0;
    float nearestT = t;
    for (int i = 0; i < MARCH_STEPS && t < tEnd; i++) {
        float d = figureDistance(start + rd * t);
        if (d < 0.002) {
            cover = 1.0;
            nearestT = t;
            break;
        }
        float ratio = d / (pixelSize * t);
        if (ratio < nearestRatio) {
            nearestRatio = ratio;
            nearestT = t;
        }
        t += d * 0.85;
    }
    if (cover == 0.0) cover = 1.0 - nearestRatio;
    if (cover <= 0.0) return vec4(0.0);
    t = nearestT;

    hitDist = t * unit;
    vec3 pos = start + rd * t;
    vec3 normal = figureNormal(pos);

    // The facets, tint and engraving fade in as it forms from the sphere.
    float formed = 1.0 - uSatBlob;
    bool isFace = int(uSatFigure + 0.5) == FIGURE_FACE;
    vec3 tint;
    float dim, sparkles, frost;
    figureLook(pos, tint, dim, sparkles, frost);
    tint = mix(vec3(1.0), tint, formed);
    dim = mix(1.0, dim, formed);

    // Light bends in through the cut facet and out through the far side.
    float spread = uDispersion * (1.0 + 2.0 * uSparkle);
    vec3 inside = refract(rd, normal, 1.0 / uIor);
    vec3 outDir = toView * figureExit(pos, inside, uIor);
    vec2 toImage = vec2(1.0 / aspect, 1.0) * uRefraction * (1.0 + 4.0 * breathe);
    vec3 color = vec3(
        texture(sTD2DInputs[0], uv + outDir.xy * toImage * (1.0 - spread * 6.0)).r,
        texture(sTD2DInputs[0], uv + outDir.xy * toImage).g,
        texture(sTD2DInputs[0], uv + outDir.xy * toImage * (1.0 + spread * 6.0)).b);

    // Tinted crystal, with enough of its own color to read over a dark image.
    color = color * tint * mix(1.0, 0.7, formed) + tint * 0.42 * formed;
    color = mix(color, vec3(0.78, 0.95, 0.94), frost * formed * 0.85);

    // The same light as the gems.
    vec3 viewNormal = toView * normal;
    vec3 lightDir = normalize(vec3(0.35, 0.6, -0.7));
    color *= (uFacetBase + uFacetContrast * max(dot(viewNormal, lightDir), 0.0)) * dim;
    float fresnel = pow(1.0 - max(dot(-rd, normal), 0.0), 3.0);
    color += vec3(0.35) * fresnel;
    float facetGlint = pow(max(dot(viewNormal, normalize(lightDir + vec3(0.0, 0.0, -1.0))), 0.0), 30.0);
    color += vec3(0.9, 0.95, 1.0) * dim * facetGlint * (0.2 + uGlintGain * uSparkle);
    color += vec3(0.95) * sparkles * formed * (0.35 + uSparkle);

    return vec4(color * cover, cover);
}

void main() {
    breathe = uSatBreathe;
    vec2 uv;
    vec3 from, rd;
    mat3 toView;
    float aspect, satDist;
    smallCrystalRay(uv, from, rd, toView, aspect);
    float unit = uSize * uScale * (1.0 + uSatBreathe);
    vec4 result = shadeFigure(uv, from, rd, toView, aspect, unit, satDist);

    fragColor = TDOutputSwizzle(result);
    fragDistance = vec4(min(satDist * uSatScale, 1e4));
}
