"""GLSL sources for the GPU renderer (see renderer.py).

Conventions: `v_uv` is the usual GL texture coordinate (origin bottom-left).
Textures uploaded from pygame (the canvas and the light map) are stored top
row first, so they are sampled with "canvas" coordinates (origin top-left);
textures rendered into framebuffers use GL coordinates."""

VERT = """
#version 330
in vec2 in_pos;
out vec2 v_uv;
void main() {
    v_uv = in_pos * 0.5 + 0.5;
    gl_Position = vec4(in_pos, 0.0, 1.0);
}
"""

# Bright pass: keeps what glows (bullets, lasers, magic) for bloom/god rays.
BRIGHT = """
#version 330
uniform sampler2D u_src;
uniform float u_threshold;
in vec2 v_uv;
out vec4 f_color;
void main() {
    vec3 c = texture(u_src, vec2(v_uv.x, 1.0 - v_uv.y)).rgb;
    float l = max(c.r, max(c.g, c.b));
    float knee = 0.25;
    float s = clamp((l - u_threshold + knee) / (2.0 * knee), 0.0, 1.0);
    s = s * s * knee;
    float w = max(s, l - u_threshold) / max(l, 1e-4);
    f_color = vec4(c * w, 1.0);
}
"""

# Separable gaussian, 9 taps folded into 5 linear samples.
BLUR = """
#version 330
uniform sampler2D u_src;
uniform vec2 u_dir;  // one texel along the blur axis
in vec2 v_uv;
out vec4 f_color;
void main() {
    vec3 c = texture(u_src, v_uv).rgb * 0.2270270270;
    c += texture(u_src, v_uv + u_dir * 1.3846153846).rgb * 0.3162162162;
    c += texture(u_src, v_uv - u_dir * 1.3846153846).rgb * 0.3162162162;
    c += texture(u_src, v_uv + u_dir * 3.2307692308).rgb * 0.0702702703;
    c += texture(u_src, v_uv - u_dir * 3.2307692308).rgb * 0.0702702703;
    f_color = vec4(c, 1.0);
}
"""

# Radial light shafts streaming out of a light source (moon, boss, orb).
RAYS = """
#version 330
uniform sampler2D u_src;
uniform vec2 u_pos;     // GL uv of the light
uniform vec3 u_color;
uniform float u_density;
in vec2 v_uv;
out vec4 f_color;
void main() {
    const int N = 28;
    vec2 delta = (v_uv - u_pos) * (u_density / float(N));
    vec2 uv = v_uv;
    float w = 1.0;
    vec3 sum = vec3(0.0);
    for (int i = 0; i < N; i++) {
        uv -= delta;
        vec3 c = texture(u_src, vec2(uv.x, 1.0 - uv.y)).rgb;  // the canvas: dark shapes occlude the light
        c = max(c - 0.28, 0.0) * 1.5;
        sum += c * c * w;
        w *= 0.955;
    }
    float d = length((v_uv - u_pos) * vec2(1.7778, 1.0));
    sum *= u_color * (1.0 / float(N)) * (1.6 - smoothstep(0.0, 1.1, d));
    f_color = vec4(sum, 1.0);
}
"""

COMPOSITE = """
#version 330
uniform sampler2D u_scene;
uniform sampler2D u_light;
uniform sampler2D u_bloom1;
uniform sampler2D u_bloom2;
uniform sampler2D u_rays;
uniform sampler2D u_ui;      // HUD layer (RGBA), drawn crisp on top
uniform float u_has_ui;
uniform vec2 u_tex;          // canvas size in pixels
uniform vec2 u_scale;        // output pixels per canvas pixel
uniform vec2 u_offset;       // screen shake, canvas pixels
uniform float u_time;
uniform vec4 u_waves[8];     // x, y, radius, thickness (canvas px)
uniform float u_wave_str[8];
uniform int u_nwaves;
uniform float u_impact;
uniform vec2 u_impact_pos;
uniform float u_aberr;
uniform float u_haze;
uniform float u_exposure;
uniform float u_contrast;
uniform float u_saturation;
uniform vec3 u_shadows;
uniform vec3 u_highlights;
uniform float u_desat;
uniform float u_bloom;
uniform float u_light_k;
uniform float u_rays_k;
uniform float u_vignette;
uniform float u_danger;
uniform float u_grain;
uniform float u_scan;
uniform float u_crt;
uniform float u_dissolve;    // < 0: off
uniform vec3 u_dissolve_col;
in vec2 v_uv;
out vec4 f_color;

float hash(vec2 p) {
    p = fract(p * vec2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
}

float vnoise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    float a = hash(i), b = hash(i + vec2(1.0, 0.0));
    float c = hash(i + vec2(0.0, 1.0)), d = hash(i + vec2(1.0, 1.0));
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

// Sharp bilinear: crisp pixel art at any (non-integer) scale.
vec2 sharp_uv(vec2 p) {
    vec2 texel_floor = floor(p);
    vec2 s = fract(p);
    vec2 range = 0.5 - 0.5 / max(u_scale, vec2(1.0));
    vec2 cd = s - 0.5;
    vec2 f = (cd - clamp(cd, -range, range)) * max(u_scale, vec2(1.0)) + 0.5;
    return (texel_floor + f) / u_tex;
}

vec3 pix(vec2 p) { return texture(u_scene, sharp_uv(p)).rgb; }

vec2 fb_uv(vec2 p) { return vec2(p.x / u_tex.x, 1.0 - p.y / u_tex.y); }

void main() {
    vec2 cuv = vec2(v_uv.x, 1.0 - v_uv.y);
    float outside = 0.0;
    if (u_crt > 0.0) {
        vec2 c = cuv * 2.0 - 1.0;
        c *= 1.0 + u_crt * 0.045 * vec2(c.y * c.y, c.x * c.x);
        cuv = c * 0.5 + 0.5;
        vec2 e = step(vec2(0.0), cuv) * step(cuv, vec2(1.0));
        outside = 1.0 - e.x * e.y;
    }
    vec2 p = cuv * u_tex - u_offset;

    // Shockwave refraction.
    float ring_glow = 0.0;
    for (int i = 0; i < 8; i++) {
        if (i >= u_nwaves) break;
        vec4 w = u_waves[i];
        vec2 d = p - w.xy;
        float dist = length(d) + 1e-4;
        float x = (dist - w.z) / w.w;
        if (abs(x) < 2.0) {
            float k = x * exp(-x * x * 2.5);
            p -= d / dist * k * 9.0 * u_wave_str[i];
            ring_glow += exp(-x * x * 3.0) * u_wave_str[i];
        }
    }
    // Heat haze (stronger towards the bottom of the screen).
    if (u_haze > 0.0) {
        float k = u_haze * (0.3 + 0.7 * cuv.y);
        p.x += sin(p.y * 0.21 + u_time * 4.1) * 1.3 * k + sin(p.y * 0.07 - u_time * 2.3) * 0.9 * k;
        p.y += cos(p.x * 0.13 + u_time * 3.3) * 0.6 * k;
    }

    // Chromatic aberration: a hint of lens fringing at the edges, more on hits.
    vec2 from_c = (p / u_tex - 0.5);
    vec2 ab = from_c * (0.9 + u_aberr * 2.2) + vec2(u_aberr * 0.6, 0.0);
    ab *= 1.0 + ring_glow * 1.5;
    vec3 col;
    col.r = pix(p + ab).r;
    col.g = pix(p).g;
    col.b = pix(p - ab).b;

    // Impact: radial zoom blur towards the hit point.
    if (u_impact > 0.01) {
        vec3 acc = col;
        for (int i = 1; i <= 6; i++) {
            vec2 q = mix(p, u_impact_pos, float(i) * 0.018 * u_impact);
            acc += pix(q);
        }
        col = mix(col, acc / 7.0, clamp(u_impact, 0.0, 1.0));
        col += u_impact * 0.12;
    }

    vec2 g = fb_uv(p);
    // Dynamic 2D lighting from bullets, spells and characters.
    vec3 light = texture(u_light, p / u_tex).rgb;
    col += col * light * (1.1 * u_light_k) + light * light * (0.25 * u_light_k);
    // Bloom (two radii) and god rays.
    col += (texture(u_bloom1, g).rgb * 0.7 + texture(u_bloom2, g).rgb * 1.0) * u_bloom;
    col += texture(u_rays, g).rgb * u_rays_k;
    col += ring_glow * 0.05;

    // Colour grade.
    col *= u_exposure;
    float l = dot(col, vec3(0.2126, 0.7152, 0.0722));
    col = mix(vec3(l), col, u_saturation * (1.0 - u_desat));
    col = (col - 0.5) * u_contrast + 0.5;
    float lc = clamp(l, 0.0, 1.0);
    col += u_shadows * (1.0 - lc) * (1.0 - lc) + u_highlights * lc * lc;
    // Soft shoulder so bloom saturates gracefully instead of clipping.
    col = max(col, 0.0);
    col = mix(col, 1.0 - exp(-col * 1.25) * 0.96, smoothstep(0.7, 1.6, col));

    // Vignette + low-health pulse.
    vec2 v = (cuv - 0.5) * vec2(1.0, 0.78);
    float vig = smoothstep(0.78, 0.18, length(v));
    col *= mix(1.0, vig, u_vignette);
    if (u_danger > 0.0) {
        float edge = smoothstep(0.25, 0.75, length(v * 1.3));
        float beat = 0.55 + 0.45 * pow(abs(sin(u_time * 3.4)), 6.0);
        col = mix(col, col * 0.6 + vec3(0.45, 0.0, 0.04), edge * u_danger * beat);
    }

    // Scanlines aligned to canvas rows, and film grain.
    if (u_scan > 0.0) {
        float row = fract(cuv.y * u_tex.y);
        col *= 1.0 - u_scan * 0.22 * smoothstep(0.35, 0.95, abs(row - 0.5) * 2.0);
    }
    col += (hash(gl_FragCoord.xy + fract(u_time * 7.0) * 311.0) - 0.5) * 0.045 * u_grain;

    // Scene transition: a burning, noisy dissolve.
    if (u_dissolve > 0.0) {
        float n = vnoise(cuv * vec2(12.0, 7.0)) * 0.2 + vnoise(cuv * vec2(40.0, 22.0)) * 0.1;
        n += cuv.x * 0.75 + (1.0 - cuv.y) * 0.25;  // a diagonal sweep, frayed by noise
        float edge = (n - (u_dissolve * 1.5 - 0.15)) / 0.03;
        float burnt = 1.0 - smoothstep(-1.0, 0.0, edge);
        float rim = exp(-edge * edge * 0.9) * step(0.001, u_dissolve) * step(u_dissolve, 0.999);
        float ember = smoothstep(0.0, 3.0, edge) * (1.0 - smoothstep(3.0, 6.0, edge));  // scorched band ahead of the flame
        col *= 1.0 - ember * 0.45;
        col = mix(col, vec3(0.024, 0.008, 0.047), burnt);
        col += mix(vec3(1.0, 0.85, 0.6), u_dissolve_col, clamp(edge * 0.5 + 0.5, 0.0, 1.0)) * rim * 1.1;
    }

    if (u_has_ui > 0.0) {
        vec4 ui = texture(u_ui, sharp_uv(cuv * u_tex - u_offset * 0.5));
        col = mix(col, ui.rgb, ui.a);
    }

    col = mix(col, vec3(0.0), outside);
    f_color = vec4(clamp(col, 0.0, 1.0), 1.0);
}
"""
