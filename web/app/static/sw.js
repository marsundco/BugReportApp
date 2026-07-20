/* Service worker — TYLKO app-shell (bez kolejki offline).
   Urządzenia są online w chwili zgłoszenia, więc celowo NIE buforujemy zgłoszeń:
   cichy retry po godzinach byłby gorszy niż jawny błąd (duplikaty kart, zgłoszenie
   „znikające" na kilka godzin). Cache służy wyłącznie szybkiemu startowi. */

const CACHE = "karta-shell-v1";
const SHELL = [
  "/",
  "/static/style.css",
  "/static/app.js",
  "/static/logo-white.png",
  "/static/icon-192.png",
  "/static/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;

  // POST /report i /upload NIGDY nie idą przez cache — muszą dotrzeć do serwera
  // albo jawnie się wywalić.
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Network-first dla dokumentu: świeży formularz po deployu, cache jako zapas.
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((resp) => {
          const copy = resp.clone();
          caches.open(CACHE).then((cache) => cache.put("/", copy));
          return resp;
        })
        .catch(() => caches.match("/"))
    );
    return;
  }

  // Statyki: cache-first (i tak mają ?v=... przy zmianie).
  event.respondWith(
    caches.match(request).then((hit) => hit || fetch(request))
  );
});
