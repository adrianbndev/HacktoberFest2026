import type { Metadata } from "next";
import { Funnel_Display, Funnel_Sans } from "next/font/google";
import "./globals.css";

const funnelSans = Funnel_Sans({
  variable: "--font-funnel-sans",
  subsets: ["latin"],
});

const funnelDisplay = Funnel_Display({
  variable: "--font-funnel-display",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "SmartLoot",
  description: "Tasa tus objetos de segunda mano con una foto del móvil: su estado y cuánto valen en Wallapop, Vinted, Milanuncios y eBay.",
};

const THEME_INIT_SCRIPT = `(function(){try{var t=localStorage.getItem("smartloot-theme");var d=window.matchMedia("(prefers-color-scheme: dark)").matches;if(t==="dark"||(!t&&d)){document.documentElement.classList.add("dark");}else{document.documentElement.classList.remove("dark");}}catch(e){}})();`;

const THEME_AND_MODAL_CSS = `
:root {
  color-scheme: light;
  --paper: #ffffff;
  --fog: #eef0f3;
  --fog-2: #e2e5ea;
  --line: #d7dbe1;
  --ink: #101114;
  --ink-2: #5b606b;
  --accent: #4b3bff;
  --accent-hover: #3b2ae8;
  --accent-soft: #eceaff;
  --on-accent-2: #e2dfff;
}
html.dark {
  color-scheme: dark;
  --paper: #0e1014;
  --fog: #161920;
  --fog-2: #20242e;
  --line: #2b303d;
  --ink: #f4f5f8;
  --ink-2: #9299a9;
  --accent: #5e4eff;
  --accent-hover: #4e3ef7;
  --accent-soft: rgba(94, 78, 255, 0.18);
  --on-accent-2: #d6d3ff;
}
dialog::backdrop {
  background-color: rgb(10 12 16 / 0.55);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}
`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="es"
      suppressHydrationWarning
      className={`${funnelSans.variable} ${funnelDisplay.variable} h-full antialiased`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
        <style dangerouslySetInnerHTML={{ __html: THEME_AND_MODAL_CSS }} />
      </head>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
