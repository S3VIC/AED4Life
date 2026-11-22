(() => {
  const R = 6371008.8, rad = Math.PI / 180;
  const dist = (a, b, c, d) => {
    const h = Math.sin((c - a) * rad / 2) ** 2 + Math.cos(a * rad) * Math.cos(c * rad) * Math.sin((d - b) * rad / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(h));
  };
  const device = () => {
    try {
      let id = localStorage.getItem('aed_dev');
      if (!id) { id = crypto.randomUUID(); localStorage.setItem('aed_dev', id); }
      return id;
    } catch { return 'anon'; }
  };

  class GpsTracker {
    constructor() { this.best = null; this.id = null; this.err = null; }
    start(onUpdate) {
      if (!('geolocation' in navigator)) { this.err = 'Brak GPS w przeglądarce'; return; }
      this.id = navigator.geolocation.watchPosition(p => {
        const fix = { lat: p.coords.latitude, lon: p.coords.longitude, accuracy: p.coords.accuracy, ts: p.timestamp };
        if (!this.best || fix.accuracy <= this.best.accuracy || fix.ts - this.best.ts > 20000) this.best = fix;
        onUpdate?.(this.best);
      }, e => { this.err = e.code === 1 ? 'Brak zgody na lokalizację' : 'Nie udało się ustalić lokalizacji'; onUpdate?.(null, this.err); },
      { enableHighAccuracy: true, maximumAge: 0, timeout: 20000 });
    }
    stop() { if (this.id != null) navigator.geolocation.clearWatch(this.id); }
    fresh(maxAgeMs = 60000) { return this.best && Date.now() - this.best.ts < maxAgeMs ? this.best : null; }
  }

  async function wyslij(endpoint, { aedId, typ = 'jest', plik, gps }) {
    const fd = new FormData();
    fd.append('aed_id', aedId);
    fd.append('typ', typ);
    fd.append('urzadzenie', device());
    if (gps) {
      fd.append('lat', gps.lat); fd.append('lon', gps.lon);
      fd.append('accuracy', gps.accuracy); fd.append('ts', new Date(gps.ts).toISOString());
    }
    if (plik) fd.append('zdjecie', plik, plik.name || 'aed.jpg');
    const r = await fetch(endpoint, { method: 'POST', body: fd });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(j.blad || `Błąd serwera (${r.status})`);
    return j;
  }

  window.AedFoto = { GpsTracker, wyslij, dist, device };
})();
