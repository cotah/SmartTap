import { ApiError, createApiClient, type ApiClient } from "@smarttap/api";
import { publicEnv } from "./env";

let cached: ApiClient | null = null;

export function getApiClient(): ApiClient {
  if (cached === null) {
    cached = createApiClient({ baseUrl: publicEnv.NEXT_PUBLIC_API_URL });
  }
  return cached;
}

export { ApiError };
export type {
  TapResponse,
  TenantPublic,
  CustomerSnapshot,
  RewardStateSnapshot,
  RewardAvailable,
  IdentifyResponse,
} from "@smarttap/api";
