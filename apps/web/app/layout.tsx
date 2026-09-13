import type { Metadata, Viewport } from "next";
import { Archivo, Atkinson_Hyperlegible, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
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
      <body className="min-h-full flex flex-col">{children}<UpdatePrompt /></body>
    </html>
  );
}
