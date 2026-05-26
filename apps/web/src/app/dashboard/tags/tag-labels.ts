/**
 * Human-readable labels for the format/color Literals. Keeping them in a
 * server-importable file lets both the list page (Server Component) and
 * the form (Client Component) share one source of truth — change the
 * label once and it updates everywhere.
 */

import type { NfcTagColor, NfcTagFormat } from "@/lib/api";

export const FORMAT_LABELS: Record<NfcTagFormat, string> = {
  counter_stand: "Counter stand",
  table_tent: "Table tent",
  wall_plaque: "Wall plaque",
  sticker: "Sticker",
};

export const COLOR_LABELS: Record<NfcTagColor, string> = {
  black: "Black",
  white: "White",
  grey: "Grey",
  navy: "Navy",
  purple: "Purple",
  red: "Red",
  yellow: "Yellow",
  stone_age: "Stone Age",
  real_green: "Real Green",
  forest_green: "Forest Green",
};

/** CSS-safe swatch colour for each PLA filament, used for the colour dot
 * on cards and in the form. Stone Age and the greens are approximations
 * — the real filament is more textured. */
export const COLOR_SWATCH: Record<NfcTagColor, string> = {
  black: "#1A1A1A",
  white: "#F7F5F0",
  grey: "#808080",
  navy: "#1F3A5F",
  purple: "#6B2D8C",
  red: "#B33A3A",
  yellow: "#E8C020",
  stone_age: "#9C8B7A",
  real_green: "#2E8B3E",
  forest_green: "#1B4D2E",
};

export const FORMAT_OPTIONS: NfcTagFormat[] = [
  "counter_stand",
  "table_tent",
  "wall_plaque",
  "sticker",
];

export const COLOR_OPTIONS: NfcTagColor[] = [
  "black",
  "white",
  "grey",
  "navy",
  "purple",
  "red",
  "yellow",
  "stone_age",
  "real_green",
  "forest_green",
];
