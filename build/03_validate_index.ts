import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { getEmbedding } from "../src/embedder.js";
import type { IconIndexEntry } from "../src/types.js";
import { cosineSimilarity, searchIcons } from "../src/vector_search.js";

const packageRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const indexPath = join(packageRoot, "data", "vector_index.json");
const goldenQueriesPath = join(
  packageRoot,
  "build",
  "fixtures",
  "golden_queries.json",
);

/** Python sentence-transformers vs JS ONNX; use 0.99 with quantized: false in embedder. */
const PARITY_THRESHOLD = Number(process.env.EMBEDDING_PARITY_THRESHOLD ?? "0.99");

interface GoldenQuery {
  query: string;
  expectedAnyOf: string[];
}

function loadIndex(): IconIndexEntry[] {
  const raw = readFileSync(indexPath, "utf8");
  return JSON.parse(raw) as IconIndexEntry[];
}

function loadGoldenQueries(): GoldenQuery[] {
  const raw = readFileSync(goldenQueriesPath, "utf8");
  return JSON.parse(raw) as GoldenQuery[];
}

async function validateParity(index: IconIndexEntry[]): Promise<void> {
  const sample = index.slice(0, 5);
  let failures = 0;

  for (const icon of sample) {
    const runtimeVector = await getEmbedding(icon.description);
    const similarity = cosineSimilarity(runtimeVector, icon.vector);

    console.error(
      `  parity ${icon.name}: ${similarity.toFixed(4)} (need >= ${PARITY_THRESHOLD})`,
    );

    if (similarity < PARITY_THRESHOLD) {
      failures += 1;
    }
  }

  if (failures > 0) {
    throw new Error(
      `${failures} icon(s) failed Python/JS embedding parity check.`,
    );
  }
}

async function validateGoldenQueries(): Promise<void> {
  const goldenQueries = loadGoldenQueries();
  let failures = 0;

  for (const { query, expectedAnyOf } of goldenQueries) {
    const queryVector = await getEmbedding(query);
    const topMatches = searchIcons(queryVector, 5);
    const topNames = topMatches.map((match) => match.name);
    const hasExpected = expectedAnyOf.some((name) => topNames.includes(name));

    console.error(`  query "${query}" -> top: ${topNames.slice(0, 3).join(", ")}`);

    if (!hasExpected) {
      console.error(
        `    FAIL: expected one of [${expectedAnyOf.join(", ")}] in top 5`,
      );
      failures += 1;
    }
  }

  if (failures > 0) {
    throw new Error(`${failures} golden query check(s) failed.`);
  }
}

async function main(): Promise<void> {
  console.error("Validating vector index...");

  const index = loadIndex();

  if (index.length === 0) {
    throw new Error("vector_index.json is empty.");
  }

  console.error(`Loaded ${index.length} icons from ${indexPath}`);
  console.error("Checking embedding parity (Python build vs JS runtime)...");

  await validateParity(index);

  console.error("Checking golden queries...");
  await validateGoldenQueries();

  console.error("All validation checks passed.");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
