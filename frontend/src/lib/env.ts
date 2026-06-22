import { z } from "zod";

const clientEnvSchema = z.object({
  NEXT_PUBLIC_API_BASE_URL: z.string().url()
});

const parsedEnv = clientEnvSchema.safeParse({
  NEXT_PUBLIC_API_BASE_URL:
    process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1"
});

if (!parsedEnv.success) {
  throw new Error("Invalid NEXT_PUBLIC_API_BASE_URL");
}

const forbiddenPublicSecrets = [
  process.env.NEXT_PUBLIC_STRIPE_SECRET_KEY,
  process.env.NEXT_PUBLIC_SERVICE_ROLE_KEY,
  process.env.NEXT_PUBLIC_SERVICE_KEY
];

if (forbiddenPublicSecrets.some((value) => Boolean(value))) {
  throw new Error(
    "Sensitive key detected in NEXT_PUBLIC_* env. Use only anon/public keys on frontend."
  );
}

export const PUBLIC_API_BASE_URL = parsedEnv.data.NEXT_PUBLIC_API_BASE_URL;
