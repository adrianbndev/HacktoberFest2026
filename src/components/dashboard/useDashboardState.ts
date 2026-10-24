"use client";

import { useEffect, useState } from "react";
import { onAuthStateChanged, signInWithPopup, signOut, type User } from "firebase/auth";
import { ApiError, requestJson } from "@/lib/api";
import { auth, googleProvider } from "@/lib/firebase";
import type { InventoryItem, InventoryResponse, UserProfile } from "@/types/sdd";

export interface LoadError {
  message: string;
  sessionExpired: boolean;
}

const NOTICE_MS = 5000;

function describeLoadError(cause: unknown): LoadError {
  const status = cause instanceof ApiError ? cause.status : 0;
  if (status === 401) return { message: "Tu sesión ha caducado. Sal y vuelve a entrar con Google.", sessionExpired: true };
  if (status === 503) {
    return { message: "El servidor no puede acceder a tus datos ahora mismo. Vuelve a intentarlo en unos segundos.", sessionExpired: false };
  }
  return { message: "No podemos conectar con SmartLoot. Comprueba la conexión y vuelve a intentarlo.", sessionExpired: false };
}

export function useDashboardState() {
  // undefined = todavía comprobando si hay sesión guardada; null = sin sesión.
  const [user, setUser] = useState<User | null | undefined>(undefined);
  const [inventory, setInventory] = useState<InventoryResponse | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [error, setError] = useState<LoadError | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => onAuthStateChanged(auth, setUser), []);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    // POST /api/auth crea el perfil (y los productos de demo) la primera vez que entra este usuario.
    requestJson<UserProfile>("/api/auth", "POST")
      .then(() => requestJson<InventoryResponse>("/api/inventory"))
      .then((loaded) => !cancelled && setInventory(loaded))
      .catch((cause) => !cancelled && setError(describeLoadError(cause)));
    return () => {
      cancelled = true;
    };
  }, [user, reloadKey]);

  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(null), NOTICE_MS);
    return () => window.clearTimeout(timer);
  }, [notice]);

  async function login(): Promise<string | null> {
    try {
      await signInWithPopup(auth, googleProvider);
      return null;
    } catch (cause) {
      const code = (cause as { code?: string }).code ?? "desconocido";
      if (code === "auth/popup-closed-by-user" || code === "auth/cancelled-popup-request") return null;
      if (code === "auth/popup-blocked") {
        return "El navegador ha bloqueado la ventana de Google. Permite las ventanas emergentes y vuelve a intentarlo.";
      }
      if (code === "auth/unauthorized-domain") {
        return `Firebase no tiene autorizado ${window.location.hostname}. Abre la web en http://localhost:3000 o añade el dominio en Firebase Auth.`;
      }
      return `No se pudo iniciar sesión con Google (${code}). Vuelve a intentarlo.`;
    }
  }

  function logout() {
    setInventory(null);
    setError(null);
    signOut(auth);
  }

  // Vuelve a pedir el inventario (p. ej. tras añadir un producto con el móvil) para que los totales cuadren.
  function reloadInventory() {
    setError(null);
    setReloadKey((key) => key + 1);
  }

  // Cambios optimistas: se ven al instante y luego se recarga lo que diga el servidor.
  async function mutate(apply: (items: InventoryItem[]) => InventoryItem[], request: () => Promise<unknown>, done: string) {
    setInventory((current) => current && { ...current, items: apply(current.items) });
    try {
      await request();
      setNotice(done);
    } catch {
      setNotice("No se ha podido guardar el cambio. Vuelve a intentarlo.");
    }
    reloadInventory();
  }

  const updateItem = (item: InventoryItem, done: string) =>
    mutate(
      (items) => items.map((current) => (current.id === item.id ? item : current)),
      () => requestJson("/api/inventory", "POST", item),
      done,
    );

  const deleteItem = (item: InventoryItem) =>
    mutate(
      (items) => items.filter((current) => current.id !== item.id),
      () => requestJson(`/api/inventory?id=${encodeURIComponent(item.id)}`, "DELETE"),
      `${item.name} se ha eliminado de tu inventario.`,
    );

  async function resetDemo() {
    try {
      setInventory(await requestJson<InventoryResponse>("/api/store/reset", "POST"));
      setNotice("Se han restaurado los productos de demo.");
    } catch {
      setNotice("No se han podido restaurar los productos de demo. Vuelve a intentarlo.");
    }
  }

  const loadingInventory = Boolean(user) && inventory?.profile.id !== user?.uid;
  return {
    user,
    inventory,
    loadingInventory,
    error,
    notice,
    login,
    logout,
    reloadInventory,
    updateItem,
    deleteItem,
    resetDemo,
  };
}
