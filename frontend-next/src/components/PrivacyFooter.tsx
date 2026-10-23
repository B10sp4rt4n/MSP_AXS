import Link from "next/link";
import { ARCO_PATH } from "@/lib/privacidad";

export default function PrivacyFooter() {
  return (
    <footer className="mt-auto border-t border-gray-800 bg-gray-950 px-6 py-5 text-sm text-gray-300">
      <nav aria-label="Privacidad y datos personales" className="mx-auto flex max-w-4xl flex-wrap items-center justify-center gap-x-6 gap-y-3">
        <Link href={ARCO_PATH} className="underline underline-offset-4 hover:text-white focus-visible:outline-2 focus-visible:outline-purple-400">
          Privacidad y derechos ARCO
        </Link>
        <Link href="/privacidad" className="underline underline-offset-4 hover:text-white focus-visible:outline-2 focus-visible:outline-purple-400">
          Aviso de Alexa
        </Link>
      </nav>
    </footer>
  );
}
