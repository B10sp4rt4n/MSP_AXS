import React, { useState, useEffect } from 'react';
import { useDeviceDetection } from '../../hooks/useDeviceDetection';
import VisitaForm from './VisitaForm';
import QRDisplay from './QRDisplay';
import ShareOptions from './ShareOptions';
import guardiaApi from '../../services/guardiaApi';

const GuardiaApp = ({ usuario, condominio, token }) => {
  const { deviceType, isDesktop } = useDeviceDetection();
  const [paso, setPaso] = useState('formulario'); // formulario | generando | qr_generado
  const [visitaActual, setVisitaActual] = useState(null);
  const [qrData, setQrData] = useState(null);
  const [mostrarCompartir, setMostrarCompartir] = useState(false);
  const [error, setError] = useState(null);
  const [visitasHoy, setVisitasHoy] = useState(0);
  const [codigosActivos, setCodigosActivos] = useState(0);
  
  // Configurar el token en guardiaApi cuando cambie
  useEffect(() => {
    if (token) {
      guardiaApi.setToken(token);
    }
  }, [token]);
  
  const handleVisitaCreada = async (visita) => {
    setVisitaActual(visita);
    setPaso('generando');
    setError(null);
    
    // Incrementar contador de visitas
    setVisitasHoy(prev => prev + 1);
    
    try {
      // Generar QR automáticamente
      // El backend retorna visita_id, no id
      const result = await guardiaApi.generarQR(visita.visita_id);
      
      if (result.success) {
        setQrData(result.data);
        setPaso('qr_generado');
        // Incrementar códigos activos
        setCodigosActivos(prev => prev + 1);
      } else {
        setError(result.error);
        setPaso('formulario');
      }
    } catch (err) {
      setError('Error al generar código QR');
      setPaso('formulario');
    }
  };
  
  const handleCompartir = (metodo) => {
    if (metodo === 'mostrar') {
      setMostrarCompartir(true);
    }
  };
  
  const handleNuevaVisita = () => {
    setPaso('formulario');
    setVisitaActual(null);
    setQrData(null);
    setError(null);
  };
  
  return (
    <div className={`guardia-app ${deviceType}`}>
      <div className="app-header">
        <div className="header-left">
          <h1>🚪 Control de Acceso</h1>
          <div className="header-info">
            <div className="info-badge tenant">
              <span className="badge-label">🏢 Tenant:</span>
              <span className="badge-value">{usuario.tenant_nombre || 'MSP Demo'}</span>
            </div>
            <div className="info-badge condominio">
              <span className="badge-label">🏘️ Condominio:</span>
              <span className="badge-value">{condominio.nombre}</span>
            </div>
          </div>
        </div>
        <div className="header-right">
          <div className="user-info">
            <span className="user-role">Guardia</span>
            <span className="user-name">{usuario.nombre}</span>
          </div>
          <button className="btn-logout" onClick={() => {
            localStorage.removeItem('token');
            window.location.reload();
          }}>
            🚪 Salir
          </button>
        </div>
      </div>
      
      {error && (
        <div className="alert alert-error alert-dismissible">
          <span>{error}</span>
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}
      
      <div className="app-body">
        {paso === 'formulario' && (
          <div className="step-container">
            <VisitaForm
              condominioId={condominio.id}
              onVisitaCreada={handleVisitaCreada}
              deviceType={deviceType}
            />
            
            {isDesktop && (
              <div className="sidebar-info">
                <div className="info-card">
                  <h3>ℹ️ Instrucciones</h3>
                  <ol>
                    <li>Complete los datos del visitante</li>
                    <li>Seleccione el apartamento destino</li>
                    <li>El sistema generará el código QR automáticamente</li>
                    <li>Comparta el código con el visitante</li>
                  </ol>
                </div>
                
                <div className="info-card">
                  <h3>📊 Estadísticas del día</h3>
                  <div className="stat-row">
                    <span>Visitas registradas:</span>
                    <strong>{visitasHoy}</strong>
                  </div>
                  <div className="stat-row">
                    <span>Códigos activos:</span>
                    <strong>{codigosActivos}</strong>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
        
        {paso === 'generando' && (
          <div className="step-container centered">
            <div className="loading-card">
              <div className="spinner large"></div>
              <h2>⏳ Generando código de acceso...</h2>
              <p>Por favor espere un momento</p>
            </div>
          </div>
        )}
        
        {paso === 'qr_generado' && visitaActual && qrData && (
          <div className="step-container">
            <QRDisplay
              qrData={qrData}
              visita={visitaActual}
              onCompartir={handleCompartir}
              deviceType={deviceType}
            />
            
            <div className="action-buttons">
              <button
                className="btn btn-secondary btn-large"
                onClick={handleNuevaVisita}
              >
                ➕ Nueva Visita
              </button>
            </div>
            
            {isDesktop && (
              <div className="sidebar-info">
                <div className="info-card success">
                  <h3>✅ Código Generado</h3>
                  <p>El código está listo para ser compartido con el visitante.</p>
                  
                  <div className="quick-actions">
                    <h4>Acciones rápidas:</h4>
                    <button
                      className="btn btn-sm btn-outline"
                      onClick={() => setMostrarCompartir(true)}
                    >
                      📤 Compartir ahora
                    </button>
                    <button
                      className="btn btn-sm btn-outline"
                      onClick={handleNuevaVisita}
                    >
                      ➕ Nuevo registro
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
      
      {mostrarCompartir && visitaActual && qrData && (
        <ShareOptions
          visita={visitaActual}
          qrData={qrData}
          onClose={() => setMostrarCompartir(false)}
        />
      )}
      
      <div className="app-footer">
        <div className="device-indicator">
          {deviceType === 'desktop' && '💻 Modo PC'}
          {deviceType === 'tablet' && '📱 Modo Tablet'}
          {deviceType === 'mobile' && '📱 Modo Móvil'}
        </div>
        <div className="version-info">
          AXS v1.0 | {new Date().toLocaleDateString('es-CO')}
        </div>
      </div>
    </div>
  );
};

export default GuardiaApp;
