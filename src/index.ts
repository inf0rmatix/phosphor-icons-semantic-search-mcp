#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

import { getIconSvg, getReactHints, toSearchResult } from "./icon_assets.js";
import type { IconWeight } from "./types.js";
import { getEmbedding } from "./embedder.js";
import { findIconByName, searchIcons } from "./vector_search.js";

const iconWeightSchema = z.enum([
  "thin",
  "light",
  "regular",
  "bold",
  "fill",
  "duotone",
]);

const server = new McpServer(
  {
    name: "phosphor-icons-semantic-search",
    version: "0.1.0",
  },
  {
    instructions:
      "Use search_icons for intent-based Phosphor icon lookup (e.g. settings menu, logout). Prefer regular weight unless the user asks for bold, fill, or duotone.",
  },
);

async function formatIconResult(
  icon: NonNullable<ReturnType<typeof findIconByName>>,
  score: number,
  weight: IconWeight,
) {
  const result = await toSearchResult(icon, score, weight);

  return {
    name: result.name,
    score: Number(result.score.toFixed(4)),
    description: result.description,
    svg: result.svg,
    react: result.react,
    categories: result.categories,
    tags: result.tags,
  };
}

server.registerTool(
  "search_icons",
  {
    description:
      "Semantic search for Phosphor icons by visual appearance, concept, or UI intent.",
    inputSchema: {
      query: z.string().describe("Natural language description of the icon you need"),
      limit: z
        .number()
        .int()
        .min(1)
        .max(20)
        .optional()
        .describe("Maximum number of results (default 5)"),
      weight: iconWeightSchema
        .optional()
        .describe("SVG weight variant (default regular)"),
    },
  },
  async ({ query, limit, weight }) => {
    const topK = limit ?? 5;
    const iconWeight = weight ?? "regular";
    const queryVector = await getEmbedding(query);
    const matches = searchIcons(queryVector, topK);
    const results = await Promise.all(
      matches.map((match) => formatIconResult(match, match.score, iconWeight)),
    );

    return {
      content: [
        {
          type: "text" as const,
          text: JSON.stringify({ query, results }, null, 2),
        },
      ],
    };
  },
);

server.registerTool(
  "get_icon",
  {
    description: "Fetch a Phosphor icon by exact kebab-case name.",
    inputSchema: {
      name: z.string().describe("Icon name in kebab-case, e.g. gear-six"),
      weight: iconWeightSchema
        .optional()
        .describe("SVG weight variant (default regular)"),
    },
  },
  async ({ name, weight }) => {
    const iconWeight = weight ?? "regular";
    const icon = findIconByName(name);

    if (!icon) {
      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify({ error: `Icon not found: ${name}` }),
          },
        ],
        isError: true,
      };
    }

    const svg = await getIconSvg(name, iconWeight);
    const react = getReactHints(icon.pascalName, iconWeight);

    return {
      content: [
        {
          type: "text" as const,
          text: JSON.stringify(
            {
              name: icon.name,
              pascalName: icon.pascalName,
              description: icon.description,
              svg,
              react,
              categories: icon.categories,
              tags: icon.tags,
            },
            null,
            2,
          ),
        },
      ],
    };
  },
);

async function main(): Promise<void> {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("phosphor-icons-semantic-search-mcp running on stdio");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
