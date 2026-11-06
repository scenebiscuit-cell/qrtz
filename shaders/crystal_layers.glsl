// Puts the small crystal's tile and the lava-lamp blobs into the picture. Whichever is
// nearer at each pixel goes on top, so the small crystal passes in front of the main
// gem and behind it, and things bud out of each other and sink back in.
//
// Inputs: main gem, its distances, the small crystal's tile, its distances, the blobs,
// their distances.

uniform float uSatOn;
uniform float uBlobsOn;
uniform float uOffsetX;
uniform float uOffsetY;
uniform float uTileX;
uniform float uTileY;
uniform float uTileHalf;

layout(location = 0) out vec4 fragColor;

void main() {
    vec4 result = texture(sTD2DInputs[0], vUV.st);
    float nearest = texture(sTD2DInputs[1], vUV.st).r;
    if (uSatOn > 0.5) {
        vec2 res = uTDOutputInfo.res.zw;
        vec2 p = (vUV.st - 0.5) * vec2(res.x / res.y, 1.0) - vec2(uOffsetX, uOffsetY);
        vec2 tile = (p - vec2(uTileX, uTileY)) / (2.0 * uTileHalf) + 0.5;
        if (all(greaterThan(tile, vec2(0.0))) && all(lessThan(tile, vec2(1.0)))) {
            vec4 small = texture(sTD2DInputs[2], tile);
            float smallDist = texture(sTD2DInputs[3], tile).r;
            if (smallDist < nearest) {
                result = small + result * (1.0 - small.a);
                nearest = smallDist;
            } else {
                result += small * (1.0 - result.a);
            }
        }
    }
    if (uBlobsOn > 0.5) {
        vec4 blobs = texture(sTD2DInputs[4], vUV.st);
        if (texture(sTD2DInputs[5], vUV.st).r < nearest) {
            result = blobs + result * (1.0 - blobs.a);
        } else {
            result += blobs * (1.0 - result.a);
        }
    }
    fragColor = TDOutputSwizzle(result);
}
