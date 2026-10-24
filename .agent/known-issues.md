# ⚠️ Problemas conocidos pendientes (`.agent/known-issues.md`)

> Riesgos detectados que se han dejado así a propósito por ahora. Antes de tocar el módulo afectado, revisa esta lista; cuando se resuelva uno, bórralo de aquí en el mismo commit.

| # | Dónde | Problema | Riesgo en la demo | Responsable |
| :---: | :--- | :--- | :--- | :--- |
| 1 | `backend/app/vision/orchestrator.py` (`VISION_TIMEOUT_SEC`, por defecto `6.0`) y `.env.example` | El timeout de Visión IA es de 6 s, pero las guardrails (§2) dan a Visión un máximo de 2,5 s, y 6 s a todo el flujo foto → salud → 3 precios. | Si Ollama responde lento, Visión sola agota el presupuesto y, sumada a la tasación del MCP (≤ 2,8 s), la tasación tarda más de 6 s delante del jurado en lugar de pasar al fallback determinista. | Ales (Visión IA) |
