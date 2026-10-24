# 🟡 SDD Spec — NIVEL 2: Rastreo Periódico de Precios y Sistema de Notificaciones

> **Ventana de Tiempo:** Horas 3:30 - 5:30
> **Prerrequisito:** Nivel 1 completado y validado al 100%.
> **Objetivo:** Hacer que el inventario esté "vivo", rastreando la evolución de las 3 métricas ($P_{\min}, P_{\text{avg}}, P_{\max}$) y alertando al usuario de oportunidades de venta.

---

## 1. Historias de Usuario del Nivel 2

1. **US-2.1 (Rastreo Periódico + Modo Demo en Vivo):** Como usuario (y como presentador ante el jurado), quiero que mis productos actualicen sus precios periódicamente vía MCP y disponer de un botón **"⚡ Forzar Actualización de Mercado (Demo Mode)"** para disparar una actualización en tiempo real durante la demo.
2. **US-2.2 (Indicadores de Tendencia Visuales):** Como vendedor, quiero ver en cada producto de mi inventario si su valor está subiendo ($\uparrow$ verde) o bajando ($\downarrow$ rojo) junto con el porcentaje de variación y su gráfico histórico de 3 precios.
3. **US-2.3 (Centro de Notificaciones Inteligente):** Como usuario, quiero recibir avisos claros cuando el precio mínimo, medio o más alto de mis objetos experimente cambios relevantes para saber cuándo publicar en Wallapop.

---

## 2. Especificación Funcional por Sub-Módulo

### 2.1 Motor de Actualización de Mercado (`/api/market/refresh` — `Track C`)
* **Ejecución en Background / Intervalo:**
  * El dashboard puede ejecutar un re-escaneo periódico configurable o ser invocado bajo demanda.
* **Botón "⚡ Forzar Actualización de Mercado (Demo Mode)":**
  * Ubicado en la barra superior del inventario.
  * Al pulsarlo, invoca `POST /api/market/refresh` con `{ userId, demoMode: true }`.
  * Para cada producto del usuario:
    * Consulta el motor MCP Stealth (aplicando variaciones de mercado realistas entre $-8\%$ y $+15\%$ sobre la oferta actual en modo demo para demostrar tanto subidas como bajadas). El modo demo **no toca la red** y **garantiza al menos una subida y una bajada por encima del umbral** en cada clic. La variación se aplica como un único factor sobre $P_{\text{base}}$ y las 3 medidas se recalculan con la fórmula del MCP (§3.2), así se mantiene $P_{\min} < P_{\text{avg}} < P_{\max}$.
    * Añade el nuevo registro `PricePoint` (`timestamp`, `priceMin`, `priceAvg`, `priceMax`) al array `priceHistory` del producto (conservando los últimos 10 puntos).
    * Calcula:
      * `priceDeltaEur = newPriceAvg - previousPriceAvg`
      * `priceDeltaPercent = round(((newPriceAvg - previousPriceAvg) / previousPriceAvg) * 100, 1)`
      * `priceTrend = priceDeltaEur > 0 ? 'up' : priceDeltaEur < 0 ? 'down' : 'stable'`

### 2.2 Generador de Alertas y Centro de Notificaciones (`Track C` + `Track A`)
* Cuando $P_{\min}$, $P_{\text{avg}}$ o $P_{\max}$ de un producto varía de forma significativa ($\ge 4\%$ o $\ge 5\text{ €}$):
  * Se crea **una sola** `MarketNotification` por producto (la métrica con mayor variación %) asociada al `userId`:
    * **Ejemplo Subida ($P_{\text{avg}}$):** *"🔔 ¡Subida detectada! El **precio medio** de tu Nintendo Switch OLED ha subido un **+12%** (185 € → 207 €). ¡Buen momento para publicar!"*
    * **Ejemplo Bajada ($P_{\min}$):** *"📉 El **precio mínimo** de los monitores LG ha bajado **10 €** esta semana (120 € → 110 €)."*
* **UI del Centro de Notificaciones (`Track A`):**
  * Campana con contador de alertas no leídas en el header + panel lateral o tarjeta dedicada en el Bento Grid.
  * Permite marcar alertas como leídas y hacer clic en una alerta para resaltar el producto correspondiente en el inventario.

### 2.3 Visualización de Evolución Histórica (`Track A`)
* Cada tarjeta de producto en **"Mi Inventario"** incorpora:
  * Badge de tendencia junto al precio medio:
    * Subida: `↑ +12.0% (+22 €)` en verde esmeralda.
    * Bajada: `↓ -5.4% (-10 €)` en rojo coral.
  * Mini-gráfico (Sparkline SVG ligero sin dependencias pesadas) o desglose visual que muestra la evolución histórica de las 3 curvas ($P_{\min}, P_{\text{avg}}, P_{\max}$).

---

## 3. Criterios de Aceptación (Definition of Done — Nivel 2)

1. [ ] El botón **"⚡ Forzar Actualización de Mercado (Demo Mode)"** actualiza en vivo los precios de los productos con animación de carga clara.
2. [ ] Los productos muestran indicadores $\uparrow$ verde o $\downarrow$ rojo con el cambio en euros y porcentaje.
3. [ ] El histórico `priceHistory` de cada producto almacena y visualiza la evolución de las 3 medidas ($P_{\min}, P_{\text{avg}}, P_{\max}$).
4. [ ] El Centro de Notificaciones muestra mensajes ricos y contextualizados con el nombre del producto, la métrica afectada y los valores antiguo $\rightarrow$ nuevo.
