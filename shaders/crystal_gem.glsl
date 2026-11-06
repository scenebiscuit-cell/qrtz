// What the crystal shaders share: a faceted gem that bends the input image through
// its facets and splits edges into color. crystal_refract draws the main gem with
// this, and crystal_small draws the small one.
//
// The gem is a convex shape made of flat facets, each described by a plane. For
// every pixel, a ray enters the gem, bends, bounces inside until it can get out,
// and bends again. Where it ends up decides which part of the image shows. Red,
// green and blue each take their own path, which makes the rainbow edges.
//
// Each small-crystal shader draws into its own small image, called its tile, sized
// to fit it and no bigger. Keeping them apart matters: the driver on this machine
// pays for code in a shader even on pixels that never run it.

uniform float uAngle;       // spin around the gem's axis, radians
uniform float uTilt;        // how far the top leans toward the viewer, radians
uniform float uRoll;        // side-to-side lean, radians
uniform float uFacetBase;   // facet brightness facing away from the light
uniform float uFacetContrast; // extra brightness facing the light
uniform float uEdgeGlow;    // how bright facet edges always are
uniform float uGlintGain;   // how bright glints get at full sparkle
uniform float uSize;        // gem size, 1 fills about the image height
uniform float uIor;         // index of refraction: how strongly facets bend light
uniform float uRefraction;  // how far bent rays shift the image
uniform float uDispersion;  // how far apart red, green and blue bend
uniform float uBreathe;     // bass: facets push outward
uniform float uSparkle;     // treble: glints and rainbow edges, 0 to 1
uniform float uShapeA;      // the shape being left, or the current shape
uniform float uShapeB;      // the shape being morphed into
uniform float uMorph;       // how far between them, 0 to 1
uniform float uScale;       // shrinks the gem during a shape change, 0 to 1
uniform float uOffsetX;     // moves the gem across the image, in image heights
uniform float uOffsetY;
uniform float uSatX;        // the small crystal's place, relative to the main gem
uniform float uSatY;
uniform float uSatZ;        // negative is nearer the viewer than the main gem
uniform float uSatScale;    // its size compared with the main gem, 0 when absent
uniform float uSatBlob;     // 1 is a smooth blob, 0 is a faceted crystal
uniform float uSatAngle;    // its own spin, radians
uniform float uSatTilt;     // its own lean, like uTilt and uRoll
uniform float uSatRoll;
uniform float uSatBreathe;  // its own soft swell, like uBreathe
uniform float uSatFigure;   // what it is: 0 crystal, 1 laughing face, 2 pill
uniform float uSatPulse;    // the beat, 0 to 1: the face laughs harder
uniform float uCameraDistance;
uniform float uLens;
uniform float uTileX;       // what part of the image the tile covers, in image heights
uniform float uTileY;
uniform float uTileHalf;

layout(location = 0) out vec4 fragColor;
layout(location = 1) out vec4 fragDistance; // how far away each pixel is, for crystal_layers

const float PI = 3.14159265;
const float FAR = 1e5;
const int RING = 8;                     // facets around each ring
const int NUM_PLANES = 1 + 3 * RING;    // table, crown, girdle, pavilion
const int MAX_BOUNCES = 4;
const float UNUSED_PLANE = 6.0;

// The numbers crystal_motion.py sends for each shape.
const int SHAPE_BRILLIANT = 0;
const int SHAPE_QUARTZ = 1;
const int SHAPE_OCTAHEDRON = 2;
const int SHAPE_EMERALD = 3;

vec3 planeNormals[NUM_PLANES];
float planeDists[NUM_PLANES];

// What the gem being drawn is cut from. The main gem uses the planes as they are.
float planeScale = 1.0;
float sphereRadius = 0.0;
float breathe = 0.0;

mat3 rotateX(float a) {
    float c = cos(a), s = sin(a);
    return mat3(1.0, 0.0, 0.0,  0.0, c, s,  0.0, -s, c);
}

mat3 rotateY(float a) {
    float c = cos(a), s = sin(a);
    return mat3(c, 0.0, -s,  0.0, 1.0, 0.0,  s, 0.0, c);
}

mat3 rotateZ(float a) {
    float c = cos(a), s = sin(a);
    return mat3(c, s, 0.0,  -s, c, 0.0,  0.0, 0.0, 1.0);
}

vec3 ringNormal(float angle, float out_, float up) {
    return normalize(vec3(cos(angle) * out_, up, sin(angle) * out_));
}

// Each shape uses the same numbered planes, so morphing can slide each one to its
// new place. Any set of planes cuts out a solid shape, which keeps every moment of
// a morph looking like a real crystal. A shape that doesn't need a plane moves it
// far away, where it cuts nothing. ring is 0 for the top ring of facets, 1 for the
// middle and 2 for the bottom.
void shapePlane(int shape, int ring, int i, out vec3 normal, out float dist) {
    float step45 = 2.0 * PI / float(RING);
    float a = float(i) * step45;
    normal = ringNormal(a, ring == 1 ? 1.0 : 0.7, ring == 0 ? 0.7 : (ring == 2 ? -0.7 : 0.0));
    dist = UNUSED_PLANE;

    if (shape == SHAPE_BRILLIANT) {
        float offset = (float(i) + 0.5) * step45;
        if (ring == 0) { normal = ringNormal(offset, 0.62, 0.78); dist = 0.74; }
        if (ring == 1) { normal = ringNormal(a, 1.0, 0.04); dist = 0.82; }
        if (ring == 2) { normal = ringNormal(offset, 0.76, -0.65); dist = 0.70; }
    } else if (shape == SHAPE_QUARTZ) {
        // A six-sided column with a pointed top and a shorter point below.
        if (i < 6) {
            float side = float(i) * PI / 3.0;
            if (ring == 0) { normal = ringNormal(side, 0.625, 0.781); dist = 0.742; }
            if (ring == 1) { normal = ringNormal(side, 1.0, 0.0); dist = 0.5; }
            if (ring == 2) { normal = ringNormal(side, 0.574, -0.819); dist = 0.656; }
        }
    } else if (shape == SHAPE_OCTAHEDRON) {
        // Two four-sided pyramids, base to base.
        if (i < 4 && ring != 1) {
            float side = (float(i) + 0.5) * PI / 2.0;
            normal = ringNormal(side, 0.765, ring == 0 ? 0.644 : -0.644);
            dist = 0.612;
        }
    } else {
        // Emerald: a long rectangle with cut corners and stepped sides.
        float reach = 0.806;
        if (i % 4 == 0) reach = 0.85;
        if (i % 4 == 2) reach = 0.55;
        if (ring == 0) { normal = ringNormal(a, 0.6, 0.8); dist = 0.6 * reach + 0.12; }
        if (ring == 1) { normal = ringNormal(a, 1.0, 0.0); dist = reach; }
        if (ring == 2) { normal = ringNormal(a, 0.65, -0.76); dist = 0.65 * reach + 0.038; }
    }
}

float tableHeight(int shape) {
    if (shape == SHAPE_BRILLIANT) return 0.42;
    if (shape == SHAPE_EMERALD) return 0.38;
    return UNUSED_PLANE;
}

// Builds the gem, partway between two shapes during a morph. Bass pushes
// alternating facets out by different amounts, so the gem's light shifts on the
// kick as well as its size.
void buildGem(float swell) {
    breathe = swell;
    int shapeA = int(uShapeA + 0.5);
    int shapeB = int(uShapeB + 0.5);
    bool morphing = uMorph > 0.0;

    planeNormals[0] = vec3(0.0, 1.0, 0.0);
    float size = uSize * uScale;
    planeDists[0] = mix(tableHeight(shapeA), tableHeight(shapeB), uMorph) * size;

    const float pushByRing[3] = float[3](1.0, 0.5, 1.5);
    for (int ring = 0; ring < 3; ring++) {
        for (int i = 0; i < RING; i++) {
            vec3 normal, normalB;
            float dist, distB;
            shapePlane(shapeA, ring, i, normal, dist);
            if (morphing) {
                shapePlane(shapeB, ring, i, normalB, distB);
                normal = normalize(mix(normal, normalB, uMorph) + vec3(0.0, 1e-4, 0.0));
                dist = mix(dist, distB, uMorph);
            }
            float push = (i % 2 == 0 ? 1.0 : 0.35) * swell * pushByRing[ring];
            int index = 1 + ring * RING + i;
            planeNormals[index] = normal;
            planeDists[index] = (dist + push) * size;
        }
    }
}

// Finds where a ray goes through the gem. edgeDist is small near a facet edge.
bool hitGem(vec3 ro, vec3 rd, out float tEnter, out float tExit, out vec3 normal, out float edgeDist) {
    tEnter = -FAR;
    tExit = FAR;
    float tSecond = -FAR;
    normal = vec3(0.0);
    for (int i = 0; i < NUM_PLANES; i++) {
        float facing = dot(rd, planeNormals[i]);
        float gap = planeDists[i] * planeScale - dot(ro, planeNormals[i]);
        if (abs(facing) < 1e-5) {
            if (gap < 0.0) return false;
            continue;
        }
        float t = gap / facing;
        if (facing < 0.0) {
            if (t > tEnter) {
                tSecond = tEnter;
                tEnter = t;
                normal = planeNormals[i];
            } else if (t > tSecond) {
                tSecond = t;
            }
        } else {
            tExit = min(tExit, t);
        }
    }
    // A blob is the same gem also cut by a sphere.
    if (sphereRadius > 0.0) {
        float along = dot(ro, rd);
        float under = along * along - dot(ro, ro) + sphereRadius * sphereRadius;
        if (under < 0.0) return false;
        float root = sqrt(under);
        if (-along - root > tEnter) {
            tSecond = tEnter;
            tEnter = -along - root;
            normal = (ro + rd * tEnter) / sphereRadius;
        }
        tExit = min(tExit, -along + root);
    }
    edgeDist = tEnter - tSecond;
    return tEnter < tExit && tExit > 0.0;
}

// Follows light inside the gem and returns its direction once it gets out.
vec3 traceInside(vec3 pos, vec3 dir, float ior) {
    for (int bounce = 0; bounce < MAX_BOUNCES; bounce++) {
        float nearest = FAR;
        vec3 exitNormal = vec3(0.0, 1.0, 0.0);
        for (int i = 0; i < NUM_PLANES; i++) {
            float facing = dot(dir, planeNormals[i]);
            if (facing > 1e-5) {
                float t = (planeDists[i] * planeScale - dot(pos, planeNormals[i])) / facing;
                if (t < nearest) {
                    nearest = t;
                    exitNormal = planeNormals[i];
                }
            }
        }
        if (sphereRadius > 0.0) {
            float along = dot(pos, dir);
            float t = -along + sqrt(max(along * along - dot(pos, pos) + sphereRadius * sphereRadius, 0.0));
            if (t < nearest) {
                nearest = t;
                exitNormal = normalize(pos + dir * t);
            }
        }
        pos += dir * nearest;
        vec3 outside = refract(dir, -exitNormal, ior);
        if (dot(outside, outside) > 0.0) {
            return outside;
        }
        dir = reflect(dir, exitNormal);
    }
    return dir;
}

// Reads the image for one color's path through the gem.
float sampleChannel(vec2 uv, vec3 pos, vec3 rd, vec3 normal, mat3 toView, float ior, float aspect, int channel) {
    vec3 inside = refract(rd, normal, 1.0 / ior);
    vec3 outDir = toView * traceInside(pos, inside, ior);
    float strength = uRefraction * (1.0 + 4.0 * breathe);
    vec2 shifted = uv + outDir.xy * strength * vec2(1.0 / aspect, 1.0);
    return texture(sTD2DInputs[0], shifted)[channel];
}

// Draws one gem for a ray that's already in its own space, on a clear background.
// hitDist says how far along the ray the gem starts, for working out which gem is
// in front.
vec4 shadeGem(vec2 uv, vec3 ro, vec3 rd, mat3 toView, float aspect, out float hitDist) {
    float tEnter, tExit, edgeDist;
    vec3 normal;
    hitDist = FAR;
    if (!hitGem(ro, rd, tEnter, tExit, normal, edgeDist)) {
        return vec4(0.0);
    }
    hitDist = tEnter;
    vec3 pos = ro + rd * tEnter;

    // Rainbow edges widen with the treble.
    float spread = uDispersion * (1.0 + 2.0 * uSparkle);
    vec3 color = vec3(
        sampleChannel(uv, pos, rd, normal, toView, uIor - spread, aspect, 0),
        sampleChannel(uv, pos, rd, normal, toView, uIor, aspect, 1),
        sampleChannel(uv, pos, rd, normal, toView, uIor + spread, aspect, 2));

    // Each facet catches the light differently, so the shape reads as cut.
    vec3 viewNormal = toView * normal;
    vec3 lightDir = normalize(vec3(0.35, 0.6, -0.7));
    color *= uFacetBase + uFacetContrast * max(dot(viewNormal, lightDir), 0.0);

    // A glancing facet mirrors more of the light above it.
    float fresnel = pow(1.0 - max(dot(-rd, normal), 0.0), 3.0);
    color += vec3(0.35) * fresnel;

    // Glints: bright lines on facet edges and highlights on facing facets. The
    // edges always show a little, so the cut stays visible in quiet passages.
    float edgeGlint = 1.0 - smoothstep(0.0, 0.016, edgeDist);
    float facetGlint = pow(max(dot(viewNormal, normalize(lightDir + vec3(0.0, 0.0, -1.0))), 0.0), 30.0);
    color += vec3(0.9, 0.95, 1.0) * (edgeGlint * (uEdgeGlow + uGlintGain * uSparkle) + facetGlint * (0.2 + uGlintGain * uSparkle));

    // Soften the outline so it doesn't look jagged. The result is on a clear
    // background, so crystal_shatter can break it apart and put it over the image.
    float margin = tExit - tEnter;
    float cover = smoothstep(0.0, max(fwidth(margin), 1e-4) * 1.5, margin);
    return vec4(color * cover, cover);
}

// Everything a small-crystal shader needs for one pixel of its tile.
void smallCrystalRay(out vec2 uv, out vec3 from, out vec3 rd, out mat3 toView, out float aspect) {
    vec2 imageSize = vec2(textureSize(sTD2DInputs[0], 0));
    aspect = imageSize.x / imageSize.y;
    vec2 p = vec2(uTileX, uTileY) + (vUV.st - 0.5) * 2.0 * uTileHalf;
    uv = (p + vec2(uOffsetX, uOffsetY)) / vec2(aspect, 1.0) + 0.5;
    vec3 cameraPos = vec3(0.0, 0.0, -uCameraDistance);
    vec3 center = vec3(uSatX, uSatY, uSatZ) * uScale;
    mat3 toSat = rotateY(-uSatAngle) * rotateX(uSatTilt) * rotateZ(uSatRoll);
    from = toSat * (cameraPos - center) / uSatScale;
    rd = toSat * normalize(vec3(p, uLens));
    toView = transpose(toSat);
}
