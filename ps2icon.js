// This file is part of PSMemoryManager.
// SPDX-License-Identifier: GPL-3.0-or-later
//
// PS2 save icons (.ico / .icn): a small 3D model with a 128x128 texture and
// optional shape animation, lit and framed as described by the save's icon.sys.
// Format as read by mymc++ (ps2icon.py); drawn here with WebGL 1.

const MAGIC = 0x010000;
const TEX = 128;

export class IconError extends Error {}

// Raw icon file -> geometry + texture. Throws IconError when the model itself is unusable.
export function parseIcon(buf) {
  const u8 = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
  const dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength);
  const len = u8.length;
  if (len < 20) throw new IconError("too small");
  if (dv.getUint32(0, true) !== MAGIC) throw new IconError("bad magic");
  const shapes = dv.getUint32(4, true);
  const texType = dv.getUint32(8, true);
  const count = dv.getUint32(16, true);
  if (shapes < 1 || shapes > 64 || count < 3 || count > 200000) throw new IconError("bad header");
  let off = 20;
  const stride = 8 * shapes + 16;
  if (len < off + count * stride) throw new IconError("truncated");

  const pos = new Int16Array(shapes * count * 3); // [shape][vertex][xyz]
  const nrm = new Int16Array(count * 3);
  const uv = new Int16Array(count * 2);
  const col = new Uint8Array(count * 4);
  let anyAlpha = false;
  for (let i = 0; i < count; i++) {
    for (let s = 0; s < shapes; s++) {
      const o = (s * count + i) * 3;
      pos[o] = dv.getInt16(off, true);
      pos[o + 1] = dv.getInt16(off + 2, true);
      pos[o + 2] = dv.getInt16(off + 4, true);
      off += 8;
    }
    nrm[i * 3] = dv.getInt16(off, true);
    nrm[i * 3 + 1] = dv.getInt16(off + 2, true);
    nrm[i * 3 + 2] = dv.getInt16(off + 4, true);
    uv[i * 2] = dv.getInt16(off + 8, true);
    uv[i * 2 + 1] = dv.getInt16(off + 10, true);
    col.set(u8.subarray(off + 12, off + 16), i * 4);
    if (u8[off + 15]) anyAlpha = true;
    off += 16;
  }
  // some games (e.g. THPS3) leave every alpha at 0: show those as opaque
  if (!anyAlpha) for (let i = 3; i < col.length; i += 4) col[i] = 128;

  // animation: a list of (shape, keys); damaged or missing data -> static icon
  let frameLength = 0, frames = [];
  try {
    if (len >= off + 20 && dv.getUint32(off, true) === 1) {
      frameLength = dv.getUint32(off + 4, true);
      const frameCount = dv.getUint32(off + 16, true);
      off += 20;
      if (frameCount > 1024) throw new IconError("frames");
      for (let f = 0; f < frameCount; f++) {
        if (len < off + 16) throw new IconError("frames");
        const shape = dv.getUint32(off, true);
        const keyCount = Math.max(0, dv.getUint32(off + 4, true) - 1);
        off += 16;
        if (keyCount > 4096 || len < off + keyCount * 8) throw new IconError("keys");
        const keys = [];
        for (let k = 0; k < keyCount; k++, off += 8) keys.push([dv.getFloat32(off, true), dv.getFloat32(off + 4, true)]);
        if (shape === 0) keys.push([0, 1]);
        if (shape < shapes) frames.push({ shape, keys });
      }
    }
  } catch {
    frameLength = 0;
    frames = [];
  }

  return { shapes, count, pos, nrm, uv, col, frameLength, frames, texture: readTexture(u8, dv, off, texType) };
}

// 128x128 RGB5551 texture (raw or RLE) -> RGBA8; null = untextured (vertex colours only).
// A damaged RLE stream keeps what was decoded instead of dropping the icon.
function readTexture(u8, dv, off, texType) {
  const len = u8.length;
  if (!(texType & 4) || off >= len) return null;
  const raw = new Uint8Array(TEX * TEX * 2);
  if (texType & 8) {
    if (len < off + 4) return null;
    const size = dv.getUint32(off, true);
    let p = off + 4, t = 0;
    const end = Math.min(len, p + size);
    while (p + 2 <= end && t < raw.length) {
      const code = dv.getUint16(p, true);
      p += 2;
      if (code & 0x8000) {
        const n = Math.min((0x10000 - code) * 2, end - p, raw.length - t);
        raw.set(u8.subarray(p, p + n), t);
        t += n;
        p += (0x10000 - code) * 2;
      } else if (code > 0 && p + 2 <= end) {
        const a = u8[p], b = u8[p + 1];
        p += 2;
        for (let r = 0; r < code && t + 1 < raw.length; r++) { raw[t++] = a; raw[t++] = b; }
      }
    }
  } else {
    raw.set(u8.subarray(off, off + raw.length));
  }
  const rgba = new Uint8Array(TEX * TEX * 4);
  for (let i = 0; i < TEX * TEX; i++) {
    const v = raw[i * 2] | (raw[i * 2 + 1] << 8);
    rgba[i * 4] = ((v & 31) * 255) / 31;
    rgba[i * 4 + 1] = (((v >> 5) & 31) * 255) / 31;
    rgba[i * 4 + 2] = (((v >> 10) & 31) * 255) / 31;
    rgba[i * 4 + 3] = 255;
  }
  return rgba;
}

// Blend weights of each shape at time t (in animation frames).
function shapeWeights(icon, t) {
  const L = icon.frameLength;
  const w = new Map();
  for (const fr of icon.frames) {
    let last = null, lastT = 0, next = null, nextT = 0;
    for (const [kt, kv] of fr.keys) {
      const a = kt <= t ? kt : kt - L;
      if (last === null || a > lastT) { last = kv; lastT = a; }
      const b = kt >= t ? kt : kt + L;
      if (next === null || b < nextT) { next = kv; nextT = b; }
    }
    if (last === null) continue;
    const p = nextT > lastT ? Math.min(1, Math.max(0, (t - lastT) / (nextT - lastT))) : 0;
    w.set(fr.shape, (1 - p) * last + p * next);
  }
  let sum = 0;
  for (const v of w.values()) sum += v;
  if (!(sum > 0)) return new Map([[0, 1]]);
  for (const [k, v] of w) w.set(k, v / sum);
  return w;
}

export const isAnimated = (icon) => icon.shapes > 1 && icon.frameLength > 0 && icon.frames.length > 0;

// ---------------------------------------------------------------------------
// WebGL

const VS = `
attribute vec3 a_pos; attribute vec3 a_nrm; attribute vec2 a_uv; attribute vec4 a_col;
uniform mat4 u_mvp; uniform mat3 u_rot;
varying vec4 v_col; varying vec2 v_uv; varying vec3 v_nrm;
void main() {
  vec3 p = u_rot * (a_pos / 4096.0 * vec3(1.0, -1.0, -1.0));
  v_nrm = u_rot * (a_nrm / 4096.0 * vec3(1.0, -1.0, -1.0));
  v_col = min(a_col / 128.0, 1.0);
  v_uv = a_uv / 4096.0;
  gl_Position = u_mvp * vec4(p, 1.0);
}`;
const FS = `
precision mediump float;
uniform sampler2D u_tex; uniform vec3 u_ldir[3]; uniform vec3 u_lcol[3]; uniform vec3 u_amb;
varying vec4 v_col; varying vec2 v_uv; varying vec3 v_nrm;
void main() {
  vec3 n = normalize(v_nrm);
  vec3 base = v_col.rgb * texture2D(u_tex, v_uv).rgb;
  vec3 c = base * u_amb;
  for (int i = 0; i < 3; i++) c += max(dot(u_ldir[i], n), 0.0) * u_lcol[i] * base;
  gl_FragColor = vec4(min(c, 1.0), v_col.a);
}`;
const BG_VS = `attribute vec2 a_xy; attribute vec4 a_c; varying vec4 v_c;
void main() { v_c = a_c; gl_Position = vec4(a_xy, 0.0, 1.0); }`;
const BG_FS = `precision mediump float; varying vec4 v_c; void main() { gl_FragColor = v_c; }`;

function program(gl, vs, fs, attrs) {
  const p = gl.createProgram();
  for (const [src, type] of [[vs, gl.VERTEX_SHADER], [fs, gl.FRAGMENT_SHADER]]) {
    const s = gl.createShader(type);
    gl.shaderSource(s, src);
    gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s) || "shader");
    gl.attachShader(p, s);
  }
  attrs.forEach((a, i) => gl.bindAttribLocation(p, i, a));
  gl.linkProgram(p);
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p) || "link");
  return p;
}

function perspective(fovDeg, aspect, near, far) {
  const f = 1 / Math.tan((fovDeg * Math.PI) / 360), d = near - far;
  return [f / aspect, 0, 0, 0, 0, f, 0, 0, 0, 0, (far + near) / d, -1, 0, 0, (2 * far * near) / d, 0];
}

// column-major 4x4 product
function mul(a, b) {
  const o = new Array(16).fill(0);
  for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) for (let k = 0; k < 4; k++) o[c * 4 + r] += a[k * 4 + r] * b[c * 4 + k];
  return o;
}

// icon.sys lighting/background, or a neutral default when it is missing
const DEFAULT_LOOK = {
  bg: [[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]],
  lightDirs: [[0.5, 0.5, 0.5], [0, -0.4, -0.1], [-0.5, -0.5, 0.5]],
  lightColors: [[0.4, 0.4, 0.4], [0.3, 0.3, 0.3], [0.2, 0.2, 0.2]],
  ambient: [0.5, 0.5, 0.5],
};

export class IconRenderer {
  constructor(canvas) {
    this.canvas = canvas;
    // software WebGL (no GPU, blocked driver) takes up to a second per icon: refuse it,
    // so the page keeps the generic symbol instead of freezing
    const opts = { alpha: true, premultipliedAlpha: false, antialias: true, preserveDrawingBuffer: true,
      failIfMajorPerformanceCaveat: true };
    const gl = canvas.getContext("webgl", opts) || canvas.getContext("experimental-webgl", opts);
    if (!gl) throw new Error("WebGL unavailable");
    const info = gl.getExtension("WEBGL_debug_renderer_info");
    const name = String(gl.getParameter(info ? info.UNMASKED_RENDERER_WEBGL : gl.RENDERER));
    if (/swiftshader|llvmpipe|softpipe|software|basic render/i.test(name)) throw new Error("software WebGL");
    this.gl = gl;
    this.lost = false;
    canvas.addEventListener("webglcontextlost", (e) => { e.preventDefault(); this.lost = true; });
    this.prog = program(gl, VS, FS, ["a_pos", "a_nrm", "a_uv", "a_col"]);
    this.bgProg = program(gl, BG_VS, BG_FS, ["a_xy", "a_c"]);
    this.u = {};
    for (const n of ["u_mvp", "u_rot", "u_tex", "u_amb"]) this.u[n] = gl.getUniformLocation(this.prog, n);
    this.u.u_ldir = gl.getUniformLocation(this.prog, "u_ldir[0]");
    this.u.u_lcol = gl.getUniformLocation(this.prog, "u_lcol[0]");
    this.buf = { pos: gl.createBuffer(), nrm: gl.createBuffer(), uv: gl.createBuffer(), col: gl.createBuffer(),
      bgXY: gl.createBuffer(), bgC: gl.createBuffer() };
    gl.bindBuffer(gl.ARRAY_BUFFER, this.buf.bgXY);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, 1, -1, -1, 1, 1, 1, -1]), gl.STATIC_DRAW);
    this.tex = gl.createTexture();
    this.white = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, this.white);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array([255, 255, 255, 255]));
    this.icon = null;
  }

  setIcon(icon, look) {
    const gl = this.gl;
    this.icon = icon;
    this.look = look || DEFAULT_LOOK;
    this.work = new Float32Array(icon.count * 3);
    this.drawCount = icon.count - (icon.count % 3);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.buf.nrm);
    gl.bufferData(gl.ARRAY_BUFFER, icon.nrm, gl.STATIC_DRAW);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.buf.uv);
    gl.bufferData(gl.ARRAY_BUFFER, icon.uv, gl.STATIC_DRAW);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.buf.col);
    gl.bufferData(gl.ARRAY_BUFFER, icon.col, gl.STATIC_DRAW);
    if (icon.texture) {
      gl.bindTexture(gl.TEXTURE_2D, this.tex);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, TEX, TEX, 0, gl.RGBA, gl.UNSIGNED_BYTE, icon.texture);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.generateMipmap(gl.TEXTURE_2D);
    }
    this.uploaded = false;
    this.uploadPositions(0);
    this.fit();
  }

  // bounding sphere of the first shape, so every icon fills the frame the same way
  fit() {
    const { pos, count } = this.icon;
    const min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
    for (let i = 0; i < count; i++) {
      const v = [pos[i * 3] / 4096, -pos[i * 3 + 1] / 4096, -pos[i * 3 + 2] / 4096];
      for (let k = 0; k < 3; k++) { if (v[k] < min[k]) min[k] = v[k]; if (v[k] > max[k]) max[k] = v[k]; }
    }
    this.center = min.map((m, k) => (m + max[k]) / 2);
    let r = 0;
    for (let i = 0; i < count; i++) {
      const dx = pos[i * 3] / 4096 - this.center[0], dy = -pos[i * 3 + 1] / 4096 - this.center[1], dz = -pos[i * 3 + 2] / 4096 - this.center[2];
      r = Math.max(r, Math.hypot(dx, dy, dz));
    }
    this.radius = r || 1;
  }

  // vertex positions at animation time t (frames); static icons are uploaded once
  uploadPositions(t) {
    const icon = this.icon, gl = this.gl, out = this.work, n = icon.count * 3;
    if (!isAnimated(icon)) {
      if (this.uploaded) return;
      for (let i = 0; i < n; i++) out[i] = icon.pos[i];
      this.uploaded = true;
    } else {
      out.fill(0);
      // t can be negative (a clock that starts over, e.g. a test's fake clock): wrap it into [0, length)
      const L = icon.frameLength;
      for (const [shape, w] of shapeWeights(icon, ((t % L) + L) % L)) {
        if (shape >= icon.shapes || !w) continue;
        const base = shape * n;
        for (let i = 0; i < n; i++) out[i] += w * icon.pos[base + i];
      }
    }
    gl.bindBuffer(gl.ARRAY_BUFFER, this.buf.pos);
    gl.bufferData(gl.ARRAY_BUFFER, out, gl.DYNAMIC_DRAW);
  }

  // time: seconds since the animation started; yaw/pitch: radians; background: draw icon.sys gradient
  draw({ time = 0, yaw = 0, pitch = 0, background = false } = {}) {
    const gl = this.gl;
    if (this.lost || !this.icon) return false;
    const w = this.canvas.width, h = this.canvas.height;
    gl.viewport(0, 0, w, h);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    for (let i = 0; i < 4; i++) gl.disableVertexAttribArray(i);

    if (background) {
      const c = (x) => Math.min(255, Math.round((x / 128) * 255));
      const b = this.look.bg; // TL, TR, BL, BR
      const cols = [b[0], b[2], b[1], b[3]].flatMap((x) => [c(x[0]), c(x[1]), c(x[2]), 255]);
      gl.useProgram(this.bgProg);
      gl.disable(gl.DEPTH_TEST);
      gl.disable(gl.BLEND);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.buf.bgXY);
      gl.enableVertexAttribArray(0);
      gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.buf.bgC);
      gl.bufferData(gl.ARRAY_BUFFER, new Uint8Array(cols), gl.DYNAMIC_DRAW);
      gl.enableVertexAttribArray(1);
      gl.vertexAttribPointer(1, 4, gl.UNSIGNED_BYTE, true, 0, 0);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      gl.disableVertexAttribArray(0);
      gl.disableVertexAttribArray(1);
    }

    const icon = this.icon;
    this.uploadPositions(time * 8);
    gl.useProgram(this.prog);
    gl.enable(gl.DEPTH_TEST);
    gl.depthMask(true);
    gl.enable(gl.CULL_FACE);
    gl.enable(gl.BLEND);
    gl.blendFuncSeparate(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA, gl.ONE, gl.ONE_MINUS_SRC_ALPHA);

    const attr = (i, buf, size, type, norm) => {
      gl.bindBuffer(gl.ARRAY_BUFFER, buf);
      gl.enableVertexAttribArray(i);
      gl.vertexAttribPointer(i, size, type, norm, 0, 0);
    };
    attr(0, this.buf.pos, 3, gl.FLOAT, false);
    attr(1, this.buf.nrm, 3, gl.SHORT, false);
    attr(2, this.buf.uv, 2, gl.SHORT, false);
    attr(3, this.buf.col, 4, gl.UNSIGNED_BYTE, false);

    // rotation around the icon's centre, then a camera that frames its bounding sphere
    const cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
    const rot = [cy, sp * sy, -cp * sy, 0, cp, sp, sy, -sp * cy, cp * cy]; // Rx(pitch) * Ry(yaw), column-major
    const [cx, cyy, cz] = this.center;
    const rc = [rot[0] * cx + rot[3] * cyy + rot[6] * cz, rot[1] * cx + rot[4] * cyy + rot[7] * cz, rot[2] * cx + rot[5] * cyy + rot[8] * cz];
    const fov = 40, dist = (this.radius * 1.08) / Math.sin((fov * Math.PI) / 360);
    const view = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, -rc[0], -rc[1], -rc[2] - dist, 1];
    gl.uniformMatrix4fv(this.u.u_mvp, false, mul(perspective(fov, w / h, dist / 20, dist * 4), view));
    gl.uniformMatrix3fv(this.u.u_rot, false, rot);

    const L = this.look;
    const dirs = L.lightDirs.flatMap((d) => {
      const l = Math.hypot(d[0], d[1], d[2]);
      return l > 0.01 ? d.map((x) => x / l) : [0, 0, 0];
    });
    gl.uniform3fv(this.u.u_ldir, dirs);
    gl.uniform3fv(this.u.u_lcol, L.lightColors.flat());
    gl.uniform3fv(this.u.u_amb, L.ambient);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, icon.texture ? this.tex : this.white);
    gl.uniform1i(this.u.u_tex, 0);
    gl.drawArrays(gl.TRIANGLES, 0, this.drawCount);
    return true;
  }
}
