import { useState, useRef } from 'react';

function ModoGuardia() {
  const [paso, setPaso] = useState('login'); // login, crear-visita, capturar-fotos, entrada-registrada
  const [token, setToken] = useState('');
  const [visitaId, setVisitaId] = useState('');
  const [qrToken, setQrToken] = useState('');
  const [fotos, setFotos] = useState({
    visitante: null,
    documentoFrente: null,
    placa: null
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const inputVisitanteRef = useRef(null);
  const inputDocumentoRef = useRef(null);
  const inputPlacaRef = useRef(null);

  // Estado del formulario
  const [formData, setFormData] = useState({
    email: 'guardia@condoriente.com',
    password: 'guard123',
    nombre: '',
    telefono: '',
    residente: '',
    casa: '',
    motivo: '',
    placa: ''
  });

  const API_BASE = '/api';

  // ========== PASO 1: LOGIN ==========
  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: formData.email.trim(),
          password: formData.password
        })
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detalle = data?.detail || `Error ${response.status}`;
        throw new Error(detalle);
      }
      setToken(data.access_token);
      setPaso('crear-visita');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // ========== PASO 2: CREAR VISITA RÁPIDA ==========
  const handleCrearVisita = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch(`${API_BASE}/visitas/rapida`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          nombre_visitante: formData.nombre,
          telefono: formData.telefono,
          residente_anfitrion: formData.residente,
          casa_unidad: formData.casa,
          motivo: formData.motivo,
          placa_vehiculo: formData.placa || null,
          tipo_visitante: 'eventual'
        })
      });

      if (!response.ok) throw new Error('Error creando visita');
      
      const data = await response.json();
      setVisitaId(data.visita_id);
      setPaso('capturar-fotos');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // ========== PASO 3: CAPTURAR FOTOS ==========
  const handleFileChange = (tipo, file) => {
    setFotos(prev => ({ ...prev, [tipo]: file }));
  };

  const handleCapturarFotos = async (e) => {
    e.preventDefault();
    
    if (!fotos.visitante) {
      setError('La foto del visitante es obligatoria');
      return;
    }

    setLoading(true);
    setError('');
    
    try {
      const formDataUpload = new FormData();
      formDataUpload.append('foto_visitante', fotos.visitante);
      if (fotos.documentoFrente) {
        formDataUpload.append('foto_documento_frente', fotos.documentoFrente);
      }
      if (fotos.placa) {
        formDataUpload.append('foto_placa', fotos.placa);
      }

      const response = await fetch(`${API_BASE}/visitas/${visitaId}/capturar-evidencias`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formDataUpload
      });

      if (!response.ok) throw new Error('Error capturando fotos');
      
      await handleRegistrarEntrada();
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  // ========== PASO 4: REGISTRAR ENTRADA ==========
  const handleRegistrarEntrada = async () => {
    try {
      const response = await fetch(`${API_BASE}/visitas/${visitaId}/registrar-entrada`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({})
      });

      if (!response.ok) throw new Error('Error registrando entrada');
      
      const data = await response.json();
      setQrToken(data.qr_token);
      setPaso('entrada-registrada');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // ========== REGISTRAR SALIDA ==========
  const handleRegistrarSalida = async () => {
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch(`${API_BASE}/visitas/${visitaId}/registrar-salida`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({})
      });

      if (!response.ok) throw new Error('Error registrando salida');
      
      // Resetear para nueva visita
      setVisitaId('');
      setQrToken('');
      setFotos({ visitante: null, documentoFrente: null, placa: null });
      setFormData(prev => ({
        ...prev,
        nombre: '',
        telefono: '',
        residente: '',
        casa: '',
        motivo: '',
        placa: ''
      }));
      setPaso('crear-visita');
      alert('✅ Salida registrada exitosamente');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleNuevaVisita = () => {
    setVisitaId('');
    setQrToken('');
    setFotos({ visitante: null, documentoFrente: null, placa: null });
    setFormData(prev => ({
      ...prev,
      nombre: '',
      telefono: '',
      residente: '',
      casa: '',
      motivo: '',
      placa: ''
    }));
    setPaso('crear-visita');
  };

  // ========== RENDERIZADO ==========
  return (
    <div style={{ 
      minHeight: '100vh', 
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      padding: '20px',
      fontFamily: 'system-ui, -apple-system, sans-serif'
    }}>
      <div style={{
        maxWidth: '600px',
        margin: '0 auto',
        background: 'white',
        borderRadius: '20px',
        boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
        overflow: 'hidden'
      }}>
        {/* Header */}
        <div style={{
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          padding: '30px',
          textAlign: 'center'
        }}>
          <h1 style={{ margin: 0, fontSize: '28px', fontWeight: 'bold' }}>
            🛡️ MODO GUARDIA
          </h1>
          <p style={{ margin: '10px 0 0', opacity: 0.9, fontSize: '14px' }}>
            Control de Acceso - Visitas Rápidas
          </p>
        </div>

        {/* Indicador de pasos */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-around',
          padding: '20px',
          borderBottom: '1px solid #e5e7eb',
          background: '#f9fafb'
        }}>
          {['login', 'crear-visita', 'capturar-fotos', 'entrada-registrada'].map((p, i) => (
            <div key={p} style={{
              flex: 1,
              textAlign: 'center',
              opacity: paso === p ? 1 : 0.3,
              transition: 'all 0.3s'
            }}>
              <div style={{
                width: '40px',
                height: '40px',
                borderRadius: '50%',
                background: paso === p ? '#667eea' : '#d1d5db',
                color: 'white',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 8px',
                fontWeight: 'bold',
                fontSize: '18px'
              }}>
                {i + 1}
              </div>
              <div style={{ fontSize: '11px', fontWeight: '600', color: '#374151' }}>
                {p === 'login' && 'Login'}
                {p === 'crear-visita' && 'Visita'}
                {p === 'capturar-fotos' && 'Fotos'}
                {p === 'entrada-registrada' && 'Entrada'}
              </div>
            </div>
          ))}
        </div>

        {/* Error message */}
        {error && (
          <div style={{
            margin: '20px',
            padding: '15px',
            background: '#fee2e2',
            color: '#991b1b',
            borderRadius: '10px',
            fontSize: '14px'
          }}>
            ⚠️ {error}
          </div>
        )}

        {/* Contenido por paso */}
        <div style={{ padding: '30px' }}>
          
          {/* PASO 1: LOGIN */}
          {paso === 'login' && (
            <form onSubmit={handleLogin}>
              <h2 style={{ marginTop: 0, fontSize: '22px', color: '#1f2937' }}>
                Autenticación del Guardia
              </h2>
              
              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600', color: '#374151' }}>
                  Email
                </label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  style={{
                    width: '100%',
                    padding: '12px',
                    border: '2px solid #e5e7eb',
                    borderRadius: '8px',
                    fontSize: '16px',
                    transition: 'border 0.3s'
                  }}
                  required
                />
              </div>

              <div style={{ marginBottom: '25px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600', color: '#374151' }}>
                  Contraseña
                </label>
                <input
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  style={{
                    width: '100%',
                    padding: '12px',
                    border: '2px solid #e5e7eb',
                    borderRadius: '8px',
                    fontSize: '16px'
                  }}
                  required
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                style={{
                  width: '100%',
                  padding: '15px',
                  background: loading ? '#9ca3af' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '10px',
                  fontSize: '16px',
                  fontWeight: 'bold',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  transition: 'transform 0.2s'
                }}
                onMouseEnter={(e) => !loading && (e.target.style.transform = 'scale(1.02)')}
                onMouseLeave={(e) => e.target.style.transform = 'scale(1)'}
              >
                {loading ? 'Autenticando...' : '🔓 Iniciar Sesión'}
              </button>
            </form>
          )}

          {/* PASO 2: CREAR VISITA */}
          {paso === 'crear-visita' && (
            <form onSubmit={handleCrearVisita}>
              <h2 style={{ marginTop: 0, fontSize: '22px', color: '#1f2937' }}>
                Registrar Visitante
              </h2>
              
              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600', color: '#374151' }}>
                  Nombre Completo *
                </label>
                <input
                  type="text"
                  value={formData.nombre}
                  onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                  placeholder="Ej: Juan Pérez"
                  style={{
                    width: '100%',
                    padding: '12px',
                    border: '2px solid #e5e7eb',
                    borderRadius: '8px',
                    fontSize: '16px'
                  }}
                  required
                />
              </div>

              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600', color: '#374151' }}>
                  Teléfono
                </label>
                <input
                  type="tel"
                  value={formData.telefono}
                  onChange={(e) => setFormData({ ...formData, telefono: e.target.value })}
                  placeholder="Ej: 3001234567"
                  style={{
                    width: '100%',
                    padding: '12px',
                    border: '2px solid #e5e7eb',
                    borderRadius: '8px',
                    fontSize: '16px'
                  }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '10px', marginBottom: '15px' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600', color: '#374151' }}>
                    Residente Anfitrión *
                  </label>
                  <input
                    type="text"
                    value={formData.residente}
                    onChange={(e) => setFormData({ ...formData, residente: e.target.value })}
                    placeholder="Nombre del residente"
                    style={{
                      width: '100%',
                      padding: '12px',
                      border: '2px solid #e5e7eb',
                      borderRadius: '8px',
                      fontSize: '16px'
                    }}
                    required
                  />
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600', color: '#374151' }}>
                    Casa *
                  </label>
                  <input
                    type="text"
                    value={formData.casa}
                    onChange={(e) => setFormData({ ...formData, casa: e.target.value })}
                    placeholder="405"
                    style={{
                      width: '100%',
                      padding: '12px',
                      border: '2px solid #e5e7eb',
                      borderRadius: '8px',
                      fontSize: '16px'
                    }}
                    required
                  />
                </div>
              </div>

              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600', color: '#374151' }}>
                  Motivo de la Visita
                </label>
                <input
                  type="text"
                  value={formData.motivo}
                  onChange={(e) => setFormData({ ...formData, motivo: e.target.value })}
                  placeholder="Ej: Visita social"
                  style={{
                    width: '100%',
                    padding: '12px',
                    border: '2px solid #e5e7eb',
                    borderRadius: '8px',
                    fontSize: '16px'
                  }}
                />
              </div>

              <div style={{ marginBottom: '25px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600', color: '#374151' }}>
                  Placa del Vehículo (opcional)
                </label>
                <input
                  type="text"
                  value={formData.placa}
                  onChange={(e) => setFormData({ ...formData, placa: e.target.value.toUpperCase() })}
                  placeholder="ABC-123"
                  style={{
                    width: '100%',
                    padding: '12px',
                    border: '2px solid #e5e7eb',
                    borderRadius: '8px',
                    fontSize: '16px',
                    textTransform: 'uppercase'
                  }}
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                style={{
                  width: '100%',
                  padding: '15px',
                  background: loading ? '#9ca3af' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '10px',
                  fontSize: '16px',
                  fontWeight: 'bold',
                  cursor: loading ? 'not-allowed' : 'pointer'
                }}
              >
                {loading ? 'Creando...' : '📝 Continuar →'}
              </button>
            </form>
          )}

          {/* PASO 3: CAPTURAR FOTOS */}
          {paso === 'capturar-fotos' && (
            <form onSubmit={handleCapturarFotos}>
              <h2 style={{ marginTop: 0, fontSize: '22px', color: '#1f2937' }}>
                Capturar Evidencias
              </h2>
              <p style={{ color: '#6b7280', fontSize: '14px', marginTop: '-10px' }}>
                ID Visita: <strong>{visitaId}</strong>
              </p>

              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600', color: '#374151' }}>
                  📷 Foto del Visitante *
                </label>
                <input
                  ref={inputVisitanteRef}
                  type="file"
                  accept="image/*"
                  capture="user"
                  onChange={(e) => handleFileChange('visitante', e.target.files[0])}
                  style={{ display: 'none' }}
                  required
                />
                <button
                  type="button"
                  onClick={() => inputVisitanteRef.current.click()}
                  style={{
                    width: '100%',
                    padding: '15px',
                    background: fotos.visitante ? '#10b981' : '#e5e7eb',
                    color: fotos.visitante ? 'white' : '#374151',
                    border: 'none',
                    borderRadius: '8px',
                    fontSize: '15px',
                    fontWeight: '600',
                    cursor: 'pointer'
                  }}
                >
                  {fotos.visitante ? `✓ ${fotos.visitante.name}` : '📸 Capturar Foto'}
                </button>
              </div>

              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600', color: '#374151' }}>
                  📋 Foto Documento (frente)
                </label>
                <input
                  ref={inputDocumentoRef}
                  type="file"
                  accept="image/*"
                  capture="environment"
                  onChange={(e) => handleFileChange('documentoFrente', e.target.files[0])}
                  style={{ display: 'none' }}
                />
                <button
                  type="button"
                  onClick={() => inputDocumentoRef.current.click()}
                  style={{
                    width: '100%',
                    padding: '15px',
                    background: fotos.documentoFrente ? '#10b981' : '#e5e7eb',
                    color: fotos.documentoFrente ? 'white' : '#374151',
                    border: 'none',
                    borderRadius: '8px',
                    fontSize: '15px',
                    fontWeight: '600',
                    cursor: 'pointer'
                  }}
                >
                  {fotos.documentoFrente ? `✓ ${fotos.documentoFrente.name}` : '📸 Capturar Documento'}
                </button>
              </div>

              {formData.placa && (
                <div style={{ marginBottom: '25px' }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600', color: '#374151' }}>
                    🚗 Foto Placa ({formData.placa})
                  </label>
                  <input
                    ref={inputPlacaRef}
                    type="file"
                    accept="image/*"
                    capture="environment"
                    onChange={(e) => handleFileChange('placa', e.target.files[0])}
                    style={{ display: 'none' }}
                  />
                  <button
                    type="button"
                    onClick={() => inputPlacaRef.current.click()}
                    style={{
                      width: '100%',
                      padding: '15px',
                      background: fotos.placa ? '#10b981' : '#e5e7eb',
                      color: fotos.placa ? 'white' : '#374151',
                      border: 'none',
                      borderRadius: '8px',
                      fontSize: '15px',
                      fontWeight: '600',
                      cursor: 'pointer'
                    }}
                  >
                    {fotos.placa ? `✓ ${fotos.placa.name}` : '📸 Capturar Placa'}
                  </button>
                </div>
              )}

              <button
                type="submit"
                disabled={loading || !fotos.visitante}
                style={{
                  width: '100%',
                  padding: '15px',
                  background: (loading || !fotos.visitante) ? '#9ca3af' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '10px',
                  fontSize: '16px',
                  fontWeight: 'bold',
                  cursor: (loading || !fotos.visitante) ? 'not-allowed' : 'pointer'
                }}
              >
                {loading ? 'Subiendo fotos...' : '✅ Registrar Entrada'}
              </button>
            </form>
          )}

          {/* PASO 4: ENTRADA REGISTRADA */}
          {paso === 'entrada-registrada' && (
            <div style={{ textAlign: 'center' }}>
              <div style={{
                width: '80px',
                height: '80px',
                borderRadius: '50%',
                background: '#10b981',
                color: 'white',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 20px',
                fontSize: '40px'
              }}>
                ✓
              </div>
              
              <h2 style={{ margin: '0 0 10px', fontSize: '24px', color: '#1f2937' }}>
                Entrada Registrada
              </h2>
              
              <p style={{ color: '#6b7280', marginBottom: '30px' }}>
                ID Visita: <strong>{visitaId}</strong>
              </p>

              {/* QR Code Display */}
              <div style={{
                background: '#f9fafb',
                padding: '30px',
                borderRadius: '15px',
                marginBottom: '25px',
                border: '2px dashed #d1d5db'
              }}>
                <div style={{
                  background: 'white',
                  padding: '20px',
                  borderRadius: '10px',
                  marginBottom: '15px',
                  boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
                }}>
                  <div style={{
                    fontSize: '12px',
                    fontFamily: 'monospace',
                    wordBreak: 'break-all',
                    color: '#374151',
                    lineHeight: '1.6'
                  }}>
                    {qrToken}
                  </div>
                </div>
                <p style={{ 
                  margin: 0, 
                  fontSize: '13px', 
                  color: '#6b7280',
                  fontStyle: 'italic'
                }}>
                  Token QR generado automáticamente
                </p>
              </div>

              <div style={{ 
                display: 'grid', 
                gridTemplateColumns: '1fr 1fr', 
                gap: '15px'
              }}>
                <button
                  onClick={handleNuevaVisita}
                  style={{
                    padding: '15px',
                    background: '#f3f4f6',
                    color: '#374151',
                    border: '2px solid #d1d5db',
                    borderRadius: '10px',
                    fontSize: '15px',
                    fontWeight: 'bold',
                    cursor: 'pointer'
                  }}
                >
                  📝 Nueva Visita
                </button>
                
                <button
                  onClick={handleRegistrarSalida}
                  disabled={loading}
                  style={{
                    padding: '15px',
                    background: loading ? '#9ca3af' : 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                    color: 'white',
                    border: 'none',
                    borderRadius: '10px',
                    fontSize: '15px',
                    fontWeight: 'bold',
                    cursor: loading ? 'not-allowed' : 'pointer'
                  }}
                >
                  {loading ? 'Procesando...' : '🚪 Registrar Salida'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div style={{
        textAlign: 'center',
        marginTop: '20px',
        color: 'white',
        fontSize: '13px',
        opacity: 0.8
      }}>
        MSP_AXS Control de Acceso v1.0
      </div>
    </div>
  );
}

export default ModoGuardia;
