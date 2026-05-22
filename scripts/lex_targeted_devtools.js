// lex_targeted_devtools.js — targeted mini photo scraper (25 units)
// ============================================================
// WHERE TO PASTE:
//   Open Firefox, navigate to any page on ageofsigmar.lexicanum.com
//   while your CF-cleared session is active (e.g. the List_of_units page).
//   Open DevTools → Console tab.
//   Paste the entire contents of this file and press Enter.
//
// WHAT IT DOES:
//   For each of the 25 units below, it:
//     1. Loads the Lexicanum wiki page via a hidden iframe (CF treats this
//        as a navigation request — clearance cookies are honoured, no 403)
//     2. Reads iframe.contentDocument (same-origin) to find the lowest-
//        numbered _M0N image reference in the rendered DOM
//     3. Downloads the image via the existing fetch→canvasBlob hybrid
//        (<img> element loads bypass CF's fetch-specific challenges)
//     4. Adds it to a JSZip archive keyed by DB slug (e.g. nagash.jpg)
//   Checkpoint ZIPs are saved every 10 units.
//   Final output: lex_targeted_minis.zip
//
// EXPECTED CONSOLE OUTPUT (per unit):
//   [targeted] 1/25 morathi-khaine ok
//   [targeted] 2/25 kairos-fateweaver ok_canvas
//   [targeted] 7/25 brokk-grungsson ok_short          ← CF-403 title, short fallback
//   ...
//   [targeted] DONE. ok=N ok_canvas=N ok_short=N ok_canvas_short=N fail=N tainted=N no_page=N no_image=N
//
// RATE LIMIT: 800ms between units (iframe loads + image loads are heavier
//             than the old two-fetch approach).
//             +400ms extra pause before each short-title fallback attempt.
// ============================================================

(async () => {

  // ── JSZip inject ──────────────────────────────────────────────────────────
  if (typeof JSZip === 'undefined') {
    await new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = 'https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js';
      s.onload = resolve;
      s.onerror = reject;
      document.head.appendChild(s);
    });
    console.log('[targeted] JSZip loaded');
  }

  // ── Unit list: [db_slug, lex_page_title] ─────────────────────────────────
  // 25 entries — verified count.
  const UNITS = [
    ["morathi-khaine",                 "Morathi-Khaine"],
    ["kairos-fateweaver",              "Kairos Fateweaver"],
    ["skragrott-the-loonking",         "Skragrott, the Loonking"],
    ["moonclan-grots",                 "Stabba"],
    ["brokk-grungsson",                "Brokk Grungsson, Lord-Magnate of Barak-Nar"],
    ["alarith-spirit-of-the-mountain", "Alarith Spirit of the Mountain"],
    ["alarith-stoneguard",             "Alarith Stoneguard"],
    ["alarith-stonemage",              "Alarith Stonemage"],
    ["scinari-cathallar",              "Scinari Cathallar"],
    ["light-of-eltharion",             "The Light of Eltharion"],
    ["vanari-lord-regent",             "Vanari Lord Regent"],
    ["vanari-auralan-wardens",         "Vanari Auralan Wardens"],
    ["rotigus",                        "Rotigus"],
    ["gordrakk-the-fist-of-gork",      "Gordrakk, the Fist of Gork"],
    ["swampcalla-shaman",              "Swampcalla Shaman with Pot-grot"],
    ["kruleboyz-gutrippaz",            "Gutrippaz"],
    ["nagash",                         "Nagash, Supreme Lord of the Undead"],
    ["thanquol-on-boneripper",         "Thanquol on Boneripper"],
    ["archaon-the-everchosen",         "Archaon, the Everchosen"],
    ["belakor",                        "Be'lakor, the Dark Master"],
    ["black-knights",                  "Barrow Knight"],
    ["mannfred-von-carstein",          "Mannfred von Carstein, Mortarch of Night"],
    ["vampire-lord-on-zombie-dragon",  "Vampire Lord"],
    ["yndrasta-the-celestial-spear",   "Yndrasta, the Celestial Spear"],
    ["drycha-hamadreth",               "Drycha Hamadreth"],
  ];

  console.log('[targeted] units to fetch:', UNITS.length);

  // ── Helpers ───────────────────────────────────────────────────────────────

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

  // Canvas fallback: loads via <img crossOrigin="anonymous"> to bypass CF
  // image-fetch blocks. Returns a Blob (image/jpeg, 0.92) or null on failure.
  // Sets taintedRef.tainted = true on SecurityError (cross-origin canvas taint).
  function canvasBlob(url, taintedRef) {
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
          if (e instanceof DOMException && e.name === 'SecurityError') {
            taintedRef.tainted = true;
          }
          resolve(null);
        }
      };
      img.onerror = () => { clearTimeout(timeout); resolve(null); };
      img.src = url;
    });
  }

  // Build the wiki page URL for a given Lex page title.
  // MediaWiki convention: spaces → underscores; everything else encodeURIComponent'd.
  function wikiUrl(title) {
    const encoded = encodeURIComponent(title).replace(/%20/g, '_');
    return 'https://ageofsigmar.lexicanum.com/wiki/' + encoded;
  }

  // ── Iframe page loader ─────────────────────────────────────────────────────
  //
  // Loads `url` in a hidden iframe (same-origin) and returns the
  // iframe's contentDocument after a short settle delay.
  // Returns null on timeout, load error, or cross-origin/CSP access failure.
  // The iframe is ALWAYS removed in the finally block.
  //
  function loadPageViaIframe(url, timeoutMs) {
    return new Promise(resolve => {
      const iframe = document.createElement('iframe');
      iframe.style.cssText =
        'position:fixed; left:-10000px; top:0; width:1px; height:1px; visibility:hidden;';

      let settled = false;
      let loadTimer = null;
      let settleTimer = null;

      function cleanup() {
        clearTimeout(loadTimer);
        clearTimeout(settleTimer);
        try { document.body.removeChild(iframe); } catch (_) {}
      }

      function finish(doc) {
        if (settled) return;
        settled = true;
        cleanup();
        resolve(doc);
      }

      // Timeout guard — fires if onload never fires within timeoutMs
      loadTimer = setTimeout(() => finish(null), timeoutMs);

      iframe.onload = () => {
        // Give the page a small settle window (300 ms) so that any
        // synchronous DOM manipulation in the wiki page's own scripts
        // (e.g. image gallery inits) finishes before we read the DOM.
        // The M0N images are in the initial HTML, so 300 ms is ample.
        settleTimer = setTimeout(() => {
          let doc = null;
          try {
            // Will throw if the page ended up cross-origin (should not
            // happen since all targets are same-origin, but be safe).
            doc = iframe.contentDocument;
          } catch (_) {
            // SecurityError — cross-origin or CSP block
          }
          finish(doc);
        }, 300);
      };

      iframe.onerror = () => finish(null);

      // Append first, then set src — ensures onload fires correctly in all
      // browsers (some browsers mis-fire onload for about:blank otherwise).
      document.body.appendChild(iframe);
      iframe.src = url;
    });
  }

  // ── DOM-based image reference extractor ───────────────────────────────────
  //
  // Given an iframe contentDocument and the unit's page title (for name-match
  // fallback), returns { type, url, n } for the best miniature photo found, or
  // null if none could be identified.
  //
  // Four-level preference cascade:
  //   1. PREFERRED  — any img whose full path matches _M\d+.(jpe?g|png).
  //                   Lowest M-number wins.
  //   2. FALLBACK A — first <img> inside .infobox with src under
  //                   /mediawiki/images/ and naturalWidth or naturalHeight ≥ 100.
  //   3. FALLBACK B — first <img> inside .mw-parser-output with src under
  //                   /mediawiki/images/ and size ≥ 200, NOT inside
  //                   .nav / .navbox / .toc / .thumb-tiny / .icon / .gallery-text.
  //   4. LAST RESORT — any img whose src is under /mediawiki/images/ and whose
  //                    filename substring matches the unit title (spaces→_).
  //
  // For every candidate the full-size URL is built by stripping /thumb/ and any
  // trailing /NNNpx-... suffix.
  //
  // When falling through to a fallback level the function logs:
  //   [targeted] N/25 <slug> ... via=<preferred|infobox|content|name-match>
  // When extraction completely fails it logs the first mediawiki image URL found
  // on the page for diagnostics:
  //   [targeted] N/25 <slug> no_image_found (first_img=<url>)
  //
  function extractImageRefFromDoc(doc, lexTitle, label) {
    if (!doc) return null;

    // ── Helpers ──────────────────────────────────────────────────────────────

    // Normalise any mediawiki images URL (possibly a thumb) to the full-size URL.
    // Returns { url, n } where n is the M-number (0 if not an _M\d+ match), or
    // null if the src is not a valid mediawiki images path on the expected host.
    function normaliseToFull(src) {
      if (!src) return null;
      let path;
      try {
        const u = new URL(src, 'https://ageofsigmar.lexicanum.com');
        if (u.hostname !== 'ageofsigmar.lexicanum.com') return null;
        path = u.pathname;
      } catch (_) {
        return null;
      }

      if (!path.startsWith('/mediawiki/images/')) return null;

      // Strip /thumb/ and the trailing /NNNpx-<filename> segment if present.
      // Input:  /mediawiki/images/thumb/H/HH/FileName.jpg/250px-FileName.jpg
      // Output: /mediawiki/images/H/HH/FileName.jpg
      let fullPath = path.replace(
        /^(\/mediawiki\/images\/)thumb\/((?:[a-f0-9]\/[a-f0-9]{2}\/)?[^/]+)\/.+$/i,
        '$1$2'
      );

      const mMatch = fullPath.match(/_M(\d+)\.(jpe?g|png)$/i);
      const n = mMatch ? parseInt(mMatch[1], 10) : 0;

      return { url: 'https://ageofsigmar.lexicanum.com' + fullPath, n };
    }

    // Return an estimated size in pixels for an img element.
    // Prefers naturalWidth/naturalHeight; falls back to parsing the URL
    // for a NNNpx- prefix (common for MW thumbs).
    function imgSize(img, src) {
      const nw = img.naturalWidth  || 0;
      const nh = img.naturalHeight || 0;
      if (nw > 0 || nh > 0) return Math.max(nw, nh);
      // Try URL: /250px-... → 250
      const m = (src || '').match(/\/(\d+)px-/);
      return m ? parseInt(m[1], 10) : 0;
    }

    // Returns true if the element is a descendant of any of the given selectors.
    function insideAny(el, selectors) {
      return selectors.some(sel => el.closest(sel) !== null);
    }

    // ── Level 1: PREFERRED — _M\d+ images ───────────────────────────────────

    const mCandidates = [];

    const allImgs = doc.querySelectorAll('img');
    for (const img of allImgs) {
      for (const attr of ['src', 'srcset']) {
        const raw = img.getAttribute(attr);
        if (!raw) continue;
        // srcset may have multiple comma-separated entries
        const parts = attr === 'srcset'
          ? raw.split(',').map(p => p.trim().split(/\s+/)[0])
          : [raw];
        for (const src of parts) {
          const ref = normaliseToFull(src);
          if (ref && ref.n > 0) {
            mCandidates.push({ type: 'preferred', url: ref.url, n: ref.n });
          }
        }
      }
    }

    // Also check <a href="/wiki/File:..._M\d+..."> wrappers for inner imgs
    const fileLinks = doc.querySelectorAll('a[href^="/wiki/File:"]');
    for (const a of fileLinks) {
      const href = a.getAttribute('href') || '';
      if (!/_M\d+\.(jpe?g|png)$/i.test(href)) continue;
      const inner = a.querySelector('img');
      if (!inner) continue;
      for (const attr of ['src', 'srcset']) {
        const raw = inner.getAttribute(attr);
        if (!raw) continue;
        const parts = attr === 'srcset'
          ? raw.split(',').map(p => p.trim().split(/\s+/)[0])
          : [raw];
        for (const src of parts) {
          const ref = normaliseToFull(src);
          if (ref && ref.n > 0) {
            mCandidates.push({ type: 'preferred', url: ref.url, n: ref.n });
          }
        }
      }
    }

    if (mCandidates.length > 0) {
      // Deduplicate by URL, sort by lowest M-number
      const seen = new Set();
      const unique = mCandidates.filter(c => {
        if (seen.has(c.url)) return false;
        seen.add(c.url); return true;
      });
      unique.sort((a, b) => a.n - b.n);
      console.log(`${label} via=preferred (M${unique[0].n})`);
      return unique[0];
    }

    // ── Level 2: FALLBACK A — first infobox image ≥ 100px ───────────────────

    const infoboxImgs = doc.querySelectorAll('.infobox img');
    for (const img of infoboxImgs) {
      const src = img.getAttribute('src') || '';
      const ref = normaliseToFull(src);
      if (!ref) continue;
      const sz = imgSize(img, src);
      if (sz >= 100 || sz === 0) {
        // sz === 0 means we couldn't determine size; include rather than skip
        console.log(`${label} via=infobox`);
        return { type: 'infobox', url: ref.url, n: ref.n };
      }
    }

    // ── Level 3: FALLBACK B — first content image ≥ 200px, not in nav/toc/etc ─

    const EXCLUDED = ['.nav', '.navbox', '.toc', '.thumb-tiny', '.icon', '.gallery-text'];
    const contentImgs = doc.querySelectorAll('.mw-parser-output img');
    for (const img of contentImgs) {
      if (insideAny(img, EXCLUDED)) continue;
      const src = img.getAttribute('src') || '';
      const ref = normaliseToFull(src);
      if (!ref) continue;
      const sz = imgSize(img, src);
      if (sz >= 200) {
        console.log(`${label} via=content`);
        return { type: 'content', url: ref.url, n: ref.n };
      }
    }

    // ── Level 4: LAST RESORT — filename matches unit title ───────────────────

    const titleSlug = (lexTitle || '').replace(/\s+/g, '_').toLowerCase();
    for (const img of allImgs) {
      const src = img.getAttribute('src') || '';
      const ref = normaliseToFull(src);
      if (!ref) continue;
      const filenamePart = ref.url.split('/').pop().toLowerCase();
      if (filenamePart.includes(titleSlug) || titleSlug.includes(filenamePart.replace(/\.\w+$/, ''))) {
        console.log(`${label} via=name-match`);
        return { type: 'name-match', url: ref.url, n: ref.n };
      }
    }

    // ── Complete failure — log first mediawiki image found for diagnostics ───

    let firstImgUrl = '(none)';
    for (const img of allImgs) {
      const src = img.getAttribute('src') || '';
      try {
        const u = new URL(src, 'https://ageofsigmar.lexicanum.com');
        if (u.pathname.startsWith('/mediawiki/images/')) {
          firstImgUrl = u.href;
          break;
        }
      } catch (_) {}
    }
    console.warn(`${label} no_image_found (first_img=${firstImgUrl})`);
    return null;
  }

  // ── Short-title fallback chain ────────────────────────────────────────────
  //
  // Returns an ordered list of fallback titles to try after the primary
  // title fails (404/403/no_image).  Each entry is a shorter variant of the
  // original title; the list is deduplicated and the original title is
  // excluded (no point retrying the same URL).
  //
  // Fallback order:
  //   1. comma-trim  — everything before the first comma
  //      "Brokk Grungsson, Lord-Magnate of Barak-Nar" → "Brokk Grungsson"
  //      "Skragrott, the Loonking"                    → "Skragrott"
  //   2. " with " trim — everything before " with "
  //      "Swampcalla Shaman with Pot-grot"            → "Swampcalla Shaman"
  //   3. " on " trim — everything before " on "
  //      "Thanquol on Boneripper"                     → "Thanquol"
  //
  function shortTitleFallbacks(title) {
    const fallbacks = [];

    const commaIdx = title.indexOf(',');
    if (commaIdx !== -1) {
      fallbacks.push(title.slice(0, commaIdx).trim());
    }

    const withIdx = title.indexOf(' with ');
    if (withIdx !== -1) {
      fallbacks.push(title.slice(0, withIdx).trim());
    }

    const onIdx = title.indexOf(' on ');
    if (onIdx !== -1) {
      fallbacks.push(title.slice(0, onIdx).trim());
    }

    // Deduplicate and exclude the original title (no-op retry).
    const seen = new Set([title]);
    return fallbacks.filter(t => {
      if (seen.has(t)) return false;
      seen.add(t);
      return true;
    });
  }

  // ── Main loop ─────────────────────────────────────────────────────────────

  const zip = new JSZip();
  let ok = 0, ok_canvas = 0, ok_short = 0, ok_canvas_short = 0,
      fail = 0, tainted = 0, no_page = 0, no_image = 0;

  for (let i = 0; i < UNITS.length; i++) {
    const [slug, lexTitle] = UNITS[i];
    const label = `[targeted] ${i+1}/${UNITS.length} ${slug}`;
    let placed = false;

    // ── Step 1: load wiki page via hidden iframe ─────────────────────────────
    let imageUrl = null;
    let usedShortFallback = false;
    const pageUrl = wikiUrl(lexTitle);

    let doc = await loadPageViaIframe(pageUrl, 20000);
    let ref = doc ? extractImageRefFromDoc(doc, lexTitle, label) : null;

    // ── Step 1b: short-title fallback chain ──────────────────────────────────
    // Triggered when the primary attempt yields no doc (iframe 403/timeout)
    // OR when the doc loaded but contained no image reference at any level.
    if (!doc || !ref) {
      const fallbacks = shortTitleFallbacks(lexTitle);

      for (const shortTitle of fallbacks) {
        await sleep(400); // brief pause before retry

        const shortUrl = wikiUrl(shortTitle);
        const shortDoc = await loadPageViaIframe(shortUrl, 20000);
        const shortRef = shortDoc ? extractImageRefFromDoc(shortDoc, shortTitle, label) : null;

        if (shortRef) {
          // Success via short-title fallback — promote results
          doc = shortDoc;
          ref = shortRef;
          usedShortFallback = true;
          break;
        }
      }
    }

    if (!doc) {
      no_page++;
      console.warn(`${label} no_page (iframe timeout or access error)`);
      placed = true;
    } else if (!ref) {
      // no_image_found already logged with first_img diagnostic by extractImageRefFromDoc
      no_image++;
      placed = true;
    } else {
      imageUrl = ref.url;
    }

    // ── Step 2: download image (fetch → canvas fallback) ───────────────────
    if (!placed && imageUrl) {
      const ext = extOf(imageUrl);

      // 2a: try fetch first (gives original bytes when CF allows)
      try {
        const imgResp = await fetch(imageUrl, { credentials: 'include' });
        if (imgResp.status === 404) {
          no_image++;
          console.warn(`${label} no_image_found (image 404)`);
          placed = true;
        } else if (imgResp.ok) {
          const blob = await imgResp.blob();
          const ct = blob.type || '';
          if (blob.size >= 1000 && ct.startsWith('image/')) {
            zip.file(`${slug}.${ext}`, blob);
            if (usedShortFallback) {
              ok_short++;
              console.log(`${label} ok_short`);
            } else {
              ok++;
              console.log(`${label} ok`);
            }
            placed = true;
          }
          // else: CF challenge masquerading as 200 image — fall through to canvas
        }
        // non-ok non-404 (403 etc): fall through to canvas
      } catch (_) {
        // network error: fall through to canvas
      }

      // 2b: canvas fallback — <img> element loads bypass CF's fetch-specific challenges
      if (!placed) {
        const taintedRef = { tainted: false };
        const cblob = await canvasBlob(imageUrl, taintedRef);
        if (taintedRef.tainted) {
          tainted++;
          console.warn(`${label} tainted`);
        } else if (cblob && cblob.size >= 1000) {
          // Canvas always outputs JPEG regardless of source format
          zip.file(`${slug}.jpg`, cblob);
          if (usedShortFallback) {
            ok_canvas_short++;
            console.log(`${label} ok_canvas_short`);
          } else {
            ok_canvas++;
            console.log(`${label} ok_canvas`);
          }
        } else {
          fail++;
          console.warn(`${label} fail`);
        }
        placed = true;
      }
    }

    // ── Checkpoint every 10 units ───────────────────────────────────────────
    if ((i + 1) % 10 === 0) {
      console.log(`[targeted] ${i+1}/${UNITS.length} ok=${ok} ok_canvas=${ok_canvas} ok_short=${ok_short} ok_canvas_short=${ok_canvas_short} fail=${fail} tainted=${tainted} no_page=${no_page} no_image=${no_image}`);
      try {
        const cpBlob = await zip.generateAsync({ type: 'blob' });
        triggerDownload(cpBlob, `lex_targeted_minis_checkpoint_${String(i+1).padStart(2,'0')}.zip`);
        console.log(`[targeted] checkpoint ${i+1} saved`);
      } catch (e) {
        console.error('[targeted] checkpoint error', e);
      }
    }

    // 800ms between units (iframe loads + image loads = heavier than phase3's 250ms)
    await sleep(800);
  }

  // ── Final download ─────────────────────────────────────────────────────────
  console.log(`[targeted] DONE. ok=${ok} ok_canvas=${ok_canvas} ok_short=${ok_short} ok_canvas_short=${ok_canvas_short} fail=${fail} tainted=${tainted} no_page=${no_page} no_image=${no_image}`);
  const finalBlob = await zip.generateAsync({ type: 'blob' });
  triggerDownload(finalBlob, 'lex_targeted_minis.zip');
  console.log('[targeted] lex_targeted_minis.zip download triggered');

})();
