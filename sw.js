const CACHE_NAME = 'agro-vision-cache-v6';
const TO_CACHE = [
  '/',
  '/scanner',
  '/library',
  '/history',
  '/settings',
  '/scan-tutorial',
  '/offline.html',
  '/manifest.json',
  '/static/css/main.css',
  '/static/js/theme.js',
  '/static/js/language.js',
  '/static/js/forecast.js',
  '/static/js/weather.js',
  '/static/js/trends.js',
  '/static/js/market.js',
  '/static/js/camera.js',
  '/static/js/history.js',
  '/static/js/voice.js',
  '/static/js/offline.js',
  '/static/js/ui-sound.js',
  '/static/data/trends.json',
  '/static/lang/eng.json',
  '/static/lang/mar.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(TO_CACHE))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    )
  );
});

self.addEventListener('fetch', (event) => {
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          return response;
        })
        .catch(() => caches.match(event.request).then((resp) => resp || caches.match('/offline.html')))
    );
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request).catch(() => caches.match('/offline.html')))
  );
});
