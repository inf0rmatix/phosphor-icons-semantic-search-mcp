import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import type { IconIndexEntry } from "./types.js";

const packageRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const indexPath = join(packageRoot, "data", "vector_index.json");

let indexCache: IconIndexEntry[] | null = null;

export function loadIconIndex(): IconIndexEntry[] {
  if (indexCache) {
    return indexCache;
  }

  const raw = readFileSync(indexPath, "utf8");
  const parsed = JSON.parse(raw) as IconIndexEntry[];

  if (!Array.isArray(parsed)) {
    throw new Error(`Invalid index format at ${indexPath}`);
  }

  indexCache = parsed;
  return indexCache;
}

export function cosineSimilarity(vectorA: number[], vectorB: number[]): number {
  let dotProduct = 0;

  for (let index = 0; index < vectorA.length; index++) {
    dotProduct += vectorA[index]! * vectorB[index]!;
  }

  return dotProduct;
}

export function searchIcons(
  queryVector: number[],
  topK = 5,
): Array<IconIndexEntry & { score: number }> {
  const index = loadIconIndex();

  const scored = index.map((icon) => ({
    ...icon,
    score: cosineSimilarity(queryVector, icon.vector),
  }));

  scored.sort((left, right) => right.score - left.score);

  return scored.slice(0, topK);
}

export function findIconByName(name: string): IconIndexEntry | undefined {
  return loadIconIndex().find((icon) => icon.name === name);
}
