// Works out how far every point is from the dolphin's outline and stores it, negative
// inside. This only runs once, so crystal_figure can look the answer up instead.

// The dolphin's outline, traced from an image the owner supplied, as a list of corner
// points. Check that image's license before selling QRTZ or using this publicly.
const int DOLPHIN_POINTS = 96;
const vec2 DOLPHIN[DOLPHIN_POINTS] = vec2[DOLPHIN_POINTS](
    vec2(-0.260, 0.386), vec2(-0.301, 0.379), vec2(-0.311, 0.370), vec2(-0.305, 0.364),
    vec2(-0.274, 0.353), vec2(-0.249, 0.336), vec2(-0.236, 0.315), vec2(-0.232, 0.295),
    vec2(-0.232, 0.277), vec2(-0.247, 0.244), vec2(-0.297, 0.185), vec2(-0.321, 0.149),
    vec2(-0.354, 0.081), vec2(-0.373, 0.017), vec2(-0.382, -0.047), vec2(-0.382, -0.131),
    vec2(-0.368, -0.226), vec2(-0.372, -0.233), vec2(-0.425, -0.281), vec2(-0.453, -0.321),
    vec2(-0.464, -0.362), vec2(-0.460, -0.386), vec2(-0.419, -0.372), vec2(-0.343, -0.361),
    vec2(-0.312, -0.353), vec2(-0.281, -0.331), vec2(-0.247, -0.339), vec2(-0.159, -0.335),
    vec2(-0.161, -0.318), vec2(-0.169, -0.303), vec2(-0.196, -0.272), vec2(-0.249, -0.242),
    vec2(-0.288, -0.227), vec2(-0.293, -0.229), vec2(-0.304, -0.253), vec2(-0.306, -0.236),
    vec2(-0.301, -0.195), vec2(-0.283, -0.123), vec2(-0.267, -0.082), vec2(-0.240, -0.032),
    vec2(-0.223, -0.007), vec2(-0.186, 0.030), vec2(-0.143, 0.060), vec2(-0.110, 0.076),
    vec2(-0.053, 0.092), vec2(-0.017, 0.098), vec2(-0.009, 0.096), vec2(-0.020, 0.086),
    vec2(-0.043, 0.049), vec2(-0.084, 0.008), vec2(-0.083, 0.003), vec2(-0.071, 0.001),
    vec2(-0.020, 0.010), vec2(0.030, 0.032), vec2(0.040, 0.041), vec2(0.053, 0.071),
    vec2(0.054, 0.059), vec2(0.045, 0.023), vec2(0.037, 0.004), vec2(0.004, -0.044),
    vec2(0.004, -0.050), vec2(0.010, -0.052), vec2(0.027, -0.049), vec2(0.057, -0.037),
    vec2(0.108, -0.004), vec2(0.143, 0.033), vec2(0.157, 0.057), vec2(0.166, 0.079),
    vec2(0.170, 0.081), vec2(0.185, 0.080), vec2(0.252, 0.061), vec2(0.357, 0.021),
    vec2(0.402, 0.009), vec2(0.439, 0.005), vec2(0.456, 0.008), vec2(0.464, 0.014),
    vec2(0.464, 0.024), vec2(0.457, 0.035), vec2(0.404, 0.081), vec2(0.393, 0.096),
    vec2(0.396, 0.141), vec2(0.391, 0.170), vec2(0.382, 0.199), vec2(0.368, 0.225),
    vec2(0.331, 0.265), vec2(0.270, 0.303), vec2(0.216, 0.325), vec2(0.180, 0.334),
    vec2(0.083, 0.348), vec2(-0.004, 0.347), vec2(-0.099, 0.329), vec2(-0.100, 0.335),
    vec2(-0.086, 0.342), vec2(-0.084, 0.346), vec2(-0.127, 0.367), vec2(-0.199, 0.384));

// Distance to the outline, negative inside it.
float dolphinDistance(vec2 p) {
    float nearest = dot(p - DOLPHIN[0], p - DOLPHIN[0]);
    float side = 1.0;
    for (int i = 0, j = DOLPHIN_POINTS - 1; i < DOLPHIN_POINTS; j = i, i++) {
        vec2 edge = DOLPHIN[j] - DOLPHIN[i];
        vec2 toPoint = p - DOLPHIN[i];
        vec2 closest = toPoint - edge * clamp(dot(toPoint, edge) / dot(edge, edge), 0.0, 1.0);
        nearest = min(nearest, dot(closest, closest));
        bool below = p.y >= DOLPHIN[i].y;
        bool under = p.y < DOLPHIN[j].y;
        bool toRight = edge.x * toPoint.y > edge.y * toPoint.x;
        if ((below && under && toRight) || (!below && !under && !toRight)) side = -side;
    }
    return side * sqrt(nearest);
}

layout(location = 0) out vec4 fragColor;

void main() {
    vec2 p = (vUV.st - 0.5) * 1.6;  // DOLPHIN_FIELD_SPAN in crystal_figure
    fragColor = vec4(vec3(dolphinDistance(p)), 1.0);
}
