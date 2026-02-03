import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

/**
 * Servicio API para la aplicación de Guardia
 */
class GuardiaAPI {
  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    // Token actual
    this.currentToken = null;
    
    // Interceptor para agregar token
    this.client.interceptors.request.use((config) => {
      const token = this.currentToken || localStorage.getItem('token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });
  }
  
  /**
   * Configurar token de autenticación
   */
  setToken(token) {
    this.currentToken = token;
    localStorage.setItem('token', token);
  }
  
  /**
   * Registrar nueva visita y generar QR
   */
  async registrarVisita(visitaData) {
    try {
      // Mapear datos al formato VisitaRapidaCreate del backend
      const visitaRapidaData = {
        nombre_visitante: `${visitaData.nombre} ${visitaData.apellido}`.trim() || visitaData.nombre || 'Visitante',
        telefono: visitaData.telefono || null,
        casa_unidad: visitaData.casa_unidad,
        residente_anfitrion: visitaData.residente_anfitrion || null,
        tipo_visitante: visitaData.tipo_visita === 'VISITANTE' ? 'eventual' : 'proveedor',
        motivo: visitaData.motivo || null,
        placa_vehiculo: visitaData.tiene_vehiculo ? visitaData.placa_vehiculo : null
      };
      
      const response = await this.client.post('/visitas/rapida', visitaRapidaData);
      return { success: true, data: response.data };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || error.message
      };
    }
  }
  
  /**
   * Generar código QR para visita existente
   */
  async generarQR(visitaId) {
    try {
      const response = await this.client.post(`/qr/generar/${visitaId}`);
      return { success: true, data: response.data };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || error.message
      };
    }
  }
  
  /**
   * Compartir QR por WhatsApp
   */
  async compartirWhatsApp(visitaId, telefono) {
    try {
      const response = await this.client.post('/qr/compartir/whatsapp', {
        visita_id: visitaId,
        telefono
      });
      return { success: true, data: response.data };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || error.message
      };
    }
  }
  
  /**
   * Compartir QR por SMS
   */
  async compartirSMS(visitaId, telefono) {
    try {
      const response = await this.client.post('/qr/compartir/sms', {
        visita_id: visitaId,
        telefono
      });
      return { success: true, data: response.data };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || error.message
      };
    }
  }
  
  /**
   * Compartir QR por Email
   */
  async compartirEmail(visitaId, email) {
    try {
      const response = await this.client.post('/qr/compartir/email', {
        visita_id: visitaId,
        email
      });
      return { success: true, data: response.data };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || error.message
      };
    }
  }
  
  /**
   * Notificar a Slack
   */
  async notificarSlack(visitaId) {
    try {
      const response = await this.client.post('/qr/compartir/slack', {
        visita_id: visitaId
      });
      return { success: true, data: response.data };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || error.message
      };
    }
  }
  
  /**
   * Subir imagen a Cloudinary
   */
  async subirImagen(file, tipo) {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('tipo', tipo);
      
      const response = await this.client.post('/cloudinary/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      return { success: true, data: response.data };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || error.message
      };
    }
  }
  
  /**
   * Obtener casas/unidades del condominio
   */
  async obtenerCasasUnidades(condominioId) {
    try {
      const response = await this.client.get(`/condominios/${condominioId}/casas`);
      return { success: true, data: response.data };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || error.message
      };
    }
  }
  
  /**
   * Validar código alfanumérico
   */
  async validarCodigo(codigo) {
    try {
      const response = await this.client.get(`/qr/acceso/${codigo}`);
      return { success: true, data: response.data };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || error.message
      };
    }
  }
}

export default new GuardiaAPI();
