"use client";

import { useEffect, useState } from "react";
import { onAuthStateChanged, signInWithPopup, signOut, type User } from "firebase/auth";
import { requestJson } from "@/lib/api";
import { auth, googleProvider } from "@/lib/firebase";
import type { InventoryResponse, UserProfile } from "@/types/sdd";

const BACKEND_DOWN = "No se puede conectar con el backend. Arráncalo con `npm run dev:api`.";

export function useDashboardState() {
  // undefined = todavía comprobando si hay sesión guardada; null = sin sesión.
  const [user, setUser] = useState<User | null | undefined>(undefined);
  const [inventory, setInventory] = useState<InventoryResponse | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => onAuthStateChanged(auth, setUser), []);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    // POST /api/auth crea el perfil (y los productos de demo) la primera vez que entra este usuario.
    requestJson<UserProfile>("/api/auth", "POST")
      .then(() => requestJson<InventoryResponse>("/api/inventory"))
      .then((loaded) => !cancelled && setInventory(loaded))
      .catch(() => !cancelled && setError(BACKEND_DOWN));
    return () => {
      cancelled = true;
    };
  }, [user, reloadKey]);

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
  const reloadInventory = () => setReloadKey((key) => key + 1);

  const loadingInventory = Boolean(user) && inventory?.profile.id !== user?.uid;
  return { user, inventory, loadingInventory, error, login, logout, reloadInventory };
}
