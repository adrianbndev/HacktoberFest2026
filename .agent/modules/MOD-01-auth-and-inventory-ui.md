# 🎨 MOD-01: Auth Rápido, Perfiles, Bento Grid UI & "Mi Inventario"

* **Nivel SDD:** 🟢 Nivel 1.1
* **Responsable:** **Track A (Ales)**
* **Estado Actual:** `⏳ READY`
* **Dependencias:** `MOD-00`

---

## 1. Responsabilidad Única (SRP) y Diseño SOLID

* **Separación Presentación vs Estado:**
  * Los componentes dentro de `src/components/inventory/` son componentes presentacionales puros que reciben props estrictamente tipadas (`InventoryItem`, callbacks de acción).
  * El estado global del dashboard (usuario activo `ales | adri | matias | jurado`, lista de productos, modal de captura móvil abierto/cerrado) se coordina en un único hook o proveedor limpio (`useDashboardState`).
* **Principio de Producto Terminado:**
  * Diseño **Bento Grid** moderno en modo oscuro/claro de alto contraste, con indicadores claros para las **3 medidas de precio** y el diagnóstico de **Salud ($0-100\%$)**.

---

## 2. Arquitectura de Componentes (`Track A`)

| Componente | Responsabilidad | Límite Líneas |
| :--- | :--- | :---: |
| `src/components/dashboard/TopNavProfileSwitcher.tsx` | Login / cambio instantáneo entre Ales, Adri, Matías y Jurado + campana de alertas | $\le 140$ |
| `src/components/dashboard/PatrimonyBentoHeader.tsx` | Muestra el valor total acumulado en las 3 métricas ($\sum P_{\min}, \sum P_{\text{avg}}, \sum P_{\max}$) y el botón principal *"📱 Añadir Producto con el Móvil"* | $\le 140$ |
| `src/components/inventory/InventoryGrid.tsx` | Grid responsivo con filtros por categoría/estado y estado vacío elegante | $\le 130$ |
| `src/components/inventory/InventoryItemCard.tsx` | Tarjeta principal del producto ensamblando subcomponentes | $\le 180$ |
| `src/components/inventory/HealthScoreBadge.tsx` | Barra de progreso y etiqueta semántica del `conditionScore` ($0-100\%$) | $\le 80$ |
| `src/components/inventory/PriceTrioDisplay.tsx` | Visualización jerárquica de 📉 $P_{\min}$, 🎯 $P_{\text{avg}}$ y 📈 $P_{\max}$ | $\le 100$ |
| `src/components/inventory/SeoAnnouncementModal.tsx` | Vista y botón *"📋 Copiar Título y Descripción SEO para Wallapop"* con feedback *"¡Copiado!"* | $\le 110$ |

---

## 3. Contratos de API del Módulo

* **`GET /api/inventory?userId=ales`** $\rightarrow$ Devuelve `{ profile: UserProfile, items: InventoryItem[], totals: { min: number, avg: number, max: number } }`.
* **`POST /api/inventory`** $\rightarrow$ Guarda un nuevo `InventoryItem` en el perfil activo.
* **`DELETE /api/inventory?id=item_123`** $\rightarrow$ Elimina o marca como vendido un artículo.

---

## 4. Checklist de Control y Calidad (MOD-01)

- [ ] Selector de sesión rápida operativo para **Ales, Adri, Matías y Jurado** con persistencia en `localStorage` + cookie/query.
- [ ] Cabecera patrimonial mostrando en grande la suma acumulada de $P_{\min}$ (Liquidez rápida), $P_{\text{avg}}$ (Valor real) y $P_{\max}$ (Techo).
- [ ] Tarjeta de producto con visualización del `conditionScore` ($0-100\%$) y `conditionLabel` con colores semánticos.
- [ ] Visualización clara de los 3 precios obligatorios ($P_{\min}, P_{\text{avg}}, P_{\max}$) y muestras de anuncios comparables (Wallapop, Vinted, Milanuncios, eBay).
- [ ] Botón de copiado en 1 clic del Título SEO y Descripción persuasiva para Wallapop.
- [ ] Integración limpia con `<MobileSyncModal />` (`MOD-02`) mediante el callback `onItemCreated`.
