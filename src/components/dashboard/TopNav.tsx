import { LogOut, Sparkles } from "lucide-react";
import type { UserProfile } from "@/types/sdd";

interface TopNavProps {
  profile?: UserProfile;
  onLogout: () => void;
}

export function TopNav({ profile, onLogout }: TopNavProps) {
  return (
    <header className="flex items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        <span className="grid size-10 place-items-center rounded-2xl bg-zinc-900 text-white dark:bg-white dark:text-zinc-900">
          <Sparkles className="size-5" aria-hidden />
        </span>
        <div>
          <p className="text-lg font-semibold leading-tight">LifeOS</p>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">ReCommerce AI</p>
        </div>
      </div>

      <div className="flex items-center gap-2 rounded-2xl bg-zinc-100 p-1 pl-2 dark:bg-zinc-900">
        {profile && (
          <>
            {/* eslint-disable-next-line @next/next/no-img-element -- foto de la cuenta de Google */}
            <img src={profile.avatarUrl} alt="" referrerPolicy="no-referrer" className="size-7 rounded-lg" />
            <span className="hidden text-sm font-medium sm:inline">{profile.name}</span>
          </>
        )}
        <button
          type="button"
          onClick={onLogout}
          className="flex items-center gap-1.5 rounded-xl px-2.5 py-1.5 text-sm text-zinc-500 transition hover:bg-white hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-white"
        >
          <LogOut className="size-4" aria-hidden /> Salir
        </button>
      </div>
    </header>
  );
}
