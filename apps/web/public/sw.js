/* LeIA service worker. Pages are always fetched from the network (a stale landing must never be served);
   only immutable static assets and the icons are cached. Version bump clears the previous cache on every device. */
const CACHE = "leia-static-v2";
const STATIC = ["/manifest.webmanifest", "/logo-mark.svg", "/logo-horizontal-dark.svg", "/logo-horizontal-light.svg", "/icon-192.png", "/icon-512.png"];
self.addEventListener("install", (e) => { e.waitUntil(caches.open(CACHE).then((c) => c.addAll(STATIC)).then(() => self.skipWaiting())); });
self.addEventListener("activate", (e) => { e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== self.location.origin) return;
  if (e.request.mode === "navigate" || url.pathname.startsWith("/api/")) return;   /* network only */
  if (url.pathname.startsWith("/_next/static/") || STATIC.includes(url.pathname)) {
    e.respondWith(caches.match(e.request).then((hit) => hit || fetch(e.request).then((res) => { if (res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(e.request, copy)); } return res; })));
  }
});
