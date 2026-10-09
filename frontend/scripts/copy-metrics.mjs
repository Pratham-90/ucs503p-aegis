// Publish metrics/prototype-metrics.json with the build so the Demo Console can show it.
import { copyFileSync, existsSync, mkdirSync } from "node:fs";

const source = new URL("../../metrics/prototype-metrics.json", import.meta.url);
const target = new URL("../public/metrics/", import.meta.url);
if (existsSync(source)) {
  mkdirSync(target, { recursive: true });
  copyFileSync(source, new URL("prototype-metrics.json", target));
  console.log("copied metrics/prototype-metrics.json into the build");
} else {
  console.log("no metrics file yet; the Demo Console will say so");
}
