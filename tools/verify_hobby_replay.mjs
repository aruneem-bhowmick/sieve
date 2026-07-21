import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const outputDirectory = "public";
const forbiddenMarkers = [
  "/api/",
  "Unlock live demo",
  "live sandbox",
  "Validate & start live suite",
  "Live-demo limits",
  "Live suite",
];

function filesIn(directory) {
  return readdirSync(directory).flatMap((entry) => {
    const path = join(directory, entry);
    return statSync(path).isDirectory() ? filesIn(path) : [path];
  });
}

if (!existsSync(outputDirectory)) throw new Error("Run the deterministic demo build before verifying it.");
if (existsSync(join(outputDirectory, "api"))) throw new Error("The static Hobby artifact must not contain api/.");

const bundle = filesIn(outputDirectory)
  .filter((path) => /\.(?:html|js|css)$/.test(path))
  .map((path) => readFileSync(path, "utf8"))
  .join("\n");
for (const marker of forbiddenMarkers) {
  if (bundle.includes(marker)) throw new Error(`Static Hobby artifact contains forbidden marker: ${marker}`);
}
console.log("Verified replay-only static Hobby artifact.");
