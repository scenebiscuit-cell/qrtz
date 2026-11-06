// Small lava-lamp blobs that morph out of the crystals and drift out of the picture.
// Each is a wobbling disc shaded like a ball, which is far cheaper than walking rays.
// The blobs' numbers come from scripts/crystal_motion.py through droplet_table.
//
// Colored blobs match the smiley and pill. Clear ones bend the image like the gem.

const int MAX_BLOBS = 8;
uniform vec4 uBlobPlace[MAX_BLOBS]; // x, y and radius in image heights, and how far away
uniform vec4 uBlobShape[MAX_BLOBS]; // heading, stretch, wobble position, kind
uniform float uBlobCount;
uniform float uRefraction;
uniform float uDispersion;
uniform float uSparkle;
uniform float uFacetBase;
uniform float uFacetContrast;
uniform float uGlintGain;

layout(location = 0) out vec4 fragColor;
layout(location = 1) out vec4 fragDistance; // how far away each pixel is, for crystal_layers

const int KIND_SMILEY = 1;
const int KIND_PILL = 2;
const vec3 SMILEY_TINT = vec3(1.0, 0.8, 0.12);
const vec3 PILL_TINT = vec3(0.41, 0.875, 0.86);

void main() {
    vec2 res = uTDOutputInfo.res.zw;
    float aspect = res.x / res.y;
    vec2 p = (vUV.st - 0.5) * vec2(aspect, 1.0);

    vec4 result = vec4(0.0);
    float nearest = 1e4;
    int count = int(uBlobCount + 0.5);
    for (int i = 0; i < count; i++) {
        vec4 place = uBlobPlace[i];
        vec4 shape = uBlobShape[i];
        float radius = place.z;
        if (radius <= 0.0) continue;
        vec2 toPixel = p - place.xy;
        if (dot(toPixel, toPixel) > radius * radius * 4.0) continue;

        // Into the blob's own space, stretched along its heading.
        float c = cos(shape.x), s = sin(shape.x);
        vec2 q = vec2(c * toPixel.x + s * toPixel.y, c * toPixel.y - s * toPixel.x) / radius;
        q *= vec2(1.0 / shape.y, shape.y);

        // The outline ripples slowly, so it never settles into a perfect circle.
        float around = atan(q.y, q.x);
        float outline = 1.0 + 0.07 * sin(around * 3.0 + shape.z) + 0.025 * sin(around * 5.0 - shape.z * 1.7);
        float rho = length(q) / outline;
        if (rho >= 1.0) continue;
        float cover = 1.0 - smoothstep(1.0 - 2.0 / (res.y * radius), 1.0, rho);

        // Shaded as a ball, with its normal turned back to face the picture.
        float bulge = sqrt(1.0 - rho * rho);
        float dist = place.w - radius * bulge;
        if (dist > nearest) continue;
        vec2 side = rho > 0.0001 ? q / length(q) * rho : vec2(0.0);
        vec3 normal = vec3(c * side.x - s * side.y, s * side.x + c * side.y, -bulge);

        // The same glass and light as the crystals, in the blob's color. A gentle bend,
        // because a strong one squeezes the whole image into a tiny ball.
        vec2 bend = normal.xy * uRefraction * 0.3 * vec2(1.0 / aspect, 1.0);
        float spread = uDispersion * (1.0 + 2.0 * uSparkle) * 6.0;
        vec3 color = vec3(
            textureLod(sTD2DInputs[0], vUV.st + bend * (1.0 - spread), 0.0).r,
            textureLod(sTD2DInputs[0], vUV.st + bend, 0.0).g,
            textureLod(sTD2DInputs[0], vUV.st + bend * (1.0 + spread), 0.0).b);
        int kind = int(shape.w + 0.5);
        if (kind == KIND_SMILEY) {
            color = color * SMILEY_TINT * 0.2 + SMILEY_TINT * 0.7;
        } else if (kind == KIND_PILL) {
            color = color * PILL_TINT * 0.2 + PILL_TINT * 0.7;
        }
        vec3 lightDir = normalize(vec3(0.35, 0.6, -0.7));
        color *= uFacetBase + uFacetContrast * max(dot(normal, lightDir), 0.0);
        color += vec3(0.35) * pow(1.0 - bulge, 3.0);
        float glint = pow(max(dot(normal, normalize(lightDir + vec3(0.0, 0.0, -1.0))), 0.0), 30.0);
        color += vec3(0.9, 0.95, 1.0) * glint * (0.2 + uGlintGain * uSparkle);

        nearest = dist;
        result = vec4(color * cover, cover);
    }
    fragColor = TDOutputSwizzle(result);
    fragDistance = vec4(nearest);
}
