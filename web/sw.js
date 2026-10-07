// Hill Rider offline support.
// Our own files: network first (so updates arrive), the saved copy when offline.
// The game engine from the pygbag server never changes for a given version: saved copy first.
const CACHE = "hill-rider-v1";

self.addEventListener("install", (e) => {
    e.waitUntil(caches.open(CACHE).then((c) => c.addAll(["./", "index.html", "manifest.webmanifest",
                                                          "icon-192.png", "icon-512.png", "icon-180.png"])));
    self.skipWaiting();
});

self.addEventListener("activate", (e) => {
    e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
                .then(() => self.clients.claim()));
});

function save(req, res) {
    if (res && (res.ok || res.type === "opaque")) {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy));
    }
    return res;
}

self.addEventListener("fetch", (e) => {
    const req = e.request;
    if (req.method !== "GET" || !req.url.startsWith("http")) return;
    const own = new URL(req.url).origin === self.location.origin;
    if (own) {
        e.respondWith(fetch(req).then((res) => save(req, res))
                      .catch(() => caches.match(req, { ignoreSearch: true })));
    } else {
        e.respondWith(caches.match(req).then((hit) => hit || fetch(req).then((res) => save(req, res))));
    }
});
