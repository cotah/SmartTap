export interface Reward {
  id: string;
  customer_id: string;
  tenant_id: string;
  stamps_used: number;
  description: string;
  validation_code: string;
  expires_at: string;
  redeemed_at: string | null;
  redeemed_by_user: string | null;
  created_at: string;
}
