import { cpSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
mkdirSync(join(root, "dist"), { recursive: true });
for (const file of ["index.html", "styles.css"]) {
  cpSync(join(root, "static", file), join(root, "dist", file));
}
console.log("static assets copied to dist/");
