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

export const profileMatchSubmitSchema = z.object({
  age: z.number().int().min(18).max(70),
  education_level: z.enum(["ensino_medio", "tecnico", "graduacao", "mestrado", "doutorado"]),
  experience_years: z.number().int().min(0).max(45),
  english_level: z.enum(["A1", "A2", "B1", "B2", "C1", "C2"]),
  french_level: z.enum(["A1", "A2", "B1", "B2", "C1", "C2"]),
  savings_brl: z.number().min(0).max(10_000_000),
  monthly_income_brl: z.number().min(0).max(1_000_000),
  profession_area: z.enum([
    "tecnologia",
    "engenharia",
    "saude",
    "negocios",
    "educacao",
    "servicos",
    "outros"
  ]),
  has_job_offer: z.boolean(),
  has_family_abroad: z.boolean(),
  willing_to_learn_language: z.boolean(),
  wants_fast_citizenship: z.boolean(),
  preferred_region: z.enum(["americas", "europa", "asia", "indiferente"]),
  guest_session_id: z.string().trim().min(8).max(64)
});

export const profileMatchClaimSchema = z.object({
  submission_id: z.string().uuid(),
  guest_session_id: z.string().trim().min(8).max(64)
});
