"""
Klient pro eDesky.cz API v2.
Dokumentace: https://edesky.cz/stranka/api-dokumentace

Hledá dokumenty týkající se stavebních řízení pro zadané parcely
v Hradci Králové.
"""
import re
import time
import requests
from config import EDESKY_API_KEY, EDESKY_API_BASE, EDESKY_BOARD_IDS

SESSION = requests.Session()

# Klíčová slova pro stavební řízení
STAVEBNI_KLICOVASLOVA = [
    "územní rozhodnutí",
    "územní řízení",
    "stavební povolení",
    "stavební řízení",
    "ohlášení stavby",
    "kolaudační souhlas",
    "kolaudační rozhodnutí",
    "zahájení řízení",
    "veřejná vyhláška",
]

# Názvy / části názvů relevantních úřadů v HK
HK_URADY_KLICE = [
    "Hradec Králové",
    "hradeckralové",
    "hradec",
]


def _api_get(endpoint: str, params: dict) -> dict | None:
    if not EDESKY_API_KEY:
        print("  [eDesky] CHYBA: Není nastaven EDESKY_API_KEY!")
        return None

    params["api_key"] = EDESKY_API_KEY
    url = f"{EDESKY_API_BASE}/{endpoint}"

    try:
        r = SESSION.get(url, params=params, timeout=20)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        print(f"  [eDesky] HTTP chyba: {e} – odpověď: {r.text[:200]}")
        return None
    except Exception as e:
        print(f"  [eDesky] Chyba při GET {url}: {e}")
        return None


def get_boards_hk() -> list[dict]:
    """Vrátí seznam úředních desek v Hradci Králové."""
    print("\n[eDesky] Hledám úřední desky Hradce Králové...")
    data = _api_get("boards", {"keywords": "Hradec Králové", "per_page": 50})
    if not data:
        return []

    boards = data.get("boards", data.get("data", []))
    hk_boards = []
    for b in boards:
        nazev = (b.get("name") or b.get("nazev") or "").lower()
        if any(k.lower() in nazev for k in HK_URADY_KLICE):
            hk_boards.append(b)
            print(f"  + [{b.get('id')}] {b.get('name') or b.get('nazev')}")

    if not hk_boards:
        print("  Žádné desky HK nenalezeny – budu hledat globálně")
    return hk_boards


def _hledej_dokumenty(query: str, board_ids: list[str], page: int = 1) -> dict | None:
    """Jeden dotaz na eDesky /documents."""
    params: dict = {
        "keywords": query,
        "per_page": 20,
        "page": page,
    }
    if board_ids:
        # eDesky API přijímá board_ids jako opakovaný parametr nebo CSV
        params["board_ids[]"] = board_ids

    return _api_get("documents", params)


def _je_relevantni(dokument: dict) -> bool:
    """Rozhodne, zda dokument může být stavební řízení."""
    text = " ".join([
        str(dokument.get("title") or ""),
        str(dokument.get("description") or ""),
        str(dokument.get("content") or ""),
    ]).lower()

    return any(kw.lower() in text for kw in STAVEBNI_KLICOVASLOVA)


def search_stavebni_rizeni(
    parcely: list[dict],
    firmy: list[dict],
    board_ids: list[str] | None = None,
) -> list[dict]:
    """
    Prohledá eDesky.cz pro stavební řízení týkající se:
      - čísel parcel skupiny v k.ú. Kukleny
      - názvů a IČO firem skupiny

    Vrátí seznam nalezených dokumentů.
    """
    if board_ids is None:
        board_ids = EDESKY_BOARD_IDS

    # Pokud nejsou boards zadány, zjistíme je
    if not board_ids:
        boards = get_boards_hk()
        board_ids = [str(b.get("id")) for b in boards]

    print(f"\n[eDesky] Prohledávám {len(board_ids) or 'všechny'} desek...")

    nalezene: list[dict] = []
    seen_ids: set[str] = set()

    def _pridej(docs: list):
        for d in docs:
            doc_id = str(d.get("id") or d.get("document_id") or "")
            if doc_id and doc_id in seen_ids:
                continue
            if doc_id:
                seen_ids.add(doc_id)
            if _je_relevantni(d):
                nalezene.append(d)

    # 1) Dotazy na čísla parcel
    for p in parcely:
        cislo = p.get("parcel_cislo", "")
        if not cislo:
            continue
        # Různé formáty čísla parcely
        queries = [cislo, f"parcela {cislo}", f"parc.č. {cislo}"]
        for q in queries:
            print(f"  Dotaz: '{q}'")
            data = _hledej_dokumenty(q, board_ids)
            if data:
                docs = data.get("documents", data.get("data", []))
                _pridej(docs)
            time.sleep(0.3)  # rate limiting

    # 2) Dotazy na firmy skupiny
    for firma in firmy:
        for q in [firma.get("nazev", ""), firma.get("ico", "")]:
            if not q:
                continue
            print(f"  Dotaz: '{q}'")
            data = _hledej_dokumenty(q, board_ids)
            if data:
                docs = data.get("documents", data.get("data", []))
                _pridej(docs)
            time.sleep(0.3)

    # 3) Obecné klíčové dotazy v kombinaci s k.ú. Kukleny
    for kw in ["Kukleny stavební povolení", "Kukleny územní rozhodnutí",
               "STYLGROUP stavební"]:
        print(f"  Dotaz: '{kw}'")
        data = _hledej_dokumenty(kw, board_ids)
        if data:
            docs = data.get("documents", data.get("data", []))
            _pridej(docs)
        time.sleep(0.3)

    print(f"\n[eDesky] Celkem nalezeno {len(nalezene)} relevantních dokumentů")
    return nalezene


def format_dokument(d: dict) -> str:
    """Formátuje dokument pro výpis."""
    lines = [
        f"  ID       : {d.get('id') or d.get('document_id', '?')}",
        f"  Název    : {d.get('title') or d.get('nazev', '?')}",
        f"  Datum    : {d.get('published_at') or d.get('created_at') or d.get('datum', '?')}",
        f"  Úřad     : {d.get('board', {}).get('name') if isinstance(d.get('board'), dict) else d.get('board_name', '?')}",
        f"  URL      : {d.get('url') or d.get('edesky_url', '')}",
    ]
    popis = d.get("description") or d.get("content") or d.get("popis", "")
    if popis:
        lines.append(f"  Popis    : {str(popis)[:300]}...")
    return "\n".join(lines)
