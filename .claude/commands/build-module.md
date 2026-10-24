Implementa o continúa el módulo indicado en `$ARGUMENTS` (ej. `MOD-00`, `MOD-01`, `MOD-02`, `MOD-03`, `MOD-04`, `MOD-05`, `MOD-06`, `MOD-07`) aplicando estrictamente la metodología SDD y SOLID:

1. Lee `.agent/modules/INDEX-control-tower.md` y la ficha específica del módulo en `.agent/modules/$ARGUMENTS*.md`.
2. Comprueba que el Nivel del módulo no esté `🔒 LOCKED`. Si el nivel anterior no está completado al 100% en `.agent/roadmap.md`, detente y avisa al usuario.
3. Sigue la receta de 6 pasos de `.agent/skills/solid-module-scaffolder/SKILL.md` y las reglas de `.agent/rules/clean-code-solid.md`:
   - Contratos en `src/types/sdd.ts` + modelos Pydantic v2 en `backend/app/models/sdd.py`.
   - Funciones puras de dominio + Adaptador Live con timeout + Adaptador Fallback determinista (Liskov).
   - Ningún archivo mayor a 220 líneas, cero `any`.
4. Al terminar, ejecuta `node .agent/skills/sdd-gatekeeper/scripts/verify-sdd-harness.mjs` y actualiza el progreso en la ficha del módulo y en `.agent/roadmap.md`.
