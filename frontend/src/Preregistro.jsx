import { useState } from "react";

export default function Preregistro() {
  const [nombre, setNombre] = useState("");
  const [fecha, setFecha] = useState("");
  const [tipo, setTipo] = useState("Visita");
  const [placa, setPlaca] = useState("");
  const [notas, setNotas] = useState("");
  const [qrImg, setQrImg] = useState(null);

  const generarQR = async () => {
    try {
      const payload = {
        nombre_visitante: nombre,
        fecha_visita: new Date(fecha).toISOString(),
        tipo_visita: tipo,
        placa: placa || null,
        notas: notas || null
      };

      const res = await fetch("http://0.0.0.0:8000/preregistro/crear", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-User-Id": "1"
        },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      console.log("Respuesta backend:", data);

      if (data.qr_base64) {
        setQrImg(`data:image/png;base64,${data.qr_base64}`);
      }
    } catch (err) {
      console.error("Error generando QR:", err);
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

      {qrImg && (
        <div style={{ marginTop: 20 }}>
          <h3>QR generado:</h3>
          <img src={qrImg} alt="QR" width={200} />
        </div>
      )}
    </div>
  );
}
