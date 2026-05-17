import { pipeline, type FeatureExtractionPipeline } from "@xenova/transformers";

const MODEL_ID = "Xenova/all-MiniLM-L6-v2";

let extractor: FeatureExtractionPipeline | null = null;

/** Must match Python `format_query_for_embedding` / passage prefix in build. */
export function formatQueryForEmbedding(query: string): string {
  const trimmed = query.trim();

  if (!trimmed) {
    return "query:";
  }

  return `query: ${trimmed}`;
}

export async function getEmbedding(text: string): Promise<number[]> {
  if (!extractor) {
    console.error(`Loading embedding model ${MODEL_ID} (first run may download ~22MB)...`);
    // Full-precision weights to match Python sentence-transformers build vectors.
    extractor = await pipeline("feature-extraction", MODEL_ID, {
      quantized: false,
    });
  }

  const output = await extractor(text, {
    pooling: "mean",
    normalize: true,
  });

  return Array.from(output.data as Float32Array);
}
