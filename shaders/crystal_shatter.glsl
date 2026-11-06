// Puts the gem over the image, and breaks it into shards when it explodes.
//
// Input 0 is the gem on a transparent background, input 1 is the image. The gem
// is split into irregular cells. For each pixel, every nearby shard is moved back
// to where it started; if that lands inside the shard's own cell, the pixel shows
// that part of the gem. The cost only applies while the gem is apart.

uniform float uExplode;        // 0 is whole, 1 is fully blown apart
uniform float uShardSpread;    // how far shards fly: 1 takes the gem's edge to the picture's
uniform float uShardSize;      // shard size, in image heights
uniform float uShardSpin;      // how many turns a shard makes at full spread
uniform float uBackgroundDim;  // brightness of the image behind the gem
uniform float uShadow;         // how dark the halo around the gem is

layout(location = 0) out vec4 fragColor;

const float GEM_REACH = 0.62;  // the gem fits within this distance of the center
const float GEM_RADIUS = 0.42; // about how far its edge usually is from the center
const int HALO_TAPS = 12;
const float HALO_RADIUS = 0.035;

float aspect;

vec2 hash2(vec2 p) {
    return fract(sin(vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)))) * 43758.5453);
}

// Centered position, in image heights, to texture coordinates.
vec2 toUV(vec2 p) {
    return p / vec2(aspect, 1.0) + 0.5;
}

vec2 seedOf(vec2 cell) {
    return (cell + 0.2 + 0.6 * hash2(cell)) * uShardSize;
}

// The cell whose seed is nearest, and how close the next nearest is. A small
// gap between the two means this point is near the shard's edge.
vec2 nearestCell(vec2 q, out float edgeGap) {
    vec2 base = floor(q / uShardSize);
    vec2 best = base;
    float first = 1e9, second = 1e9;
    for (int y = -1; y <= 1; y++) {
        for (int x = -1; x <= 1; x++) {
            vec2 cell = base + vec2(float(x), float(y));
            float d = length(q - seedOf(cell));
            if (d < first) {
                second = first;
                first = d;
                best = cell;
            } else if (d < second) {
                second = d;
            }
        }
    }
    edgeGap = second - first;
    return best;
}

vec4 shatteredGem(vec2 p) {
    int reach = int(ceil(GEM_REACH / uShardSize));
    for (int j = -reach; j <= reach; j++) {
        for (int i = -reach; i <= reach; i++) {
            vec2 cell = vec2(float(i), float(j));
            vec2 seed = seedOf(cell);
            vec2 random = hash2(cell + 17.0);

            // The gem is stretched over the whole picture: shards from its edge reach the
            // picture's edges and corners, and the ones in between fill the space. Each
            // goes a different distance, so they don't keep the gem's shape.
            vec2 fill = vec2(aspect * 0.5, 0.5) / GEM_RADIUS * uShardSpread;
            vec2 away = (seed * fill * (0.75 + 0.5 * random.x) - seed) * uExplode;
            float spin = (random.y - 0.5) * 6.28318 * uShardSpin * uExplode;
            float scale = 1.0;
            float c = cos(-spin), s = sin(-spin);
            vec2 local = (p - seed - away) / scale;
            if (dot(local, local) > uShardSize * uShardSize * 3.0) {
                continue;
            }
            vec2 q = vec2(c * local.x - s * local.y, s * local.x + c * local.y) + seed;

            float edgeGap;
            if (nearestCell(q, edgeGap) != cell) {
                continue;
            }
            vec4 color = texture(sTD2DInputs[0], toUV(q));
            if (color.a < 0.02) {
                continue;
            }
            // The freshly broken edges catch the light.
            float glow = (1.0 - smoothstep(0.0, 0.012, edgeGap)) * uExplode;
            color.rgb += vec3(0.9, 0.95, 1.0) * glow * color.a;
            return color;
        }
    }
    return vec4(0.0);
}

void main() {
    vec2 res = uTDOutputInfo.res.zw;
    aspect = res.x / res.y;
    vec2 uv = vUV.st;
    vec2 p = (uv - 0.5) * vec2(aspect, 1.0);

    vec4 gem = uExplode > 0.001 ? shatteredGem(p) : texture(sTD2DInputs[0], uv);

    // A dark halo around the whole gem separates it from the image. It fades as
    // the gem breaks apart, when there's no longer one outline to follow.
    float halo = 0.0;
    for (int i = 0; i < HALO_TAPS; i++) {
        float a = 6.28318 * float(i) / float(HALO_TAPS);
        halo += texture(sTD2DInputs[0], uv + vec2(cos(a) / aspect, sin(a)) * HALO_RADIUS).a;
    }
    halo *= (1.0 - uExplode) / float(HALO_TAPS);

    vec3 background = texture(sTD2DInputs[1], uv).rgb * uBackgroundDim * (1.0 - uShadow * halo);
    fragColor = TDOutputSwizzle(vec4(gem.rgb + background * (1.0 - gem.a), 1.0));
}
