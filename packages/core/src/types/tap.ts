export type DeviceType = "ios" | "android" | "other" | "unknown";
export type InteractionType = "nfc" | "qr";

export interface Tap {
  id: string;
  tag_id: string;
  tenant_id: string;
  customer_id: string | null;
  device_type: DeviceType | null;
  interaction_type: InteractionType | null;
  action_taken: string | null;
  user_agent: string | null;
  ip_hash: string | null;
  created_at: string;
}
