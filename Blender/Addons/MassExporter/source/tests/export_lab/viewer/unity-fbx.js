// Unity's FBX import, modelled on top of three.js FBXLoader.
//
// FBXLoader evaluates the FBX transform model (pre/post rotation, pivots, inherit type) the
// way the FBX SDK does, but it ignores two GlobalSettings that Unity applies:
//   - UnitScaleFactor ("Convert Units", on by default): Unity scales the file by
//     UnitScaleFactor / 100, so 1 unit = 1 m whatever Apply Scalings wrote.
//   - the axis system (UpAxis / FrontAxis / CoordAxis and signs): Unity converts the file to
//     its own axes. Without "Bake Axis Conversion" the conversion sits on the root, with it
//     the result faces the other way round the up axis (both measured in Unity 6000.3).
// The result is shown in three.js's right-handed space: Unity's left-handed X flip is the
// only difference between the two, so positions here are Unity's with x negated.
//
// unity.json (unity_dump.py) holds what Unity really made of every FBX of a run; checks.js
// measures this model against it.
import * as THREE from "three";
import { FBXLoader } from "three/addons/loaders/FBXLoader.js";

// ------------------------------------------------------------------ binary FBX GlobalSettings

const MAGIC = "Kaydara FBX Binary  ";

export function readGlobalSettings(buffer) {
  const dv = new DataView(buffer);
  const bytes = new Uint8Array(buffer);
  const head = String.fromCharCode(...bytes.subarray(0, 20));
  if (head !== MAGIC) return null;   // ASCII FBX: Blender never writes it
  const version = dv.getUint32(23, true);
  const wide = version >= 7500;
  const u = (o) => (wide ? Number(dv.getBigUint64(o, true)) : dv.getUint32(o, true));
  const W = wide ? 8 : 4;
  const dec = new TextDecoder();

  // Read one node record at o; returns { name, props, children:[start,end], end }
  function node(o) {
    const end = u(o), nProps = u(o + W), propLen = u(o + 2 * W);
    if (end === 0) return null;
    const nameLen = bytes[o + 3 * W];
    const name = dec.decode(bytes.subarray(o + 3 * W + 1, o + 3 * W + 1 + nameLen));
    let p = o + 3 * W + 1 + nameLen;
    const propsStart = p;
    const props = [];
    for (let i = 0; i < nProps; i++) {
      const t = String.fromCharCode(bytes[p++]);
      switch (t) {
        case "Y": props.push(dv.getInt16(p, true)); p += 2; break;
        case "C": props.push(bytes[p] !== 0); p += 1; break;
        case "I": props.push(dv.getInt32(p, true)); p += 4; break;
        case "F": props.push(dv.getFloat32(p, true)); p += 4; break;
        case "D": props.push(dv.getFloat64(p, true)); p += 8; break;
        case "L": props.push(Number(dv.getBigInt64(p, true))); p += 8; break;
        case "S": case "R": {
          const len = dv.getUint32(p, true); p += 4;
          props.push(t === "S" ? dec.decode(bytes.subarray(p, p + len)) : null);
          p += len; break;
        }
        default: {   // f d l i b arrays: length, encoding, compressed length, data
          const clen = dv.getUint32(p + 8, true);
          props.push(null);
          p += 12 + clen;
        }
      }
    }
    return { name, props, children: [propsStart + propLen, end], end };
  }

  function children(start, end) {
    const out = [];
    let o = start;
    while (o < end) {
      const n = node(o);
      if (!n) break;
      out.push(n);
      o = n.end;
    }
    return out;
  }

  const top = children(27, bytes.length);
  const gs = top.find((n) => n.name === "GlobalSettings");
  if (!gs) return null;
  const p70 = children(...gs.children).find((n) => n.name === "Properties70");
  const out = {};
  for (const p of children(...p70.children)) {
    if (p.name === "P") out[p.props[0]] = p.props[4];
  }
  return out;
}

// ------------------------------------------------------------------ axis + unit conversion

const AXES = [new THREE.Vector3(1, 0, 0), new THREE.Vector3(0, 1, 0), new THREE.Vector3(0, 0, 1)];

// Matrix taking the file's axis system to Unity's (right-handed view: X right, Y up, Z front).
// FBX FrontAxis is the parity axis: the front direction is -sign along it (FBX SDK).
export function axisMatrix(gs) {
  const up = AXES[gs.UpAxis ?? 1].clone().multiplyScalar(gs.UpAxisSign ?? 1);
  const front = AXES[gs.FrontAxis ?? 2].clone().multiplyScalar(gs.FrontAxisSign ?? 1);
  const coord = AXES[gs.CoordAxis ?? 0].clone().multiplyScalar(gs.CoordAxisSign ?? 1);
  // Rows: where each file axis goes. File coord -> +X, up -> +Y, front -> +Z
  const m = new THREE.Matrix4().makeBasis(coord, up, front).transpose();
  return m;
}

export function unitScale(gs) {
  return (gs?.UnitScaleFactor ?? 1) / 100;
}

// Bake Axis Conversion turns the result half a turn round the up axis (measured)
const BAKE_TURN = new THREE.Matrix4().makeRotationY(Math.PI);

/**
 * Load an FBX the way Unity's model importer places it.
 * opts.bakeAxisConversion: Unity's "Bake Axis Conversion" import setting (default off).
 * Returns a Group whose single child is the FBXLoader scene, with the conversion on the
 * group; userData.unity holds the settings that were read.
 */
export function loadUnityFBX(buffer, opts = {}) {
  const gs = readGlobalSettings(buffer) || {};
  const scene = new FBXLoader().parse(buffer, "");
  const root = new THREE.Group();
  root.name = "unity-import";
  const m = axisMatrix(gs).premultiply(new THREE.Matrix4().makeScale(...Array(3).fill(unitScale(gs))));
  if (opts.bakeAxisConversion) m.premultiply(BAKE_TURN);
  root.applyMatrix4(m);
  root.add(scene);
  root.userData.unity = { globalSettings: gs, unitScale: unitScale(gs), bakeAxisConversion: !!opts.bakeAxisConversion };
  return root;
}
