import { z } from "zod";

export const registerRequestSchema = z.object({
  email: z.string().trim().email(),
  password: z.string().min(8).max(128)
});

export const loginRequestSchema = registerRequestSchema;

export const assessmentCreateSchema = z.object({
  program_id: z.string().uuid(),
  profile_json: z.record(z.string(), z.unknown()),
  idempotency_key: z.string().trim().min(1).max(128)
});

export const roadmapCreateSchema = z.object({
  assessment_id: z.string().uuid(),
  idempotency_key: z.string().trim().min(1).max(128).optional()
});

export const checkoutSessionCreateSchema = z.object({
  plan_code: z.string().trim().min(1).max(32),
  success_url: z.string().url().max(2048),
  cancel_url: z.string().url().max(2048)
});
