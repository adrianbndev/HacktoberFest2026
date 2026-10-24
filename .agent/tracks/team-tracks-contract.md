# 🤝 Contrato de Tracks Paralelos para el Equipo (`.agent/tracks/team-tracks-contract.md`)

> **Objetivo:** Permitir que **Ales**, **Adri** y **Matías** trabajen simultáneamente con **Antigravity CLI**, **Claude Code** u **OpenCode** sin conflictos de merge (`git merge` limpio) gracias a fronteras de directorios estrictas y contratos tipados en `src/types/sdd.ts`.

---

## 1. Matriz de Propiedad de Archivos por Track

| Módulo / Carpeta | Track A (**Ales**) | Track B (**Adri**) | Track C (**Matías**) | Regla de Coordinación |
| :--- | :---: | :---: | :---: | :--- |
| `src/types/sdd.ts` | Lectura | Lectura | Lectura | Fuente de verdad común (definida en Fase 1.0). |
| `src/lib/store/` | Lectura/Uso | Lectura/Uso | Lectura/Uso | Capa de persistencia compartida. |
| `src/app/(dashboard)/` | **PROPIETARIO** | No tocar | No tocar | Ales ensambla los widgets de B y C en el Bento Grid. |
| `src/components/dashboard/` | **PROPIETARIO** | No tocar | No tocar | Layout general, Login switcher, KPIs superiores. |
| `src/components/inventory/` | **PROPIETARIO** | No tocar | No tocar | Tarjetas de producto, 3 precios ($P_{\min}, P_{\text{avg}}, P_{\max}$), Sparklines. |
| `src/components/notifications/` | **PROPIETARIO** | No tocar | No tocar | Centro de alertas y badges $\uparrow/\downarrow$. |
| `src/components/mobile-sync/` | Importa componente | **PROPIETARIO** | No tocar | Adri exporta `<MobileSyncModal onProductCaptured={...} />`. |
| `src/app/mobile-capture/` | No tocar | **PROPIETARIO** | No tocar | Página móvil QR con captura de cámara y compresión Canvas. |
| `src/app/api/capture-session/` | No tocar | **PROPIETARIO** | No tocar | Estado de sesión Móvil $\leftrightarrow$ PC. |
| `src/app/api/vision/` & `src/lib/vision/` | No tocar | **PROPIETARIO** | No tocar | Visión IA: nombre, marca, `conditionScore` ($0-100\%$), SEO. |
| `src/mcp/` & `src/lib/mcp/` | No tocar | No tocar | **PROPIETARIO** | Servidor MCP Stealth, jitter humano, ponderación y fallback. |
| `src/app/api/market/` | Consume vía `fetch` | Consume vía `fetch` | **PROPIETARIO** | Endpoints `/valuate` (Nivel 1) y `/refresh` (Nivel 2). |
| `src/app/api/lifeos/` & `src/lib/lifeos/` | Consume vía `fetch` | No tocar | **PROPIETARIO** | Clima, Planes Locales, Calendario y GitHub Hacktoberfest. |
| `src/components/lifeos/` | Co-edición UI | No tocar | **PROPIETARIO** | Componentes encapsulados para Nivel 3 y Nivel 4. |

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
