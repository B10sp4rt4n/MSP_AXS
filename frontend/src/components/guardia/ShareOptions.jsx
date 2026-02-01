import React, { useState } from 'react';
import guardiaApi from '../../services/guardiaApi';

const ShareOptions = ({ visita, qrData, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState(null);
  
  const compartir = async (metodo) => {
    setLoading(true);
    setError(null);
    setResultado(null);
    
    try {
      let result;
      
      switch (metodo) {
        case 'whatsapp':
          result = await guardiaApi.compartirWhatsApp(visita.visita_id, visita.telefono);
          break;
        case 'sms':
          result = await guardiaApi.compartirSMS(visita.visita_id, visita.telefono);
          break;
        case 'email':
          if (!visita.email) {
            setError('El visitante no tiene email registrado');
            return;
          }
          result = await guardiaApi.compartirEmail(visita.visita_id, visita.email);
          break;
        case 'slack':
          result = await guardiaApi.notificarSlack(visita.visita_id);
          break;
        default:
          setError('Método no soportado');
          return;
      }
      
      if (result.success) {
        setResultado({
          tipo: metodo,
          mensaje: result.data.message || `Enviado por ${metodo} correctamente`
        });
        
        // Auto-cerrar después de 3 segundos
        setTimeout(() => {
          onClose();
        }, 3000);
      } else {
        setError(result.error);
      }
    } catch (err) {
      setError('Error al compartir: ' + err.message);
    } finally {
      setLoading(false);
    }
  };
  
  const copiarCodigo = () => {
    navigator.clipboard.writeText(qrData.codigo_alfanumerico);
    setResultado({
      tipo: 'clipboard',
      mensaje: 'Código copiado al portapapeles'
    });
    
    setTimeout(() => {
      setResultado(null);
    }, 2000);
  };
  
  const copiarURL = () => {
    navigator.clipboard.writeText(qrData.url_validacion);
    setResultado({
      tipo: 'clipboard',
      mensaje: 'URL copiada al portapapeles'
    });
    
    setTimeout(() => {
      setResultado(null);
    }, 2000);
  };
  
  return (
    <div className="share-options-overlay" onClick={onClose}>
      <div className="share-options-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>📤 Compartir Código de Acceso</h3>
          <button className="btn-close" onClick={onClose}>×</button>
        </div>
        
        <div className="modal-body">
          {error && (
            <div className="alert alert-error">
              {error}
            </div>
          )}
          
          {resultado && (
            <div className="alert alert-success">
              ✅ {resultado.mensaje}
            </div>
          )}
          
          <div className="share-visitor-info">
            <p><strong>Visitante:</strong> {visita.nombre} {visita.apellido}</p>
            <p><strong>Teléfono:</strong> {visita.telefono}</p>
            {visita.email && <p><strong>Email:</strong> {visita.email}</p>}
          </div>
          
          <div className="share-methods">
            <h4>Selecciona el método de envío:</h4>
            
            <div className="method-grid">
              <button
                className="method-card"
                onClick={() => compartir('whatsapp')}
                disabled={loading}
              >
                <div className="method-icon">📱</div>
                <div className="method-name">WhatsApp</div>
                <div className="method-desc">Mensaje directo</div>
              </button>
              
              <button
                className="method-card"
                onClick={() => compartir('sms')}
                disabled={loading}
              >
                <div className="method-icon">💬</div>
                <div className="method-name">SMS</div>
                <div className="method-desc">Mensaje de texto</div>
              </button>
              
              {visita.email && (
                <button
                  className="method-card"
                  onClick={() => compartir('email')}
                  disabled={loading}
                >
                  <div className="method-icon">📧</div>
                  <div className="method-name">Email</div>
                  <div className="method-desc">Correo electrónico</div>
                </button>
              )}
              
              <button
                className="method-card"
                onClick={() => compartir('slack')}
                disabled={loading}
              >
                <div className="method-icon">🔔</div>
                <div className="method-name">Slack</div>
                <div className="method-desc">Notificar equipo</div>
              </button>
            </div>
            
            <div className="method-divider">
              <span>o copiar manualmente</span>
            </div>
            
            <div className="manual-options">
              <button
                className="btn btn-outline btn-block"
                onClick={copiarCodigo}
              >
                📋 Copiar código: <strong>{qrData.codigo_alfanumerico}</strong>
              </button>
              
              <button
                className="btn btn-outline btn-block"
                onClick={copiarURL}
              >
                🔗 Copiar URL de validación
              </button>
            </div>
          </div>
        </div>
        
        <div className="modal-footer">
          <button
            className="btn btn-secondary"
            onClick={onClose}
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
};

export default ShareOptions;
