/*
 * Vanilla-JS port of the React Bits "SoftAurora" component.
 * Same Perlin-noise aurora-glow shader, no React/ogl dependency —
 * plain WebGL1 (gl_FragColor) so it runs with a single <script> include.
 */
(function () {
  function hexToVec3(hex) {
    const h = hex.replace('#', '');
    return [
      parseInt(h.slice(0, 2), 16) / 255,
      parseInt(h.slice(2, 4), 16) / 255,
      parseInt(h.slice(4, 6), 16) / 255,
    ];
  }

  const VERTEX_SHADER = `
attribute vec2 position;
void main() {
  gl_Position = vec4(position, 0.0, 1.0);
}
`;

  const FRAGMENT_SHADER = `
precision highp float;

uniform float uTime;
uniform vec3 uResolution;
uniform float uSpeed;
uniform float uScale;
uniform float uBrightness;
uniform vec3 uColor1;
uniform vec3 uColor2;
uniform float uNoiseFreq;
uniform float uNoiseAmp;
uniform float uBandHeight;
uniform float uBandSpread;
uniform float uOctaveDecay;
uniform float uLayerOffset;
uniform float uColorSpeed;
uniform vec2 uMouse;
uniform float uMouseInfluence;
uniform bool uEnableMouse;

#define TAU 6.28318

vec3 gradientHash(vec3 p) {
  p = vec3(
    dot(p, vec3(127.1, 311.7, 234.6)),
    dot(p, vec3(269.5, 183.3, 198.3)),
    dot(p, vec3(169.5, 283.3, 156.9))
  );
  vec3 h = fract(sin(p) * 43758.5453123);
  float phi = acos(2.0 * h.x - 1.0);
  float theta = TAU * h.y;
  return vec3(cos(theta) * sin(phi), sin(theta) * cos(phi), cos(phi));
}

float quinticSmooth(float t) {
  float t2 = t * t;
  float t3 = t * t2;
  return 6.0 * t3 * t2 - 15.0 * t2 * t2 + 10.0 * t3;
}

vec3 cosineGradient(float t, vec3 a, vec3 b, vec3 c, vec3 d) {
  return a + b * cos(TAU * (c * t + d));
}

float perlin3D(float amplitude, float frequency, float px, float py, float pz) {
  float x = px * frequency;
  float y = py * frequency;

  float fx = floor(x); float fy = floor(y); float fz = floor(pz);
  float cx = ceil(x);  float cy = ceil(y);  float cz = ceil(pz);

  vec3 g000 = gradientHash(vec3(fx, fy, fz));
  vec3 g100 = gradientHash(vec3(cx, fy, fz));
  vec3 g010 = gradientHash(vec3(fx, cy, fz));
  vec3 g110 = gradientHash(vec3(cx, cy, fz));
  vec3 g001 = gradientHash(vec3(fx, fy, cz));
  vec3 g101 = gradientHash(vec3(cx, fy, cz));
  vec3 g011 = gradientHash(vec3(fx, cy, cz));
  vec3 g111 = gradientHash(vec3(cx, cy, cz));

  float d000 = dot(g000, vec3(x - fx, y - fy, pz - fz));
  float d100 = dot(g100, vec3(x - cx, y - fy, pz - fz));
  float d010 = dot(g010, vec3(x - fx, y - cy, pz - fz));
  float d110 = dot(g110, vec3(x - cx, y - cy, pz - fz));
  float d001 = dot(g001, vec3(x - fx, y - fy, pz - cz));
  float d101 = dot(g101, vec3(x - cx, y - fy, pz - cz));
  float d011 = dot(g011, vec3(x - fx, y - cy, pz - cz));
  float d111 = dot(g111, vec3(x - cx, y - cy, pz - cz));

  float sx = quinticSmooth(x - fx);
  float sy = quinticSmooth(y - fy);
  float sz = quinticSmooth(pz - fz);

  float lx00 = mix(d000, d100, sx);
  float lx10 = mix(d010, d110, sx);
  float lx01 = mix(d001, d101, sx);
  float lx11 = mix(d011, d111, sx);

  float ly0 = mix(lx00, lx10, sy);
  float ly1 = mix(lx01, lx11, sy);

  return amplitude * mix(ly0, ly1, sz);
}

float auroraGlow(float t, vec2 shift) {
  vec2 uv = gl_FragCoord.xy / uResolution.y;
  uv += shift;

  float noiseVal = 0.0;
  float freq = uNoiseFreq;
  float amp = uNoiseAmp;
  vec2 samplePos = uv * uScale;

  for (float i = 0.0; i < 3.0; i += 1.0) {
    noiseVal += perlin3D(amp, freq, samplePos.x, samplePos.y, t);
    amp *= uOctaveDecay;
    freq *= 2.0;
  }

  float yBand = uv.y * 10.0 - uBandHeight * 10.0;
  return 0.3 * max(exp(uBandSpread * (1.0 - 1.1 * abs(noiseVal + yBand))), 0.0);
}

void main() {
  vec2 uv = gl_FragCoord.xy / uResolution.xy;
  float t = uSpeed * 0.4 * uTime;

  vec2 shift = vec2(0.0);
  if (uEnableMouse) {
    shift = (uMouse - 0.5) * uMouseInfluence;
  }

  vec3 col = vec3(0.0);
  col += 0.99 * auroraGlow(t, shift) * cosineGradient(uv.x + uTime * uSpeed * 0.2 * uColorSpeed, vec3(0.5), vec3(0.5), vec3(1.0), vec3(0.3, 0.20, 0.20)) * uColor1;
  col += 0.99 * auroraGlow(t + uLayerOffset, shift) * cosineGradient(uv.x + uTime * uSpeed * 0.1 * uColorSpeed, vec3(0.5), vec3(0.5), vec3(2.0, 1.0, 0.0), vec3(0.5, 0.20, 0.25)) * uColor2;

  col *= uBrightness;
  float alpha = clamp(length(col), 0.0, 1.0);
  gl_FragColor = vec4(col, alpha);
}
`;

  function compileShader(gl, type, source) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      console.warn('[aurora-bg] shader compile error:', gl.getShaderInfoLog(shader));
      gl.deleteShader(shader);
      return null;
    }
    return shader;
  }

  function initAuroraBackground(containerEl, options) {
    options = options || {};
    if (!containerEl) return function () {};

    const canvas = document.createElement('canvas');
    canvas.style.width = '100%';
    canvas.style.height = '100%';
    canvas.style.display = 'block';
    containerEl.appendChild(canvas);

    const gl = canvas.getContext('webgl', { alpha: true, premultipliedAlpha: false }) ||
      canvas.getContext('experimental-webgl', { alpha: true, premultipliedAlpha: false });

    if (!gl) {
      console.warn('[aurora-bg] WebGL not available, skipping aurora background.');
      return function () {};
    }

    gl.clearColor(0, 0, 0, 0);

    const vs = compileShader(gl, gl.VERTEX_SHADER, VERTEX_SHADER);
    const fs = compileShader(gl, gl.FRAGMENT_SHADER, FRAGMENT_SHADER);
    if (!vs || !fs) return function () {};

    const program = gl.createProgram();
    gl.attachShader(program, vs);
    gl.attachShader(program, fs);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      console.warn('[aurora-bg] program link error:', gl.getProgramInfoLog(program));
      return function () {};
    }
    gl.useProgram(program);

    // Fullscreen triangle (covers the viewport without a quad's extra vertices).
    const positionBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([
      -1, -1,
      3, -1,
      -1, 3,
    ]), gl.STATIC_DRAW);
    const positionLoc = gl.getAttribLocation(program, 'position');
    gl.enableVertexAttribArray(positionLoc);
    gl.vertexAttribPointer(positionLoc, 2, gl.FLOAT, false, 0, 0);

    const uniforms = {
      uTime: gl.getUniformLocation(program, 'uTime'),
      uResolution: gl.getUniformLocation(program, 'uResolution'),
      uSpeed: gl.getUniformLocation(program, 'uSpeed'),
      uScale: gl.getUniformLocation(program, 'uScale'),
      uBrightness: gl.getUniformLocation(program, 'uBrightness'),
      uColor1: gl.getUniformLocation(program, 'uColor1'),
      uColor2: gl.getUniformLocation(program, 'uColor2'),
      uNoiseFreq: gl.getUniformLocation(program, 'uNoiseFreq'),
      uNoiseAmp: gl.getUniformLocation(program, 'uNoiseAmp'),
      uBandHeight: gl.getUniformLocation(program, 'uBandHeight'),
      uBandSpread: gl.getUniformLocation(program, 'uBandSpread'),
      uOctaveDecay: gl.getUniformLocation(program, 'uOctaveDecay'),
      uLayerOffset: gl.getUniformLocation(program, 'uLayerOffset'),
      uColorSpeed: gl.getUniformLocation(program, 'uColorSpeed'),
      uMouse: gl.getUniformLocation(program, 'uMouse'),
      uMouseInfluence: gl.getUniformLocation(program, 'uMouseInfluence'),
      uEnableMouse: gl.getUniformLocation(program, 'uEnableMouse'),
    };

    const cfg = {
      speed: options.speed !== undefined ? options.speed : 0.35,
      scale: options.scale !== undefined ? options.scale : 1.5,
      brightness: options.brightness !== undefined ? options.brightness : 0.55,
      color1: hexToVec3(options.color1 || '#E8A04A'),
      color2: hexToVec3(options.color2 || '#0CC8A8'),
      noiseFrequency: options.noiseFrequency !== undefined ? options.noiseFrequency : 2.5,
      noiseAmplitude: options.noiseAmplitude !== undefined ? options.noiseAmplitude : 1.0,
      bandHeight: options.bandHeight !== undefined ? options.bandHeight : 0.5,
      bandSpread: options.bandSpread !== undefined ? options.bandSpread : 1.0,
      octaveDecay: options.octaveDecay !== undefined ? options.octaveDecay : 0.1,
      layerOffset: options.layerOffset !== undefined ? options.layerOffset : 0,
      colorSpeed: options.colorSpeed !== undefined ? options.colorSpeed : 1.0,
      enableMouseInteraction: options.enableMouseInteraction || false,
      mouseInfluence: options.mouseInfluence !== undefined ? options.mouseInfluence : 0.25,
    };

    gl.uniform1f(uniforms.uSpeed, cfg.speed);
    gl.uniform1f(uniforms.uScale, cfg.scale);
    gl.uniform1f(uniforms.uBrightness, cfg.brightness);
    gl.uniform3fv(uniforms.uColor1, cfg.color1);
    gl.uniform3fv(uniforms.uColor2, cfg.color2);
    gl.uniform1f(uniforms.uNoiseFreq, cfg.noiseFrequency);
    gl.uniform1f(uniforms.uNoiseAmp, cfg.noiseAmplitude);
    gl.uniform1f(uniforms.uBandHeight, cfg.bandHeight);
    gl.uniform1f(uniforms.uBandSpread, cfg.bandSpread);
    gl.uniform1f(uniforms.uOctaveDecay, cfg.octaveDecay);
    gl.uniform1f(uniforms.uLayerOffset, cfg.layerOffset);
    gl.uniform1f(uniforms.uColorSpeed, cfg.colorSpeed);
    gl.uniform1i(uniforms.uEnableMouse, cfg.enableMouseInteraction ? 1 : 0);
    gl.uniform1f(uniforms.uMouseInfluence, cfg.mouseInfluence);

    let currentMouse = [0.5, 0.5];
    let targetMouse = [0.5, 0.5];

    function handleMouseMove(e) {
      const rect = canvas.getBoundingClientRect();
      targetMouse = [
        (e.clientX - rect.left) / rect.width,
        1.0 - (e.clientY - rect.top) / rect.height,
      ];
    }
    function handleMouseLeave() {
      targetMouse = [0.5, 0.5];
    }

    function resize() {
      const w = containerEl.clientWidth || 1;
      const h = containerEl.clientHeight || 1;
      canvas.width = w;
      canvas.height = h;
      gl.viewport(0, 0, w, h);
      gl.uniform3f(uniforms.uResolution, w, h, w / h);
    }
    window.addEventListener('resize', resize);
    resize();

    if (cfg.enableMouseInteraction) {
      canvas.addEventListener('mousemove', handleMouseMove);
      canvas.addEventListener('mouseleave', handleMouseLeave);
    }

    let animationFrameId;
    function update(time) {
      animationFrameId = requestAnimationFrame(update);
      gl.uniform1f(uniforms.uTime, time * 0.001);

      if (cfg.enableMouseInteraction) {
        currentMouse[0] += 0.05 * (targetMouse[0] - currentMouse[0]);
        currentMouse[1] += 0.05 * (targetMouse[1] - currentMouse[1]);
        gl.uniform2f(uniforms.uMouse, currentMouse[0], currentMouse[1]);
      } else {
        gl.uniform2f(uniforms.uMouse, 0.5, 0.5);
      }

      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    }
    animationFrameId = requestAnimationFrame(update);

    return function teardown() {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', resize);
      if (cfg.enableMouseInteraction) {
        canvas.removeEventListener('mousemove', handleMouseMove);
        canvas.removeEventListener('mouseleave', handleMouseLeave);
      }
      if (canvas.parentElement) containerEl.removeChild(canvas);
      const ext = gl.getExtension('WEBGL_lose_context');
      if (ext) ext.loseContext();
    };
  }

  window.initAuroraBackground = initAuroraBackground;
})();
