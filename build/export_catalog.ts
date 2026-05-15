import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { icons } from "@phosphor-icons/core";

const buildDir = dirname(fileURLToPath(import.meta.url));
const cacheDir = join(buildDir, "cache");
const outputPath = join(cacheDir, "catalog.json");

await mkdir(cacheDir, { recursive: true });

const catalog = icons.map((icon) => ({
  name: icon.name,
  pascalName: icon.pascal_name,
  categories: icon.categories,
  tags: icon.tags,
}));

await writeFile(outputPath, JSON.stringify(catalog, null, 2), "utf8");
console.error(`Wrote ${catalog.length} icons to ${outputPath}`);
