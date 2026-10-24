"use client";

import { createContext, useContext, useState, type ReactNode } from "react";
import { CloudOff, LoaderCircle } from "lucide-react";
import { MobileSyncModal } from "@/components/mobile-sync/MobileSyncModal";
import { LoginScreen } from "./LoginScreen";
import { TopNav } from "./TopNav";
import { useDashboardState } from "./useDashboardState";

type DashboardValue = ReturnType<typeof useDashboardState> & {
  openCapture: () => void;
  lastAddedId: string | null;
};

const DashboardContext = createContext<DashboardValue | null>(null);

export function useDashboard() {
  const value = useContext(DashboardContext);
  if (!value) throw new Error("useDashboard solo funciona dentro de <DashboardShell>");
  return value;
}

// Sesión, barra superior y modal de captura compartidos por Inicio y Mi inventario.
export function DashboardShell({ children }: { children: ReactNode }) {
  const state = useDashboardState();
  const [captureOpen, setCaptureOpen] = useState(false);
  const [lastAddedId, setLastAddedId] = useState<string | null>(null);
  const [pendingReload, setPendingReload] = useState(false);

  if (state.user === undefined) {
    return (
      <main className="grid min-h-dvh place-items-center" aria-busy>
        <LoaderCircle className="size-6 animate-spin text-ink-2" aria-hidden />
        <span className="sr-only">Comprobando tu sesión…</span>
      </main>
    );
  }
  if (state.user === null) return <LoginScreen onLogin={state.login} />;

  // El inventario se recarga al cerrar el modal, para que el saldo suba a la vista y no detrás de él.
  function closeCapture() {
    setCaptureOpen(false);
    if (pendingReload) state.reloadInventory();
    setPendingReload(false);
  }

  return (
    <DashboardContext value={{ ...state, openCapture: () => setCaptureOpen(true), lastAddedId }}>
      <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 px-4 pb-16 pt-4 sm:px-6 lg:pt-6">
        <TopNav profile={state.inventory?.profile} onLogout={state.logout} onResetDemo={state.resetDemo} />
        <main className="flex flex-col gap-8">
          {state.error ? (
            <section role="alert" className="flex flex-col items-start gap-4 rounded-panel bg-fog p-8">
              <CloudOff className="size-8 text-ink-2" aria-hidden />
              <div>
                <h1 className="text-xl font-semibold">No se ha podido cargar tu inventario</h1>
                <p className="mt-1 max-w-prose text-ink-2">{state.error.message}</p>
              </div>
              <button
                type="button"
                onClick={state.error.sessionExpired ? state.logout : state.reloadInventory}
                className="h-11 rounded-full bg-accent px-5 text-[15px] font-semibold text-white transition-colors hover:bg-accent-hover"
              >
                {state.error.sessionExpired ? "Volver a entrar" : "Reintentar"}
              </button>
            </section>
          ) : (
            children
          )}
        </main>
      </div>
      <MobileSyncModal
        userId={state.user.uid}
        isOpen={captureOpen}
        onOpen={() => setCaptureOpen(true)}
        onClose={closeCapture}
        onItemCreated={(item) => {
          setLastAddedId(item.id);
          setPendingReload(true);
        }}
      />
      {state.notice && (
        <p
          role="status"
          className="fixed bottom-5 left-1/2 z-40 w-max max-w-[calc(100vw-2rem)] -translate-x-1/2 rounded-full bg-ink px-5 py-3 text-[15px] font-medium text-white shadow-[0_12px_32px_-8px_rgb(16_17_20/0.4)]"
        >
          {state.notice}
        </p>
      )}
    </DashboardContext>
  );
}
