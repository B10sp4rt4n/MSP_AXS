import AxsBrand from "@/components/AxsBrand";
import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="flex flex-col items-center gap-6">
        <AxsBrand />
        <SignUp />
      </div>
    </div>
  );
}
