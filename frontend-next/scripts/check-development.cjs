// Development deployment gate: no secret values are printed.
const env = process.env;
const expectedApi = "https://axs-development-backend-production.up.railway.app";

if (env.APP_ENV !== "development" || env.NEXT_PUBLIC_API_URL !== expectedApi) {
  console.error("Development API URL and APP_ENV required");
  process.exit(1);
}
if (!env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY?.startsWith("pk_test_") ||
    !env.CLERK_SECRET_KEY?.startsWith("sk_test_")) {
  console.error("Clerk development keys required");
  process.exit(1);
}
console.log("Development frontend configuration verified");
