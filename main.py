"""
Hlavní skript: analýza stavebních řízení pro skupinu STYLGROUP s.r.o.
v katastrálním území Kukleny [647209].

Spuštění:
  pip install -r requirements.txt
  cp .env.example .env        # vyplňte EDESKY_API_KEY (+ volitelně ČÚZK přístupy)
  python main.py

Výstup:
  - výpis do konzole
  - report.txt (přehledná zpráva)
"""
import sys
import datetime
from pathlib import Path

# Ověření přítomnosti .env / API klíče před importem klientů
from dotenv import load_dotenv
load_dotenv()

import config
from ares_client import build_skupina
from cuzk_client import get_parcely, cuzk_nahled_url
from edesky_client import search_stavebni_rizeni, format_dokument, get_boards_hk


# ── Pomocné funkce ────────────────────────────────────────────────────────────

def print_sekce(nazev: str):
    print("\n" + "=" * 70)
    print(f"  {nazev}")
    print("=" * 70)


def zkontroluj_konfiguraci():
    chyby = []
    if not config.EDESKY_API_KEY:
        chyby.append(
            "EDESKY_API_KEY není nastaven.\n"
            "  → Zkopírujte .env.example jako .env a doplňte API klíč."
        )
    if chyby:
        print("\n[CHYBA KONFIGURACE]")
        for c in chyby:
            print(f"  ✗ {c}")
        print()
        # Pokračujeme, ale eDesky krok selže


# ── Sestavení reportu ─────────────────────────────────────────────────────────

def sestavit_report(
    skupina: list[dict],
    parcely: list[dict],
    dokumenty: list[dict],
) -> str:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "=" * 70,
        "  REPORT: Stavební řízení skupiny STYLGROUP v k.ú. Kukleny",
        f"  Vygenerováno: {now}",
        "=" * 70,
        "",
        "SLEDOVANÁ FIRMA:",
        f"  {config.ROOT_NAZEV}  (IČO {config.ROOT_ICO})",
        "",
        f"KATASTRÁLNÍ ÚZEMÍ: {config.KAT_UZEMI_NAZEV} [{config.KAT_UZEMI_KOD}]",
        "",
    ]

    # Sekce 1: Skupina firem
    lines += [
        "─" * 70,
        "1. FIRMY SKUPINY",
        "─" * 70,
    ]
    if not skupina:
        lines.append("  Žádné firmy nenalezeny.")
    else:
        for f in skupina:
            stav = f.get("stavSubjektu", "")
            lines.append(
                f"  IČO {f['ico']}  |  {f['nazev']}"
                + (f"  [{stav}]" if stav else "")
            )
            if f.get("sidlo"):
                lines.append(f"          Sídlo: {f['sidlo']}")
    lines.append("")

    # Sekce 2: Parcely
    lines += [
        "─" * 70,
        f"2. PARCELY V K.Ú. {config.KAT_UZEMI_NAZEV.upper()} (vlastněné skupinou)",
        "─" * 70,
    ]
    if not parcely:
        lines.append("  Žádné parcely nebyly nalezeny automaticky.")
        lines.append("  → Zkontrolujte ručně: https://nahlizenidokn.cuzk.cz/")
        lines.append(f"    (vyhledat vlastníka: {config.ROOT_NAZEV})")
    else:
        for p in parcely:
            url = cuzk_nahled_url(p["parcel_cislo"])
            lines.append(
                f"  Parcela {p['parcel_cislo']:12s}  "
                f"LV {p.get('lv', '?'):6s}  "
                f"Vlastník: {p.get('vlastnik_nazev', '?')}"
            )
            lines.append(f"    URL: {url}")
    lines.append("")

    # Sekce 3: Stavební řízení
    lines += [
        "─" * 70,
        "3. STAVEBNÍ ŘÍZENÍ / POVOLENÍ (z eDesky.cz)",
        "─" * 70,
    ]
    if not dokumenty:
        lines.append("  Žádné dokumenty stavebního řízení nenalezeny.")
        lines.append("  Možné důvody:")
        lines.append("    - Řízení dosud nezahájeno nebo nepodána žádost")
        lines.append("    - Dokument nebyl zveřejněn na sledovaných deskách")
        lines.append("    - Nesprávný API klíč nebo omezení přístupu")
    else:
        for i, d in enumerate(dokumenty, 1):
            lines.append(f"\n  [{i}]")
            lines.append(format_dokument(d))

    lines += [
        "",
        "─" * 70,
        "ZÁVĚR",
        "─" * 70,
        f"  Firem ve skupině         : {len(skupina)}",
        f"  Parcel v k.ú. Kukleny   : {len(parcely)}",
        f"  Dokumentů staveb. řízení : {len(dokumenty)}",
        "",
    ]

    if dokumenty:
        lines.append("  ⚠ NALEZENY DOKUMENTY STAVEBNÍHO ŘÍZENÍ – viz sekce 3.")
    else:
        lines.append("  ✓ Žádné stavební řízení na deskách eDesky nenalezeno.")

    lines.append("")
    return "\n".join(lines)


# ── Hlavní průběh ─────────────────────────────────────────────────────────────

def main():
    print_sekce("ANALÝZA: STYLGROUP – stavební řízení v k.ú. Kukleny")
    zkontroluj_konfiguraci()

    # Krok 1: Zjistit firmy skupiny
    print_sekce("Krok 1/3: Firmy skupiny (ARES)")
    skupina = build_skupina(config.ROOT_ICO, config.SKUPINA_ICOS or None)

    if not skupina:
        print("\n[CHYBA] Nepodařilo se načíst žádnou firmu ze skupiny. Ukončuji.")
        sys.exit(1)

    # Krok 2: Parcely v ČÚZK
    print_sekce("Krok 2/3: Parcely v k.ú. Kukleny (ČÚZK)")

    cuzk_ok = bool(config.CUZK_WSDP_USER and config.CUZK_WSDP_PASS)
    if not cuzk_ok:
        print(
            "\n  INFO: Přihlašovací údaje ČÚZK WSDP nejsou nastaveny.\n"
            "  Budu se pokoušet o veřejné nahlížení (web scraping).\n"
            "  Pro spolehlivější výsledky doporučuji bezplatnou registraci:\n"
            "  https://katastr.cuzk.cz/Pristup/Login.aspx\n"
        )

    parcely = get_parcely(skupina)

    if not parcely:
        print(
            "\n  INFO: Parcely se nepodařilo načíst automaticky.\n"
            "  Zjistěte je ručně na https://nahlizenidokn.cuzk.cz/\n"
            "  a přidejte čísla parcel do config.py → SKUPINA_ICOS nebo\n"
            "  upravte skript pro přímé zadání čísel parcel.\n"
        )

    # Krok 3: Stavební řízení na eDesky
    print_sekce("Krok 3/3: Stavební řízení (eDesky.cz)")

    if not config.EDESKY_API_KEY:
        print("  PŘESKAKUJI – EDESKY_API_KEY není nastaven.")
        dokumenty = []
    else:
        board_ids = list(config.EDESKY_BOARD_IDS)
        dokumenty = search_stavebni_rizeni(parcely, skupina, board_ids)

    # Sestavení a uložení reportu
    print_sekce("Výsledný report")
    report = sestavit_report(skupina, parcely, dokumenty)
    print(report)

    report_path = Path(config.REPORT_FILE)
    report_path.write_text(report, encoding="utf-8")
    print(f"Report uložen: {report_path.resolve()}")


if __name__ == "__main__":
    main()
