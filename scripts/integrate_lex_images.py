"""
integrate_lex_images.py — importa imagens de units AoS4 a partir de um zip
gerado pelo script JS do Lexicanum (Firefox DevTools).

Estrutura aceita (auto-detect):
  - FLAT:    <unit_slug>.<ext>
  - NESTED:  <old_faction_slug>/<unit_slug>.<ext>
  ext aceito: jpg, jpeg, png, webp (case-insensitive)

COMO RODAR (dentro do container):
  1. Copie o zip pro container:
       docker compose cp ~/Downloads/lex_images.zip app:/tmp/lex_images.zip
  2. Execute:
       docker compose exec app python scripts/integrate_lex_images.py --zip /tmp/lex_images.zip

  Flags opcionais:
    --force    Sobrescreve imagens já existentes no disco + no DB
"""

import argparse
import os
import re
import sys
import zipfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap: garante que o pacote `app` é importável independente do cwd
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from app import create_app          # noqa: E402
from app.extensions import db       # noqa: E402
from app.models.game import Unit    # noqa: E402  (Faction carregado via backref)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
VALID_EXTS = {"jpg", "jpeg", "png", "webp"}
BATCH_SIZE = 50
MIN_SIZE_BYTES = 1024  # entradas < 1 KB são suspeitas / placeholder
STATIC_UNITS_DIR = _REPO_ROOT / "app" / "static" / "img" / "units"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Integra imagens de units AoS4 a partir de lex_images.zip"
    )
    parser.add_argument(
        "zip_path",
        nargs="?",
        default=None,
        help="Caminho para o zip (posicional, opcional)",
    )
    parser.add_argument(
        "--zip",
        dest="zip_flag",
        default=None,
        metavar="PATH",
        help="Caminho para o zip (flag alternativa)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Sobrescreve imagens já existentes",
    )
    return parser.parse_args()


def resolve_zip_path(args: argparse.Namespace) -> Path:
    """Resolve o caminho do zip: flag --zip > arg posicional > default ~/Downloads."""
    raw = args.zip_flag or args.zip_path
    if raw:
        return Path(raw).expanduser().resolve()
    return Path.home() / "Downloads" / "lex_images.zip"


def parse_entry_name(name: str):
    """
    Parseia nome de entry no zip. Aceita:
      - FLAT:   '<slug>.<ext>'
      - NESTED: '<old_faction>/<slug>.<ext>'
    Retorna (old_faction_or_None, slug, ext_lower) ou None se não bater.
    """
    # Normaliza separadores (alguns zips usam backslash no Windows)
    name = name.replace("\\", "/").strip("/")

    # Nested: <faction>/<slug>.<ext>
    m = re.fullmatch(r"([^/]+)/([^/]+)\.([^./]+)", name)
    if m:
        old_faction, slug, ext = m.groups()
        ext = ext.lower()
        if ext not in VALID_EXTS:
            return None
        return old_faction, slug, ext

    # Flat: <slug>.<ext>
    m = re.fullmatch(r"([^/]+)\.([^./]+)", name)
    if m:
        slug, ext = m.groups()
        ext = ext.lower()
        if ext not in VALID_EXTS:
            return None
        return None, slug, ext

    return None


def log(level: str, msg: str) -> None:
    prefix = {
        "INFO":  "[INFO ]",
        "WARN":  "[WARN ]",
        "ERROR": "[ERROR]",
        "SKIP":  "[SKIP ]",
        "SAVE":  "[SAVE ]",
    }.get(level, f"[{level}]")
    print(f"{prefix} {msg}", flush=True)


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def run(zip_path: Path, force: bool) -> None:
    if not zip_path.exists():
        print(f"[ERROR] Zip não encontrado: {zip_path}", flush=True)
        sys.exit(1)

    print(f"[INFO ] Abrindo zip: {zip_path}", flush=True)
    print(f"[INFO ] force={force}  batch_size={BATCH_SIZE}", flush=True)

    # Contadores
    total_entries   = 0
    saved           = 0
    skipped_exists  = 0
    skipped_small   = 0
    skipped_noparse = 0
    unknown_slugs   = 0
    faction_remaps  = 0  # slug do zip difere do slug atual da faction

    app = create_app()

    with app.app_context():
        dirty = 0  # unidades modificadas desde o último commit

        with zipfile.ZipFile(zip_path, "r") as zf:
            entries = [e for e in zf.infolist() if not e.is_dir()]
            print(f"[INFO ] Entries no zip (arquivos): {len(entries)}", flush=True)

            for entry in entries:
                total_entries += 1
                name = entry.filename

                # --- Parse do nome ---
                parsed = parse_entry_name(name)
                if not parsed:
                    log("SKIP", f"Nome não reconhecido, pulando: {name!r}")
                    skipped_noparse += 1
                    continue

                old_faction_slug, unit_slug, ext = parsed

                # --- Tamanho mínimo ---
                if entry.file_size < MIN_SIZE_BYTES:
                    log("SKIP", f"{name!r}: tamanho {entry.file_size}B < {MIN_SIZE_BYTES}B, pulando")
                    skipped_small += 1
                    continue

                # --- Lookup no DB ---
                unit = Unit.query.filter_by(slug=unit_slug).first()
                if unit is None:
                    log("WARN", f"Slug não encontrado no DB: {unit_slug!r}  (entry: {name!r})")
                    unknown_slugs += 1
                    continue

                # --- Faction atual (deriva do DB; zip pode ser flat ou ter old slug) ---
                current_faction_slug = unit.faction.slug
                if old_faction_slug is not None and current_faction_slug != old_faction_slug:
                    log(
                        "INFO",
                        f"Faction remap: {unit_slug!r}  zip={old_faction_slug!r} → db={current_faction_slug!r}",
                    )
                    faction_remaps += 1

                # --- Caminhos ---
                target_rel  = f"units/{current_faction_slug}/{unit_slug}.{ext}"
                target_abs  = STATIC_UNITS_DIR / current_faction_slug / f"{unit_slug}.{ext}"

                # --- Verifica se já existe (no disco E no DB) ---
                already_in_db   = bool(unit.image_path)
                already_on_disk = target_abs.exists()

                if already_in_db and already_on_disk and not force:
                    log(
                        "SKIP",
                        f"{unit_slug}: já existe (db={unit.image_path!r}), use --force pra sobrescrever",
                    )
                    skipped_exists += 1
                    continue

                # --- Cria diretório se necessário ---
                target_abs.parent.mkdir(parents=True, exist_ok=True)

                # --- Extrai e salva ---
                image_data = zf.read(entry.filename)
                target_abs.write_bytes(image_data)

                action = "sobrescrito" if (already_in_db or already_on_disk) else "novo"
                log("SAVE", f"{unit_slug}: {action} → {target_rel}  ({len(image_data):,}B)")

                # --- Atualiza DB ---
                # image_path usa forward slashes (é parte de URL no template)
                unit.image_path = target_rel
                saved += 1
                dirty += 1

                # --- Commit em batch ---
                if dirty >= BATCH_SIZE:
                    db.session.commit()
                    print(f"[INFO ] Commit parcial: {dirty} unidades.", flush=True)
                    dirty = 0

            # Commit final
            if dirty:
                db.session.commit()
                print(f"[INFO ] Commit final: {dirty} unidades.", flush=True)

    # ---------------------------------------------------------------------------
    # Stats finais
    # ---------------------------------------------------------------------------
    print()
    print("=" * 60)
    print("  RESULTADO FINAL")
    print("=" * 60)
    print(f"  Total entries no zip    : {total_entries}")
    print(f"  Salvos (novos/force)    : {saved}")
    print(f"  Skipped (já existia)    : {skipped_exists}")
    print(f"  Skipped (< {MIN_SIZE_BYTES}B suspeito): {skipped_small}")
    print(f"  Skipped (nome inválido) : {skipped_noparse}")
    print(f"  Slug desconhecido (WARN): {unknown_slugs}")
    print(f"  Faction remap (info)    : {faction_remaps}")
    print("=" * 60)

    # Tamanho e path do script (para referência)
    script_path = Path(__file__).resolve()
    script_size = script_path.stat().st_size
    print(f"\n  Script: {script_path}  ({script_size:,} bytes)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    args = resolve_zip_path.__globals__  # só pra não executar no import
    args = parse_args()
    zip_path = resolve_zip_path(args)
    run(zip_path=zip_path, force=args.force)
