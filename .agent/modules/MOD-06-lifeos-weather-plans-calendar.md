# 🌤️ MOD-06: Expansión LifeOS — Planes Locales + Clima + Calendario y Entregas

* **Nivel SDD:** 🟠 Nivel 3 (Horas 5:30 - 7:30)
* **Responsables:** **Track C (Matías)** — Servicios LifeOS & Cruce de Presupuesto | **Track A (Ales)** — Widgets Bento Grid
* **Estado Actual:** `🔒 LOCKED (Requiere Gate Nivel 2)`
* **SLA de Latencia:** Respuesta combinada Clima + Planes + Agenda $\le 1200\text{ ms}$

---

## 1. Responsabilidad Única (SRP) y Diseño SOLID

* **`InventoryBudgetBridge` (Función Pura de Dominio):**
  * Conecta matemáticamente el Nivel 1 y Nivel 2 con el Nivel 3:
    * Calcula `todayGainEur`: suma de subidas recientes ($\Delta P_{\text{avg}} > 0$) en el inventario del usuario.
    * Calcula `liquidInventoryEur`: valor acumulado de artículos listos para vender.
    * Empareja cada `LocalPlan` con el artículo o la subida que lo financia (ej. *"Cubierto al 100% por la subida hoy de +25 € en tu inventario"*).
* **`WeatherService` (`OpenMeteoAdapter` + `FallbackWeatherAdapter`):**
  * Obtiene el clima real de la ciudad del perfil activo (`Madrid`, `Barcelona`, `Valencia`) y determina `recommendIndoor: boolean`.
* **`CalendarService`:**
  * Unifica eventos personales, planes locales agendados y **citas de entrega o envío de productos vendidos en Wallapop**.

---

## 2. Archivos del Módulo (`Track C` + `Track A`)

| Archivo | Track | Propósito | Límite Líneas |
| :--- | :---: | :--- | :---: |
| `backend/app/lifeos/weather_service.py` | Track C | Cliente Python async Open-Meteo + modo simulación de lluvia/sol + fallback | $\le 110$ |
| `backend/app/lifeos/plans_engine.py` | Track C | Catálogo de planes por ciudad + cruce con valor/subida del inventario | $\le 150$ |
| `backend/app/lifeos/calendar_service.py` | Track C | Gestión de agenda y entregas de Wallapop vinculadas a `InventoryItem` | $\le 110$ |
| `backend/app/routers/lifeos.py` | Track C | Endpoints FastAPI `/api/lifeos/{weather,plans,calendar,github}` | $\le 90$ |
| `src/components/lifeos/LocalPlansWidget.tsx` | Track A | Buscador y recomendador con banner de presupuesto del inventario | $\le 170$ |
| `src/components/lifeos/WeatherForecastWidget.tsx` | Track B/A | Widget meteorológico con filtro automático Interior/Exterior | $\le 120$ |
| `src/components/lifeos/DailyCalendarWidget.tsx` | Track B/A | Agenda diaria/semanal con citas de entrega Wallapop y tareas | $\le 170$ |

---

## 3. Checklist de Control y Calidad (MOD-06)

- [ ] Banner financiero visible en Planes Locales: *"El valor medio de tu inventario ha subido +{X} € hoy y tienes {Y} € acumulados en productos listos para vender..."*.
- [ ] Todos los planes recomendados respetan el presupuesto calculado del inventario (`estimatedCostEur <= totalBudget`).
- [ ] Si el clima está en modo `rainy` (lluvia), se priorizan planes `indoor`; si está `sunny` (soleado), se destacan planes `outdoor`.
- [ ] Botón *"🤝 Agendar Entrega Wallapop"* en las tarjetas del inventario crea un evento `wallapop_delivery` directamente en el Calendario.
