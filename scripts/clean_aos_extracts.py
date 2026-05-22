"""Limpa ruido de char-dedup do pdfplumber nos 4 extracts AoS.

PDF render bug: muitos chars vem duplicados/triplicados, ex 'ttthhheee' = 'the'.
Pattern: cada char repetido 2-4x em sequencia.

Heuristica: se 3+ chars consecutivos sao o mesmo, reduz pra 1. Mas preserva palavras
legitimas (ex: 'GG' em sigla, 'AA' em ALL-CAPS). Aplica so quando o pattern eh
absurdo: 3+ repeticoes de letra minuscula, ou 4+ de qualquer.
"""
import re
from pathlib import Path

EXTRACT_DIR = Path(__file__).parent / "cache" / "aos_rules_extract"

# Pattern 1: 3+ of same lowercase letter -> 1
# Pattern 2: 3+ of same uppercase letter -> 1 (catches "TTHHEE" cases)
# Pattern 3: 2 of same letter followed by another doubled letter (mmaaiinn pattern) -> singles
def clean_dedup(text: str) -> str:
    # Most aggressive: collapse 3+ same chars to 1
    text = re.sub(r"([A-Za-z])\1{2,}", r"\1", text)
    # Pattern "mmaaiinn" = sequence of doubled letters forming a word
    # If 2+ doubled-letter pairs in row, collapse each pair
    def collapse_doubles(m):
        s = m.group(0)
        out = []
        i = 0
        while i < len(s):
            if i + 1 < len(s) and s[i] == s[i+1]:
                out.append(s[i])
                i += 2
            else:
                out.append(s[i])
                i += 1
        return "".join(out)
    text = re.sub(r"(?:([A-Za-z])\1){2,}", collapse_doubles, text)
    return text


def clean_file(p: Path):
    raw = p.read_text(encoding="utf-8")
    cleaned = clean_dedup(raw)
    out = p.with_suffix(".clean.md")
    out.write_text(cleaned, encoding="utf-8")
    print(f"{p.name}: {len(raw)} -> {len(cleaned)} ({out.name})")


if __name__ == "__main__":
    for name in ("core_rules", "updates", "battle_profiles", "ghb"):
        p = EXTRACT_DIR / f"{name}.md"
        if p.exists():
            clean_file(p)
        else:
            print(f"missing: {p}")
