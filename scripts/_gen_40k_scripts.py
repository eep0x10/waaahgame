"""Generate 5 batch DevTools scraper scripts for 40K minis."""
import json, pathlib, re

units = json.loads(pathlib.Path(__file__).parent / '..' / 'scripts' / 'cache' / '40k_units_clean.json'
                   if False else
                   (pathlib.Path(__file__).parent.parent / 'scripts' / 'cache' / '40k_units_clean.json')
                   .read_text(encoding='utf-8'))

assert len(units) == 351, f"Expected 351, got {len(units)}"

def make_entry(slug, name):
    """Build [slug, query] JS array entry. Strips [Legends]/[Crucible]/(Parens) from query."""
    query = re.sub(r'\s*\[.*?\]', '', name).strip()
    query = re.sub(r'\s*\(.*?\)', '', query).strip()
    query = query.replace("&apos;", "'").replace("&amp;", "&")
    return f"  [{json.dumps(slug)}, {json.dumps(query)}]"


def make_script(batch_num, batch_units, all_batches):
    n = len(batch_units)
    start_idx = sum(len(all_batches[i]) for i in range(batch_num - 1)) + 1
    end_idx = start_idx + n - 1
    eta_min = round(n * 8 / 60)
    prev_info = f"batch{batch_num - 1}" if batch_num > 1 else "(none — this is first)"

    entries_js = ",\n".join(make_entry(u['slug'], u['name']) for u in batch_units)

    return f"""\
// wh_40k_devtools_batch{batch_num}.js — 40K mini photo scraper
// Batch {batch_num}/5: units {start_idx}–{end_idx} of 351 ({n} units)
// ============================================================
// WHERE TO PASTE:
//   Open Firefox, navigate to any warhammer.com/en-US/shop/* page while
//   your AWS WAF-cleared session is active (logged in / clearance cookies
//   present).  Open DevTools → Console tab, paste entire file, Enter.
//
// WHAT IT DOES:
//   For each unit: load search page in hidden iframe → find first product
//   card → load product page in same iframe → extract largest gallery img
//   (naturalWidth >= 400) → fetch/canvas-fallback → add to JSZip.
//   Checkpoints every 5 units. Final: wh_40k_minis_batch{batch_num}.zip
//
// EXPECTED RUNTIME: ~{eta_min} min ({n} units × ~8s each).
// RUN ORDER: Run {prev_info} before this. Wait for it to finish.
//
// DIAGNOSTIC: Mostly no_search_result? WAF re-challenged.
//   Refresh warhammer.com main tab, wait, re-paste.
// ============================================================

(async () => {{

  // ── JSZip inject ─────────────────────────────────────────────────────────────
  if (typeof JSZip === 'undefined') {{
    await new Promise((resolve, reject) => {{
      const s = document.createElement('script');
      s.src = 'https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js';
      s.onload = resolve;
      s.onerror = reject;
      document.head.appendChild(s);
    }});
    console.log('[wh] JSZip loaded');
  }}

  // ── Unit list: [db_slug, search_query] ───────────────────────────────────────
  // Batch {batch_num}/5: {n} entries (units {start_idx}–{end_idx} of 351).
  // [Legends] and (variant) suffixes stripped from search queries.
  const UNITS = [
{entries_js}
  ];

  console.log('[wh] batch {batch_num}/5: units to fetch:', UNITS.length);

  // ── Helpers ───────────────────────────────────────────────────────────────────

  const sleep = (ms) => new Promise(r => setTimeout(r, ms));

  const extOf = (url) => {{
    const m = url.match(/\\.([a-zA-Z0-9]+)(?:\\?|$)/);
    return m ? m[1].toLowerCase() : 'jpg';
  }};

  const triggerDownload = (blob, filename) => {{
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }};

  function canvasBlob(url) {{
    return new Promise(resolve => {{
      const img = new Image();
      img.crossOrigin = 'anonymous';
      const timeout = setTimeout(() => {{
        img.onload = img.onerror = null;
        resolve(null);
      }}, 15000);
      img.onload = () => {{
        clearTimeout(timeout);
        try {{
          const c = document.createElement('canvas');
          c.width  = img.naturalWidth  || img.width;
          c.height = img.naturalHeight || img.height;
          const ctx = c.getContext('2d');
          ctx.drawImage(img, 0, 0);
          c.toBlob(blob => resolve(blob || null), 'image/jpeg', 0.92);
        }} catch (e) {{
          resolve(null);
        }}
      }};
      img.onerror = () => {{ clearTimeout(timeout); resolve(null); }};
      img.src = url;
    }});
  }}

  // ── Iframe page loader ────────────────────────────────────────────────────────
  // Loads url in hidden iframe, resolves {{iframe, doc, cleanup}} after
  // onload + hydrationMs. Resolves {{iframe:null, doc:null}} on timeout.
  function loadPageViaIframe(url, timeoutMs, hydrationMs) {{
    return new Promise(resolve => {{
      const iframe = document.createElement('iframe');
      iframe.style.cssText =
        'position:fixed; left:-10000px; top:0; width:1px; height:1px; visibility:hidden;';

      let settled = false;
      let loadTimer = null;
      let hydrateTimer = null;

      function cleanup() {{
        clearTimeout(loadTimer);
        clearTimeout(hydrateTimer);
        try {{ document.body.removeChild(iframe); }} catch (_) {{}}
      }}

      function finish(iframeEl, doc) {{
        if (settled) return;
        settled = true;
        clearTimeout(loadTimer);
        clearTimeout(hydrateTimer);
        resolve({{ iframe: iframeEl, doc, cleanup }});
      }}

      loadTimer = setTimeout(() => finish(null, null), timeoutMs);

      iframe.onload = () => {{
        hydrateTimer = setTimeout(() => {{
          let doc = null;
          try {{ doc = iframe.contentDocument; }} catch (_) {{}}
          finish(iframe, doc);
        }}, hydrationMs);
      }};

      iframe.onerror = () => finish(null, null);

      document.body.appendChild(iframe);
      iframe.src = url;
    }});
  }}

  function loadPageInExistingIframe(iframe, url, timeoutMs, hydrationMs) {{
    return new Promise(resolve => {{
      let settled = false;
      let loadTimer = null;
      let hydrateTimer = null;

      function finish(doc) {{
        if (settled) return;
        settled = true;
        clearTimeout(loadTimer);
        clearTimeout(hydrateTimer);
        iframe.onload  = null;
        iframe.onerror = null;
        resolve(doc);
      }}

      loadTimer = setTimeout(() => finish(null), timeoutMs);

      iframe.onload = () => {{
        hydrateTimer = setTimeout(() => {{
          let doc = null;
          try {{ doc = iframe.contentDocument; }} catch (_) {{}}
          finish(doc);
        }}, hydrationMs);
      }};

      iframe.onerror = () => finish(null);

      iframe.src = url;
    }});
  }}

  // ── Product image extractor ───────────────────────────────────────────────────
  // Selector cascade: product-image testid → gallery testid → main img →
  // any img from CDN hosts. Among candidates with naturalWidth>=400, picks
  // the largest. Falls back to width=0 candidates if nothing qualifies.
  function extractProductImage(doc) {{
    if (!doc) return null;

    const candidates = [];

    function collect(selector) {{
      try {{
        const imgs = doc.querySelectorAll(selector);
        for (const img of imgs) {{
          const src = img.src || img.getAttribute('src') || '';
          if (!src) continue;
          candidates.push({{ src, nw: img.naturalWidth || 0 }});
        }}
      }} catch (_) {{}}
    }}

    collect('[data-testid*="product-image"] img');
    collect('[data-testid*="gallery"] img');
    collect('main img');

    try {{
      const allImgs = doc.querySelectorAll('img');
      for (const img of allImgs) {{
        const src = img.src || img.getAttribute('src') || '';
        if (!src) continue;
        if (src.includes('/assets/') || src.includes('media.') ||
            src.includes('images.warhammer') || src.includes('warhammer.com')) {{
          candidates.push({{ src, nw: img.naturalWidth || 0 }});
        }}
      }}
    }} catch (_) {{}}

    const withSize = candidates.filter(c => c.nw >= 400);
    const fallback = candidates.filter(c => c.nw === 0);
    const pool = withSize.length > 0 ? withSize : fallback;
    if (pool.length === 0) return null;

    const seen = new Set();
    const unique = pool.filter(c => {{
      if (seen.has(c.src)) return false;
      seen.add(c.src); return true;
    }});
    unique.sort((a, b) => b.nw - a.nw);
    return unique[0].src;
  }}

  // ── Search result extractor ───────────────────────────────────────────────────
  // Returns first product-card href from search page DOM.
  // Skips category URLs and filter/query-string URLs.
  function extractFirstProductHref(doc) {{
    if (!doc) return null;
    try {{
      const anchors = doc.querySelectorAll('a[href^="/en-US/shop/"]');
      for (const a of anchors) {{
        const href = a.getAttribute('href') || '';
        if (!href.startsWith('/en-US/shop/')) continue;
        const afterShop = href.slice('/en-US/shop/'.length);
        if (afterShop.startsWith('category/')) continue;
        if (!afterShop) continue;
        if (href.includes('?')) continue;
        return href;
      }}
    }} catch (_) {{}}
    return null;
  }}

  // ── Main loop ─────────────────────────────────────────────────────────────────

  const zip = new JSZip();
  let ok = 0, ok_canvas = 0, no_search_result = 0, no_product_image = 0, fail = 0;

  const HYDRATION_MS  = 3500;   // Next.js settle window after iframe load
  const TIMEOUT_MS    = 25000;  // total iframe load timeout
  const UNIT_PAUSE_MS = 1000;   // pause between units

  for (let i = 0; i < UNITS.length; i++) {{
    const [slug, query] = UNITS[i];
    const label = `[wh] ${{i+1}}/${{UNITS.length}} ${{slug}} (b{batch_num}/5)`;

    console.log(`${{label}} searching...`);
    let placed = false;

    const searchUrl =
      `https://www.warhammer.com/en-US/shop?query=${{encodeURIComponent(query)}}`;

    const {{ iframe, doc: searchDoc, cleanup }} = await loadPageViaIframe(
      searchUrl, TIMEOUT_MS, HYDRATION_MS
    );

    if (!iframe || !searchDoc) {{
      no_search_result++;
      console.warn(`${{label}} no_search_result`);
      if (cleanup) cleanup();
      await sleep(UNIT_PAUSE_MS);
      continue;
    }}

    const productHref = extractFirstProductHref(searchDoc);

    if (!productHref) {{
      no_search_result++;
      console.warn(`${{label}} no_search_result`);
      cleanup();
      await sleep(UNIT_PAUSE_MS);
      continue;
    }}

    const productSlugForLog = productHref.split('/').pop() || productHref;
    console.log(`${{label}} product=${{productSlugForLog}}`);

    const productUrl = 'https://www.warhammer.com' + productHref;

    const productDoc = await loadPageInExistingIframe(
      iframe, productUrl, TIMEOUT_MS, HYDRATION_MS
    );

    cleanup();

    if (!productDoc) {{
      no_product_image++;
      console.warn(`${{label}} no_product_image`);
      await sleep(UNIT_PAUSE_MS);
      continue;
    }}

    const imageUrl = extractProductImage(productDoc);

    if (!imageUrl) {{
      no_product_image++;
      console.warn(`${{label}} no_product_image`);
      await sleep(UNIT_PAUSE_MS);
      continue;
    }}

    const ext = extOf(imageUrl);

    // 2a: try fetch (WAF clearance cookies should allow this)
    try {{
      const imgResp = await fetch(imageUrl, {{ credentials: 'include' }});
      if (imgResp.ok) {{
        const blob = await imgResp.blob();
        const ct = blob.type || '';
        if (blob.size >= 1000 && ct.startsWith('image/')) {{
          zip.file(`${{slug}}.${{ext}}`, blob);
          ok++;
          console.log(`${{label}} ok url=${{imageUrl}}`);
          placed = true;
        }}
      }}
    }} catch (_) {{}}

    // 2b: canvas fallback
    if (!placed) {{
      const cblob = await canvasBlob(imageUrl);
      if (cblob && cblob.size >= 1000) {{
        zip.file(`${{slug}}.jpg`, cblob);
        ok_canvas++;
        console.log(`${{label}} ok_canvas`);
        placed = true;
      }} else {{
        fail++;
        console.warn(`${{label}} fail`);
        placed = true;
      }}
    }}

    // Checkpoint every 5 units
    if ((i + 1) % 5 === 0) {{
      console.log(
        `[wh] checkpoint ${{i+1}}/${{UNITS.length}} b{batch_num} ` +
        `ok=${{ok}} ok_canvas=${{ok_canvas}} no_search_result=${{no_search_result}} ` +
        `no_product_image=${{no_product_image}} fail=${{fail}}`
      );
      try {{
        const cpBlob = await zip.generateAsync({{ type: 'blob' }});
        triggerDownload(cpBlob,
          `wh_40k_minis_batch{batch_num}_cp${{String(i+1).padStart(2,'0')}}.zip`);
        console.log(`[wh] checkpoint ${{i+1}} saved`);
      }} catch (e) {{
        console.error('[wh] checkpoint error', e);
      }}
    }}

    await sleep(UNIT_PAUSE_MS);
  }}

  // Final download
  console.log(
    `[wh] DONE batch {batch_num}/5. ok=${{ok}} ok_canvas=${{ok_canvas}} ` +
    `no_search_result=${{no_search_result}} no_product_image=${{no_product_image}} ` +
    `fail=${{fail}}`
  );
  const finalBlob = await zip.generateAsync({{ type: 'blob' }});
  triggerDownload(finalBlob, 'wh_40k_minis_batch{batch_num}.zip');
  console.log('[wh] wh_40k_minis_batch{batch_num}.zip download triggered');

}})();
"""


# Split into batches: 71, 71, 71, 71, 67
BATCH_SIZE = 71
all_batches = []
for b in range(5):
    start = b * BATCH_SIZE
    end = min(start + BATCH_SIZE, len(units))
    all_batches.append(units[start:end])

print("Batch sizes:", [len(b) for b in all_batches])
print("Total:", sum(len(b) for b in all_batches))

scripts_dir = pathlib.Path(__file__).parent
for b_num, batch_units in enumerate(all_batches, 1):
    script_content = make_script(b_num, batch_units, all_batches)
    out_path = scripts_dir / f'wh_40k_devtools_batch{b_num}.js'
    out_path.write_text(script_content, encoding='utf-8')
    print(f"Written: {out_path} ({len(batch_units)} units, {len(script_content):,} bytes)")

print("All 5 batch scripts generated.")
