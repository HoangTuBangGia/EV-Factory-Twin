import * as THREE from "three";

/**
 * Every texture here is drawn on an offscreen canvas at import-free runtime, so
 * the 3D map ships no image assets and makes no network requests. A tiny
 * deterministic PRNG keeps speckle stable across React strict-mode remounts.
 */
function makeRandom(seed: number) {
  let state = seed >>> 0;
  return () => {
    state = (state * 1664525 + 1013904223) >>> 0;
    return state / 0x100000000;
  };
}

function createCanvas(width: number, height = width) {
  const canvas = document.createElement("canvas");
  canvas.width = width; canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("2D canvas context unavailable");
  return { canvas, context };
}

function toTexture(canvas: HTMLCanvasElement, repeat?: [number, number], srgb = true) {
  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  texture.anisotropy = 4;
  if (srgb) texture.colorSpace = THREE.SRGBColorSpace;
  if (repeat) texture.repeat.set(repeat[0], repeat[1]);
  return texture;
}

/** Sealed-concrete speckle, used as a roughness map so the floor catches light unevenly. */
export function concreteRoughnessTexture() {
  const { canvas, context } = createCanvas(512);
  const random = makeRandom(0x5eed);
  context.fillStyle = "#8a8a8a";
  context.fillRect(0, 0, 512, 512);
  for (let i = 0; i < 9000; i += 1) {
    const shade = 90 + Math.floor(random() * 130);
    context.fillStyle = `rgba(${shade},${shade},${shade},0.5)`;
    context.fillRect(random() * 512, random() * 512, 1 + random() * 2.2, 1 + random() * 2.2);
  }
  for (let i = 0; i < 70; i += 1) {
    const y = random() * 512;
    context.strokeStyle = `rgba(${140 + random() * 60 | 0},${140 + random() * 60 | 0},${150},0.16)`;
    context.lineWidth = 0.6 + random() * 1.6;
    context.beginPath();
    context.moveTo(0, y);
    context.bezierCurveTo(170, y + random() * 40 - 20, 340, y + random() * 40 - 20, 512, y);
    context.stroke();
  }
  return toTexture(canvas, [5, 4], false);
}

/** Power-float sheen variation for the floor colour map. */
export function concreteColorTexture() {
  const { canvas, context } = createCanvas(512);
  const random = makeRandom(0xc0ffee);
  context.fillStyle = "#8fa6ae";
  context.fillRect(0, 0, 512, 512);
  for (let i = 0; i < 240; i += 1) {
    const radius = 24 + random() * 120;
    const gradient = context.createRadialGradient(
      random() * 512, random() * 512, 0, random() * 512, random() * 512, radius,
    );
    const light = random() > 0.5;
    gradient.addColorStop(0, light ? "rgba(190,214,222,0.09)" : "rgba(48,66,76,0.11)");
    gradient.addColorStop(1, "rgba(0,0,0,0)");
    context.fillStyle = gradient;
    context.fillRect(0, 0, 512, 512);
  }
  for (let i = 0; i < 2600; i += 1) {
    context.fillStyle = random() > 0.5 ? "rgba(214,232,238,0.10)" : "rgba(26,40,48,0.14)";
    context.fillRect(random() * 512, random() * 512, 1, 1);
  }
  return toTexture(canvas, [4, 3]);
}

/** 45-degree hazard bands for keep-out floor patches. */
export function hazardStripeTexture(warm = "#f4c236", dark = "#1a1405") {
  const size = 256;
  const { canvas, context } = createCanvas(size);
  context.fillStyle = dark;
  context.fillRect(0, 0, size, size);
  context.strokeStyle = warm;
  context.lineWidth = size / 9;
  context.beginPath();
  for (let offset = -size; offset <= size * 2; offset += size / 4.5) {
    context.moveTo(offset, -8);
    context.lineTo(offset + size + 8, size + 8);
  }
  context.stroke();
  context.globalAlpha = 0.16;
  context.fillStyle = "#000";
  for (let i = 0; i < size; i += 4) context.fillRect(0, i, size, 1);
  return toTexture(canvas);
}

/** Flowing travel-direction chevrons painted down the middle of the aisle. */
export function laneChevronTexture(color = "#3fe6d0") {
  const { canvas, context } = createCanvas(128, 128);
  context.clearRect(0, 0, 128, 128);
  context.fillStyle = color;
  context.globalAlpha = 0.85;
  for (const originY of [10, 74]) {
    context.beginPath();
    context.moveTo(18, originY);
    context.lineTo(64, originY + 22);
    context.lineTo(110, originY);
    context.lineTo(110, originY + 15);
    context.lineTo(64, originY + 37);
    context.lineTo(18, originY + 15);
    context.closePath();
    context.fill();
  }
  return toTexture(canvas);
}

/** Floor-painted zone lettering; real plants stencil area names on the slab. */
export function floorLabelTexture(text: string, color = "#7ecbdc", subtitle?: string) {
  const width = 1024, height = 256;
  const { canvas, context } = createCanvas(width, height);
  context.clearRect(0, 0, width, height);
  context.fillStyle = color;
  context.textBaseline = "middle";
  context.textAlign = "center";
  context.font = "700 108px Arial, Helvetica, sans-serif";
  context.letterSpacing = "18px";
  context.globalAlpha = 0.92;
  context.fillText(text, width / 2, subtitle ? height / 2 - 34 : height / 2);
  if (subtitle) {
    context.font = "600 52px Arial, Helvetica, sans-serif";
    context.letterSpacing = "12px";
    context.globalAlpha = 0.6;
    context.fillText(subtitle, width / 2, height / 2 + 62);
  }
  const texture = toTexture(canvas);
  texture.wrapS = texture.wrapT = THREE.ClampToEdgeWrapping;
  return texture;
}

/** Emissive equipment face: title bar, readout rows and an indicator pip. */
export function hmiPanelTexture(title: string, rows: string[], accent = "#3fe6d0") {
  const width = 512, height = 320;
  const { canvas, context } = createCanvas(width, height);
  context.fillStyle = "#08151b";
  context.fillRect(0, 0, width, height);
  context.strokeStyle = "#1d3a45";
  context.lineWidth = 6;
  context.strokeRect(3, 3, width - 6, height - 6);
  context.fillStyle = accent;
  context.fillRect(3, 3, width - 6, 54);
  context.fillStyle = "#04191c";
  context.font = "700 30px Arial, Helvetica, sans-serif";
  context.letterSpacing = "6px";
  context.textBaseline = "middle";
  context.fillText(title, 22, 31);
  rows.forEach((row, index) => {
    const y = 96 + index * 54;
    context.fillStyle = "#0e2029";
    context.fillRect(22, y - 20, width - 44, 42);
    context.fillStyle = accent;
    context.beginPath();
    context.arc(44, y, 7, 0, Math.PI * 2);
    context.fill();
    context.fillStyle = "#b8d6dd";
    context.font = "600 26px Arial, Helvetica, sans-serif";
    context.letterSpacing = "2px";
    context.fillText(row, 66, y);
  });
  return toTexture(canvas);
}

/** ISO-style warning triangle for the no-go signpost. */
export function warningSignTexture() {
  const size = 256;
  const { canvas, context } = createCanvas(size);
  context.clearRect(0, 0, size, size);
  context.fillStyle = "#f4c236";
  context.beginPath();
  context.moveTo(size / 2, 24);
  context.lineTo(size - 22, size - 34);
  context.lineTo(22, size - 34);
  context.closePath();
  context.fill();
  context.strokeStyle = "#12100a";
  context.lineWidth = 14;
  context.stroke();
  context.fillStyle = "#12100a";
  context.fillRect(size / 2 - 13, 86, 26, 92);
  context.beginPath();
  context.arc(size / 2, 196, 16, 0, Math.PI * 2);
  context.fill();
  return toTexture(canvas);
}

/** Soft radial falloff reused for light pools and selection glows. */
export function radialGlowTexture(inner = "rgba(63,230,208,0.55)") {
  const size = 256;
  const { canvas, context } = createCanvas(size);
  const gradient = context.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  gradient.addColorStop(0, inner);
  gradient.addColorStop(0.45, inner.replace(/[\d.]+\)$/, "0.18)"));
  gradient.addColorStop(1, "rgba(0,0,0,0)");
  context.fillStyle = gradient;
  context.fillRect(0, 0, size, size);
  const texture = toTexture(canvas);
  texture.wrapS = texture.wrapT = THREE.ClampToEdgeWrapping;
  return texture;
}
