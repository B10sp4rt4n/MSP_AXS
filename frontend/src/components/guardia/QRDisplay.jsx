import React, { useState, useEffect } from 'react';

const QRDisplay = ({ qrData, visita, onCompartir, deviceType }) => {
  const [qrImage, setQrImage] = useState(null);
  
  useEffect(() => {
    if (qrData?.qr_base64) {
      setQrImage(`data:image/png;base64,${qrData.qr_base64}`);
    }
  }, [qrData]);
  
  const descargarQR = () => {
    if (!qrImage) return;
    
    const link = document.createElement('a');
    link.href = qrImage;
    link.download = `QR_${visita.nombre_visitante || 'Visitante'}_${new Date().getTime()}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };
  
  const imprimirQR = () => {
    if (!qrImage) return;
    
    // Calcular fecha de validez (del QR o 24h desde ahora)
    const fechaValidez = qrData?.qr_vigencia 
      ? new Date(qrData.qr_vigencia).toLocaleString('es-CO')
      : new Date(Date.now() + 24*60*60*1000).toLocaleString('es-CO');
    
    const ventana = window.open('', '_blank');
    ventana.document.write(`
      <html>
        <head>
          <title>Código QR - ${visita.nombre_visitante || 'Visitante'}</title>
          <style>
            body {
              display: flex;
              flex-direction: column;
              align-items: center;
              justify-content: center;
              min-height: 100vh;
              margin: 0;
              font-family: Arial, sans-serif;
            }
            h1 { font-size: 24px; margin-bottom: 10px; }
            .info { margin: 20px 0; text-align: center; }
            img { max-width: 400px; border: 2px solid #333; }
          </style>
        </head>
        <body>
          <h1>Código de Acceso</h1>
          <div class="info">
            <p><strong>Visitante:</strong> ${visita.nombre_visitante || 'N/A'}</p>
            <p><strong>Casa/Unidad:</strong> ${visita.casa_unidad || 'N/A'}</p>
            <p><strong>Válido hasta:</strong> ${fechaValidez}</p>
            <p><strong>Código:</strong> ${qrData.codigo_alfanumerico || qrData.token || 'N/A'}</p>
          </div>
          <img src="${qrImage}" alt="Código QR" />
          <script>
            window.onload = function() {
              window.print();
              window.onafterprint = function() {
                window.close();
              };
            };
          </script>
        </body>
      </html>
    `);
    ventana.document.close();
  };
  
  if (!qrData || !qrImage) {
    return (
      <div className="qr-display loading">
        <div className="spinner"></div>
        <p>Generando código QR...</p>
      </div>
    );
  }
  
  // Calcular fecha de validez
  const fechaValidez = qrData?.qr_vigencia 
    ? new Date(qrData.qr_vigencia)
    : new Date(Date.now() + 24*60*60*1000);
  
  return (
    <div className={`qr-display ${deviceType}`}>
      <div className="qr-header">
        <h2>✅ Código Generado</h2>
        <div className="badge badge-success">ACTIVO</div>
      </div>
      
      <div className="visitor-info">
        <div className="info-row">
          <span className="label">👤 Visitante:</span>
          <span className="value">{visita.nombre_visitante || 'N/A'}</span>
        </div>
        <div className="info-row">
          <span className="label">🏠 Casa/Unidad:</span>
          <span className="value">{visita.casa_unidad || 'N/A'}</span>
        </div>
        <div className="info-row">
          <span className="label">📞 Teléfono:</span>
          <span className="value">{visita.telefono || 'N/A'}</span>
        </div>
        <div className="info-row">
          <span className="label">⏰ Válido hasta:</span>
          <span className="value">
            {fechaValidez.toLocaleString('es-CO', {
              dateStyle: 'short',
              timeStyle: 'short'
            })}
          </span>
        </div>
      </div>
      
      <div className="qr-container">
        <img src={qrImage} alt="Código QR" className="qr-image" />
        
        <div className="codigo-manual">
          <p className="codigo-label">Código manual:</p>
          <div className="codigo-value">{qrData.codigo_alfanumerico || qrData.token || 'N/A'}</div>
          <p className="codigo-hint">
            Si no puede escanear el QR, ingrese este código
          </p>
        </div>
      </div>
      
      <div className="qr-actions">
        <button
          className="btn btn-outline"
          onClick={descargarQR}
        >
          💾 Descargar
        </button>
        
        <button
          className="btn btn-outline"
          onClick={imprimirQR}
        >
          🖨️ Imprimir
        </button>
        
        <button
          className="btn btn-primary"
          onClick={() => onCompartir('mostrar')}
        >
          📤 Compartir
        </button>
      </div>
    </div>
  );
};

export default QRDisplay;
