import AxsBrand from "@/components/AxsBrand";
import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="flex flex-col items-center gap-6">
        <AxsBrand />
        <SignIn />
      </div>
    </div>
  );
}
