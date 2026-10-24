# 📈 MOD-05: Rastreo Periódico de Precios, Botón Demo y Centro de Alertas

* **Nivel SDD:** 🟡 Nivel 2 (Horas 3:30 - 5:30)
* **Responsables:** **Track C (Matías)** — Motor `/api/market/refresh` | **Track A (Ales)** — Tendencias UI, Sparklines y Centro de Notificaciones
* **Estado Actual:** `🔒 LOCKED (Requiere Gate Nivel 1)`
* **SLA de Latencia:** Refresco de inventario completo $\le 2500\text{ ms}$

---

## 1. Responsabilidad Única (SRP) y Diseño SOLID

* **`MarketRefreshUseCase` (`Track C`):**
  * Toma el inventario actual del usuario, obtiene una nueva instantánea de precios $(P_{\min}, P_{\text{avg}}, P_{\max})$ para cada producto, añade el nuevo punto a `priceHistory` y calcula la variación exacta respecto al escaneo anterior.
  * Genera objetos `MarketNotification` tipados explicando qué métrica cambió (`priceMin`, `priceAvg` o `priceMax`), el porcentaje y el cambio en euros.
* **Componentes Visuales de Tendencia (`Track A`):**
  * `TrendIndicatorBadge.tsx`: Muestra $\uparrow$ verde o $\downarrow$ rojo con $\Delta\%$ y $\Delta\text{ €}$.
  * `PriceHistorySparkline.tsx`: Gráfico SVG puro que dibuja las 3 curvas ($P_{\min}$ punteada inferior, $P_{\text{avg}}$ sólida central, $P_{\max}$ punteada superior).
  * `NotificationCenterPanel.tsx`: Centro de alertas con filtro de no leídas y acción directa *"Publicar ahora en Wallapop"*.

---

## 2. Reglas de Generación de Notificaciones

Cada actualización de mercado evalúa las 3 métricas del producto:
1. **Alerta de Subida de Precio Medio (`type: 'price_up'`, `metricChanged: 'priceAvg'`):**
   * *"🔔 ¡Subida detectada! El **precio medio** de tu {item.name} ha subido un **+{deltaPercent}%** ({oldAvg} € → {newAvg} €). ¡Buen momento para publicar!"*
2. **Alerta de Variación en Precio Mínimo (`type: 'price_down'`, `metricChanged: 'priceMin'`):**
   * *"📉 El **precio mínimo** de {item.name} ha bajado **{absDeltaEur} €** esta semana ({oldMin} € → {newMin} €)."*
3. **Alerta de Techo Máximo (`type: 'sell_opportunity'`, `metricChanged: 'priceMax'`):**
   * *"🚀 ¡Nuevo techo de mercado! El **precio más alto** de {item.name} alcanza los **{newMax} €** en Wallapop."*

---

## 3. Archivos del Módulo (`Track C` + `Track A`)

| Archivo | Track | Propósito | Límite Líneas |
| :--- | :---: | :--- | :---: |
| `backend/app/mcp/market_refresh.py` | Track C | Lógica pura en Python de re-escaneo, cálculo de deltas y creación de alertas | $\le 150$ |
| `backend/app/routers/market.py` | Track C | Endpoint FastAPI `POST /api/market/refresh` para job periódico y botón *"Forzar Actualización (Demo Mode)"* | $\le 70$ |
| `src/components/inventory/TrendIndicatorBadge.tsx` | Track A | Badge $\uparrow$ verde / $\downarrow$ rojo con porcentaje y euros | $\le 70$ |
| `src/components/inventory/PriceHistorySparkline.tsx` | Track A | Gráfico SVG de evolución de las 3 medidas ($P_{\min}, P_{\text{avg}}, P_{\max}$) | $\le 120$ |
| `src/components/notifications/NotificationCenter.tsx` | Track A | Panel de alertas con contador e interacción con el inventario | $\le 160$ |

---

## 4. Checklist de Control y Calidad (MOD-05)

- [ ] Botón **"⚡ Forzar Actualización de Mercado (Demo Mode)"** visible y funcional en el dashboard.
- [ ] Al pulsar el botón, cada producto añade un nuevo `PricePoint` a su `priceHistory` manteniendo la invariante $P_{\min} < P_{\text{avg}} < P_{\max}$.
- [ ] Los indicadores visuales $\uparrow$ (verde) y $\downarrow$ (rojo) coinciden exactamente con el signo de `priceDeltaEur`.
- [ ] El gráfico histórico renderiza las 3 series ($P_{\min}, P_{\text{avg}}, P_{\max}$) sin errores de hidratación en Next.js.
- [ ] El Centro de Notificaciones registra y muestra en vivo los avisos generados en cada refresco.
