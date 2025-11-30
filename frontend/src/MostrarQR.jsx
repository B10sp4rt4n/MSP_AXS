export default function MostrarQR({ qrData, onBack }) {
  return (
    <div style={styles.container}>
      <h1 style={styles.title}>Tu QR</h1>

      <img
        src={`data:image/png;base64,${qrData.qr_base64}`}
        style={styles.qr}
      />

      <button style={styles.button} onClick={onBack}>
        Regresar
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
    gap: 20,
  },
  title: {
    fontSize: 32,
    fontWeight: "bold",
  },
  qr: {
    width: 300,
    height: 300,
    border: "4px solid black",
  },
  button: {
    width: "90%",
    padding: 15,
    fontSize: 22,
    borderRadius: 10,
    background: "#2196F3",
    color: "white",
    border: "none",
    cursor: "pointer",
  },
};
