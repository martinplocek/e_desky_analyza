"""
Klient pro ARES (Administrativní registr ekonomických subjektů).
Zjistí základní údaje o firmě a pokusí se najít propojené subjekty
ze zápisů v Obchodním rejstříku (justice.cz).
"""
import re
import requests
from bs4 import BeautifulSoup
from config import ARES_BASE

HEADERS = {"Accept": "application/json", "User-Agent": "StylgroupAnalyza/1.0"}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def _get(url: str, **kwargs) -> dict | None:
    try:
        r = SESSION.get(url, timeout=15, **kwargs)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  [ARES] Chyba při GET {url}: {e}")
        return None


def get_firma(ico: str) -> dict:
    """Vrátí základní údaje o firmě z ARES."""
    data = _get(f"{ARES_BASE}/ekonomicke-subjekty/{ico}")
    if not data:
        return {}
    return {
        "ico": data.get("ico", ico),
        "nazev": data.get("obchodniJmeno", ""),
        "sidlo": _sidlo(data),
        "pravniForma": data.get("pravniForma", {}).get("nazev", ""),
        "datumVzniku": data.get("datumVzniku", ""),
        "datumZaniku": data.get("datumZaniku", ""),
        "stavSubjektu": data.get("stavSubjektu", {}).get("nazev", ""),
    }


def _sidlo(data: dict) -> str:
    a = data.get("sidlo", {})
    parts = [
        str(a.get("nazevObce") or ""),
        str(a.get("nazevUlice") or ""),
        str(a.get("cisloDomovni") or ""),
        str(a.get("psc") or ""),
    ]
    return " ".join(p for p in parts if p)


def get_or_data(ico: str) -> dict:
    """
    Stáhne data z Obchodního rejstříku (justice.cz) – jednatelé, společníci.
    Používá ARES odkaz na OR nebo přímo justice.cz.
    """
    url = f"https://or.justice.cz/ias/ui/rejstrik-$firma?ico={ico}&jenPlatne=PLATNE"
    try:
        r = SESSION.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "lxml")

        result: dict = {"jednatelé": [], "společníci": [], "propojené_ico": []}

        # Hledáme IČO v textu stránky – propojené subjekty
        icos_found = set(re.findall(r"\b\d{8}\b", r.text))
        icos_found.discard(ico)
        result["propojené_ico"] = sorted(icos_found)

        # Jednatelé / členové
        for tag in soup.select(".aunp-table tr"):
            cells = [td.get_text(strip=True) for td in tag.find_all("td")]
            if len(cells) >= 2:
                if "jednatel" in cells[0].lower():
                    result["jednatelé"].append(cells[1] if len(cells) > 1 else "")
                if "spole" in cells[0].lower():
                    result["společníci"].append(cells[1] if len(cells) > 1 else "")

        return result
    except Exception as e:
        print(f"  [OR] Nelze stáhnout data pro {ico}: {e}")
        return {}


def get_propojene_ico(ico: str) -> list[str]:
    """
    Vrátí seznam IČO subjektů propojených s danou firmou.
    Zdroje: ARES ekonomické subjekty + OR justice.cz.
    """
    propojene: set[str] = set()

    # 1) ARES – ekonomicky propojené subjekty
    data = _get(f"{ARES_BASE}/ekonomicke-subjekty/{ico}/propojene-osoby")
    if data:
        for subj in data.get("ekonomickeSubjekty", []):
            if subj.get("ico"):
                propojene.add(subj["ico"])

    # 2) OR justice.cz – heuristika přes IČO v textu
    or_data = get_or_data(ico)
    for prop_ico in or_data.get("propojené_ico", []):
        if len(prop_ico) == 8 and prop_ico.isdigit():
            propojene.add(prop_ico)

    propojene.discard(ico)
    return sorted(propojene)


def build_skupina(root_ico: str, extra_icos: list[str] | None = None) -> list[dict]:
    """
    Sestaví seznam firem skupiny.
    Pokud je v config.py SKUPINA_FIRMY vyplněn, použije ho přímo (rychlé).
    Jinak začíná od root_ico a pokusí se najít propojené subjekty přes ARES.
    """
    from config import SKUPINA_FIRMY  # import zde, aby nevznikl cirkulární import

    # Rychlá cesta: předdefinovaný seznam firem
    if SKUPINA_FIRMY:
        print(f"\n[ARES] Používám předdefinovaný seznam {len(SKUPINA_FIRMY)} firem skupiny.")
        print("  Ověřuji aktuální stav přes ARES...")
        skupina = []
        for entry in SKUPINA_FIRMY:
            ico = entry["ico"]
            info = get_firma(ico)
            if info.get("nazev"):
                firma = {**entry, **info}  # ARES data mají přednost
            else:
                firma = {**entry, "stavSubjektu": "nelze ověřit"}
            skupina.append(firma)
            stav = firma.get("stavSubjektu", "")
            print(f"  + {ico}  {firma.get('nazev', entry['nazev'])}  [{stav}]")
        return skupina

    # Fallback: automatické hledání přes ARES
    print(f"\n[ARES] Zjišťuji skupinu firem pro IČO {root_ico}...")
    skupina_dict: dict[str, dict] = {}

    def _pridej(ico: str):
        if ico in skupina_dict:
            return
        info = get_firma(ico)
        if not info.get("nazev"):
            print(f"  [ARES] IČO {ico} – firma nenalezena, přeskakuji")
            return
        skupina_dict[ico] = info
        print(f"  + {ico}  {info['nazev']}  ({info.get('stavSubjektu', '')})")

    _pridej(root_ico)
    for ico in (extra_icos or []):
        _pridej(ico)

    print("  Hledám propojené subjekty přes ARES...")
    propojene = get_propojene_ico(root_ico)
    if propojene:
        print(f"  Nalezeno {len(propojene)} potenciálně propojených IČO: {propojene}")
        for ico in propojene:
            _pridej(ico)
    else:
        print("  Žádné propojené subjekty přes ARES API nenalezeny.")

    return list(skupina_dict.values())
