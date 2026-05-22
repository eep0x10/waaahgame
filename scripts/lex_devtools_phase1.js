// PHASE 1 (v2 — iframe nav) — Cole no DevTools em https://ageofsigmar.lexicanum.com/wiki/List_of_units
// fetch() bloqueado pelo CF (Sec-Fetch-Mode: cors). Iframe = navigation real, passa CF.
// Tempo: ~500 units * 2s = ~17min

(async () => {
  function loadInIframe(url, timeoutMs = 15000) {
    return new Promise(resolve => {
      const iframe = document.createElement('iframe');
      iframe.style.cssText = 'position:absolute;left:-9999px;width:1px;height:1px';
      let done = false;
      const finish = (val) => {
        if (done) return;
        done = true;
        try { iframe.remove(); } catch(e){}
        resolve(val);
      };
      const timer = setTimeout(() => finish(null), timeoutMs);
      iframe.onload = () => {
        clearTimeout(timer);
        try {
          const doc = iframe.contentDocument;
          const html = doc.documentElement.outerHTML;
          finish({ url: iframe.contentWindow.location.href, html });
        } catch (e) {
          finish({ url: iframe.src, html: null, err: e.message });
        }
      };
      iframe.onerror = () => { clearTimeout(timer); finish(null); };
      iframe.src = url;
      document.body.appendChild(iframe);
    });
  }

  console.log('[phase1] loading List_of_units via iframe...');
  const listRes = await loadInIframe('/wiki/List_of_units');
  if (!listRes || !listRes.html || listRes.html.includes('Just a moment')) {
    console.error('[phase1] FAIL: CF blocked iframe too. Aborting.', listRes);
    return;
  }
  console.log('[phase1] list_html size:', listRes.html.length);

  const doc = new DOMParser().parseFromString(listRes.html, 'text/html');
  const tableLinks = [...doc.querySelectorAll('table.wikitable a[href^="/wiki/"]')];
  const seen = new Set();
  const unitHrefs = [];
  for (const a of tableLinks) {
    const h = a.getAttribute('href');
    if (!h || h.includes(':') || h.endsWith('redlink=1')) continue;
    if (a.classList.contains('new')) continue;
    if (seen.has(h)) continue;
    seen.add(h);
    unitHrefs.push(h);
  }
  console.log(`[phase1] ${unitHrefs.length} unique unit pages`);

  const result = { list_html: listRes.html, units: {}, errors: [] };
  for (let i = 0; i < unitHrefs.length; i++) {
    const href = unitHrefs[i];
    const res = await loadInIframe(href);
    if (res && res.html && !res.html.includes('Just a moment')) {
      result.units[href] = res.html;
    } else {
      result.errors.push(href);
    }
    if (i % 20 === 0 || i === unitHrefs.length - 1) {
      console.log(`[phase1] ${i + 1}/${unitHrefs.length} (errors=${result.errors.length})`);
      // checkpoint dump every 100 to avoid losing progress
      if (i > 0 && i % 100 === 0) {
        const partial = new Blob([JSON.stringify(result)], { type: 'application/json' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(partial);
        a.download = `lex_dump_checkpoint_${i}.json`;
        a.click();
      }
    }
    await new Promise(r => setTimeout(r, 600));
  }
  console.log(`[phase1] DONE. units=${Object.keys(result.units).length} errors=${result.errors.length}`);

  const blob = new Blob([JSON.stringify(result)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'lex_dump.json';
  a.click();
})();
