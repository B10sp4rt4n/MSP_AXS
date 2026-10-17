import Image from "next/image";
import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="flex flex-col items-center gap-6">
        <div className="text-center">
          <h1><Image src="/brand/axs-logo-on-purple.svg" alt="AXS" width={175} height={64} priority /></h1>
          <p className="text-gray-400 mt-1">Control de acceso para condominios</p>
        </div>
        <SignIn />
      </div>
    </div>
  );
}
