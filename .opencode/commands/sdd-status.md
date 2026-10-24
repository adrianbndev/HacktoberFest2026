---
description: Audita el estado SDD, ejecuta el harness de calidad y muestra el progreso por módulo y Track
---
Ejecuta una auditoría completa del estado SDD del proyecto siguiendo estos pasos:

1. Ejecuta el harness de verificación:
   `node .agent/skills/sdd-gatekeeper/scripts/verify-sdd-harness.mjs`
2. Ejecuta la suite de invariantes matemáticas del motor MCP:
   `node .agent/skills/mcp-stealth-builder/scripts/test-mcp-math.mjs`
3. Lee `.agent/modules/INDEX-control-tower.md` y `.agent/roadmap.md`.
4. Muestra un resumen ejecutivo con el estado de cada módulo (`MOD-00` a `MOD-07`) y las tareas desbloqueadas para **Ales (Track A)**, **Adri (Track B)** y **Matías (Track C)**.
