export interface Stamp {
  id: string;
  customer_id: string;
  tenant_id: string;
  tap_id: string | null;
  multiplier: number;
  awarded_by: "auto" | "manual";
  awarded_by_user: string | null;
  created_at: string;
}
