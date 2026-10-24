// fetch con JSON y error si la respuesta no es 2xx; todas las rutas pasan por el proxy /api de Next.
export async function requestJson<T>(url: string, method = "GET", body?: unknown): Promise<T> {
  const response = await fetch(url, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`${method} ${url} -> ${response.status}`);
  return response.json() as Promise<T>;
}
