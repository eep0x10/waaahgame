// wh_targeted_devtools.js — targeted mini photo scraper (25 units, warhammer.com)
// ============================================================
// WHERE TO PASTE:
//   Open Firefox, navigate to any warhammer.com/en-US/shop/* page while
//   your AWS WAF-cleared session is active (must be logged in / clearance
//   cookies present).  Open DevTools → Console tab.
//   Paste the entire contents of this file and press Enter.
//
// WHAT IT DOES:
//   For each of the 25 units below, it:
//     1. Loads the warhammer.com search page for that unit's query in a
//        hidden iframe (same-origin, WAF clearance cookies honoured).
//        Waits onload + 3500ms for Next.js client-side hydration.
//     2. Reads iframe.contentDocument to find the first product-card anchor
//        (href starts with /en-US/shop/ but is not a category/filter URL).
//     3. Loads that product page in the same iframe, waits onload + 3500ms.
//     4. Reads the product page DOM to find the largest gallery image
//        (naturalWidth >= 400).
//     5. Downloads the image via fetch → canvasBlob fallback (crossOrigin
//        anonymous; WAF clearance means fetch should succeed).
//     6. Stores in a JSZip archive keyed by DB slug (e.g. nagash.jpg).
//   Checkpoint ZIPs are saved every 5 units.
//   Final output: wh_targeted_minis.zip
//
// EXPECTED CONSOLE OUTPUT (per unit):
//   [wh] 1/25 skragrott-the-loonking searching...
//   [wh] 1/25 skragrott-the-loonking product=Skragrott-the-Loonking
//   [wh] 1/25 skragrott-the-loonking ok url=https://images.warhammer.com/...
//   [wh] 2/25 nagash no_search_result
//   [wh] 3/25 kairos-fateweaver ok_canvas
//   ...
//   [wh] DONE. ok=N ok_canvas=N no_search_result=N no_product_image=N fail=N
//
// DIAGNOSTIC:
//   If you see mostly no_search_result, the iframe was WAF-challenged.
//   Refresh the warhammer.com page in the main tab, wait a moment, then
//   re-paste and run this script.
//
// EXPECTED RUNTIME: ~3 minutes (25 units × ~7s each).
// OUTPUT: downloads wh_targeted_minis.zip automatically when done.
// ============================================================

(async () => {

  // ── JSZip inject ─────────────────────────────────────────────────────────────
  if (typeof JSZip === 'undefined') {
    await new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = 'https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js';
      s.onload = resolve;
      s.onerror = reject;
      document.head.appendChild(s);
    });
    console.log('[wh] JSZip loaded');
  }

  // ── Unit list: [db_slug, search_query] ───────────────────────────────────────
  // 25 entries — verified count.
  const UNITS_JSON = [
    ["skragrott-the-loonking",         "Skragrott the Loonking"],
    ["moonclan-grots",                 "Stabbas"],
    ["brokk-grungsson",                "Brokk Grungsson"],
    ["alarith-spirit-of-the-mountain", "Alarith Spirit of the Mountain"],
    ["alarith-stoneguard",             "Alarith Stoneguard"],
    ["alarith-stonemage",              "Alarith Stonemage"],
    ["scinari-cathallar",              "Scinari Cathallar"],
    ["light-of-eltharion",             "The Light of Eltharion"],
    ["vanari-lord-regent",             "Vanari Lord Regent"],
    ["vanari-auralan-wardens",         "Vanari Auralan Wardens"],
    ["rotigus",                        "Rotigus"],
    ["gordrakk-the-fist-of-gork",      "Gordrakk the Fist of Gork"],
    ["swampcalla-shaman",              "Swampcalla Shaman"],
    ["kruleboyz-gutrippaz",            "Gutrippaz"],
    ["nagash",                         "Nagash Supreme Lord of the Undead"],
    ["thanquol-on-boneripper",         "Thanquol on Boneripper"],
    ["archaon-the-everchosen",         "Archaon the Everchosen"],
    ["belakor",                        "Belakor"],
    ["black-knights",                  "Barrow Knights"],
    ["mannfred-von-carstein",          "Mannfred von Carstein"],
    ["vampire-lord-on-zombie-dragon",  "Vampire Lord on Zombie Dragon"],
    ["yndrasta-the-celestial-spear",   "Yndrasta the Celestial Spear"],
    ["drycha-hamadreth",               "Drycha Hamadreth"],
    ["morathi-khaine",                 "Morathi-Khaine"],
    ["kairos-fateweaver",              "Kairos Fateweaver"],
  ];

  console.log('[wh] units to fetch:', UNITS_JSON.length);

  // ── Helpers ───────────────────────────────────────────────────────────────────

  const sleep = (ms) => new Promise(r => setTimeout(r, ms));

  const extOf = (url) => {
    const m = url.match(/\.([a-zA-Z0-9]+)(?:\?|$)/);
    return m ? m[1].toLowerCase() : 'jpg';
  };

  const triggerDownload = (blob, filename) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  // Canvas fallback: loads via <img crossOrigin="anonymous">.
  // Returns a Blob (image/jpeg, 0.92) or null on failure.
  function canvasBlob(url) {
    return new Promise(resolve => {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      const timeout = setTimeout(() => {
        img.onload = img.onerror = null;
        resolve(null);
      }, 15000);
      img.onload = () => {
        clearTimeout(timeout);
        try {
          const c = document.createElement('canvas');
          c.width  = img.naturalWidth  || img.width;
          c.height = img.naturalHeight || img.height;
          const ctx = c.getContext('2d');
          ctx.drawImage(img, 0, 0);
          c.toBlob(blob => resolve(blob || null), 'image/jpeg', 0.92);
        } catch (e) {
          resolve(null);
        }
      };
      img.onerror = () => { clearTimeout(timeout); resolve(null); };
      img.src = url;
    });
  }

  // ── Iframe page loader ────────────────────────────────────────────────────────
  //
  // Loads `url` in a hidden iframe and resolves with { iframe, doc } after
  // onload + `hydrationMs` milliseconds (Next.js client-side rendering settle).
  // Resolves with { iframe: null, doc: null } on timeout or access failure.
  //
  // IMPORTANT: the caller MUST call cleanup() on the returned object when done.
  // This is intentional so the caller can re-use the same iframe for the product
  // page load without an extra DOM insertion cycle (we simply reset iframe.src).
  //
  function loadPageViaIframe(url, timeoutMs, hydrationMs) {
    return new Promise(resolve => {
      const iframe = document.createElement('iframe');
      iframe.style.cssText =
        'position:fixed; left:-10000px; top:0; width:1px; height:1px; visibility:hidden;';

      let settled = false;
      let loadTimer = null;
      let hydrateTimer = null;

      function cleanup() {
        clearTimeout(loadTimer);
        clearTimeout(hydrateTimer);
        try { document.body.removeChild(iframe); } catch (_) {}
      }

      function finish(iframeEl, doc) {
        if (settled) return;
        settled = true;
        clearTimeout(loadTimer);
        clearTimeout(hydrateTimer);
        resolve({ iframe: iframeEl, doc, cleanup });
      }

      loadTimer = setTimeout(() => finish(null, null), timeoutMs);

      iframe.onload = () => {
        // Wait for Next.js hydration before reading the DOM.
        hydrateTimer = setTimeout(() => {
          let doc = null;
          try {
            doc = iframe.contentDocument;
          } catch (_) {
            // SecurityError — cross-origin or CSP block (should not happen same-origin)
          }
          finish(iframe, doc);
        }, hydrationMs);
      };

      iframe.onerror = () => finish(null, null);

      document.body.appendChild(iframe);
      iframe.src = url;
    });
  }

  // loadPageInExistingIframe: reassign src on an already-appended iframe and
  // wait for onload + hydrationMs.  Returns doc (or null on timeout/error).
  function loadPageInExistingIframe(iframe, url, timeoutMs, hydrationMs) {
    return new Promise(resolve => {
      let settled = false;
      let loadTimer = null;
      let hydrateTimer = null;

      function finish(doc) {
        if (settled) return;
        settled = true;
        clearTimeout(loadTimer);
        clearTimeout(hydrateTimer);
        iframe.onload  = null;
        iframe.onerror = null;
        resolve(doc);
      }

      loadTimer = setTimeout(() => finish(null), timeoutMs);

      iframe.onload = () => {
        hydrateTimer = setTimeout(() => {
          let doc = null;
          try {
            doc = iframe.contentDocument;
          } catch (_) {}
          finish(doc);
        }, hydrationMs);
      };

      iframe.onerror = () => finish(null);

      iframe.src = url;
    });
  }

  // ── Product image extractor ───────────────────────────────────────────────────
  //
  // Given the product page contentDocument, tries a cascade of selectors to find
  // the main miniature photo.  Returns the URL string of the best candidate, or
  // null if nothing usable is found.
  //
  // Selector cascade (first match with naturalWidth >= 400 wins):
  //   1. [data-testid*="product-image"] img
  //   2. [data-testid*="gallery"] img
  //   3. main img[src*="warhammer"] with naturalWidth >= 400
  //   4. Any <img> whose src contains /assets/ or media. or images.warhammer,
  //      with naturalWidth >= 400
  //
  // Among all candidates that pass the size threshold, the one with the greatest
  // naturalWidth is returned (i.e. the highest-resolution image found).
  //
  function extractProductImage(doc) {
    if (!doc) return null;

    const candidates = [];

    function collect(selector) {
      try {
        const imgs = doc.querySelectorAll(selector);
        for (const img of imgs) {
          const src = img.src || img.getAttribute('src') || '';
          if (!src) continue;
          const nw = img.naturalWidth || 0;
          candidates.push({ src, nw });
        }
      } catch (_) {}
    }

    collect('[data-testid*="product-image"] img');
    collect('[data-testid*="gallery"] img');
    collect('main img');

    // Also collect any <img> anywhere whose src hints at a CDN image host.
    try {
      const allImgs = doc.querySelectorAll('img');
      for (const img of allImgs) {
        const src = img.src || img.getAttribute('src') || '';
        if (!src) continue;
        if (
          src.includes('/assets/') ||
          src.includes('media.') ||
          src.includes('images.warhammer') ||
          src.includes('warhammer.com')
        ) {
          const nw = img.naturalWidth || 0;
          candidates.push({ src, nw });
        }
      }
    } catch (_) {}

    // Filter: naturalWidth must be >= 400 (or unknown — 0 means not yet loaded,
    // include rather than discard so we have something to try).
    // Among those with known width, prefer the largest.
    const withSize = candidates.filter(c => c.nw >= 400);
    const fallback = candidates.filter(c => c.nw === 0);
    const pool = withSize.length > 0 ? withSize : fallback;

    if (pool.length === 0) return null;

    // Deduplicate by src, then pick largest nw.
    const seen = new Set();
    const unique = pool.filter(c => {
      if (seen.has(c.src)) return false;
      seen.add(c.src); return true;
    });
    unique.sort((a, b) => b.nw - a.nw);
    return unique[0].src;
  }

  // ── Search result extractor ───────────────────────────────────────────────────
  //
  // Given the search page contentDocument and the current query URL (so we can
  // exclude "self" links), returns the href of the first valid product card, or
  // null.
  //
  // Valid product card: anchor whose href starts with /en-US/shop/ but is NOT:
  //   - a category URL  (/en-US/shop/category/...)
  //   - a filter URL    (/en-US/shop?...)
  //   - the search URL  (/en-US/shop?query=...)
  //
  function extractFirstProductHref(doc) {
    if (!doc) return null;

    try {
      const anchors = doc.querySelectorAll('a[href^="/en-US/shop/"]');
      for (const a of anchors) {
        const href = a.getAttribute('href') || '';
        // Must start with /en-US/shop/ and have something after the slash
        if (!href.startsWith('/en-US/shop/')) continue;
        const afterShop = href.slice('/en-US/shop/'.length);
        // Skip: category pages
        if (afterShop.startsWith('category/')) continue;
        // Skip: any empty after-shop segment
        if (!afterShop) continue;
        // Skip: query strings (shouldn't match `a[href^="/en-US/shop/"]` but be safe)
        if (href.includes('?')) continue;
        return href;
      }
    } catch (_) {}

    return null;
  }

  // ── Main loop ─────────────────────────────────────────────────────────────────

  const zip = new JSZip();
  let ok = 0, ok_canvas = 0, no_search_result = 0, no_product_image = 0, fail = 0;

  const HYDRATION_MS  = 3500;  // Next.js settle window after each iframe load
  const TIMEOUT_MS    = 25000; // total iframe load timeout
  const UNIT_PAUSE_MS = 1000;  // pause between units

  for (let i = 0; i < UNITS_JSON.length; i++) {
    const [slug, query] = UNITS_JSON[i];
    const label = `[wh] ${i+1}/${UNITS_JSON.length} ${slug}`;

    console.log(`${label} searching...`);

    let placed = false;

    // ── IFRAME LOAD 1: search page ────────────────────────────────────────────
    const searchUrl = `https://www.warhammer.com/en-US/shop?query=${encodeURIComponent(query)}`;

    const { iframe, doc: searchDoc, cleanup } = await loadPageViaIframe(
      searchUrl, TIMEOUT_MS, HYDRATION_MS
    );

    if (!iframe || !searchDoc) {
      no_search_result++;
      console.warn(`${label} no_search_result`);
      if (cleanup) cleanup();
      await sleep(UNIT_PAUSE_MS);
      continue;
    }

    const productHref = extractFirstProductHref(searchDoc);

    if (!productHref) {
      no_search_result++;
      console.warn(`${label} no_search_result`);
      cleanup();
      await sleep(UNIT_PAUSE_MS);
      continue;
    }

    // Derive a short slug from the product href for logging.
    const productSlugForLog = productHref.split('/').pop() || productHref;
    console.log(`${label} product=${productSlugForLog}`);

    // ── IFRAME LOAD 2: product page ───────────────────────────────────────────
    const productUrl = 'https://www.warhammer.com' + productHref;

    const productDoc = await loadPageInExistingIframe(
      iframe, productUrl, TIMEOUT_MS, HYDRATION_MS
    );

    // Done with iframe — clean it up regardless of outcome.
    cleanup();

    if (!productDoc) {
      no_product_image++;
      console.warn(`${label} no_product_image`);
      await sleep(UNIT_PAUSE_MS);
      continue;
    }

    const imageUrl = extractProductImage(productDoc);

    if (!imageUrl) {
      no_product_image++;
      console.warn(`${label} no_product_image`);
      await sleep(UNIT_PAUSE_MS);
      continue;
    }

    // ── Image download: fetch → canvas fallback ───────────────────────────────
    const ext = extOf(imageUrl);

    // 2a: try fetch first (gives original bytes; WAF clearance should allow this)
    try {
      const imgResp = await fetch(imageUrl, { credentials: 'include' });
      if (imgResp.ok) {
        const blob = await imgResp.blob();
        const ct = blob.type || '';
        if (blob.size >= 1000 && ct.startsWith('image/')) {
          zip.file(`${slug}.${ext}`, blob);
          ok++;
          console.log(`${label} ok url=${imageUrl}`);
          placed = true;
        }
        // else: CF/WAF challenge masquerading as 200 — fall through to canvas
      }
      // non-ok: fall through to canvas
    } catch (_) {
      // network error — fall through to canvas
    }

    // 2b: canvas fallback
    if (!placed) {
      const cblob = await canvasBlob(imageUrl);
      if (cblob && cblob.size >= 1000) {
        zip.file(`${slug}.jpg`, cblob);
        ok_canvas++;
        console.log(`${label} ok_canvas`);
        placed = true;
      } else {
        fail++;
        console.warn(`${label} fail`);
        placed = true;
      }
    }

    // ── Checkpoint every 5 units ──────────────────────────────────────────────
    if ((i + 1) % 5 === 0) {
      console.log(
        `[wh] checkpoint ${i+1}/${UNITS_JSON.length} ` +
        `ok=${ok} ok_canvas=${ok_canvas} no_search_result=${no_search_result} ` +
        `no_product_image=${no_product_image} fail=${fail}`
      );
      try {
        const cpBlob = await zip.generateAsync({ type: 'blob' });
        triggerDownload(cpBlob, `wh_targeted_minis_checkpoint_${String(i+1).padStart(2,'0')}.zip`);
        console.log(`[wh] checkpoint ${i+1} saved`);
      } catch (e) {
        console.error('[wh] checkpoint error', e);
      }
    }

    await sleep(UNIT_PAUSE_MS);
  }

  // ── Final download ────────────────────────────────────────────────────────────
  console.log(
    `[wh] DONE. ok=${ok} ok_canvas=${ok_canvas} ` +
    `no_search_result=${no_search_result} no_product_image=${no_product_image} fail=${fail}`
  );
  const finalBlob = await zip.generateAsync({ type: 'blob' });
  triggerDownload(finalBlob, 'wh_targeted_minis.zip');
  console.log('[wh] wh_targeted_minis.zip download triggered');

})();
