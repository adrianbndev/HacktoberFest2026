"use client";

import { useEffect, useState } from "react";
import { requestJson } from "@/lib/api";
import type { AuthSession, InventoryResponse, TeamMemberId } from "@/types/sdd";

const STORAGE_KEY = "lifeos.activeUserId";
const BACKEND_DOWN = "No se puede conectar con el backend. Arráncalo con `npm run dev:api`.";

export function useDashboardState() {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [userId, setUserId] = useState<TeamMemberId | null>(null);
  const [inventory, setInventory] = useState<InventoryResponse | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    requestJson<AuthSession>("/api/auth")
      .then((loaded) => {
        setSession(loaded);
        const saved = window.localStorage.getItem(STORAGE_KEY);
        const known = loaded.profiles.find((profile) => profile.id === saved);
        setUserId(known ? known.id : loaded.activeUserId);
      })
      .catch(() => setError(BACKEND_DOWN));
  }, []);

  useEffect(() => {
    if (!userId) return;
    let cancelled = false;
    requestJson<InventoryResponse>(`/api/inventory?userId=${userId}`)
      .then((loaded) => !cancelled && setInventory(loaded))
      .catch(() => !cancelled && setError(BACKEND_DOWN));
    return () => {
      cancelled = true;
    };
  }, [userId, reloadKey]);

  function switchUser(nextUserId: TeamMemberId) {
    setUserId(nextUserId);
    window.localStorage.setItem(STORAGE_KEY, nextUserId);
    requestJson("/api/auth", "POST", { userId: nextUserId }).catch(() => setError(BACKEND_DOWN));
  }

  // Vuelve a pedir el inventario (p. ej. tras añadir un producto con el móvil) para que los totales cuadren.
  const reloadInventory = () => setReloadKey((key) => key + 1);

  const loadingInventory = userId !== null && inventory?.profile.id !== userId;
  return { session, userId, inventory, loadingInventory, error, switchUser, reloadInventory };
}
