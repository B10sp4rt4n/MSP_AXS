import { useState } from "react";
import Preregistro from "./Preregistro";
import MostrarQR from "./MostrarQR";

export default function App() {
  const [qrData, setQrData] = useState(null);

  if (qrData) {
    return <MostrarQR qrData={qrData} onBack={() => setQrData(null)} />;
  }

  return <Preregistro onFinish={(data) => setQrData(data)} />;
}
