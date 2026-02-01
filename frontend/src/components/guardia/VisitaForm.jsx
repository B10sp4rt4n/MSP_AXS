import React, { useState, useEffect } from 'react';
import guardiaApi from '../../services/guardiaApi';

const VisitaForm = ({ condominioId, onVisitaCreada, deviceType }) => {
  const [formData, setFormData] = useState({
    nombre: '',
    apellido: '',
    telefono: '',
    email: '',
    casa_unidad: '',
    motivo: '',
    tipo_visita: 'VISITANTE',
    tiene_vehiculo: false,
    placa_vehiculo: ''
  });
  
  const [casasUnidades, setCasasUnidades] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    cargarCasasUnidades();
  }, [condominioId]);
  
  const cargarCasasUnidades = async () => {
    console.log('🏠 Cargando casas para condominio:', condominioId);
    const result = await guardiaApi.obtenerCasasUnidades(condominioId);
    console.log('🏠 Resultado casas:', result);
    if (result.success && result.data.casas) {
      setCasasUnidades(result.data.casas);
      console.log('🏠 Casas cargadas:', result.data.casas);
    }
  };
  
  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    
    try {
      // Preparar datos
      const visitaData = {
        ...formData,
        condominio_id: condominioId,
        fecha_inicio: new Date().toISOString(),
        fecha_fin: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString() // 24h
      };
      
      // Registrar visita
      const result = await guardiaApi.registrarVisita(visitaData);
      
      if (result.success) {
        onVisitaCreada(result.data);
        // Reset form
        setFormData({
          nombre: '',
          apellido: '',
          telefono: '',
          email: '',
          casa_unidad: '',
          motivo: '',
          tipo_visita: 'VISITANTE',
          tiene_vehiculo: false,
          placa_vehiculo: ''
        });
      } else {
        setError(result.error);
      }
    } catch (err) {
      setError('Error al registrar visita');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className={`visita-form ${deviceType}`}>
      <h2>📝 Registro de Visita</h2>
      
      {error && (
        <div className="alert alert-error">
          {error}
        </div>
      )}
      
      <form onSubmit={handleSubmit}>
        <div className="form-row">
          <div className="form-group">
            <label htmlFor="nombre">Nombre *</label>
            <input
              type="text"
              id="nombre"
              name="nombre"
              value={formData.nombre}
              onChange={handleChange}
              required
              placeholder="Juan"
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="apellido">Apellido *</label>
            <input
              type="text"
              id="apellido"
              name="apellido"
              value={formData.apellido}
              onChange={handleChange}
              required
              placeholder="Pérez"
            />
          </div>
        </div>
        
        <div className="form-row">
          <div className="form-group">
            <label htmlFor="telefono">Teléfono *</label>
            <input
              type="tel"
              id="telefono"
              name="telefono"
              value={formData.telefono}
              onChange={handleChange}
              required
              placeholder="+573001234567"
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="email">Email (opcional)</label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              placeholder="juan@ejemplo.com"
            />
          </div>
        </div>
        
        <div className="form-group">
          <label htmlFor="casa_unidad">Casa/Unidad a visitar *</label>
          <select
            id="casa_unidad"
            name="casa_unidad"
            value={formData.casa_unidad}
            onChange={handleChange}
            required
          >
            <option value="">Seleccionar...</option>
            {casasUnidades.map(casa => (
              <option key={casa.casa_unidad} value={casa.casa_unidad}>
                {casa.casa_unidad} - {casa.residentes?.[0]?.nombre || 'Sin residente'}
              </option>
            ))}
          </select>
        </div>
        
        <div className="form-group">
          <label htmlFor="tipo_visita">Tipo de visita</label>
          <select
            id="tipo_visita"
            name="tipo_visita"
            value={formData.tipo_visita}
            onChange={handleChange}
          >
            <option value="VISITANTE">Visitante</option>
            <option value="PROVEEDOR">Proveedor</option>
            <option value="DELIVERY">Delivery</option>
            <option value="MANTENIMIENTO">Mantenimiento</option>
          </select>
        </div>
        
        <div className="form-group">
          <label htmlFor="motivo">Motivo de la visita</label>
          <textarea
            id="motivo"
            name="motivo"
            value={formData.motivo}
            onChange={handleChange}
            rows="3"
            placeholder="Reunión familiar, entrega de paquete, etc."
          />
        </div>
        
        <div className="form-group checkbox-group">
          <label>
            <input
              type="checkbox"
              name="tiene_vehiculo"
              checked={formData.tiene_vehiculo}
              onChange={handleChange}
            />
            <span>Tiene vehículo</span>
          </label>
        </div>
        
        {formData.tiene_vehiculo && (
          <div className="form-group">
            <label htmlFor="placa_vehiculo">Placa del vehículo</label>
            <input
              type="text"
              id="placa_vehiculo"
              name="placa_vehiculo"
              value={formData.placa_vehiculo}
              onChange={handleChange}
              placeholder="ABC123"
              style={{ textTransform: 'uppercase' }}
            />
          </div>
        )}
        
        <button
          type="submit"
          className="btn btn-primary btn-block"
          disabled={loading}
        >
          {loading ? '⏳ Registrando...' : '✅ Registrar y Generar QR'}
        </button>
      </form>
    </div>
  );
};

export default VisitaForm;
