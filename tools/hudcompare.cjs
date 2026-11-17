// Side-by-side HUD comparison (personal use): node hudcompare.cjs <reference> <current> <out.png>
// crops the same normalised regions from both (reference row above current row)
const path = require("path");
const P = require(path.join(process.env.APPDATA, "npm/node_modules/@earendil-works/pi-coding-agent/node_modules/@silvia-odwyer/photon-node"));
const fs = require("fs");
const [ref, cur, out] = process.argv.slice(2);
const regions = (process.env.REGIONS || "0.28,0.04,0.72,0.17;0.74,0.04,0.94,0.32;0.04,0.64,0.32,0.90")
  .split(";").map(r => r.split(",").map(Number));
function load(f, W, H) {
  let im = P.PhotonImage.new_from_byteslice(new Uint8Array(fs.readFileSync(f)));
  if (im.get_width() !== W) im = P.resize(im, W, H, 1);
  return im;
}
const W = 1920, H = 1080;
const a = load(ref, W, H), b = load(cur, W, H);
const crops = regions.map(([x0, y0, x1, y1]) => [Math.round(x0 * W), Math.round(y0 * H), Math.round(x1 * W), Math.round(y1 * H)]);
const totalW = crops.reduce((s, c) => s + (c[2] - c[0]) + 8, 0);
const rowH = Math.max(...crops.map(c => c[3] - c[1]));
const canvas = new P.PhotonImage(new Uint8Array(totalW * (rowH * 2 + 8) * 4).fill(40), totalW, rowH * 2 + 8);
let x = 0;
for (const c of crops) {
  P.watermark(canvas, P.crop(a, c[0], c[1], c[2], c[3]), BigInt(x), 0n);
  P.watermark(canvas, P.crop(b, c[0], c[1], c[2], c[3]), BigInt(x), BigInt(rowH + 8));
  x += (c[2] - c[0]) + 8;
}
fs.writeFileSync(out, canvas.get_bytes());
console.log("wrote", out, totalW, rowH * 2 + 8);
