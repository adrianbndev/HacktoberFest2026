# 🤝 Contrato de Tracks Paralelos para el Equipo (`.agent/tracks/team-tracks-contract.md`)

> **Objetivo:** Permitir que **Ales**, **Adri** y **Matías** trabajen simultáneamente con **Antigravity CLI**, **Claude Code** u **OpenCode** sin conflictos de merge (`git merge` limpio) gracias a fronteras de directorios estrictas y contratos tipados en `src/types/sdd.ts`.

---

## 1. Matriz de Propiedad de Archivos por Track (Frontend Next.js + Backend Python FastAPI)

| Módulo / Carpeta | Track A (**Ales**) | Track B (**Adri**) | Track C (**Matías**) | Regla de Coordinación |
| :--- | :---: | :---: | :---: | :--- |
| `src/types/sdd.ts` & `backend/app/models/sdd.py` | Lectura | Lectura | Lectura | Fuente de verdad común (definida en `MOD-00`). |
| `backend/app/store/` | Lectura/Uso | Lectura/Uso | Lectura/Uso | Capa de persistencia JSON atómica en Python compartida. |
| `src/app/(dashboard)/` | **PROPIETARIO** | No tocar | No tocar | Ales ensambla los widgets de B y C en el Bento Grid. |
| `src/components/dashboard/` | **PROPIETARIO** | No tocar | No tocar | Layout general, Login switcher, KPIs superiores. |
| `src/components/inventory/` | **PROPIETARIO** | No tocar | No tocar | Tarjetas de producto, 3 precios ($P_{\min}, P_{\text{avg}}, P_{\max}$), Sparklines. |
| `src/components/notifications/` | **PROPIETARIO** | No tocar | No tocar | Centro de alertas y badges $\uparrow/\downarrow$. |
| `src/components/mobile-sync/` | Importa componente | **PROPIETARIO** | No tocar | Adri exporta `<MobileSyncModal onItemCreated={...} />`. |
| `src/app/mobile-capture/` | No tocar | **PROPIETARIO** | No tocar | Página móvil QR con captura de cámara y compresión Canvas. |
| `backend/app/routers/capture_session.py` | No tocar | **PROPIETARIO** | No tocar | Estado de sesión Móvil $\leftrightarrow$ PC en FastAPI. |
| `backend/app/vision/` & `backend/app/routers/vision.py` | No tocar | **PROPIETARIO** | No tocar | Reconocimiento de imágenes en Python (`Pillow` + Gemini/OpenAI): nombre, marca, `conditionScore` ($0-100\%$), SEO. |
| `backend/mcp_server.py` & `backend/app/mcp/` | No tocar | No tocar | **PROPIETARIO** | Servidor MCP Stealth en Python (`FastMCP`), jitter humano, ponderación y fallback. |
| `backend/app/routers/market.py` | Consume vía `fetch` | Consume vía `fetch` | **PROPIETARIO** | Endpoints FastAPI `/api/market/valuate` (Nivel 1) y `/api/market/refresh` (Nivel 2). |
| `backend/app/lifeos/` & `backend/app/routers/lifeos.py` | Consume vía `fetch` | Consume vía `fetch` | **PROPIETARIO** | Servicios Python de Clima, Planes Locales, Calendario y GitHub Hacktoberfest. |
| `src/components/lifeos/` | Co-edición UI (Planes/GitHub) | Co-edición UI (Clima/Agenda) | Soporte contratos | Componentes encapsulados en archivos separados para Nivel 3 y 4. |

---

## 1.5 Protocolo de los Primeros 30 Minutos (`MOD-00` Conjunto) y Balanceo de Carga

1. **Prohibido Ramificar antes de `MOD-00` (Minutos 0:00 - 0:30):**
   * Antes de que Ales, Adri y Matías creen sus ramas o lancen agentes en paralelo, **se debe completar `MOD-00` en `main`**:
     * Inicialización del Frontend Next.js (`src/`, `next.config.ts` con rewrite proxy `/api/* -> :8000`) y del Backend Python FastAPI (`backend/app/main.py`, `requirements.txt`).
     * Creación de `src/types/sdd.ts`, `backend/app/models/sdd.py` (Pydantic v2) y `backend/app/store/` con datos semilla para `ales`, `adri`, `matias` y `jurado`.
     * Creación de **endpoints stub (mocks de 5 líneas en FastAPI)** en `/api/vision/analyze` y `/api/market/valuate` para que Track A y Track B puedan probar de extremo a extremo sin esperar a que Track C termine el motor MCP.
2. **Re-equilibrio de Carga de Trabajo en Niveles 2, 3 y 4:**
   * En el **Nivel 1**, **Adri (`Track B`)** tiene la carga crítica de Cámara Móvil + Reconocimiento de Imágenes en Python (`MOD-02` y `MOD-03`).
   * A partir del **Nivel 2, 3 y 4**, una vez cerrados `MOD-02` y `MOD-03`, **Adri** apoya en componentes UI aislados (`WeatherForecastWidget.tsx`, `DailyCalendarWidget.tsx` y el modal de *"Agendar Entrega Wallapop"*), evitando cuellos de botella en el Track A de **Ales** mientras **Matías (`Track C`)** construye los servicios Python de backend.

---

## 2. Puntos de Integración Entre Tracks (Interfaces Limpias)

### Integración Track B (Adri) $\rightarrow$ Track A (Ales)
Adri expone un único componente autónomo en `src/components/mobile-sync/MobileSyncModal.tsx`:
```tsx
export interface MobileSyncModalProps {
  userId: TeamMemberId;
  isOpen: boolean;
  onClose: () => void;
  onItemCreated: (newItem: InventoryItem) => void;
}
```
* **Flujo:** Ales solo coloca el botón *"📱 Añadir Producto con el Móvil"* en el dashboard y le pasa `onItemCreated`. Cuando Adri completa la captura móvil + Visión IA + llamada a `/api/market/valuate`, invoca `onItemCreated(newItem)` y el inventario de Ales se actualiza al instante.

### Integración Track C (Matías) $\rightarrow$ Track B (Adri) y Track A (Ales)
Matías expone endpoints REST internos con contrato JSON fijo:
1. `POST /api/market/valuate` $\rightarrow$ Usado por el flujo de captura de Adri para obtener `priceMin`, `priceAvg`, `priceMax` y `comparableListings` a partir del `conditionScore`.
2. `POST /api/market/refresh` $\rightarrow$ Usado por el botón *"⚡ Forzar Actualización de Mercado (Demo Mode)"* de Ales para recibir el inventario actualizado y las nuevas notificaciones `MarketNotification[]`.
3. `GET /api/lifeos/plans`, `GET /api/lifeos/weather`, `GET/POST /api/lifeos/calendar`, `GET /api/lifeos/github` $\rightarrow$ Consumidos por los widgets de Nivel 3 y Nivel 4.

---

## 3. Cómo Invocar a tu Agente Según tu Herramienta

Tanto **Antigravity CLI**, como **Claude Code**, como **OpenCode** leen automáticamente `AGENTS.md` / `CLAUDE.md` en la raíz del proyecto.

* **Si eres Ales (Track A):**
  > *"Sigue AGENTS.md y .agent/roadmap.md. Actúa como responsable del Track A en el Nivel [1/2/3/4]. Respeta los contratos de .agent/architecture.md."*
* **Si eres Adri (Track B):**
  > *"Sigue AGENTS.md y .agent/roadmap.md. Actúa como responsable del Track B (Sync Móvil-PC y Visión IA + Salud + SEO). Respeta .agent/rules/hackathon-guardrails.md."*
* **Si eres Matías (Track C):**
  > *"Sigue AGENTS.md y .agent/mcp/stealth-market-mcp.md. Actúa como responsable del Track C (MCP Stealth 3 precios, Cron de mercado y APIs LifeOS)."*
