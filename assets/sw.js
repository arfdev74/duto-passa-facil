// Service Worker — Duto Passa Fácil PWA
// Versão do cache — incremente ao fazer deploy
const CACHE_VERSION = 'duto-v1';
const CACHE_ASSETS = [
  '/',
  '/assets/icon-192.png',
  '/assets/icon-512.png',
];

// Instala e faz cache dos assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then(cache => {
      return cache.addAll(CACHE_ASSETS);
    })
  );
  self.skipWaiting();
});

// Limpa caches antigos
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k !== CACHE_VERSION).map(k => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// Estratégia: network first, fallback para cache
self.addEventListener('fetch', event => {
  event.respondWith(
    fetch(event.request)
      .catch(() => caches.match(event.request))
  );
});
