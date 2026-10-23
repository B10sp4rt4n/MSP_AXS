import type { Metadata } from "next";
import Link from "next/link";
import AxsBrand from "@/components/AxsBrand";
import { ARCO_FECHA, ARCO_VERSION, PRIVACIDAD_CONTACTO } from "@/lib/privacidad";

export const metadata: Metadata = {
  title: "Privacidad y derechos ARCO | AXS",
  description: "Cómo solicitar acceso, rectificación, cancelación u oposición al tratamiento de tus datos personales en AXS.",
  robots: { index: false, follow: false },
  alternates: { canonical: "https://app.axs-mx.com/privacidad/arco" },
};

const derechos = [
  { nombre: "Acceso", descripcion: "Conocer qué datos personales se tienen sobre ti y cómo se utilizan." },
  { nombre: "Rectificación", descripcion: "Pedir que se corrijan tus datos cuando sean incorrectos, incompletos o estén desactualizados." },
  { nombre: "Cancelación", descripcion: "Solicitar que tus datos dejen de tratarse y se eliminen cuando corresponda. Puede existir un periodo de bloqueo o una obligación de conservación aplicable." },
  { nombre: "Oposición", descripcion: "Solicitar que cese un tratamiento de tus datos por una causa legítima, en los supuestos que permite la ley." },
];

export default function DerechosArcoPage() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-gray-800 px-6 py-5">
        <AxsBrand />
        <Link href="/dashboard" className="rounded-lg border border-gray-700 px-4 py-2 text-sm hover:bg-gray-800 focus-visible:outline-2 focus-visible:outline-purple-400">
          Ir al portal
        </Link>
      </header>
      <main className="mx-auto max-w-3xl space-y-8 px-6 py-10 leading-relaxed">
        <div className="space-y-3">
          <p className="text-sm font-medium text-purple-300">Tus datos personales</p>
          <h1 className="text-3xl font-semibold">Privacidad y derechos ARCO</h1>
          <p className="text-sm text-gray-400">Versión {ARCO_VERSION}. Actualización: {ARCO_FECHA}.</p>
          <p>Puedes solicitar acceso, rectificación, cancelación u oposición al tratamiento de tus datos personales. Este canal está disponible para visitantes, residentes y personal, sin necesidad de iniciar sesión ni contratar un plan.</p>
        </div>

        <section aria-labelledby="derechos" className="space-y-4">
          <h2 id="derechos" className="text-xl font-semibold">Qué puedes solicitar</h2>
          <dl className="grid gap-4 sm:grid-cols-2">
            {derechos.map((derecho) => (
              <div key={derecho.nombre} className="rounded-xl border border-gray-800 bg-gray-900 p-5">
                <dt className="font-semibold text-purple-300">{derecho.nombre}</dt>
                <dd className="mt-2 text-sm text-gray-300">{derecho.descripcion}</dd>
              </div>
            ))}
          </dl>
          <p>También puedes solicitar la revocación de tu consentimiento o limitar el uso o divulgación de tus datos. Estas solicitudes son distintas de dar de baja una cuenta o desvincular Alexa.</p>
        </section>

        <section aria-labelledby="solicitud" className="space-y-3 rounded-xl border border-purple-800 bg-purple-950/30 p-6">
          <h2 id="solicitud" className="text-xl font-semibold">Cómo presentar tu solicitud</h2>
          <p>Escribe a <a href={`mailto:${PRIVACIDAD_CONTACTO}`} className="break-all text-purple-300 underline underline-offset-4">{PRIVACIDAD_CONTACTO}</a>. Atención de privacidad: Salvador Ruiz Esparza, SynAppsSys.</p>
          <ol className="list-decimal space-y-2 pl-5">
            <li>Indica tu nombre y un medio para recibir la respuesta.</li>
            <li>Explica qué deseas solicitar. Si buscas corregir datos, señala la corrección y los elementos que la sustenten.</li>
            <li>Si los conoces, indica el condominio o la empresa, la fecha aproximada de visita o la referencia del registro para localizar tus datos. No necesitas conocer un identificador interno.</li>
          </ol>
          <p className="text-sm text-gray-300">Se te indicará un medio adecuado para acreditar tu identidad y, en su caso, la representación. No envíes contraseñas, códigos de acceso ni fotografías de identificaciones en el primer correo.</p>
          <p className="text-sm text-gray-300">El enlace abre tu aplicación de correo. La solicitud se recibe cuando envías el mensaje; esta página no genera un folio ni ejecuta un borrado automático.</p>
          <a href={`mailto:${PRIVACIDAD_CONTACTO}`} className="inline-flex min-h-11 items-center rounded-lg bg-purple-600 px-4 py-3 font-medium text-white hover:bg-purple-500 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-purple-300">
            Abrir correo de privacidad
          </a>
        </section>

        <section aria-labelledby="responsable" className="space-y-3">
          <h2 id="responsable" className="text-xl font-semibold">Quién atiende tus datos</h2>
          <p>Sinapsis Aplicaciones y Sistemas, bajo la marca SynAppsSys, atiende este canal. Para los datos de la integración Alexa consulta su <Link href="/privacidad" className="text-purple-300 underline">aviso de privacidad</Link>.</p>
          <p>Para registros de visitas, fotografías y movimientos, se identificará al responsable del tratamiento conforme al aviso del condominio o empresa que recabó tus datos. Cuando corresponda, SynAppsSys apoyará su localización y atención como proveedor de la plataforma. Si no sabes quién es el responsable, indícalo al escribir y te orientaremos.</p>
          <p>Esta guía no sustituye el aviso de cada responsable ni extiende el aviso de Alexa a las fotografías de identificación.</p>
        </section>

        <section aria-labelledby="respuesta" className="space-y-3">
          <h2 id="respuesta" className="text-xl font-semibold">Respuesta y seguimiento</h2>
          <p>La atención se realiza por personal autorizado mediante el canal de privacidad. El ejercicio de tus derechos es gratuito; solo pueden aplicar los costos de reproducción o envío permitidos por la ley.</p>
          <p>Para responsables privados en México, la ley prevé comunicar la determinación en un máximo de 20 días hábiles desde la recepción de la solicitud y, si procede, hacerla efectiva dentro de los 15 días hábiles siguientes a la respuesta. Los plazos pueden ampliarse una sola vez por un periodo igual cuando las circunstancias lo justifiquen.</p>
          <p>El responsable te comunicará la decisión y sus motivos, incluidas las restricciones que correspondan. La entrega de datos requiere verificar tu identidad y proteger información de terceros.</p>
        </section>

        <section aria-labelledby="conservacion" className="space-y-3">
          <h2 id="conservacion" className="text-xl font-semibold">Fotografías, movimientos y conservación</h2>
          <p>Puedes incluir en tu solicitud tus datos de perfil, fotografías de identificación, registros de visita y movimientos. Cada categoría requiere revisar su finalidad y el plazo de conservación aplicable.</p>
          <p>Una solicitud de cancelación no siempre implica eliminación inmediata: puede corresponder bloquear los datos y conservarlos de forma restringida para atender responsabilidades antes de suprimirlos. Cualquier excepción debe tener fundamento; la auditoría no justifica por sí sola conservar información personal indefinidamente.</p>
          <p>El cierre de una visita, la baja de una cuenta o desactivar Alexa no equivalen a solicitar la cancelación. La ventana de consulta de Alexa de 24 horas tampoco determina cuándo se borran los datos. La atención considerará las copias y los proveedores que corresponda, y se te informará el alcance de las acciones.</p>
        </section>

        <section aria-labelledby="fundamento" className="space-y-3 text-sm text-gray-400">
          <h2 id="fundamento" className="text-xl font-semibold text-gray-100">Marco de referencia</h2>
          <p>Ley Federal de Protección de Datos Personales en Posesión de los Particulares, artículos 21 a 34. Consulta el <a href="https://www.diputados.gob.mx/LeyesBiblio/ref/lfpdppp.htm" className="text-purple-300 underline">índice oficial de la ley y sus reformas</a>.</p>
          <p>Las actualizaciones de este procedimiento se identificarán con su versión y fecha en esta página.</p>
        </section>
      </main>
    </div>
  );
}
