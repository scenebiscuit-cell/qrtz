// The main crystal. Everything that makes it a gem is in crystal_gem.

#include <crystal_gem>

void main() {
    buildGem(uBreathe);

    vec2 res = uTDOutputInfo.res.zw;
    float aspect = res.x / res.y;
    vec2 uv = vUV.st;

    // The camera's ray. Moving the gem across the image is the same as moving
    // where the ray points.
    vec2 p = (uv - 0.5) * vec2(aspect, 1.0) - vec2(uOffsetX, uOffsetY);
    vec3 cameraPos = vec3(0.0, 0.0, -uCameraDistance);
    vec3 cameraRay = normalize(vec3(p, uLens));

    // The gem, moved into its own turned and tilted space.
    mat3 toGem = rotateY(-uAngle) * rotateX(uTilt) * rotateZ(uRoll);
    float gemDist;
    vec4 result = shadeGem(uv, toGem * cameraPos, toGem * cameraRay, transpose(toGem), aspect, gemDist);

    fragColor = TDOutputSwizzle(result);
    fragDistance = vec4(min(gemDist, 1e4));
}

