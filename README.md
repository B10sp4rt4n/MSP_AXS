# MSP_AXS

Esqueleto del backend `axs-backend` (FastAPI) con la estructura indicada.

Instrucciones rápidas:

- Instalar dependencias:

```
python -m pip install -r requirements.txt
```

- Ejecutar servidor (desde la raíz del repo):

```
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Endpoints de ejemplo:

- `GET /` -> estado
- `GET /msp/` -> lista msps (placeholder)
- `GET /qr/generate?q=texto` -> genera QR placeholder
