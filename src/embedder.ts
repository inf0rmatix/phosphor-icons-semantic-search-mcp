import { pipeline, type FeatureExtractionPipeline } from "@xenova/transformers";

const MODEL_ID = "Xenova/all-MiniLM-L6-v2";

let extractor: FeatureExtractionPipeline | null = null;

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
