# 🟠 SDD Spec — NIVEL 3: Expansión a LifeOS (Planes en tu Zona + Clima + Calendario y Entregas)

> **Ventana de Tiempo:** Horas 5:30 - 7:30
> **Prerrequisito:** Niveles 1 y 2 completados y validados al 100%.
> **Objetivo:** Transformar el gestor de inventario en un **Dashboard de Vida (LifeOS)** donde el valor y las subidas de tus objetos financian planes reales adaptados al clima y a tu agenda de entregas de Wallapop.

---

## 1. Historias de Usuario del Nivel 3

1. **US-3.1 (Planes Locales Financiados por tu Inventario):** Como usuario, quiero que el dashboard me recomiende planes en mi ciudad (gastronomía, eventos, aire libre, cultura) cuyo coste esté conectado directamente con la subida hoy de mi inventario ($\Delta P_{\text{avg}}$) o el valor acumulado de mis productos listos para vender.
2. **US-3.2 (Clima Inteligente Interior/Exterior):** Como usuario, quiero ver el clima actual y la previsión semanal de mi ciudad y que los planes recomendados se adapten automáticamente a planes de interior (si llueve) o exterior (si hace buen tiempo).
3. **US-3.3 (Calendario Día a Día + Entregas de Wallapop):** Como vendedor y usuario de LifeOS, quiero una agenda diaria/semanal donde gestionar tanto mis tareas personales como las citas de entrega en mano o envío de los productos de mi inventario.

---

## 2. Especificación Funcional por Sub-Módulo

### 2.1 Módulo de Planes Locales Conectado al Inventario (`/api/lifeos/plans` — `Track C` + `Track A`)
* **Motor de Cruce Financiero (ReCommerce $\rightarrow$ LifeOS):**
  * Calcula para el usuario activo:
    * `dailyGainEur`: Suma de variaciones positivas recientes ($\sum \max(0, \text{priceDeltaEur})$).
    * `readyToSellTotalEur`: Suma de $P_{\text{avg}}$ de los artículos en estado `in_stock` o `listed`.
  * Genera un banner inteligente personalizado en la cabecera del módulo:
    * *"💡 El valor medio de tu inventario ha subido **+{dailyGainEur} €** hoy y tienes **{readyToSellTotalEur} €** acumulados en productos listos para vender: aquí tienes planes increíbles en **{city}** dentro de ese presupuesto."*
* **Catálogo y Filtro de Planes:**
  * Categorías: `gastronomia`, `eventos`, `aire_libre`, `cultura`.
  * Cada tarjeta de plan muestra:
    * Coste estimado en euros (`estimatedCostEur`).
    * Badge de equivalencia con el inventario: ej. *"Financiado al 100% con la subida de tu Nintendo Switch (+22 €)"* o *"Equivale al 30% de la venta de tus Auriculares Sony"*.
    * Botón **"📅 Añadir al Calendario"** que agenda el plan directamente en el módulo Día a Día.

### 2.2 Widget de Clima y Condicionamiento de Planes (`/api/lifeos/weather` — `Track C` + `Track A`)
* Consulta el clima de la ciudad del usuario (con API abierta tipo Open-Meteo sin API key obligatoria + fallback instantáneo si no hay red).
* Muestra temperatura actual, estado meteorológico y previsión de 5-7 días.
* **Conexión con Planes:**
  * Si `condition === 'rainy'` (`recommendIndoor: true`), prioriza y destaca los planes `indoor` (museos, gastronomía, cine, escape rooms) mostrando un aviso: *"🌧️ Llueve en {city}: priorizando planes de interior"*.
  * Si hace sol (`sunny`), destaca planes `outdoor` (rutas, terrazas, conciertos al aire libre).

### 2.3 Calendario Día a Día y Entregas de Wallapop (`/api/lifeos/calendar` — `Track C` + `Track A`)
* Vista de agenda limpia por días de la semana con código de colores por tipo de evento:
  * 📦 **Entrega / Envío Wallapop (`wallapop_delivery`)**: Vinculado a un `InventoryItem` concreto (muestra el nombre del producto y el precio acordado $P_{\text{avg}}$).
  * 🎉 **Plan Local (`local_plan`)**: Añadido desde el recomendador de planes.
  * 📌 **Personal (`personal`)**: Tareas diarias del usuario.
* **Acción Rápida desde el Inventario:**
  * Cada producto en "Mi Inventario" incluye un botón *"🤝 Agendar Entrega Wallapop"* que abre un mini-selector rápido (Fecha, Hora, Punto de encuentro / Correos) y lo inserta al instante en el calendario.

---

## 3. Criterios de Aceptación (Definition of Done — Nivel 3)

1. [ ] El módulo de Planes Locales muestra explícitamente el mensaje que relaciona la subida en euros ($\Delta\text{ €}$) y el total acumulado del inventario con el presupuesto de los planes.
2. [ ] El widget de Clima condiciona visiblemente qué planes se recomiendan (`Interior` vs `Exterior`), e incluye un toggle rápido para simular lluvia/sol en la demo si se desea mostrar la reactividad.
3. [ ] El Calendario permite agendar entregas de productos de Wallapop y planes locales, persistiendo los eventos en el perfil del usuario.
