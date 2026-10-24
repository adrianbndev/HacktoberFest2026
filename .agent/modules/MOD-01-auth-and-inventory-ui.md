# 🎨 MOD-01: Auth Rápido, Perfiles, Bento Grid UI & "Mi Inventario"

* **Nivel SDD:** 🟢 Nivel 1.1
* **Responsable:** **Track A (Ales)**
* **Estado Actual:** `⏳ READY`
* **Dependencias:** `MOD-00`

---

## 1. Responsabilidad Única (SRP) y Diseño SOLID

* **Separación Presentación vs Estado:**
  * Los componentes dentro de `src/components/inventory/` son componentes presentacionales puros que reciben props estrictamente tipadas (`InventoryItem`, callbacks de acción).
  * El estado global del dashboard (usuario de Firebase Auth, lista de productos, modal de captura móvil abierto/cerrado) se coordina en un único hook o proveedor limpio (`useDashboardState`).
* **Principio de Producto Terminado:**
  * Diseño **Bento Grid** moderno en modo oscuro/claro de alto contraste, con indicadores claros para las **3 medidas de precio** y el diagnóstico de **Salud ($0-100\%$)**.

---

## 2. Arquitectura de Componentes (`Track A`)

| Componente | Responsabilidad | Límite Líneas |
| :--- | :--- | :---: |
| `src/components/dashboard/LoginScreen.tsx` | Pantalla de bienvenida con *"Continuar con Google"* y errores de login con su código | $\le 80$ |
| `src/components/dashboard/TopNav.tsx` | Marca + usuario de la sesión (foto y nombre de Google) + botón *Salir* | $\le 60$ |
| `src/components/dashboard/PatrimonyBentoHeader.tsx` | Muestra el valor total acumulado en las 3 métricas ($\sum P_{\min}, \sum P_{\text{avg}}, \sum P_{\max}$) y el botón principal *"📱 Añadir Producto con el Móvil"* | $\le 140$ |
| `src/components/inventory/InventoryGrid.tsx` | Grid responsivo con filtros por categoría/estado y estado vacío elegante | $\le 130$ |
| `src/components/inventory/InventoryItemCard.tsx` | Tarjeta principal del producto ensamblando subcomponentes | $\le 180$ |
| `src/components/inventory/HealthScoreBadge.tsx` | Barra de progreso y etiqueta semántica del `conditionScore` ($0-100\%$) | $\le 80$ |
| `src/components/inventory/PriceTrioDisplay.tsx` | Visualización jerárquica de 📉 $P_{\min}$, 🎯 $P_{\text{avg}}$ y 📈 $P_{\max}$ | $\le 100$ |
| `src/components/inventory/SeoAnnouncementModal.tsx` | Vista y botón *"📋 Copiar Título y Descripción SEO para Wallapop"* con feedback *"¡Copiado!"* | $\le 110$ |

---

## 3. Contratos de API del Módulo

Todas con el ID token de Firebase (ver [`.agent/architecture.md`](../architecture.md) §3.0):
* **`POST /api/auth`** $\rightarrow$ `UserProfile` (crea el perfil y los 3 productos de demo en el primer acceso).
* **`GET /api/inventory`** $\rightarrow$ `InventoryResponse` (`{ profile, items, totals: InventoryTotals }`).
* **`POST /api/inventory`** $\rightarrow$ Crea o reemplaza un `InventoryItem` del usuario de la sesión.
* **`DELETE /api/inventory?id=…`** $\rightarrow$ Elimina un artículo del usuario (`404` si es ajeno o no existe).

---

## 4. Checklist de Control y Calidad (MOD-01)

- [x] Login con Google (Firebase Auth) con sesión persistente y botón *Salir*.
- [x] Cabecera patrimonial mostrando en grande la suma acumulada de $P_{\min}$ (Liquidez rápida), $P_{\text{avg}}$ (Valor real) y $P_{\max}$ (Techo).
- [x] Tarjeta de producto con visualización del `conditionScore` ($0-100\%$) y `conditionLabel` con colores semánticos.
- [x] Visualización clara de los 3 precios obligatorios ($P_{\min}, P_{\text{avg}}, P_{\max}$) y muestras de anuncios comparables (Wallapop, Vinted, Milanuncios, eBay).
- [x] Botón de copiado en 1 clic del Título SEO y Descripción persuasiva para Wallapop.
- [x] Integración limpia con `<MobileSyncModal />` (`MOD-02`) mediante el callback `onItemCreated`.
