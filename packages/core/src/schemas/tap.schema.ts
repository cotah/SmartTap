import { z } from "zod";

export const tapEventSchema = z.object({
  magic_link_token: z.string().uuid().optional(),
  device_type: z.enum(["ios", "android", "other", "unknown"]).optional(),
  interaction_type: z.enum(["nfc", "qr"]).default("nfc"),
});

export type TapEvent = z.infer<typeof tapEventSchema>;
