import type { MetadataRoute } from "next";

/* PWA manifest (served at /manifest.webmanifest). Icons come from the logo mark in public/. */
export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/",
    name: "LeIA",
    short_name: "LeIA",
    description: "Entenda o seu documento jurídico em linguagem simples, com registro de que você entendeu.",
    lang: "pt-BR",
    dir: "ltr",
    start_url: "/",
    scope: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: "#081820",
    theme_color: "#081820",
    categories: ["productivity", "education", "utilities"],
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icon-512-maskable.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
