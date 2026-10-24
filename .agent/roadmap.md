# 🗺️ SDD Roadmap & Gatekeeping Checklist (Hacktoberfest 2026 — 9h)

> **REGLA DE BLOQUEO SDD:** Ningún agente (Antigravity CLI, Claude Code u OpenCode) puede iniciar tareas de un Nivel $N+1$ hasta que **todos** los ítems del Nivel $N$ estén marcados como `[x]` y el Criterio de Cierre haya sido validado.

---

## 🏁 FASE 0: Bootstrap SDD & Estructura Agéntica (Completado)
- [x] Generar `AGENTS.md` y `CLAUDE.md` compatibles con Antigravity CLI, Claude Code y OpenCode.
- [x] Generar `.agent/roadmap.md` con priorización estricta en 4 niveles.
- [x] Generar `.agent/architecture.md` con esquemas TypeScript y contratos REST/SSE.
- [x] Generar `.agent/mcp/stealth-market-mcp.md` con especificación anti-bots y fallback determinista.
- [x] Generar `.agent/rules/hackathon-guardrails.md` con reglas de seguridad y demo.
- [x] Generar `.agent/specs/level-*.md` y `.agent/tracks/team-tracks-contract.md`.

---

## 🟢 NIVEL 1: El Core Absoluto — Inventario IA, Sync Móvil-PC, MCP Stealth y Login (Horas 0:00 - 3:30)
> 📄 **Spec Detallada:** [`.agent/specs/level-1-core-recommerce.md`](specs/level-1-core-recommerce.md)

### 1.0 Inicialización del Proyecto Base (`MOD-00` — Común para los 3 Tracks antes de ramificar)
- [ ] Inicializar Frontend Next.js (`src/`, App Router + TypeScript + Tailwind CSS + `lucide-react` + Rewrite Proxy `/api/* -> :8000`) y Backend Python FastAPI (`backend/app/main.py`, `requirements.txt`, `Pillow`, `FastMCP`).
- [ ] Definir todas las interfaces compartidas en `src/types/sdd.ts` (Frontend) y los modelos Pydantic v2 equivalentes en `backend/app/models/sdd.py` (Backend) según [`.agent/architecture.md`](architecture.md).
- [ ] Crear capa de persistencia local atómica en Python (`backend/app/store/repository.py` con `RLock` + `.tmp` `os.replace`) y perfiles semilla para **Ales**, **Adri**, **Matías** y **Jurado** + endpoint `/api/store/reset`.
- [ ] Configurar `.env.example`, `backend/Dockerfile` y `docker-compose.yml` (con volumen `./data` y túnel HTTPS `cloudflared` para evitar AP Isolation en el móvil).

### 1.1 Inicio de Sesión y Perfil de Usuario (`Track A - Ales`)
- [ ] Selector de sesión rápida / Login sin fricción (Ales, Adri, Matías, Jurado) con persistencia de sesión.
- [ ] Vista principal del Perfil con **"Mi Inventario"** en layout Bento Grid.
- [ ] KPI de **Valoración Total Acumulada** del inventario (mostrando suma de $P_{\min}$, $P_{\text{avg}}$ y $P_{\max}$).

### 1.2 Flujo Cámara Móvil $\leftrightarrow$ Web PC sin Fricción (`Track B - Adri`)
- [ ] Botón destacado en PC: *"📱 Añadir Producto con el Móvil"*.
- [ ] Generación de sesión única (`/mobile-capture/[sessionId]`) con código QR escaneable y link directo integrable en LAN/túnel.
- [ ] Interfaz móvil limpia con apertura directa de cámara trasera (`<input type="file" accept="image/*" capture="environment" />`) y compresión cliente en Canvas ($\le 1024\text{ px}$, JPEG $0.78$, $<350\text{ KB}$) para evitar errores de payload.
- [ ] Sincronización en tiempo real Móvil $\rightarrow$ PC mediante SSE (`/api/capture-session/[sessionId]/stream`) + fallback de *short-polling* cada $1\text{ s}$.
- [ ] Recepción instantánea de la foto en la pantalla del PC y disparo automático del análisis sin intervención manual.

### 1.3 Reconocimiento por Visión IA + Salud/Estado + SEO (`Track B - Adri`)
- [x] Endpoint `/api/vision/analyze` que recibe la imagen capturada.
- [x] Identificación precisa de: **Nombre exacto, Categoría, Marca y Modelo**.
- [x] Diagnóstico de **Estado / Salud del Producto**:
  - `conditionScore` numérico de $0$ a $100\%$.
  - `conditionLabel` categorizado (`Nuevo`, `Como nuevo`, `Buen estado`, `Desgaste visible`, `Para piezas`).
  - Justificación visual breve del estado detectado.
- [x] Generación automática de **Título SEO** y **Descripción persuasiva** lista para copiar y publicar en Wallapop.

### 1.4 Motor MCP "Human-Like" (Anti-Bot) y las 3 Medidas de Precio (`Track C - Matías`)
- [ ] Implementar motor MCP Stealth (`src/mcp/stealth-market-mcp.ts` y `/api/market/valuate`) siguiendo [`.agent/mcp/stealth-market-mcp.md`](mcp/stealth-market-mcp.md).
- [ ] Simulación de navegación humana: rotación de User-Agents reales, cabeceras HTTP completas y *jitter* aleatorio ($800\text{ ms} - 2200\text{ ms}$).
- [ ] Consulta multi-plataforma (Wallapop, Vinted, Milanuncios, eBay) ponderada por el `conditionScore` ($0-100\%$).
- [ ] Capa de **Fallback Determinista Blindado** si la red del recinto bloquea peticiones o excede el timeout.
- [ ] Retorno y visualización clara en UI de las **3 medidas obligatorias**:
  1. 📉 **Precio Mínimo ($P_{\min}$):** Venta rápida / liquidez inmediata.
  2. 🎯 **Precio Medio ($P_{\text{avg}}$):** Valor real de mercado ajustado por salud.
  3. 📈 **Precio Más Alto ($P_{\max}$):** Techo de mercado para artículos impecables.
- [ ] Guardado automático/confirmado del producto tasado en el perfil del usuario.

> ✅ **CRITERIO DE CIERRE NIVEL 1 (GATE 1):**
> - [ ] El usuario inicia sesión, abre el QR en el teléfono, toma una foto real, la imagen aparece sola en la pantalla del PC en $<1.5\text{ s}$, la IA muestra salud ($0-100\%$) + SEO, el MCP devuelve $P_{\min}, P_{\text{avg}}, P_{\max}$ en $<6\text{ s}$, y el objeto queda guardado en "Mi Inventario".

---

## 🟡 NIVEL 2: Rastreo Periódico de Precios y Sistema de Notificaciones (Horas 3:30 - 5:30)
> 📄 **Spec Detallada:** [`.agent/specs/level-2-price-tracking-alerts.md`](specs/level-2-price-tracking-alerts.md)

### 2.1 Actualización Periódica de Precios (`Track C - Matías`)
- [ ] Endpoint y servicio de re-escaneo de mercado (`/api/market/refresh`) que consulta el MCP para todos los productos del inventario del usuario.
- [ ] Actualización de `priceHistory` en cada producto guardando timestamp y la terna $(P_{\min}, P_{\text{avg}}, P_{\max})$.
- [ ] **Botón Especial de Demo:** *"⚡ Forzar Actualización de Mercado (Demo Mode)"* visible en el dashboard para disparar fluctuaciones y re-escaneo en vivo frente al jurado sin esperar horas.

### 2.2 Alertas, Tendencias y Centro de Notificaciones (`Track A - Ales`)
- [ ] Badges visuales de tendencia en cada tarjeta de producto:
  - $\uparrow$ **Verde** (subida de precio respecto al escaneo anterior, con $\%$ y $\Delta\text{ €}$).
  - $\downarrow$ **Rojo** (bajada de precio respecto al escaneo anterior, con $\%$ y $\Delta\text{ €}$).
- [ ] Gráfico / Sparkline de evolución histórica de las 3 medidas ($P_{\min}, P_{\text{avg}}, P_{\max}$).
- [ ] **Centro de Notificaciones** en el perfil con alertas accionables (ej. *"🔔 ¡Subida detectada! El precio medio de tu Nintendo Switch ha subido un +12% (185 € → 207 €). ¡Buen momento para publicar!"*).

> ✅ **CRITERIO DE CIERRE NIVEL 2 (GATE 2):**
> - [ ] Al pulsar *"Forzar Actualización de Mercado (Demo Mode)"* (o por ejecución periódica), los productos actualizan su historial de 3 precios, muestran flechas $\uparrow/\downarrow$ con porcentajes y generan notificaciones en tiempo real en el Centro de Alertas.

---

## 🟠 NIVEL 3: Expansión a LifeOS — Planes en tu Zona + Día a Día (Horas 5:30 - 7:30)
> 📄 **Spec Detallada:** [`.agent/specs/level-3-lifeos-plans-calendar.md`](specs/level-3-lifeos-plans-calendar.md)

### 3.1 Módulo de Planes Locales Conectado al Inventario (`Track C + Track A`)
- [ ] Servicio `/api/lifeos/plans` con recomendador de planes locales (gastronomía, eventos, aire libre, cultura).
- [ ] **Cruce Inteligente con Nivel 1 y 2:** Cálculo del presupuesto desbloqueado por la subida reciente del inventario ($\Delta P_{\text{avg}}$ positivo) y/o el valor de mercado de lo listo para vender ($\sum P_{\text{avg}}$ de artículos `in_stock` / `listed`).
- [ ] UI en el Bento Grid mostrando mensajes contextuales: *"El valor medio de tu inventario ha subido +25 € hoy y tienes 140 € acumulados listos para vender: aquí tienes 3 planes increíbles por tu zona dentro de ese presupuesto"*.

### 3.2 Módulo Día a Día: Clima, Calendario y Entregas Wallapop (`Track C + Track A`)
- [ ] Widget de **Clima actual y previsión semanal** (`/api/lifeos/weather`) que filtra/etiqueta automáticamente los planes recomendados en `Interior` vs `Exterior`.
- [ ] **Calendario Diario/Semanal** interactivo que unifica:
  - Tareas y eventos personales del usuario.
  - Citas de entrega en mano o envíos de productos vendidos en Wallapop (con botón rápido *"Agendar Entrega"* desde cualquier producto del inventario).

> ✅ **CRITERIO DE CIERRE NIVEL 3 (GATE 3):**
> - [ ] El dashboard muestra el clima real/simulado, filtra planes locales ajustados exactamente al valor/subida en euros del inventario y permite agendar entregas de Wallapop en el calendario diario.

---

## 🔴 NIVEL 4: Módulo de Trabajo & Especial Hacktoberfest (Horas 7:30 - 8:30)
> 📄 **Spec Detallada:** [`.agent/specs/level-4-github-hacktoberfest.md`](specs/level-4-github-hacktoberfest.md)

### 4.1 Buscador Inteligente de Repositorios de GitHub (`Track C + Track A`)
- [ ] Endpoint `/api/lifeos/github` conectado a la API de GitHub (con caché y fallback local para evitar rate-limits en el recinto).
- [ ] **Filtro Rápido "Hacktoberfest 2026":** Botón de 1 clic para filtrar repositorios con issues abiertas `hacktoberfest` o `good-first-issue` según el lenguaje favorito del perfil activo (**Ales**, **Adri** o **Matías**).
- [ ] **Resumen con IA (2 líneas):** Explicación ultra-concisa de la arquitectura del repositorio y por dónde empezar a contribuir rápidamente.

> ✅ **CRITERIO DE CIERRE NIVEL 4 (GATE 4):**
> - [ ] Ecosistema LifeOS 100% completado: Inventario ReCommerce + Sync Móvil + MCP 3 Precios + Alertas de Mercado + Clima + Calendario de Entregas + Planes financiados con tus objetos + Buscador Hacktoberfest 2026 con resumen IA.
