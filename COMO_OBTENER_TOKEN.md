# 🔐 CÓMO OBTENER EL TOKEN PARA DEBUGGEAR

## Paso 1: Login en GitHub Codespaces
```
https://verbose-xylophone-7v5p45gj7q79hx4vv-8000.app.github.dev/
```

Login: `test@example.com` / `test123`

## Paso 2: Ir a Panel de Administración
Click en "🏢 Panel de Administración"

## Paso 3: Abrir consola del navegador
Presiona `F12` → Tab `Console`

## Paso 4: Obtener token completo

En la consola, ejecuta:
```javascript
localStorage.getItem('auth_token')
```

Debería mostrar algo como:
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyX3Rlc3RfMDAxIiwicm9sZSI6IkFETUlOIiwibWV0aG9kIjoibG9jYWwiLCJpYXQiOjE3Njk3ODY4NzYsImV4cCI6MTc2OTc5MDQ3Nn0.D4OGXSR8hZKx3F642Iu9T0HkQCrDvSqL8EtQNpoiI7A
```

**Copia TODO, incluyendo los puntos (.) que separan las 3 partes**

## Paso 5: Ejecutar script de debug
```bash
cd /workspaces/MSP_AXS
python3 extraer_token.py
```

Pega el token completo cuando te lo pida.

## Paso 6: Compartir resultados
Compartir:
1. El output del script `extraer_token.py`
2. Los logs del servidor (terminal donde corre uvicorn)
   - Buscar líneas con: `🔍 Authorization header` o `❌ JWT Error`
