import { useState } from "react";

export default function Preregistro() {
  const [nombre, setNombre] = useState("");
  const [fecha, setFecha] = useState("");
  const [tipo, setTipo] = useState("Visita");
  const [placa, setPlaca] = useState("");
  const [notas, setNotas] = useState("");
  const [qrImg, setQrImg] = useState(null);

  // UI-AUP-02: Estados para manejo de respuestas AUP
  const [errorAUP, setErrorAUP] = useState(null);
  
  // UI-AUP-03: Estado para mostrar última acción registrada
  const [ultimaAccion, setUltimaAccion] = useState(null);

  // UI-AUP-01: Token mock temporal (en producción vendría de login real)
  const TOKEN_MOCK = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJ1c2VyMSJ9.MOCK";

  const generarQR = async () => {
    // Limpiar estados previos
    setErrorAUP(null);
    setQrImg(null);
    setUltimaAccion(null);

    try {
      const payload = {
        nombre_visitante: nombre,
        fecha_visita: new Date(fecha).toISOString(),
        tipo_visita: tipo,
        placa: placa || null,
        notas: notas || null
      };

      // UI-AUP-01: Cambio de endpoint y headers
      // - Endpoint: /preregistro/crear → /qr/generar_gobernado
      // - Removido: X-User-Id (bypasseaba AUP)
      // - Agregado: Authorization Bearer (cumple SESSION)
      const res = await fetch("http://0.0.0.0:8000/qr/generar_gobernado", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${TOKEN_MOCK}`
        },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      console.log("Respuesta backend:", data);

      // UI-AUP-02: Manejo explícito de respuestas AUP
      if (res.status === 401) {
        setErrorAUP("Sesión no válida o expirada. Acceso no autorizado.");
        setUltimaAccion({
          timestamp: new Date().toLocaleTimeString(),
          accion: "Generación de QR",
          resultado: "DENEGADA"
        });
        return;
      }

      if (res.status === 403) {
        setErrorAUP("Acceso denegado por política del condominio. Este intento fue registrado.");
        setUltimaAccion({
          timestamp: new Date().toLocaleTimeString(),
          accion: "Generación de QR",
          resultado: "DENEGADA"
        });
        return;
      }

      // UI-AUP-03: Registro de acción exitosa
      if (data.qr_base64) {
        setQrImg(`data:image/png;base64,${data.qr_base64}`);
        setUltimaAccion({
          timestamp: new Date().toLocaleTimeString(),
          accion: "Generación de QR",
          resultado: "AUTORIZADA"
        });
      }
    } catch (err) {
      console.error("Error generando QR:", err);
      setErrorAUP("Error de conexión con el servidor.");
    }
  };

  return (
    <div style={{ padding: 40, maxWidth: 400, margin: "auto" }}>
      <h1>Preregistro</h1>

      <input
        placeholder="Nombre del visitante"
        value={nombre}
        onChange={(e) => setNombre(e.target.value)}
      />

      <input
        type="datetime-local"
        value={fecha}
        onChange={(e) => setFecha(e.target.value)}
      />

      <select value={tipo} onChange={(e) => setTipo(e.target.value)}>
        <option value="Visita">Visita</option>
        <option value="Servicio">Servicio</option>
      </select>

      <input
        placeholder="Placas (opcional)"
        value={placa}
        onChange={(e) => setPlaca(e.target.value)}
      />

      <textarea
        placeholder="Notas"
        value={notas}
        onChange={(e) => setNotas(e.target.value)}
      ></textarea>

      <button onClick={generarQR}>Generar QR</button>

      {/* UI-AUP-02: Mensajes de error AUP visibles en UI */}
      {errorAUP && (
        <div style={{ 
          marginTop: 15, 
          padding: 15, 
          backgroundColor: "#ffebee", 
          border: "1px solid #c62828",
          borderRadius: 4,
          color: "#c62828"
        }}>
          <strong>⚠️ {errorAUP}</strong>
        </div>
      )}

      {/* UI-AUP-03: Evidencia de última acción registrada */}
      {ultimaAccion && (
        <div style={{ 
          marginTop: 15, 
          padding: 10, 
          backgroundColor: ultimaAccion.resultado === "AUTORIZADA" ? "#e8f5e9" : "#fff3e0",
          border: `1px solid ${ultimaAccion.resultado === "AUTORIZADA" ? "#4caf50" : "#ff9800"}`,
          borderRadius: 4,
          fontSize: 14
        }}>
          <strong>Última acción registrada:</strong><br />
          🕒 {ultimaAccion.timestamp} — {ultimaAccion.accion} ({ultimaAccion.resultado})
        </div>
      )}

      {qrImg && (
        <div style={{ marginTop: 20 }}>
          <h3>QR generado:</h3>
          <img src={qrImg} alt="QR" width={200} />
        </div>
      )}
    </div>
  );
}
