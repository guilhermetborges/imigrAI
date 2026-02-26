const forbiddenPattern = /(SECRET|SERVICE_ROLE|PRIVATE|PASSWORD)/i;
const exposedKeys = Object.keys(process.env).filter((key) =>
  key.startsWith("NEXT_PUBLIC_")
);

const forbidden = exposedKeys.filter((key) => forbiddenPattern.test(key));
if (forbidden.length > 0) {
  throw new Error(
    `Sensitive key name detected in public env: ${forbidden.join(", ")}`
  );
}

if (!process.env.NEXT_PUBLIC_API_BASE_URL) {
  console.warn(
    "NEXT_PUBLIC_API_BASE_URL not explicitly set. Falling back to frontend default."
  );
}
