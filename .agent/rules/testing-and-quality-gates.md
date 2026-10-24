# 🧪 Reglas de Calidad, Testing y Harness de Verificación (`.agent/rules/testing-and-quality-gates.md`)

> **Aplicación:** Regla activa siempre (`always_on`). Define los criterios de calidad automatizados ("Harness") que cada módulo y cada Nivel deben superar antes de darse por terminados.

---

## 1. Filosofía de "Agentic Harness" en el Hackathon

Un agente nunca debe declarar *"Ya está listo el Nivel X"* basándose únicamente en que el código parece correcto. Debe existir un **Harness de Verificación Ejecutable** que compruebe:
1. **Compilación y Tipos (`tsc --noEmit`):** Cero errores de TypeScript en todo el repositorio.
2. **Invariantes de Dominio (Tests Unitarios Rápidos):** Las fórmulas matemáticas y transformaciones cumplen las reglas de negocio.
3. **Contratos de API (Smoke Tests):** Los endpoints responden con el JSON esperado en $< 6\text{ segundos}$ tanto con red como sin red (modo fallback).
4. **Integridad SDD:** Ningún archivo del Nivel $N+1$ se ha creado prematuramente y el estado en `.agent/roadmap.md` y `.agent/modules/INDEX-control-tower.md` está sincronizado.

---

## 2. Invariantes Matemáticas y de Negocio Obligatorias

Todo test y validador de runtime debe asegurar estas **5 invariantes innegociables**:

1. **Invariante de los 3 Precios MCP:**
   $$\forall \text{ item } \in \text{Inventory}: \quad 0 < \text{priceMin} < \text{priceAvg} < \text{priceMax}$$
   *(Si una muestra cruda de mercado tiene precios idénticos, el motor aplica el diferencial de liquidez/techo para garantizar que las 3 métricas sean siempre distintas y coherentes).*
2. **Invariante de Salud del Producto:**
   $$0 \le \text{conditionScore} \le 100 \quad \land \quad \text{conditionLabel} \in \{\text{'Nuevo'}, \text{'Como nuevo'}, \text{'Buen estado'}, \text{'Desgaste visible'}, \text{'Para piezas'}\}$$
3. **Invariante de Monotonicidad de Salud:**
   Para un mismo producto y muestra de mercado, si $\text{conditionScore}_A > \text{conditionScore}_B$, entonces:
   $$P_{\text{avg}}(\text{score}_A) \ge P_{\text{avg}}(\text{score}_B)$$
4. **Invariante de Tendencias y Notificaciones (Nivel 2):**
   * Si $\text{newPriceAvg} > \text{oldPriceAvg} \implies \text{priceTrend} = \text{'up'}$ y $\text{priceDeltaPercent} > 0$.
   * Si $\text{newPriceAvg} < \text{oldPriceAvg} \implies \text{priceTrend} = \text{'down'}$ y $\text{priceDeltaPercent} < 0$.
5. **Invariante de Presupuesto LifeOS (Nivel 3):**
   * Todo `LocalPlan` recomendado bajo el filtro de inventario debe tener `estimatedCostEur` $\le \text{readyToSellTotalEur}$.

---

## 3. Protocolo de Cierre de Módulo y de Nivel (Quality Gate)

Antes de marcar cualquier tarea como `[x]` en [`.agent/roadmap.md`](../roadmap.md) o cambiar un módulo a `✅ DONE` en [`.agent/modules/INDEX-control-tower.md`](../modules/INDEX-control-tower.md), el agente debe ejecutar:

1. **Verificación de Harness SDD:**
   ```bash
   node .agent/skills/sdd-gatekeeper/scripts/verify-sdd-harness.mjs
   ```
2. **Verificación de Tipos Frontend y Tests Backend en Python (`pytest`):**
   ```bash
   npm run typecheck && pytest backend/tests
   ```
3. **Actualización Documental:**
   * Actualizar el estado y métricas del módulo en `.agent/modules/MOD-0X-*.md`.
   * Marcar las casillas verificadas en `.agent/roadmap.md`.
