# 🧱 MOD-00: Foundation — Tipos, Validación Pydantic v2, Login con Google y Datos en Firestore

* **Nivel SDD:** 🟢 Nivel 1.0 (Prerrequisito común para Tracks A, B y C)
* **Responsable:** Compartido (implementado por Matías)
* **Estado Actual:** `✅ DONE` (Docker sin probar: ver checklist)
* **Latencia:** Firestore en `nam5`; la primera carga tras arrancar el backend tarda ~4 s (conexión + certificados)

---

## 1. Responsabilidad Única (SRP) y Diseño SOLID

Cimientos del proyecto (Frontend Next.js + Backend Python FastAPI) para que los tres Tracks trabajen en paralelo:
* **Contratos:** `src/types/sdd.ts` (+ `src/types/vision-follow-up.ts`) en el frontend y `backend/app/models/` en Python: `base.py` (CamelModel, literales, `PriceTriplet` con la invariante $0 < P_{\min} < P_{\text{avg}} < P_{\max}$), `domain.py` (usuarios, inventario, sesiones de captura, LifeOS, preguntas de seguimiento) y `sdd.py` (Visión IA y tasación, Track B).
* **Usuarios:** Firebase Auth con Google. El backend verifica el ID token en `backend/app/auth.py` (`CurrentUser`) y nunca acepta `userId` del cliente.
* **Datos:** patrón **Repository**: `StoreRepository` (`backend/app/store/repository.py`) con la implementación de Firestore (`firestore_repository.py`). Detalle de colecciones y formato en [`.agent/architecture.md`](../architecture.md) §5.

---

## 2. Archivos del Módulo

| Archivo | Propósito | Límite Líneas |
| :--- | :--- | :---: |
| `src/types/sdd.ts` | Interfaces globales del dominio en TypeScript (Frontend) | $\le 250$ |
| `backend/app/models/base.py` & `domain.py` | Modelos Pydantic v2 con serialización `camelCase` | $\le 250$ |
| `backend/app/firebase.py` & `auth.py` | Conexión con Firebase Admin y verificación del token de login | $\le 60$ |
| `backend/app/store/repository.py` & `firestore_repository.py` | Interfaz de almacenamiento + Firestore (503 sin clave de servicio) | $\le 120$ |
| `backend/app/store/seed_data.py` | Perfil del primer login desde Google + 3 productos de demo | $\le 120$ |
| `backend/app/main.py` & `backend/app/routers/auth_inventory.py` | FastAPI base (monta todos los routers de `app/routers`) + perfil, inventario y reset | $\le 80$ |
| `backend/tests/conftest.py` | Almacén en memoria para probar la API sin red ni credenciales | $\le 60$ |
| `backend/Dockerfile` & `docker-compose.yml` | Contenedores FastAPI + Next.js + clave de servicio montada + túnel `cloudflared` | $\le 100$ |

---

## 3. Datos de Demo

* **Primer login de cada usuario:** `POST /api/auth` crea su perfil desde la cuenta de Google (nombre, foto, email; ciudad `Madrid` y lenguajes `TypeScript`, `Python` por defecto) y le carga **3 productos de demo** con `priceHistory` de 3 escaneos: una subida, una bajada y uno estable, para que el Nivel 2 se vea poblado desde el segundo cero.
* **Antes de presentar:** `POST /api/store/reset` restaura los 3 productos de demo del usuario de la sesión.

---

## 4. Checklist de Control y Calidad (MOD-00)

- [x] `src/types/sdd.ts` y los modelos Pydantic v2 espejo en `backend/app/models/` cumplen el contrato de [`.agent/architecture.md`](../architecture.md).
- [x] Login con Google (Firebase Auth) verificado en el backend: sin token o con uno inválido, `401`.
- [x] Datos en Firestore detrás de `StoreRepository`; cada producto pertenece al `uid` del token (un usuario no ve ni borra los ajenos).
- [x] Productos de demo que cumplen $0 < P_{\min} < P_{\text{avg}} < P_{\max}$ y endpoint `POST /api/store/reset`.
- [x] `pytest backend/tests` en verde con el almacén en memoria, y prueba manual contra Firebase real con usuarios temporales.
- [ ] `docker compose up` probado de punta a punta (Docker no estaba instalado al escribir esto).
