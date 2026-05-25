export interface Customer {
  id: string;
  tenant_id: string;
  phone: string | null;
  email: string | null;
  name: string | null;
  birthday: string | null;
  magic_link_token: string | null;
  gdpr_consent: boolean;
  gdpr_consent_at: string | null;
  gdpr_consent_text: string | null;
  total_visits: number;
  total_stamps: number;
  current_stamps: number;
  last_visit_at: string | null;
  created_at: string;
  updated_at: string;
}
