# Evidencia O0 — 2026-11-03 (CDMX)

- Base leída: main `76bc9d619836f0872241741570fb7974e51d2bf6`.
- Ejecución local: `python3 -m unittest discover -s labs/contingency -p 'test_*.py' -v`.
- Resultado: **18 aprobadas**, archivos SQLite temporales reales y HTTP loopback.
- Navegador local: **no ejecutado**. No hay Chromium instalado; el instalador
  Playwright devolvió un ZIP inválido. Se conserva la prueba y se ejecuta en CI.
- CI: **no ejecutada**. Workflow **Contingency lab (synthetic SQLite)** preparado.
  La publicación inicial fue bloqueada; Salvador autorizó expresamente publicar
  la rama y abrir un PR en borrador. Consultar sus checks antes de declarar CI aprobada.
- Prueba en dispositivo de Salvador: **pendiente**.
- Corte físico de internet/electricidad: **pendiente**. O0 no hace solicitudes externas.
- PostgreSQL/RLS, Clerk, QR actuales, firmas y piloto productivo: **fuera de O0**.

No confundir el receptor simulado con un backend remoto ni con el servicio desplegado.
No se usaron personas, condominios ni movimientos reales. No se aplicaron migraciones,
no se cambiaron flags y no se habilitó contingencia en ningún cliente.
