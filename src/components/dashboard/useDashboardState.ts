"use client";

import { useEffect, useState } from "react";
import type { AuthSession, InventoryResponse, TeamMemberId } from "@/types/sdd";

const STORAGE_KEY = "lifeos.activeUserId";
const BACKEND_DOWN = "No se puede conectar con el backend. Arráncalo con `npm run dev:api`.";

async function getJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) throw new Error(`${response.status} ${url}`);
  return response.json() as Promise<T>;
}

export function useDashboardState() {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [userId, setUserId] = useState<TeamMemberId | null>(null);
  const [inventory, setInventory] = useState<InventoryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getJson<AuthSession>("/api/auth")
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
    getJson<InventoryResponse>(`/api/inventory?userId=${userId}`)
      .then((loaded) => !cancelled && setInventory(loaded))
      .catch(() => !cancelled && setError(BACKEND_DOWN));
    return () => {
      cancelled = true;
    };
  }, [userId]);

  function switchUser(nextUserId: TeamMemberId) {
    setUserId(nextUserId);
    window.localStorage.setItem(STORAGE_KEY, nextUserId);
    getJson("/api/auth", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ userId: nextUserId }),
    }).catch(() => setError(BACKEND_DOWN));
  }

  const loadingInventory = userId !== null && inventory?.profile.id !== userId;
  return { session, userId, inventory, loadingInventory, error, switchUser };
}
