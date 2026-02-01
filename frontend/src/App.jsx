import { useState } from "react";
import Preregistro from "./Preregistro";
import ModoGuardia from "./ModoGuardia";
import GuardiaApp from "./components/guardia/GuardiaApp";
import LoginGuardia from "./components/LoginGuardia";
import "./styles/guardia.css";

function App() {
  const [modo, setModo] = useState("menu"); // menu, preregistro, guardia, guardia-nueva
  const [usuarioAutenticado, setUsuarioAutenticado] = useState(null);
  const [token, setToken] = useState(null);
  
  // Handler para login exitoso
  const handleLoginSuccess = (userData, accessToken) => {
    setUsuarioAutenticado(userData);
    setToken(accessToken);
  };

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
  
  if (modo === "guardia-nueva") {
    // Si no hay usuario autenticado, mostrar login
    if (!usuarioAutenticado) {
      return <LoginGuardia onLoginSuccess={handleLoginSuccess} />;
    }
    
    // Si ya está autenticado, mostrar la app con datos reales
    return (
      <GuardiaApp 
        usuario={{
          nombre: usuarioAutenticado.nombre,
          rol: usuarioAutenticado.rol,
          tenant_nombre: usuarioAutenticado.tenant_nombre || "MSP Demo",
          usuario_id: usuarioAutenticado.usuario_id
        }}
        condominio={{
          id: usuarioAutenticado.condominio_id,
          nombre: usuarioAutenticado.condominio_nombre || "Sin condominio"
        }}
        token={token}
      />
    );
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
            gridTemplateColumns: "1fr 1fr 1fr",
            gap: "30px",
            maxWidth: "1000px",
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

          {/* Card Modo Guardia (Antiguo) */}
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
          
          {/* Card Nueva App Guardia */}
          <div
            onClick={() => setModo("guardia-nueva")}
            style={{
              background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
              borderRadius: "20px",
              padding: "40px 30px",
              cursor: "pointer",
              transition: "all 0.3s",
              boxShadow: "0 10px 30px rgba(0,0,0,0.2)",
              border: "3px solid white",
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
              ✨
            </div>
            <h2
              style={{
                fontSize: "24px",
                fontWeight: "bold",
                color: "white",
                marginBottom: "10px",
              }}
            >
              App Guardia PRO
            </h2>
            <p
              style={{
                color: "rgba(255,255,255,0.9)",
                fontSize: "15px",
                lineHeight: "1.5",
              }}
            >
              Nueva interfaz PWA con QR, compartir WhatsApp/SMS/Email/Slack
            </p>
            <div
              style={{
                marginTop: "15px",
                padding: "5px 15px",
                background: "rgba(255,255,255,0.2)",
                borderRadius: "20px",
                fontSize: "12px",
                color: "white",
                fontWeight: "bold",
              }}
            >
              🆕 NUEVO
            </div>
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
