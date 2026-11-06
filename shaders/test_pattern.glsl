// A test image for the virtual crystal: straight lines and clear colors make the
// bending and the rainbow edges easy to see. The photo deck replaces it in M5.

layout(location = 0) out vec4 fragColor;

vec3 hueToColor(float hue) {
    return 0.5 + 0.5 * cos(6.28318 * (hue + vec3(0.0, 0.33, 0.67)));
}

void main() {
    vec2 res = uTDOutputInfo.res.zw;
    vec2 p = vUV.st * vec2(res.x / res.y, 1.0);

    vec3 color = hueToColor(p.x * 0.45 + p.y * 0.25) * (0.35 + 0.35 * vUV.t);

    // Grid lines.
    vec2 cell = abs(fract(p * 8.0) - 0.5);
    float line = smoothstep(0.47, 0.49, max(cell.x, cell.y));
    color = mix(color, vec3(0.95), line * 0.8);

    // A ring of dots in the cells.
    vec2 id = floor(p * 8.0);
    float dot_ = smoothstep(0.2, 0.17, length(fract(p * 8.0) - 0.5));
    float every = step(mod(id.x + id.y, 3.0), 0.5);
    color = mix(color, hueToColor(id.x * 0.07 + id.y * 0.13), dot_ * every);

    fragColor = TDOutputSwizzle(vec4(color, 1.0));
}
