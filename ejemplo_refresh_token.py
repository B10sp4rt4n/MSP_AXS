#!/usr/bin/env python3
"""
Ejemplo de cómo usar el sistema de refresh tokens

FLUJO COMPLETO:
1. Login inicial → Obtienes access_token
2. Usas el token para llamadas API
3. ANTES de que expire (8h), llamas a /auth/refresh
4. Recibes nuevo token con 8h más de vida
5. Repites el proceso

VENTAJA:
- No necesitas hacer login cada 8 horas
- Sesión continua mientras uses la app
"""

import requests
import time
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

def login(email: str, password: str) -> str:
    """Paso 1: Login inicial"""
    print(f"\n🔐 Haciendo login con {email}...")
    
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password}
    )
    
    if response.status_code == 200:
        data = response.json()
        token = data["access_token"]
        print(f"✅ Login exitoso!")
        print(f"   Token: {token[:30]}...")
        return token
    else:
        print(f"❌ Login fallido: {response.status_code}")
        print(f"   {response.json()}")
        return None


def refresh_token(current_token: str) -> str:
    """Paso 2: Renovar token ANTES de que expire"""
    print(f"\n🔄 Renovando token...")
    
    response = requests.post(
        f"{BASE_URL}/auth/refresh",
        headers={"Authorization": f"Bearer {current_token}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        new_token = data["access_token"]
        print(f"✅ Token renovado!")
        print(f"   Nuevo token: {new_token[:30]}...")
        return new_token
    else:
        print(f"❌ Renovación fallida: {response.status_code}")
        print(f"   {response.json()}")
        return None


def usar_api(token: str):
    """Ejemplo de uso del token en una llamada API"""
    print(f"\n📊 Consultando MSPs...")
    
    response = requests.get(
        f"{BASE_URL}/msps/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ MSPs obtenidos: {len(data)} registros")
        for msp in data[:3]:  # Mostrar primeros 3
            print(f"   • {msp.get('nombre')} (ID: {msp.get('msp_id')})")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"   {response.json()}")


def ejemplo_completo():
    """
    Ejemplo completo del flujo de tokens
    """
    print("=" * 70)
    print("EJEMPLO: SISTEMA DE REFRESH TOKENS")
    print("=" * 70)
    
    # Paso 1: Login inicial
    token = login("guardia@condoriente.com", "guardia123")
    
    if not token:
        print("\n❌ No se pudo hacer login. Verifica las credenciales.")
        return
    
    # Paso 2: Usar el token
    usar_api(token)
    
    # Paso 3: Simular paso del tiempo (en producción esto sería 7 horas)
    print("\n⏰ Esperando... (en producción esperarías ~7 horas)")
    time.sleep(2)
    
    # Paso 4: Renovar token ANTES de que expire
    nuevo_token = refresh_token(token)
    
    if not nuevo_token:
        print("\n❌ No se pudo renovar el token. Necesitas hacer login de nuevo.")
        return
    
    # Paso 5: Seguir usando la API con el nuevo token
    usar_api(nuevo_token)
    
    print("\n" + "=" * 70)
    print("✅ FLUJO COMPLETADO")
    print("=" * 70)
    print("\n💡 TIPS:")
    print("   • Token dura 8 horas (480 minutos)")
    print("   • Renuévalo cada 7 horas para no perder sesión")
    print("   • Puedes renovar cuantas veces quieras")
    print("   • Si olvidas renovar, solo haz login de nuevo")


def ejemplo_frontend_timer():
    """
    Ejemplo de cómo implementarlo en el frontend
    """
    print("\n" + "=" * 70)
    print("IMPLEMENTACIÓN EN FRONTEND (JavaScript/React)")
    print("=" * 70)
    
    codigo = """
// 1. Al hacer login, guarda el token y la hora
const login = async (email, password) => {
    const response = await fetch('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
        headers: { 'Content-Type': 'application/json' }
    });
    
    const data = await response.json();
    
    // Guardar token y hora de login
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('login_time', Date.now());
    
    // Iniciar timer de renovación automática
    startRefreshTimer();
};

// 2. Timer automático para renovar cada 7 horas
const startRefreshTimer = () => {
    // Renovar cada 7 horas (25200000 ms)
    setInterval(async () => {
        await refreshToken();
    }, 7 * 60 * 60 * 1000);
};

// 3. Función de renovación
const refreshToken = async () => {
    const currentToken = localStorage.getItem('access_token');
    
    const response = await fetch('/auth/refresh', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${currentToken}`
        }
    });
    
    if (response.ok) {
        const data = await response.json();
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('login_time', Date.now());
        console.log('✅ Token renovado automáticamente');
    } else {
        // Token expiró, redirigir a login
        console.log('❌ Token expirado, redirigiendo a login...');
        window.location.href = '/login';
    }
};

// 4. Interceptor para renovar en cada request si está cerca de expirar
axios.interceptors.request.use(async (config) => {
    const loginTime = localStorage.getItem('login_time');
    const hoursElapsed = (Date.now() - loginTime) / (1000 * 60 * 60);
    
    // Si han pasado más de 7 horas, renovar antes del request
    if (hoursElapsed > 7) {
        await refreshToken();
    }
    
    return config;
});
"""
    
    print(codigo)
    print("\n✅ Con esta implementación, el usuario NUNCA tiene que volver a hacer login")
    print("   mientras use la app regularmente.")


if __name__ == "__main__":
    # Ejecutar ejemplo completo
    ejemplo_completo()
    
    # Mostrar código de ejemplo para frontend
    ejemplo_frontend_timer()
