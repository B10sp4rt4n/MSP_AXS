import { useState } from "react";

export default function Preregistro({ onFinish }) {
  const [nombre, setNombre] = useState("");
  const [fecha, setFecha] = useState("");
  const [tipo, setTipo] = useState("Visita");
  const [placa, setPlaca] = useState("");
  const [notas, setNotas] = useState("");

  const API = "http://0.0.0.0:8000/preregistro/crear";

  async function generarQR() {
    const payload = {
      nombre_visitante: nombre,
      fecha_visita: fecha,
      tipo_visita: tipo,
      placa,
      notas,
    };

    const res = await fetch(API, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-User-Id": "1",
      },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    onFinish(data);
  }

  return (
    <div style={styles.container}>
      <h1 style={styles.title}>Preregistro</h1>

      <input
        style={styles.input}
        placeholder="Nombre del visitante"
        value={nombre}
        onChange={(e) => setNombre(e.target.value)}
      />

      <input
        style={styles.input}
        type="datetime-local"
        value={fecha}
        onChange={(e) => setFecha(e.target.value)}
      />

      <select style={styles.input} value={tipo} onChange={(e) => setTipo(e.target.value)}>
        <option value="Visita">Visita</option>
        <option value="Proveedor">Proveedor</option>
      </select>

      <input
        style={styles.input}
        placeholder="Placas (opcional)"
        value={placa}
        onChange={(e) => setPlaca(e.target.value)}
      />

      <textarea
        style={styles.input}
        placeholder="Notas (opcional)"
        value={notas}
        onChange={(e) => setNotas(e.target.value)}
      />

      <button style={styles.button} onClick={generarQR}>
        Generar QR
      </button>
    </div>
  );
}

const styles = {
  container: {
    padding: 30,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 15,
  },
  title: {
    fontSize: 32,
    fontWeight: "bold",
  },
  input: {
    width: "90%",
    padding: 12,
    fontSize: 20,
    borderRadius: 8,
    border: "2px solid #ccc",
  },
  button: {
    width: "90%",
    padding: 15,
    fontSize: 22,
    borderRadius: 10,
    background: "#4CAF50",
    color: "white",
    border: "none",
    cursor: "pointer",
  },
};
