/* Show the real outcome of the latest scan separately from historical availability. */
(function () {
  'use strict';
  const mount = document.querySelector('main');
  if (!mount) return;
  const E = (tag, text, cls) => {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = text;
    if (cls) el.className = cls;
    return el;
  };
  fetch('./scan.json', {cache: 'no-store'}).then(r => {
    if (!r.ok) throw new Error('Scan summary unavailable');
    return r.json();
  }).then(s => {
    if (!s || !s.run_id || !s.coverage || !s.confirmed_changes) return;
    const c = s.coverage, n = s.confirmed_changes;
    const box = E('section', undefined, 'notice');
    box.id = 'latestScan';
    box.setAttribute('aria-label', 'Wynik ostatniego skanu');
    let time = s.finished_at || s.started_at || s.run_id;
    const date = new Date(time);
    if (Number.isFinite(date.getTime())) time = new Intl.DateTimeFormat('pl-PL', {
      timeZone: 'Europe/Warsaw', dateStyle: 'short', timeStyle: 'short'
    }).format(date);
    box.append(E('strong', 'Ostatni skan: ' + time + ' · ' + (s.status === 'partial' ? 'WERYFIKACJA CZĘŚCIOWA' : s.status)));
    box.append(E('p', s.summary || 'Brak szczegółowego podsumowania.'));
    box.append(E('p', 'Potwierdzone w tym skanie: ' + (c.fresh_active_confirmations ?? '—') +
      ' aktualnie dostępnych aut · ' + (n.vehicles_gone ?? '—') + ' zniknięć · ' +
      (n.price_changes ?? '—') + ' zmian cen. Odzyskane pełne linki: ' + (s.recovered_links || []).length + '.'));
    if (s.status === 'partial') box.append(E('p', 'Błędy i stare kopie nie aktualizują cen ani nie oznaczają sprzedaży. Tabela zachowuje ostatnie znane dane; nie przedstawia wszystkich ofert jako sprawdzonych teraz.', 'muted'));
    const details = E('details'); details.append(E('summary', 'Zakres sprawdzenia portali'));
    for (const [portal, p] of Object.entries(c.by_portal || {})) {
      details.append(E('p', portal.toUpperCase() + ': ' + (p.direct_attempts || 0) + ' prób otwarcia · ' +
        (p.historical_cached_pages || 0) + ' starych kopii · ' + (p.failed_direct_reads || 0) +
        ' nieudanych odczytów · ' + (p.http_410 || 0) + ' komunikatów 410' +
        (p.search_only ? ' · ' + p.search_only + ' dodatkowych kopii szukanych po ID' : '') + '.'));
    }
    const a = E('a', 'Pełny zapis tego skanu (JSON) ↗');
    a.href = './scan.json'; a.target = '_blank'; a.rel = 'noopener noreferrer'; details.append(a);
    box.append(details); mount.prepend(box);
  }).catch(() => {
    const box = E('p', 'Nie udało się wczytać wyniku ostatniego skanu. Widoczne daty raportów nie są nowym potwierdzeniem dostępności.', 'notice');
    box.id = 'latestScan'; mount.prepend(box);
  });
})();
