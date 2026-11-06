// The small crystal when it's a faceted gem. A smooth sphere cuts the same facets:
// while it's a blob the sphere is small and the facets sit outside it, and they
// slide in as it turns into a crystal.

#include <crystal_gem>

void main() {
    buildGem(uSatBreathe);
    planeScale = mix(1.0, 1.6, uSatBlob);
    sphereRadius = mix(1.3, 0.62, uSatBlob) * uSize * uScale;

    vec2 uv;
    vec3 from, rd;
    mat3 toView;
    float aspect, satDist;
    smallCrystalRay(uv, from, rd, toView, aspect);
    vec4 result = shadeGem(uv, from, rd, toView, aspect, satDist);

    fragColor = TDOutputSwizzle(result);
    fragDistance = vec4(min(satDist * uSatScale, 1e4));
}
