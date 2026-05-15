export type IconWeight =
  | "thin"
  | "light"
  | "regular"
  | "bold"
  | "fill"
  | "duotone";

export interface IconIndexEntry {
  name: string;
  pascalName: string;
  description: string;
  vector: number[];
  svg: string;
  categories?: readonly string[];
  tags?: readonly string[];
}

export interface IconSearchResult {
  name: string;
  pascalName: string;
  score: number;
  description: string;
  svg: string;
  react: {
    importLine: string;
    jsx: string;
  };
  categories?: readonly string[];
  tags?: readonly string[];
}
