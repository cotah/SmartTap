import { z } from "zod";

const irishPhoneRegex = /^\+353[1-9]\d{6,9}$/;

export const customerIdentifySchema = z.object({
  tenant_id: z.string().uuid(),
  phone: z.string().regex(irishPhoneRegex, "Use Irish format: +353..."),
  name: z.string().min(1).max(80).optional(),
  birthday: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/, "Format YYYY-MM-DD")
    .optional(),
  gdpr_consent: z.literal(true, {
    errorMap: () => ({ message: "Consent is required to sign up" }),
  }),
  gdpr_consent_text: z.string().min(10).max(2000),
});

export type CustomerIdentify = z.infer<typeof customerIdentifySchema>;
