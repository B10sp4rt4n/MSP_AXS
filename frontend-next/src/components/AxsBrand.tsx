import Image from "next/image";

export default function AxsBrand() {
  return (
    <div className="flex w-[175px] shrink-0 flex-col items-center gap-2 text-center">
      <h1 className="w-full">
        <Image src="/brand/axs-logo-on-purple.svg" alt="AXS" width={175} height={64} priority className="block h-auto w-full" />
      </h1>
      <p className="w-full font-sans text-[11px] font-semibold uppercase leading-4 tracking-[0.14em] text-gray-300">
        Control de Acceso
      </p>
    </div>
  );
}
