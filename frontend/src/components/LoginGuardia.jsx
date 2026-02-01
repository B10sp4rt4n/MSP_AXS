import { useState } from 'react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function LoginGuardia({ onLoginSuccess }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // Hacer login
      const response = await axios.post(`${API_URL}/auth/login`, {
        email,
        password
      });

      const { access_token } = response.data;
      
      // Guardar token
      localStorage.setItem('token', access_token);

      // Obtener datos del usuario autenticado
      const userResponse = await axios.get(`${API_URL}/auth/me`, {
        headers: {
          'Authorization': `Bearer ${access_token}`
        }
      });

      const userData = userResponse.data;

      // Verificar que sea un guardia
      if (userData.rol !== 'GUARDIA') {
        setError('Solo usuarios con rol de Guardia pueden acceder');
        localStorage.removeItem('token');
        setLoading(false);
        return;
      }

      // Llamar al callback con los datos del usuario
      onLoginSuccess(userData, access_token);
      
    } catch (err) {
      console.error('Error en login:', err);
      setError(
        err.response?.data?.detail || 
        'Error al iniciar sesión. Verifica tus credenciales.'
      );
      setLoading(false);
    }
  };

  return (
    <div className="login-guardia">
      <div className="login-card">
        <div className="login-header">
          <h1>🚪 Control de Acceso</h1>
          <p>Iniciar sesión como Guardia</p>
        </div>

        <form onSubmit={handleLogin} className="login-form">
          <div className="form-group">
            <label htmlFor="email">📧 Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="guardia@demo.com"
              required
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">🔒 Contraseña</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              disabled={loading}
            />
          </div>

          {error && (
            <div className="error-message">
              ⚠️ {error}
            </div>
          )}

          <button 
            type="submit" 
            className="btn-login"
            disabled={loading}
          >
            {loading ? '🔄 Iniciando sesión...' : '✅ Iniciar Sesión'}
          </button>
        </form>

        <div className="login-footer">
          <p className="demo-credentials">
            <strong>💡 Credenciales de prueba:</strong><br />
            Email: <code>guardia@demo.com</code><br />
            Password: <code>demo123</code>
          </p>
        </div>
      </div>

      <style jsx="true">{`
        .login-guardia {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          padding: 20px;
        }

        .login-card {
          background: white;
          border-radius: 16px;
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
          max-width: 450px;
          width: 100%;
          padding: 40px;
        }

        .login-header {
          text-align: center;
          margin-bottom: 32px;
        }

        .login-header h1 {
          font-size: 2rem;
          color: #2563eb;
          margin-bottom: 8px;
        }

        .login-header p {
          color: #64748b;
          font-size: 1rem;
        }

        .login-form {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .form-group {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .form-group label {
          font-weight: 600;
          color: #334155;
          font-size: 0.875rem;
        }

        .form-group input {
          padding: 12px 16px;
          border: 2px solid #e2e8f0;
          border-radius: 8px;
          font-size: 1rem;
          transition: all 0.2s;
        }

        .form-group input:focus {
          outline: none;
          border-color: #2563eb;
          box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        }

        .form-group input:disabled {
          background: #f1f5f9;
          cursor: not-allowed;
        }

        .error-message {
          padding: 12px 16px;
          background: #fee2e2;
          border: 1px solid #ef4444;
          border-radius: 8px;
          color: #dc2626;
          font-size: 0.875rem;
        }

        .btn-login {
          padding: 14px 24px;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          border: none;
          border-radius: 8px;
          font-size: 1rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
        }

        .btn-login:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
        }

        .btn-login:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .login-footer {
          margin-top: 24px;
          padding-top: 24px;
          border-top: 1px solid #e2e8f0;
        }

        .demo-credentials {
          font-size: 0.875rem;
          color: #64748b;
          line-height: 1.6;
        }

        .demo-credentials code {
          background: #f1f5f9;
          padding: 2px 6px;
          border-radius: 4px;
          font-family: 'Courier New', monospace;
          color: #2563eb;
        }

        @media (max-width: 768px) {
          .login-card {
            padding: 24px;
          }

          .login-header h1 {
            font-size: 1.5rem;
          }
        }
      `}</style>
    </div>
  );
}
