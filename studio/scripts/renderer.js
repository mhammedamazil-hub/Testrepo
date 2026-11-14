// Minimal software 3D renderer — perspective camera, z-buffer, Lambert + rim + fresnel,
// depth fog, 2x supersampling. Used to fake "rendered in bpy" key art without any GPU.
const { mat4, vec3 } = (() => {
  const vec3 = {
    sub: (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]],
    add: (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]],
    mul: (a, s) => [a[0] * s, a[1] * s, a[2] * s],
    dot: (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2],
    cross: (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]],
    len: (a) => Math.hypot(a[0], a[1], a[2]),
    norm: (a) => {
      const l = Math.hypot(a[0], a[1], a[2]) || 1;
      return [a[0] / l, a[1] / l, a[2] / l];
    },
  };
  const mat4 = {
    ident: () => [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
    mul: (a, b) => {
      const o = new Array(16).fill(0);
      for (let i = 0; i < 4; i++)
        for (let j = 0; j < 4; j++) {
          let s = 0;
          for (let k = 0; k < 4; k++) s += a[k * 4 + j] * b[i * 4 + k];
          o[i * 4 + j] = s;
        }
      return o;
    },
    translate: (x, y, z) => [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, x, y, z, 1],
    scale: (x, y, z) => [x, 0, 0, 0, 0, y, 0, 0, 0, 0, z, 0, 0, 0, 0, 1],
    rotX: (a) => [1, 0, 0, 0, 0, Math.cos(a), Math.sin(a), 0, 0, -Math.sin(a), Math.cos(a), 0, 0, 0, 0, 1],
    rotY: (a) => [Math.cos(a), 0, -Math.sin(a), 0, 0, 1, 0, 0, Math.sin(a), 0, Math.cos(a), 0, 0, 0, 0, 1],
    rotZ: (a) => [Math.cos(a), Math.sin(a), 0, 0, -Math.sin(a), Math.cos(a), 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
    perspective: (fovy, aspect, near, far) => {
      const f = 1 / Math.tan(fovy / 2);
      return [f / aspect, 0, 0, 0, 0, f, 0, 0, 0, 0, (far + near) / (near - far), -1, 0, 0, (2 * far * near) / (near - far), 0];
    },
    lookAt: (eye, target, up = [0, 1, 0]) => {
      const z = vec3.norm(vec3.sub(eye, target));
      const x = vec3.norm(vec3.cross(up, z));
      const y = vec3.cross(z, x);
      return [x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0, -vec3.dot(x, eye), -vec3.dot(y, eye), -vec3.dot(z, eye), 1];
    },
    apply: (m, p) => {
      const x = p[0], y = p[1], z = p[2];
      const w = m[3] * x + m[7] * y + m[11] * z + m[15] || 1;
      return [
        (m[0] * x + m[4] * y + m[8] * z + m[12]) / w,
        (m[1] * x + m[5] * y + m[9] * z + m[13]) / w,
        (m[2] * x + m[6] * y + m[10] * z + m[14]) / w,
      ];
    },
    applyDir: (m, p) => [
      m[0] * p[0] + m[4] * p[1] + m[8] * p[2],
      m[1] * p[0] + m[5] * p[1] + m[9] * p[2],
      m[2] * p[0] + m[6] * p[1] + m[10] * p[2],
    ],
  };
  return { mat4, vec3 };
})();

/* ---------- geometry ---------- */
function icosphere(sub = 2) {
  const t = (1 + Math.sqrt(5)) / 2;
  let verts = [
    [-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0],
    [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t],
    [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1],
  ].map((v) => vec3.norm(v));
  let faces = [
    [0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
    [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
    [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
    [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1],
  ];
  for (let s = 0; s < sub; s++) {
    const cache = new Map();
    const mid = (a, b) => {
      const k = a < b ? `${a}_${b}` : `${b}_${a}`;
      if (cache.has(k)) return cache.get(k);
      const m = vec3.norm(vec3.mul(vec3.add(verts[a], verts[b]), 0.5));
      verts.push(m);
      cache.set(k, verts.length - 1);
      return verts.length - 1;
    };
    const nf = [];
    for (const [a, b, c] of faces) {
      const ab = mid(a, b), bc = mid(b, c), ca = mid(c, a);
      nf.push([a, ab, ca], [b, bc, ab], [c, ca, bc], [ab, bc, ca]);
    }
    faces = nf;
  }
  return { verts, faces };
}

function boxGeo(sx = 1, sy = 1, sz = 1) {
  const x = sx / 2, y = sy / 2, z = sz / 2;
  const verts = [
    [-x, -y, -z], [x, -y, -z], [x, y, -z], [-x, y, -z],
    [-x, -y, z], [x, -y, z], [x, y, z], [-x, y, z],
  ];
  const faces = [
    [0, 1, 2], [0, 2, 3], [5, 4, 7], [5, 7, 6],
    [4, 0, 3], [4, 3, 7], [1, 5, 6], [1, 6, 2],
    [3, 2, 6], [3, 6, 7], [4, 5, 1], [4, 1, 0],
  ];
  return { verts, faces };
}

function spireGeo({ N = 8, rings = 14, top = 0.62, height = 3.4, taper = 0.62 } = {}) {
  const verts = [], faces = [];
  for (let i = 0; i < rings; i++) {
    const t = i / (rings - 1);
    const prof = Math.sin(Math.PI * Math.pow(t, taper));
    const rad = top * Math.pow(prof, 0.85) + 0.012;
    const y = height / 2 - t * height;
    for (let j = 0; j < N; j++) {
      const a = (j / N) * Math.PI * 2 + t * 0.55;
      verts.push([Math.cos(a) * rad, y, Math.sin(a) * rad]);
    }
  }
  for (let i = 0; i < rings - 1; i++)
    for (let j = 0; j < N; j++) {
      const a = i * N + j, b = i * N + ((j + 1) % N), c = (i + 1) * N + ((j + 1) % N), d = (i + 1) * N + j;
      faces.push([a, b, c], [a, c, d]);
    }
  return { verts, faces };
}

function torusGeo(R = 1, r = 0.35, seg = 64, ring = 24) {
  const verts = [], faces = [];
  for (let i = 0; i < seg; i++) {
    const u = (i / seg) * Math.PI * 2;
    for (let j = 0; j < ring; j++) {
      const v = (j / ring) * Math.PI * 2;
      verts.push([(R + r * Math.cos(v)) * Math.cos(u), r * Math.sin(v), (R + r * Math.cos(v)) * Math.sin(u)]);
    }
  }
  for (let i = 0; i < seg; i++)
    for (let j = 0; j < ring; j++) {
      const a = i * ring + j, b = ((i + 1) % seg) * ring + j, c = ((i + 1) % seg) * ring + ((j + 1) % ring), d = i * ring + ((j + 1) % ring);
      faces.push([a, b, c], [a, c, d]);
    }
  return { verts, faces };
}

function funnelGeometry({ top = 1.0, height = 3.0, power = 0.8, N = 96, rings = 30 } = {}) {
  // abstract "funnel" of stacked rings — reads as a forged funnel/portal
  const verts = [], faces = [];
  for (let i = 0; i < rings; i++) {
    const t = i / (rings - 1);
    const rad = top * Math.pow(1 - t, power) + 0.05;
    const y = height / 2 - t * height;
    for (let j = 0; j < N; j++) {
      const a = (j / N) * Math.PI * 2;
      const wob = 1 + 0.045 * Math.sin(a * 7 + t * 5.5) + 0.02 * Math.cos(a * 13 - t * 3);
      verts.push([Math.cos(a) * rad * wob, y, Math.sin(a) * rad * wob]);
    }
  }
  for (let i = 0; i < rings - 1; i++)
    for (let j = 0; j < N; j++) {
      const a = i * N + j, b = i * N + ((j + 1) % N), c = (i + 1) * N + ((j + 1) % N), d = (i + 1) * N + j;
      faces.push([a, b, c], [a, c, d]);
    }
  return { verts, faces };
}

/* ---------- color helpers ---------- */
const hex = (h) => {
  const s = h.replace('#', '');
  return [parseInt(s.slice(0, 2), 16) / 255, parseInt(s.slice(2, 4), 16) / 255, parseInt(s.slice(4, 6), 16) / 255];
};
const mix = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
const smoothstep = (e0, e1, x) => {
  const t = Math.min(1, Math.max(0, (x - e0) / (e1 - e0)));
  return t * t * (3 - 2 * t);
};

/**
 * Render a scene.
 * scene = { objects:[{geo:'sphere'|'box'|'torus'|'funnel', pos, rot, scale, color, emissive, metal, wire, opacity}],
 *           camera:{eye,target,fov}, light:{dir,color,intensity}, rim:{color}, bg:{top,bottom}, fog:{near,far,color},
 *           grid:{y,extent,step,color,distance}, glow:{x,y,r,color,strength} }
 */
function render(scene, W, H, ss = 2) {
  const w = W * ss, h = H * ss;
  const color = new Float32Array(w * h * 3);
  const depth = new Float32Array(w * h).fill(Infinity);
  const bgTop = hex(scene.bg?.top || '#0B0D13');
  const bgBot = hex(scene.bg?.bottom || '#04050A');
  const fogCol = hex(scene.fog?.color || scene.bg?.bottom || '#04050A');
  const fogNear = scene.fog?.near ?? 6;
  const fogFar = scene.fog?.far ?? 26;

  const cam = scene.camera || {};
  const eye = cam.eye || [0, 0.6, 6.4];
  const target = cam.target || [0, 0, 0];
  const fov = ((cam.fov || 42) * Math.PI) / 180;
  const proj = mat4.mul(mat4.perspective(fov, w / h, 0.1, 200), mat4.lookAt(eye, target));
  const invView = mat4.lookAt(eye, target); // for view-space lighting fallback

  // background + radial glow
  for (let y = 0; y < h; y++) {
    const t = y / (h - 1);
    const base = mix(bgTop, bgBot, Math.pow(t, 0.85));
    for (let x = 0; x < w; x++) {
      let c = base;
      if (scene.glow) {
        const gx = (x / w - scene.glow.x) * (w / h), gy = y / h - scene.glow.y;
        const d = Math.hypot(gx, gy) / scene.glow.r;
        const f = Math.max(0, 1 - d);
        c = mix(c, hex(scene.glow.color || '#FF6B2C'), Math.pow(f, 2.2) * (scene.glow.strength ?? 0.55));
      }
      const i = (y * w + x) * 3;
      color[i] = c[0]; color[i + 1] = c[1]; color[i + 2] = c[2];
    }
  }

  const L = vec3.norm(scene.light?.dir || [-0.45, 0.8, 0.55]);
  const Lcol = hex(scene.light?.color || '#FFF1E0');
  const Li = scene.light?.intensity ?? 1.25;
  const rimCol = hex(scene.rim?.color || '#22E8C8');
  const rimI = scene.rim?.intensity ?? 0.9;

  const tris = [];
  const wires = [];

  for (const obj of scene.objects || []) {
    let geo;
    if (obj.geo === 'box') geo = boxGeo(obj.size?.[0] ?? 1, obj.size?.[1] ?? 1, obj.size?.[2] ?? 1);
    else if (obj.geo === 'torus') geo = torusGeo(obj.R ?? 1, obj.r ?? 0.32, obj.seg ?? 72, obj.ring ?? 24);
    else if (obj.geo === 'funnel') geo = funnelGeometry(obj.geoParams || {});
    else if (obj.geo === 'spire') geo = spireGeo(obj.geoParams || {});
    else geo = icosphere(obj.sub ?? 2);

    let M = mat4.ident();
    M = mat4.mul(mat4.translate(...(obj.pos || [0, 0, 0])), M);
    if (obj.rot) {
      const [rx, ry, rz] = obj.rot;
      M = mat4.mul(M, mat4.rotX(rx));
      M = mat4.mul(M, mat4.rotY(ry));
      M = mat4.mul(M, mat4.rotZ(rz));
    }
    const sc = obj.scale === undefined ? [1, 1, 1] : Array.isArray(obj.scale) ? obj.scale : [obj.scale, obj.scale, obj.scale];
    M = mat4.mul(M, mat4.scale(...sc));

    const world = geo.verts.map((v) => mat4.apply(M, v));
    const nrm = geo.verts.map((v) => vec3.norm(mat4.applyDir(M, v)));
    const clip = world.map((v) => mat4.apply(proj, v));

    for (const f of geo.faces) {
      const [a, b, c] = f;
      const pa = clip[a], pb = clip[b], pc = clip[c];
      if (pa[2] < -1 || pb[2] < -1 || pc[2] < -1) continue;
      const faceN = vec3.norm(vec3.cross(vec3.sub(world[b], world[a]), vec3.sub(world[c], world[a])));
      tris.push({
        fn: faceN,
        p: [pa, pb, pc],
        n: [nrm[a], nrm[b], nrm[c]],
        w: [world[a], world[b], world[c]],
        obj,
      });
      if (obj.wire) wires.push({ p: [pa, pb], w: [world[a], world[b]], dist: world[a][2] });
    }
  }

  const project = (p) => [((p[0] * 0.5 + 0.5) * w), ((-p[1] * 0.5 + 0.5) * h)];
  const shade = (obj, n, worldPos) => {
    const albedo = hex(obj.color || '#C9C2B2');
    const ndl = Math.max(0, vec3.dot(n, L));
    const viewDir = vec3.norm(vec3.sub(eye, worldPos));
    const facing = Math.max(0, vec3.dot(n, viewDir));
    const fres = Math.pow(1 - facing, 4);
    const ha = vec3.norm(vec3.add(L, viewDir));
    const spec = Math.pow(Math.max(0, vec3.dot(n, ha)), obj.metal ? 120 : 30) * (obj.metal ? 1.0 : 0.22);
    const emAmt = Math.min(1, obj.emissiveAmt ?? 0);

    let c = [0, 0, 0];
    const dim = obj.ambient ?? (obj.metal ? 0.26 : 0.46);
    for (let k = 0; k < 3; k++) c[k] = albedo[k] * (dim + ndl * Li * 0.85);
    c = mix(c, [1, 1, 1], spec * 0.7);
    // teal rim light: only where the surface faces away from the rim light direction
    const rimDir = vec3.norm([0.7, -0.2, -0.65]);
    const rimL = Math.pow(1 - Math.max(0, vec3.dot(n, rimDir)), 3.0);
    c = mix(c, rimCol, rimL * rimI * 0.08 * (1 - emAmt));
    // emissive materials glow with their own colour, almost unlit
    c = mix(c, hex(obj.emissive || '#FF6B2C'), emAmt);
    c = mix(c, [1, 1, 1], fres * (obj.metal ? 0.22 : 0.06) * (1 - emAmt * 0.8));
    const d = vec3.len(vec3.sub(eye, worldPos));
    const fog = smoothstep(fogNear, fogFar, d);
    c = mix(c, fogCol, fog * (obj.fogAmount ?? 0.85));
    return c;
  };

  // z-buffered triangle raster
  for (const t of tris) {
    const A = project(t.p[0]), B = project(t.p[1]), Cc = project(t.p[2]);
    const minX = Math.max(0, Math.floor(Math.min(A[0], B[0], Cc[0])));
    const maxX = Math.min(w - 1, Math.ceil(Math.max(A[0], B[0], Cc[0])));
    const minY = Math.max(0, Math.floor(Math.min(A[1], B[1], Cc[1])));
    const maxY = Math.min(h - 1, Math.ceil(Math.max(A[1], B[1], Cc[1])));
    const area = (B[0] - A[0]) * (Cc[1] - A[1]) - (B[1] - A[1]) * (Cc[0] - A[0]);
    if (Math.abs(area) < 1e-9) continue;
    for (let y = minY; y <= maxY; y++) {
      for (let x = minX; x <= maxX; x++) {
        const px = x + 0.5, py = y + 0.5;
        const w0 = ((B[0] - px) * (Cc[1] - py) - (B[1] - py) * (Cc[0] - px)) / area;
        const w1 = ((Cc[0] - px) * (A[1] - py) - (Cc[1] - py) * (A[0] - px)) / area;
        const w2 = 1 - w0 - w1;
        if (w0 < 0 || w1 < 0 || w2 < 0) continue;
        const z = w0 * t.p[0][2] + w1 * t.p[1][2] + w2 * t.p[2][2];
        const idx = y * w + x;
        if (z >= depth[idx]) continue;
        depth[idx] = z;
        let n = vec3.norm([
          w0 * t.n[0][0] + w1 * t.n[1][0] + w2 * t.n[2][0],
          w0 * t.n[0][1] + w1 * t.n[1][1] + w2 * t.n[2][1],
          w0 * t.n[0][2] + w1 * t.n[1][2] + w2 * t.n[2][2],
        ]);
        if (t.obj.flat) n = t.fn;
        const wp = [
          w0 * t.w[0][0] + w1 * t.w[1][0] + w2 * t.w[2][0],
          w0 * t.w[0][1] + w1 * t.w[1][1] + w2 * t.w[2][1],
          w0 * t.w[0][2] + w1 * t.w[1][2] + w2 * t.w[2][2],
        ];
        const c = shade(t.obj, n, wp);
        const o = 1 - (t.obj.opacity ?? 1);
        const i3 = idx * 3;
        color[i3] = color[i3] * o + c[0] * (1 - o);
        color[i3 + 1] = color[i3 + 1] * o + c[1] * (1 - o);
        color[i3 + 2] = color[i3 + 2] * o + c[2] * (1 - o);
      }
    }
  }

  // ground grid lines (projected), with fade
  if (scene.grid) {
    const g = scene.grid;
    const ext = g.extent ?? 12, step = g.step ?? 0.5, gy = g.y ?? -1.6;
    const gcol = hex(g.color || '#22E8C8');
    const lines = [];
    for (let i = -ext; i <= ext; i += step) {
      lines.push([[i, gy, -ext], [i, gy, ext]]);
      lines.push([[-ext, gy, i], [ext, gy, i]]);
    }
    for (const [p, q] of lines) {
      const a = mat4.apply(proj, p), b = mat4.apply(proj, q);
      if (a[2] < -1 || b[2] < -1) continue;
      const A = project(a), B = project(b);
      const dA = Math.hypot(a[0] - eye[0], a[1] - eye[1], a[2] - eye[2]);
      const dB = Math.hypot(b[0] - eye[0], b[1] - eye[1], b[2] - eye[2]);
      const fog = 1 - smoothstep(g.near ?? 5, g.far ?? 20, (dA + dB) / 2);
      if (fog <= 0.01) continue;
      // Bresenham-ish line with alpha
      const steps = Math.max(2, Math.ceil(Math.hypot(B[0] - A[0], B[1] - A[1])));
      for (let s = 0; s <= steps; s++) {
        const t = s / steps;
        const x = Math.round(A[0] + (B[0] - A[0]) * t), y = Math.round(A[1] + (B[1] - A[1]) * t);
        if (x < 0 || x >= w || y < 0 || y >= h) continue;
        const i3 = (y * w + x) * 3;
        const al = 0.42 * fog;
        color[i3] = color[i3] * (1 - al) + gcol[0] * al;
        color[i3 + 1] = color[i3 + 1] * (1 - al) + gcol[1] * al;
        color[i3 + 2] = color[i3 + 2] * (1 - al) + gcol[2] * al;
      }
    }
  }

  // wire overlay
  for (const seg of wires) {
    const A = project(seg.p[0]), B = project(seg.p[1]);
    const fog = 1 - smoothstep(fogNear, fogFar, seg.dist);
    if (fog <= 0.02) continue;
    const wc = hex(seg.color || '#FF9A62');
    const steps = Math.max(2, Math.ceil(Math.hypot(B[0] - A[0], B[1] - A[1])));
    for (let s = 0; s <= steps; s++) {
      const t = s / steps;
      const x = Math.round(A[0] + (B[0] - A[0]) * t), y = Math.round(A[1] + (B[1] - A[1]) * t);
      if (x < 0 || x >= w || y < 0 || y >= h) continue;
      const i3 = (y * w + x) * 3;
      const al = 0.5 * fog;
      color[i3] = color[i3] * (1 - al) + wc[0] * al;
      color[i3 + 1] = color[i3 + 1] * (1 - al) + wc[1] * al;
      color[i3 + 2] = color[i3 + 2] * (1 - al) + wc[2] * al;
    }
  }

  // vignette
  if (scene.vignette !== false) {
    const vc = hex(scene.vignetteColor || '#000000');
    const vs = scene.vignetteStrength ?? 0.55;
    const cx = w / 2, cy = h * 0.48, maxr = Math.hypot(cx, cy);
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const d = Math.hypot(x - cx, y - cy) / maxr;
        const f = Math.pow(Math.min(1, d / 0.92), 2.1) * vs;
        const i3 = (y * w + x) * 3;
        color[i3] = color[i3] * (1 - f) + vc[0] * f;
        color[i3 + 1] = color[i3 + 1] * (1 - f) + vc[1] * f;
        color[i3 + 2] = color[i3 + 2] * (1 - f) + vc[2] * f;
      }
    }
  }

  // down-sample (box filter) -> 8-bit RGB
  const out = Buffer.alloc(W * H * 3);
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      let r = 0, g = 0, b = 0;
      for (let dy = 0; dy < ss; dy++) {
        for (let dx = 0; dx < ss; dx++) {
          const i = ((y * ss + dy) * w + (x * ss + dx)) * 3;
          r += color[i]; g += color[i + 1]; b += color[i + 2];
        }
      }
      const n = ss * ss;
      const o = (y * W + x) * 3;
      out[o] = Math.max(0, Math.min(255, Math.round((r / n) * 255)));
      out[o + 1] = Math.max(0, Math.min(255, Math.round((g / n) * 255)));
      out[o + 2] = Math.max(0, Math.min(255, Math.round((b / n) * 255)));
    }
  }
  return out;
}

module.exports = { render, vec3, mat4, hex, mix, icosphere, boxGeo, torusGeo, funnelGeometry };
