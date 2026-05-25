export type NfcTagFormat = "counter_stand" | "table_tent" | "wall_plaque" | "sticker";

export interface NfcTag {
  id: string;
  tenant_id: string;
  tag_uuid: string;
  format: NfcTagFormat | null;
  color: string | null;
  location_name: string | null;
  is_active: boolean;
  deployed_at: string | null;
  created_at: string;
}
