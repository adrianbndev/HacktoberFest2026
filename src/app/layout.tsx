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
  --accent: #0b6b3a;
  --accent-hover: #095530;
  --accent-soft: #e6f9ef;
  --on-accent-2: #d7f5e6;
}
html.dark {
  color-scheme: dark;
  --paper: #0e1014;
  --fog: #161920;
  --fog-2: #20242e;
  --line: #2b303d;
  --ink: #f4f5f8;
  --ink-2: #9299a9;
  --accent: #0e7f52;
  --accent-hover: #0b6b45;
  --accent-soft: rgba(14, 127, 82, 0.18);
  --on-accent-2: #eafff5;
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
