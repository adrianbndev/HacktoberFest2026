# 🔍 Revisión de Specs (Track C — Matías, 24/10/2026)

> Revisión de `AGENTS.md`, `CLAUDE.md` y todo `.agent/` antes de escribir código.
> ✅ = ya corregido en los specs en este mismo cambio · ❓ = decisión del equipo · 📝 = recomendación para quien implemente.

## Decisiones pendientes antes de programar

1. **¿Quién monta la Fase 1.0?** (punto 3)
2. **¿Relajamos el gate de niveles para el backend?** (punto 2)
3. **¿P_min / P_max deben depender del estado del objeto?** (punto 7)

---

## 🔴 Rompen algo

| # | Problema | Estado |
| :-: | :--- | :-: |
| 1 | **El presupuesto de 6 s no se cumplía en el peor caso.** Visión y MCP van en serie: 4 s + 2,2 s de jitter + 3,5 s de timeout = 9,7 s. Y el jitter antes de *una sola* petición no te hace parecer humano, solo añade latencia. **Arreglo aplicado:** Visión 3 s; MCP con *deadline* total de 2,5 s (jitter incluido); en `/valuate` jitter corto (200–600 ms); el rango 800–2200 ms se queda para peticiones seguidas en `/refresh`. | ✅ |
| 2 | **El gate estricto deja paradas a 2 de 3 personas.** `AGENTS.md` prohíbe escribir código de N+1 hasta cerrar N. El MCP (C) se termina mucho antes que cámara + visión (B), y **Track B no tiene ninguna tarea en los niveles 2-4**. Los agentes cumplirán esa regla al pie de la letra. **Propuesta:** el gate se aplica a lo que se *muestra en la UI*, no al backend; y dar el Nivel 4 (GitHub + resumen IA) a Adri, que reutiliza su cliente de IA. | ❓ |
| 3 | **Nadie es dueño de `src/types/sdd.ts`, `src/lib/store/`, `/api/auth`, `/api/inventory` ni `/api/notifications`.** La matriz da "Lectura" a los tres en `sdd.ts` y las rutas no aparecen. Hay que nombrar a alguien para la Fase 1.0. | ❓ |
| 4 | **El botón de demo podía no generar ninguna alerta delante del jurado** (variación aleatoria por debajo del umbral, o redondeo a 0 € en objetos baratos), y variar min/avg/max por separado podía romper `P_min < P_avg < P_max`. **Arreglo aplicado:** el modo demo no toca la red, garantiza al menos una subida y una bajada por clic, y aplica un único factor sobre `P_base` antes de recalcular con la fórmula. | ✅ |
| 5 | **El fallback de visión no puede saber qué hay en la foto.** Sin red tendría que inventarse el producto: una taza que sale como "Nintendo Switch" queda peor que un error. **Propuesta (Track B):** el fallback es un campo para escribir el nombre a mano + `conditionScore` por defecto; el MCP sigue igual. | 📝 |

## 🟡 Contradicciones y huecos de contrato

| # | Problema | Estado |
| :-: | :--- | :-: |
| 6 | Con `W = 0.65 + 0.50·s/100`, score 75 da 1,025, no 1,00. La tabla cuadra con la fórmula; se ha corregido la frase (1,00 con score 70). | ✅ |
| 7 | **P_min y P_max casi no dependen del estado.** `P_max = max(P85(S), 1.24·P_avg)` → un objeto "Para piezas" hereda el techo de los impecables, y el P_min de un "Nuevo" es el P20 crudo. Choca con US-1.4 ("3 precios ajustados al estado"). Si deben depender: multiplicar también los percentiles por `W_health`. Además, en objetos de ~2 € el `round` puede dar `P_min = P_avg` o 0 € → hace falta un mínimo de 1 € y forzar el orden estricto. | ❓ |
| 8 | Faltaban tipos de respuesta en `sdd.ts`. Añadidos en `architecture.md` §2.6: `VisionAnalysis`, `ValuationRequest`, `ValuationResult`, `MarketRefreshResponse`. | ✅ |
| 9 | No había endpoint de notificaciones (Ales tiene que listarlas y marcarlas como leídas). Añadidos `GET /api/notifications?userId=` y `PATCH /api/notifications`. El dueño se decide con el punto 3. `delivery_reminder` no lo genera ningún spec todavía: su tipado se decide al llegar a L3. | ✅ |
| 10 | L2 decía "cada vez que cambia P_min, P_avg o P_max" (3 objetos × 3 métricas = 9 alertas por clic) y `architecture.md` decía umbral. Unificado: umbral ≥5 % o ≥5 € y **una alerta por objeto** (la métrica con mayor variación). | ✅ |
| 11 | Valores que no coincidían, ya unificados: imagen <350 KB (1024 px, JPEG 0,78); polling del PC **1 s** (con 1,5 s más la subida no se cumplía "aparece en <1,5 s"); timeouts (ver punto 1); presupuesto de planes = ΣP_avg de lo listo para vender (como en el spec L3). | ✅ |

## 🟢 Riesgos prácticos (recomendaciones)

| # | Riesgo | Para |
| :-: | :--- | :-: |
| 12 | **Las cabeceras "stealth" no pasarán Datadome/Cloudflare.** `Sec-Ch-Ua-Platform: "Linux"` está fijo mientras el UA cambia entre Mac, Windows e iOS (huella incoherente); Safari y Firefox no envían `Sec-Ch-Ua`; y la huella TLS del `fetch` de Node no es la de un navegador. Lo realista: Wallapop en vivo y el resto por fallback, así que **la calidad del catálogo semilla es la demo**. Idea barata: que la visión devuelva también `estimatedRetailEur` como `P_base` cuando el catálogo no tenga el modelo. Si un escaneo es en vivo y el siguiente por fallback, el salto de precio genera alertas falsas: comparar solo escaneos del mismo origen. | C |
| 13 | **Nadie usa el servidor MCP como tal.** `/api/market/valuate` llama a la librería directamente; `src/mcp/server.ts` es un envoltorio fino por stdio sobre las mismas funciones, para enseñarlo conectado a Claude. No hace falta un cliente MCP dentro de Next. | C |
| 14 | **GitHub sin token: 10 búsquedas/min por IP**, y en el recinto la IP es compartida. Usar `GITHUB_TOKEN`, el filtro `good-first-issues:>0` en la búsqueda de repos, contar issues con **una** llamada a `search/issues` agrupando por repo, y pedir el resumen IA de todos los repos en una sola llamada. | C |
| 15 | **Open-Meteo necesita lat/lon, no la ciudad.** Mapa fijo ciudad → coordenadas (sirve también para la búsqueda de Wallapop). | C |
| 16 | **El móvil puede no llegar al PC:** las redes de hackathon suelen aislar dispositivos entre sí. Probarlo en la primera hora con un móvil real; plan B: túnel (cloudflared) o hotspot del móvil. Hacer la demo con `next build && next start`: según la versión, `next dev` bloquea recursos `/_next` pedidos desde orígenes que no son localhost (`allowedDevOrigins`) y la página móvil podría cargar sin JS (el botón de cámara no haría nada). | Todos |
| 17 | **Fotos como data URL en `store.json`:** cada lectura del inventario arrastra ~300 KB por objeto. Mejor servirlas por `/api/photo/[id]` (con `next start`, lo escrito en `public/` en ejecución no se sirve). Escrituras del JSON: archivo temporal + renombrar, y el estado en `globalThis` para que no se pierda con la recarga en caliente. | Fase 1.0 |
