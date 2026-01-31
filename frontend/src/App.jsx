import { useState } from "react";
import Preregistro from "./Preregistro";
import ModoGuardia from "./ModoGuardia";

function App() {
  const [modo, setModo] = useState("menu"); // menu, preregistro, guardia

  if (modo === "preregistro") {
    return (
      <>
        <button
          onClick={() => setModo("menu")}
          style={{
            position: "fixed",
            top: "20px",
            left: "20px",
            zIndex: 1000,
            padding: "10px 20px",
            background: "#667eea",
            color: "white",
            border: "none",
            borderRadius: "8px",
            cursor: "pointer",
            fontWeight: "bold",
          }}
        >
          ← Volver
        </button>
        <Preregistro />
      </>
    );
  }

  if (modo === "guardia") {
    return <ModoGuardia />;
  }

  // Menu Principal
  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "20px",
        fontFamily: "system-ui, -apple-system, sans-serif",
      }}
    >
      <div
        style={{
          textAlign: "center",
          maxWidth: "800px",
        }}
      >
        <h1
          style={{
            color: "white",
            fontSize: "48px",
            fontWeight: "bold",
            marginBottom: "20px",
            textShadow: "0 4px 6px rgba(0,0,0,0.3)",
          }}
        >
          MSP_AXS Control de Acceso
        </h1>
        <p
          style={{
            color: "white",
            fontSize: "18px",
            opacity: 0.9,
            marginBottom: "50px",
          }}
        >
          Selecciona el modo de operación
        </p>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "30px",
            maxWidth: "700px",
            margin: "0 auto",
          }}
        >
          {/* Card Preregistro */}
          <div
            onClick={() => setModo("preregistro")}
            style={{
              background: "white",
              borderRadius: "20px",
              padding: "40px 30px",
              cursor: "pointer",
              transition: "all 0.3s",
              boxShadow: "0 10px 30px rgba(0,0,0,0.2)",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = "translateY(-10px)";
              e.currentTarget.style.boxShadow = "0 20px 40px rgba(0,0,0,0.3)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = "translateY(0)";
              e.currentTarget.style.boxShadow = "0 10px 30px rgba(0,0,0,0.2)";
            }}
          >
            <div
              style={{
                fontSize: "60px",
                marginBottom: "20px",
              }}
            >
              📱
            </div>
            <h2
              style={{
                fontSize: "24px",
                fontWeight: "bold",
                color: "#1f2937",
                marginBottom: "10px",
              }}
            >
              Preregistro
            </h2>
            <p
              style={{
                color: "#6b7280",
                fontSize: "15px",
                lineHeight: "1.5",
              }}
            >
              Residentes crean QR para sus visitantes con anticipación
            </p>
          </div>

          {/* Card Modo Guardia */}
          <div
            onClick={() => setModo("guardia")}
            style={{
              background: "white",
              borderRadius: "20px",
              padding: "40px 30px",
              cursor: "pointer",
              transition: "all 0.3s",
              boxShadow: "0 10px 30px rgba(0,0,0,0.2)",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = "translateY(-10px)";
              e.currentTarget.style.boxShadow = "0 20px 40px rgba(0,0,0,0.3)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = "translateY(0)";
              e.currentTarget.style.boxShadow = "0 10px 30px rgba(0,0,0,0.2)";
            }}
          >
            <div
              style={{
                fontSize: "60px",
                marginBottom: "20px",
              }}
            >
              🛡️
            </div>
            <h2
              style={{
                fontSize: "24px",
                fontWeight: "bold",
                color: "#1f2937",
                marginBottom: "10px",
              }}
            >
              Modo Guardia
            </h2>
            <p
              style={{
                color: "#6b7280",
                fontSize: "15px",
                lineHeight: "1.5",
              }}
            >
              Guardias registran visitas rápidas sin preregistro (60% de casos)
            </p>
          </div>
        </div>

        <div
          style={{
            marginTop: "50px",
            color: "white",
            fontSize: "14px",
            opacity: 0.8,
          }}
        >
          v1.0 - Sistema de Control de Acceso Residencial
        </div>
      </div>
    </div>
  );
}

export default App;
