import { Sparkles } from "lucide-react";
import type { TeamMemberId, UserProfile } from "@/types/sdd";

interface TopNavProfileSwitcherProps {
  profiles: UserProfile[];
  activeUserId: TeamMemberId | null;
  onSwitch: (userId: TeamMemberId) => void;
}

export function TopNavProfileSwitcher({ profiles, activeUserId, onSwitch }: TopNavProfileSwitcherProps) {
  return (
    <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-center gap-3">
        <span className="grid size-10 place-items-center rounded-2xl bg-zinc-900 text-white dark:bg-white dark:text-zinc-900">
          <Sparkles className="size-5" aria-hidden />
        </span>
        <div>
          <p className="text-lg font-semibold leading-tight">LifeOS</p>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">ReCommerce AI</p>
        </div>
      </div>

      <nav aria-label="Cambiar de perfil" className="flex gap-1 rounded-2xl bg-zinc-100 p-1 dark:bg-zinc-900">
        {profiles.map((profile) => {
          const active = profile.id === activeUserId;
          return (
            <button
              key={profile.id}
              type="button"
              aria-pressed={active}
              onClick={() => onSwitch(profile.id)}
              className={`flex items-center gap-2 rounded-xl px-2.5 py-1.5 text-sm transition ${
                active
                  ? "bg-white font-semibold shadow-sm dark:bg-zinc-800"
                  : "text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-white"
              }`}
            >
              {/* eslint-disable-next-line @next/next/no-img-element -- avatar SVG embebido */}
              <img src={profile.avatarUrl} alt="" className="size-6 rounded-lg" />
              <span className="sr-only sm:not-sr-only">{profile.name}</span>
            </button>
          );
        })}
      </nav>
    </header>
  );
}
