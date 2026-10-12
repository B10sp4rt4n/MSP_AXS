import { clerkMiddleware } from "@clerk/nextjs/server";

export default clerkMiddleware({
  frontendApiProxy: { enabled: true },
});

export const config = {
  matcher: ["/__clerk/:path*", "/((?!.*\\..*|_next).*)", "/", "/(api|trpc)(.*)"],
};
