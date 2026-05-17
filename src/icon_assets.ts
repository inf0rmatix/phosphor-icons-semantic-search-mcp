import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";

import type { IconIndexEntry, IconSearchResult, IconWeight } from "./types.js";
import { findIconByName } from "./vector_search.js";

const require = createRequire(import.meta.url);

/** package.json is not exported; resolve via a known SVG export path. */
const assetsRoot = dirname(
  dirname(require.resolve("@phosphor-icons/core/assets/regular/gear-six.svg")),
);

export async function getIconSvg(
  name: string,
  weight: IconWeight = "regular",
): Promise<string> {
  if (weight === "regular") {
    const indexed = findIconByName(name);

    if (indexed?.svg) {
      return indexed.svg;
    }
  }

  const fileName =
    weight === "regular" ? `${name}.svg` : `${name}-${weight}.svg`;
  const svgPath = join(assetsRoot, weight, fileName);

  return readFile(svgPath, "utf8");
}

const FLUTTER_ICON_CLASS: Record<IconWeight, string> = {
  thin: "PhosphorIconsThin",
  light: "PhosphorIconsLight",
  regular: "PhosphorIconsRegular",
  bold: "PhosphorIconsBold",
  fill: "PhosphorIconsFill",
  duotone: "PhosphorIconsDuotone",
};

function pascalToCamel(pascalName: string): string {
  if (!pascalName) {
    return pascalName;
  }

  return pascalName.charAt(0).toLowerCase() + pascalName.slice(1);
}

export function getReactHints(
  pascalName: string,
  weight: IconWeight = "regular",
): IconSearchResult["react"] {
  const weightProp = weight === "regular" ? "" : ` weight="${weight}"`;

  return {
    importLine: `import { ${pascalName} } from '@phosphor-icons/react';`,
    jsx: `<${pascalName}${weightProp} />`,
  };
}

export function getFlutterHints(
  pascalName: string,
  weight: IconWeight = "regular",
): IconSearchResult["flutter"] {
  const iconClass = FLUTTER_ICON_CLASS[weight];
  const iconReference = `${iconClass}.${pascalToCamel(pascalName)}`;

  return {
    importLine: "import 'package:phosphor_flutter/phosphor_flutter.dart';",
    widget: `PhosphorIcon(${iconReference})`,
  };
}

export async function toSearchResult(
  icon: IconIndexEntry,
  score: number,
  weight: IconWeight = "regular",
): Promise<IconSearchResult> {
  const svg = await getIconSvg(icon.name, weight);

  return {
    name: icon.name,
    pascalName: icon.pascalName,
    score,
    description: icon.description,
    svg,
    react: getReactHints(icon.pascalName, weight),
    flutter: getFlutterHints(icon.pascalName, weight),
    categories: icon.categories,
    tags: icon.tags,
  };
}
