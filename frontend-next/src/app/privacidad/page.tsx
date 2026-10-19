import type { Metadata } from "next";
import AxsBrand from "@/components/AxsBrand";

export const metadata: Metadata = {
  title: "Privacidad de AXS Condominios y Alexa",
  description: "Datos y preferencias de la integración de AXS Condominios con Amazon Alexa.",
  robots: { index: false, follow: false },
  alternates: { canonical: "https://app.axs-mx.com/privacidad" },
};

const responsable = "Sinapsis Aplicaciones y Sistemas";
const domicilio = "Sierra Nevada 755, Col. Lomas de Chapultepec I Sección, Miguel Hidalgo, C.P. 11000, Ciudad de México, México";
const contacto = "sruiz@synappssys.com";

export default function PrivacidadPage() {
  return <div className="min-h-screen bg-gray-950 text-gray-100">
    <header className="border-b border-gray-800 px-6 py-5"><AxsBrand /></header>
    <main className="mx-auto max-w-3xl space-y-7 px-6 py-10 leading-relaxed">
      <h1 className="text-3xl font-semibold">Aviso de privacidad: AXS Condominios y Alexa</h1>
      <p className="text-sm text-gray-400">Última actualización: 18 de octubre de 2026.</p>
      <p>Este aviso describe la integración opcional de AXS Condominios con Amazon Alexa. El control de acceso del condominio y las fotografías de identificación requieren su propio aviso y condiciones; este documento no los sustituye.</p>
      <section className="space-y-3"><h2 className="text-xl font-semibold">Responsable y contacto</h2>
        <p>Responsable de la integración: {responsable}, bajo la marca SynAppsSys. Domicilio: {domicilio}.</p>
        <p>Atención de privacidad: Salvador Ruiz Esparza. Correo: <a className="text-purple-300 underline break-all" href={`mailto:${contacto}`}>{contacto}</a>.</p>
      </section>
      <section className="space-y-3"><h2 className="text-xl font-semibold">Datos utilizados y finalidades</h2>
        <p>Para relacionar la cuenta de Alexa con el residente, AXS utiliza identificadores de cuenta Amazon y AXS, identidad de inicio de sesión, condominio y vivienda asignados, así como permisos, suscripciones y fechas de vinculación o baja. También registra eventos técnicos de consulta y cambios de preferencias.</p>
        <p>Estos datos permiten verificar la vivienda y los permisos vigentes, enviar avisos de movimientos confirmados, responder consultas por voz y conservar trazabilidad de la operación. La consulta actual comunica el nombre de la visita, si entró o salió y la hora del último movimiento de la vivienda registrado durante las últimas 24 horas.</p>
        <p>Los avisos proactivos son genéricos. Al consultar por voz, el nombre y la hora se envían a Amazon para generar la respuesta; otras personas próximas al dispositivo pueden escucharla. Esta integración no envía fotografías de identificaciones ni datos biométricos a Alexa, ni permite abrir el portón o autorizar el acceso por voz.</p>
        <p>La integración no solicita datos personales sensibles. La vinculación de cuentas y las notificaciones son opcionales y requieren las autorizaciones correspondientes. La skill no incorpora finalidades publicitarias ni de prospección comercial.</p>
      </section>
      <section className="space-y-3"><h2 className="text-xl font-semibold">Proveedores y tratamiento de información</h2>
        <p>Amazon procesa la interacción con Alexa conforme a sus propias condiciones y aviso de privacidad. Clerk interviene en la autenticación de AXS. La infraestructura utilizada incluye Neon, Railway y Vercel; el tratamiento puede realizarse fuera de México. El contenido de la consulta se comunica a Amazon para prestar la función solicitada.</p>
        <p>AXS utiliza el vínculo para las funciones descritas. La skill actual no incorpora compras ni publicidad. Guardar un correo Amazon en el perfil de AXS es una referencia opcional: no verifica la cuenta ni vincula Alexa.</p>
      </section>
      <section className="space-y-3"><h2 className="text-xl font-semibold">Opcionalidad, desvinculación y conservación</h2>
        <p>Puedes desactivar la skill o retirar permisos desde Alexa. Para solicitar la baja del vínculo en AXS, usa el contacto de privacidad. Dejar de usar Alexa no impide utilizar el control de acceso de AXS.</p>
        <p>Desactivar la skill no elimina automáticamente los registros de visitas ni la trazabilidad previa. Las solicitudes de eliminación se evalúan según su finalidad, obligaciones de conservación y derechos de terceros. La ventana de consulta de 24 horas no es un plazo de borrado. Los datos que Amazon conserva se gestionan mediante sus propios controles de privacidad.</p>
        <p>Los datos del vínculo se utilizan mientras la función esté activa; después de la baja puede conservarse la información necesaria para acreditar preferencias, atender solicitudes y determinar responsabilidades. Cuando los datos dejen de ser necesarios, corresponde su bloqueo y supresión conforme a las obligaciones aplicables.</p>
      </section>
      <section className="space-y-3"><h2 className="text-xl font-semibold">Derechos y solicitudes</h2>
        <p>Para solicitar acceso, rectificación, cancelación u oposición, revocar tu consentimiento o limitar el uso de tus datos, escribe al contacto de privacidad indicando el derecho que deseas ejercer, los datos afectados y un medio de respuesta. Se verificará tu identidad mediante un canal adecuado antes de atender la solicitud; no envíes contraseñas ni códigos de acceso.</p>
        <p>Las solicitudes sobre los registros del condominio se canalizarán también con su administración cuando corresponda.</p>
      </section>
      <section className="space-y-3"><h2 className="text-xl font-semibold">Cambios al aviso</h2>
        <p>Los cambios se comunicarán en esta página mediante la fecha de actualización. Si se requieren nuevas finalidades o permisos, se solicitará la autorización que corresponda.</p>
      </section>
    </main>
  </div>;
}
