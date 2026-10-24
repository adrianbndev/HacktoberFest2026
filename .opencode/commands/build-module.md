---
description: Implementa un módulo SDD (MOD-00 a MOD-07) siguiendo Clean Architecture, SOLID y verificando el harness
---
Implementa o continúa el módulo indicado en `$ARGUMENTS` aplicando estrictamente SDD y SOLID:

1. Lee `.agent/modules/INDEX-control-tower.md` y `.agent/modules/$ARGUMENTS*.md`.
2. Verifica que el Nivel actual esté desbloqueado en `.agent/roadmap.md`.
3. Aplica `.agent/skills/solid-module-scaffolder/SKILL.md` y `.agent/rules/clean-code-solid.md`.
4. Ejecuta `node .agent/skills/sdd-gatekeeper/scripts/verify-sdd-harness.mjs` y actualiza el estado en `.agent/modules/INDEX-control-tower.md` y `.agent/roadmap.md`.
