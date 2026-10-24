import { auth } from "@/lib/firebase";

// fetch con JSON y error si la respuesta no es 2xx; todas las rutas pasan por el proxy /api de Next.
// Si hay sesión de Firebase se envía su ID token: el backend identifica al usuario con él.
export async function requestJson<T>(url: string, method = "GET", body?: unknown): Promise<T> {
  const token = await auth.currentUser?.getIdToken();
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(url, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`${method} ${url} -> ${response.status}`);
  return response.status === 204 ? (undefined as T) : (response.json() as Promise<T>);
}
