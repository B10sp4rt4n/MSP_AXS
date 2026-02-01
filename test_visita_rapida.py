#!/usr/bin/env python3
"""
Test POST /visitas/rapida - Crear visita in-situ por guardia
"""
import requests
import json
import base64

BASE_URL = "http://localhost:8000"

def test_crear_visita_rapida():
    """Test flujo completo: login guardia → crear visita rápida"""
    
    print("=" * 70)
    print("TEST: Crear visita rápida (in-situ sin QR previo)")
    print("=" * 70)
    
    # PASO 1: Login como guardia
    print("\n[1/3] Login como GUARDIA...")
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": "guardia@axs.com",
            "password": "guardia123"
        }
    )
    
    if login_response.status_code != 200:
        print(f"❌ Error login: {login_response.status_code}")
        print(f"Respuesta: {login_response.json()}")
        return False
    
    token = login_response.json().get("access_token")
    print(f"✅ Token obtenido: {token[:20]}...")
    
    # PASO 2: Crear visita rápida
    print("\n[2/3] Crear visita rápida...")
    headers = {"Authorization": f"Bearer {token}"}
    
    visita_data = {
        "nombre_visitante": "Juan Pérez García",
        "telefono": "+57 310 1234567",
        "casa_unidad": "302",
        "residente_anfitrion": "Carlos López",
        "tipo_visitante": "eventual",
        "motivo": "Visita social - cliente",
        "placa_vehiculo": "ABC-123"
    }
    
    response = requests.post(
        f"{BASE_URL}/visitas/rapida",
        json=visita_data,
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code not in [200, 201]:
        print(f"❌ Error creando visita: {response.status_code}")
        print(f"Respuesta: {response.json()}")
        return False
    
    visita = response.json()
    visita_id = visita.get("visita_id")
    
    print(f"✅ Visita creada exitosamente")
    print(f"   Visita ID: {visita_id}")
    print(f"   Visitante: {visita.get('nombre_visitante')}")
    print(f"   Casa: {visita.get('casa_unidad')}")
    print(f"   Estado: {visita.get('estado')}")
    print(f"   Creada por: {visita.get('creada_por')}")
    
    # PASO 3: Verificar visita en GET /visitas/{visita_id}
    print(f"\n[3/3] Verificar visita creada...")
    response = requests.get(
        f"{BASE_URL}/visitas/{visita_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        visita_verify = response.json()
        print(f"✅ Visita encontrada")
        print(f"   Estado: {visita_verify.get('estado')}")
        print(f"   Teléfono: {visita_verify.get('telefono')}")
        print(f"   Motivo: {visita_verify.get('motivo')}")
    else:
        print(f"⚠️  No se pudo verificar (status {response.status_code})")
    
    print("\n" + "=" * 70)
    print("✅ TEST COMPLETADO EXITOSAMENTE")
    print("=" * 70)
    
    return True


def test_error_sin_rol_guardia():
    """Test que solo GUARDIA puede crear visitas rápidas"""
    
    print("\n" + "=" * 70)
    print("TEST: Validar que solo GUARDIA puede crear visitas rápidas")
    print("=" * 70)
    
    # Login como RESIDENTE
    print("\n[1/2] Login como RESIDENTE...")
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": "residente@test.com",
            "password": "residente123"
        }
    )
    
    if login_response.status_code != 200:
        print(f"ℹ️  Residente no existe, test no aplicable")
        return True
    
    token = login_response.json().get("access_token")
    
    # Intentar crear visita rápida
    print("\n[2/2] Intentar crear visita rápida como RESIDENTE...")
    headers = {"Authorization": f"Bearer {token}"}
    
    visita_data = {
        "nombre_visitante": "Test Visitante",
        "casa_unidad": "101",
        "tipo_visitante": "eventual"
    }
    
    response = requests.post(
        f"{BASE_URL}/visitas/rapida",
        json=visita_data,
        headers=headers
    )
    
    if response.status_code == 403:
        print(f"✅ Acceso denegado correctamente (status 403)")
        return True
    else:
        print(f"❌ Se esperaba 403, se recibió {response.status_code}")
        print(f"   Respuesta: {response.json()}")
        return False


if __name__ == "__main__":
    try:
        result1 = test_crear_visita_rapida()
        result2 = test_error_sin_rol_guardia()
        
        if result1 and result2:
            print("\n✅ TODOS LOS TESTS PASARON")
        else:
            print("\n❌ ALGUNOS TESTS FALLARON")
    except Exception as e:
        print(f"\n❌ Error ejecutando tests: {e}")
