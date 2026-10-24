# 🟢 SDD Spec — NIVEL 1: El Core Absoluto (Inventario IA, Sync Móvil-PC, MCP Stealth y Login)

> **Ventana de Tiempo:** Horas 0:00 - 3:30
> **Prioridad:** CRÍTICA (Bloquea todos los demás niveles)
> **Estado objetivo:** Producto MVP 100% funcional, visualmente impactante y demostrable de extremo a extremo.

---

## 1. Historias de Usuario del Nivel 1

1. **US-1.1 (Login y Perfil de Inventario):** Como usuario (**Ales, Adri, Matías o Jurado**), quiero iniciar sesión en 1 clic y ver mi perfil con todos mis productos fotografiados y el valor total acumulado de mi inventario ($P_{\min}, P_{\text{avg}}, P_{\max}$).
2. **US-1.2 (Captura Móvil $\leftrightarrow$ PC Instantánea):** Como usuario en mi PC, quiero pulsar *"Añadir Producto con el Móvil"*, escanear un QR con mi teléfono, sacar una foto al objeto que tengo en la mesa y ver cómo la foto aparece sola en la pantalla del PC en menos de $1.5\text{ segundos}$ sin cables ni recargas manuales.
3. **US-1.3 (Visión IA + Diagnóstico de Salud + SEO):** Como vendedor de segunda mano, quiero que la IA identifique automáticamente el producto exacto, evalúe su **Estado/Salud ($0-100\%$)** y redacte el **Título SEO y Descripción persuasiva** optimizada para Wallapop.
4. **US-1.4 (Tasación MCP Stealth de 3 Precios):** Como vendedor, quiero que el sistema consulte Wallapop y plataformas similares comportándose como un humano y me muestre claramente el **Precio Mínimo ($P_{\min}$)**, **Precio Medio ($P_{\text{avg}}$)** y **Precio Más Alto ($P_{\max}$)** ajustados al estado de salud de mi objeto.

---

## 2. Especificación Funcional por Sub-Módulo

### 2.1 Autenticación Rápida y Vista "Mi Inventario" (`Track A`)
* **Componente Login / Switcher:** Selector de perfil persistente en cabecera y pantalla de bienvenida con avatares, ciudad y rol para `ales`, `adri`, `matias` y `jurado`.
* **Header de Valoración Patrimonial:**
  * Muestra 3 contadores globales del inventario del usuario:
    * 📉 **Liquidez Inmediata Total ($\sum P_{\min}$)**
    * 🎯 **Valor Real de Mercado ($\sum P_{\text{avg}}$)**
    * 📈 **Potencial Máximo ($\sum P_{\max}$)**
* **Grid de Productos ("Mi Inventario"):**
  * Tarjetas con imagen del objeto, marca/modelo, badge de Salud (`conditionScore` % + color semántico: esmeralda $\ge 85\%$, ámbar $60-84\%$, coral $<60\%$), las 3 métricas de precio y botón de *"Copiar Anuncio SEO para Wallapop"*.

### 2.2 Flujo Cámara Móvil $\leftrightarrow$ Web PC (`Track B`)
* **En PC (`MobileSyncModal`):**
  * Al pulsar *"📱 Añadir Producto con el Móvil"*, llama a `POST /api/capture-session`.
  * Renderiza un código QR grande (usando `qrcode.react` o SVG generador local sin dependencias rotas) apuntando a `http://<LAN_IP_OR_HOST>:3000/mobile-capture/[sessionId]`.
  * Incluye un campo editable para ajustar la IP LAN local si se detecta `localhost`, facilitando el escaneo desde el móvil en la red del hackathon, además de un botón *"Simular Captura Móvil desde PC"* como respaldo adicional.
  * Inicia polling cada $1000\text{ ms}$ (o conexión SSE) contra `GET /api/capture-session/[sessionId]`.
* **En Móvil (`/mobile-capture/[sessionId]`):**
  * Al cargar la página, notifica `status: 'mobile_connected'` para que el PC muestre *"📱 ¡Móvil conectado! Esperando foto..."*.
  * Muestra un botón de acción masivo que activa `<input type="file" accept="image/*" capture="environment" />`.
  * Al tomar la foto, la comprime en `<canvas>` ($\le 1024\text{ px}$, JPEG $0.78$) y la envía vía `PUT /api/capture-session/[sessionId]`.
  * Muestra confirmación en el móvil: *"✅ ¡Foto enviada al PC! Mira la pantalla de tu ordenador"*.

### 2.3 Reconocimiento por Visión IA + Salud + SEO (`Track B`)
* Al detectar `status === 'photo_uploaded'`, el PC invoca `POST /api/vision/analyze`.
* El prompt del modelo multimodal exige respuesta JSON estricta:
  * `name`: Nombre comercial completo.
  * `category`: Categoría de segunda mano.
  * `brand` y `model`: Marca y modelo.
  * `conditionScore`: Entero de $0$ a $100$ evaluando desgaste superficial, arañazos, limpieza e integridad.
  * `conditionLabel`: `'Nuevo' | 'Como nuevo' | 'Buen estado' | 'Desgaste visible' | 'Para piezas'`.
  * `conditionReasoning`: 1 frase explicando el diagnóstico visual.
  * `seoTitle`: Título gancho ($\le 65$ caracteres) con palabras clave de búsqueda en Wallapop.
  * `seoDescription`: Descripción persuasiva estructurada con emojis, estado honesto y argumentos de venta.

### 2.4 Tasación MCP Stealth de 3 Medidas (`Track C`)
* Con el resultado de Visión IA, se invoca `POST /api/market/valuate` pasándole `{ query: name, category, conditionScore, conditionLabel }`.
* Ejecuta la búsqueda en `stealth-market-mcp` (con *jitter* $800-2200\text{ ms}$, rotación de headers y fallback determinista).
* Devuelve `priceMin`, `priceAvg`, `priceMax` y listado de anuncios comparables en Wallapop, Vinted, Milanuncios y eBay.
* El producto completo se guarda automáticamente en el perfil del usuario (`POST /api/inventory`) y aparece resaltado al principio de **"Mi Inventario"**.

---

## 3. Criterios de Aceptación (Definition of Done — Nivel 1)

1. [ ] El cambio entre perfiles (**Ales, Adri, Matías, Jurado**) actualiza instantáneamente el inventario mostrado.
2. [ ] El código QR funciona desde un teléfono real y la foto tomada aparece en el PC en $< 1.5\text{ s}$ sin refrescar la página.
3. [ ] La tarjeta de resultado muestra claramente la barra/puntuación de **Salud ($0-100\%$)** y el texto **SEO copiable en 1 clic**.
4. [ ] Las **3 medidas de precio ($P_{\min}, P_{\text{avg}}, P_{\max}$)** se muestran con jerarquía visual clara y cumplen $P_{\min} < P_{\text{avg}} < P_{\max}$.
5. [ ] Al recargar la página del navegador, todos los productos añadidos permanecen guardados en el perfil.
