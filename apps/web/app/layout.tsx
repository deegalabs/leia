import type { Metadata, Viewport } from "next";
import { Archivo, Atkinson_Hyperlegible, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import Link from "next/link";

import { RouteAnnouncer } from "@/components/RouteAnnouncer";
import { UpdatePrompt } from "@/components/UpdatePrompt";

const archivo = Archivo({ subsets: ["latin"], weight: ["600", "700", "800"], variable: "--font-archivo" });
const atkinson = Atkinson_Hyperlegible({ subsets: ["latin"], weight: ["400", "700"], variable: "--font-atkinson" });
const plexMono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-plex-mono" });

export const metadata: Metadata = {
  title: { default: "LeIA", template: "%s · LeIA" },
  description: "Leia antes de assinar. Entenda cada parte do seu documento em linguagem simples, com registro de que você entendeu.",
  robots: { index: false },
  manifest: "/manifest.webmanifest",
  applicationName: "LeIA",
  appleWebApp: { capable: true, statusBarStyle: "black", title: "LeIA" },
  icons: { icon: "/icon-192.png", apple: "/icon-192.png" },
};

export const viewport: Viewport = { themeColor: "#081820", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pt-BR" className={`${archivo.variable} ${atkinson.variable} ${plexMono.variable} h-full`}>
      <body className="min-h-full flex flex-col">
        {/* Primeiro elemento focável da página: quem navega por teclado pula o cabeçalho e cai direto no
            conteúdo, em vez de atravessar a navegação inteira em toda tela. Ele só aparece ao receber foco. */}
        <a href="#conteudo"
           className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-3 focus:z-50 focus:rounded-button focus:bg-teal focus:px-4 focus:py-2 focus:font-bold focus:text-navy">
          Pular para o conteúdo
        </a>
        {/* O único `<main>` do produto. Antes cada tela criava o seu, pelo `Page` e pelo `DocsShell`, e
            página que usasse os dois nascia com dois marcos principais: o leitor de tela oferece "ir para o
            conteúdo principal" e a pessoa não sabe qual dos dois vai receber. `tabIndex={-1}` existe para o
            link acima conseguir mover o foco para cá, e não só rolar a página. */}
        <main id="conteudo" tabIndex={-1} className="flex flex-1 flex-col">{children}</main>
        <footer className="border-t border-line px-4 py-4 text-center text-[0.95rem] text-ink-2">
          <Link href="/acessibilidade" className="font-bold text-teal-deep underline underline-offset-4">
            Acessibilidade
          </Link>
        </footer>
        <RouteAnnouncer />
        <UpdatePrompt />
      </body>
    </html>
  );
}
