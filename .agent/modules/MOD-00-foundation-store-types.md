# 🧱 MOD-00: Foundation — Tipos, Validación Zod & Persistencia Atómica

* **Nivel SDD:** 🟢 Nivel 1.0 (Prerrequisito común para Tracks A, B y C)
* **Responsable:** Compartido (Ales / Adri / Matías)
* **Estado Actual:** `⏳ READY`
* **SLA de Latencia:** Lectura $< 2\text{ ms}$ (RAM Cache) | Escritura atómica $< 15\text{ ms}$

---

## 1. Responsabilidad Única (SRP) y Diseño SOLID

Este módulo establece los cimientos desacoplados del proyecto (Frontend Next.js + Backend Python FastAPI) para que los tres Tracks trabajen en paralelo sin bloqueos:
* **`src/types/sdd.ts`**: Contratos de dominio inmutables en TypeScript para el Frontend.
* **`backend/app/models/sdd.py`**: Modelos **Pydantic v2** (`camelCase` aliases) para validar entradas/salidas en tiempo de ejecución en Python (respuestas de IA, bodies de APIs, archivo JSON en disco).
* **`backend/app/store/repository.py`**: Implementación en Python del patrón **Repository** (`AppStoreRepository`) con bloqueo thread-safe (`threading.RLock`), escritura atómica (`store.json.tmp` + `os.replace`) y datos semilla ricos para **Ales, Adri, Matías y Jurado**.

---

## 2. Archivos del Módulo

| Archivo | Propósito | Límite Líneas |
| :--- | :--- | :---: |
| `src/types/sdd.ts` | Interfaces globales del dominio en TypeScript (Frontend) | $\le 220$ |
| `backend/app/models/sdd.py` | Esquemas Pydantic v2 con serialización `camelCase` (Backend Python) | $\le 220$ |
| `backend/app/store/seed_data.py` | Perfiles de Ales, Adri, Matías y Jurado + inventario inicial realista | $\le 220$ |
| `backend/app/store/repository.py` | Singleton en memoria + CRUD atómico sobre `/data/store.json` + `reset_to_seed()` | $\le 180$ |
| `backend/app/main.py` & `backend/app/routers/auth_inventory.py` | Aplicación FastAPI base + CRUD de inventario y reset | $\le 120$ |
| `backend/Dockerfile` & `docker-compose.yml` | Contenedores Python FastAPI + Next.js + volumen `./data` + túnel `cloudflared` | $\le 100$ |
| `.env.example` | Plantilla de variables (`GEMINI_API_KEY`, `OPENAI_API_KEY`, `GITHUB_TOKEN`, `FASTAPI_INTERNAL_URL`) | $\le 30$ |

---

## 3. Datos Semilla Obligatorios (`seed-data.ts`)

Para que cualquier prueba de Nivel 1, 2, 3 o 4 sea inmediata:
1. **Perfiles:**
   * `ales` (Madrid — Favoritos: `TypeScript`, `React`, `Next.js`)
   * `adri` (Barcelona — Favoritos: `Python`, `TypeScript`, `AI/Vision`)
   * `matias` (Valencia — Favoritos: `Rust`, `TypeScript`, `Node.js`)
   * `jurado` (Madrid — Favoritos: `TypeScript`, `Python`, `Go`)
2. **Inventario Inicial por Defecto:**
   * Al menos 3 productos por perfil con su `conditionScore`, descripción SEO y `priceHistory` de 3 puntos previos para que las gráficas y tendencias se vean pobladas desde el segundo cero, además de los productos nuevos que se fotografíen en vivo con el móvil.

---

## 4. Checklist de Control y Calidad (MOD-00)

- [ ] Crear `src/types/sdd.ts` cumpliendo el 100% del contrato de [`.agent/architecture.md`](../architecture.md).
- [ ] Crear validadores Zod en `src/lib/schema/sdd-schema.ts`.
- [ ] Implementar `FileJsonRepository` con singleton en `globalThis.__LIFEOS_STORE__` y escritura atómica (`.tmp` + `renameSync`) que evita corrupción de JSON ante peticiones concurrentes de polling y subida móvil.
- [ ] Crear `src/lib/store/seed-data.ts` con productos cuyas métricas cumplan $0 < P_{\min} < P_{\text{avg}} < P_{\max}$.
- [ ] Añadir endpoint `POST /api/store/reset` para restaurar el estado de demo en 1 clic si se desea repetir el ensayo.
- [ ] Crear `.env.example`, `Dockerfile` y `docker-compose.yml` (con volumen `./data:/app/data` y servicio opcional `mobile-tunnel` con `cloudflared`).
- [ ] Verificar con test unitario que la lectura/escritura y las invariantes de `seed-data.ts` pasan al 100%.
