// HRIS PWA Service Worker
const CACHE_NAME = 'hris-absen-v1';
const STATIC_ASSETS = [
  '/hr_payroll_indonesia/static/src/pwa/manifest.json',
  '/hr_payroll_indonesia/static/description/icon.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  // Only cache GET requests, skip POST (attendance submission)
  if (event.request.method !== 'GET') return;

  // Network-first for API calls, cache-first for static assets
  const url = new URL(event.request.url);

  if (url.pathname.startsWith('/hr_payroll_indonesia/')) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          return response;
        })
        .catch(() => caches.match(event.request))
    );
  }
});
