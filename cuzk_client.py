"""
Klient pro ČÚZK – hledání parcel v daném katastrálním území podle vlastníka.

Strategie (v pořadí preference):
  1. ČÚZK WSDP SOAP – pokud jsou zadány přihlašovací údaje
  2. Nahlížení do katastru (web scraping) – vždy zdarma, bez registrace
"""
import re
import time
import requests
from bs4 import BeautifulSoup
from config import (
    KAT_UZEMI_KOD, KAT_UZEMI_NAZEV,
    CUZK_WSDP_URL, CUZK_WSDP_USER, CUZK_WSDP_PASS,
)

NAHLED_BASE = "https://nahlizenidokn.cuzk.cz"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"})


# ── WSDP SOAP ─────────────────────────────────────────────────────────────────

SOAP_NS = "http://katastr.cuzk.cz/Schema/odpoved/2_12"
SOAP_ENVELOPE = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:wsdp="http://katastr.cuzk.cz/wsdpService/types/2_12">
  <soap:Body>
    <wsdp:SeznamNemovitostiRequest>
      <wsdp:popis>Parcely vlastníka IČO {ico} v k.ú. {kat_uzemi}</wsdp:popis>
      <wsdp:katastralniUzemi><wsdp:kod>{kat_uzemi_kod}</wsdp:kod></wsdp:katastralniUzemi>
      <wsdp:typNemovitosti>PARCELA</wsdp:typNemovitosti>
      <wsdp:vlastnikIco>{ico}</wsdp:vlastnikIco>
    </wsdp:SeznamNemovitostiRequest>
  </soap:Body>
</soap:Envelope>"""


def _wsdp_parcely(ico: str) -> list[dict]:
    """Dotáže se ČÚZK WSDP na parcely vlastněné daným IČO."""
    if not CUZK_WSDP_USER or not CUZK_WSDP_PASS:
        return []

    body = SOAP_ENVELOPE.format(
        ico=ico,
        kat_uzemi=KAT_UZEMI_NAZEV,
        kat_uzemi_kod=KAT_UZEMI_KOD,
    )
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "SeznamNemovitosti",
    }
    try:
        r = SESSION.post(
            CUZK_WSDP_URL,
            data=body.encode("utf-8"),
            headers=headers,
            auth=(CUZK_WSDP_USER, CUZK_WSDP_PASS),
            timeout=30,
        )
        r.raise_for_status()
        return _parse_wsdp_parcely(r.text)
    except Exception as e:
        print(f"  [WSDP] Chyba pro IČO {ico}: {e}")
        return []


def _parse_wsdp_parcely(xml_text: str) -> list[dict]:
    soup = BeautifulSoup(xml_text, "lxml-xml")
    parcely = []
    for p in soup.find_all("parcela"):
        parcely.append({
            "parcel_cislo": p.find("cisloParcelni", recursive=False) and
                            p.find("cisloParcelni").get_text(strip=True),
            "lv": p.find("lv") and p.find("lv").get_text(strip=True),
            "vymera": p.find("vymera") and p.find("vymera").get_text(strip=True),
            "druh_pozemku": p.find("druhPozemku") and p.find("druhPozemku").get_text(strip=True),
            "zpusob_vyuziti": p.find("zpusobVyuziti") and p.find("zpusobVyuziti").get_text(strip=True),
            "kat_uzemi": KAT_UZEMI_NAZEV,
            "zdroj": "WSDP",
        })
    return parcely


# ── Web scraping – Nahlížení do katastru ──────────────────────────────────────

def _nahled_hledat_vlastnika(nazev_nebo_ico: str) -> list[str]:
    """
    Vrátí seznam URL listů vlastnictví nalezených pro daného vlastníka
    v katastrálním území Kukleny.
    """
    print(f"  [ČÚZK web] Hledám vlastníka: {nazev_nebo_ico} v k.ú. {KAT_UZEMI_NAZEV}...")

    search_url = (
        f"{NAHLED_BASE}/ZobrazObjekt.aspx"
        f"?typ=V"                               # typ=V = vlastník
        f"&text={requests.utils.quote(nazev_nebo_ico)}"
        f"&katastralniUzemiKod={KAT_UZEMI_KOD}"
    )

    try:
        r = SESSION.get(search_url, timeout=20)
        soup = BeautifulSoup(r.text, "lxml")

        lv_urls = []
        for a in soup.select("a[href*='ZobrazObjekt']"):
            href = a.get("href", "")
            if "LV" in href or "lv" in href or "listVlastnictvi" in href.lower():
                full = href if href.startswith("http") else NAHLED_BASE + "/" + href.lstrip("/")
                lv_urls.append(full)

        # Alternativní selektor pro nové rozhraní ČÚZK
        for a in soup.select("table.result-table a, .search-result a"):
            href = a.get("href", "")
            full = href if href.startswith("http") else NAHLED_BASE + "/" + href.lstrip("/")
            if full not in lv_urls:
                lv_urls.append(full)

        return lv_urls
    except Exception as e:
        print(f"  [ČÚZK web] Chyba při hledání vlastníka: {e}")
        return []


def _nahled_parcely_z_lv(lv_url: str) -> list[dict]:
    """Stáhne list vlastnictví a extrahuje z něj seznam parcel."""
    parcely = []
    try:
        time.sleep(0.5)  # slušné chování k serveru
        r = SESSION.get(lv_url, timeout=20)
        soup = BeautifulSoup(r.text, "lxml")

        # LV číslo z URL nebo stránky
        lv_match = re.search(r"[Ll][Vv]=?(\d+)", lv_url)
        lv_cislo = lv_match.group(1) if lv_match else "?"

        # Hledáme tabulku s parcelami
        for row in soup.select("table tr"):
            cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
            if not cells:
                continue
            # Parcely mají tvar "123/45" nebo "123" (stavební parcela)
            for cell in cells:
                if re.match(r"^\d{1,6}(/\d+)?$", cell) and len(cells) >= 2:
                    parcely.append({
                        "parcel_cislo": cell,
                        "lv": lv_cislo,
                        "kat_uzemi": KAT_UZEMI_NAZEV,
                        "kat_uzemi_kod": KAT_UZEMI_KOD,
                        "lv_url": lv_url,
                        "zdroj": "ČÚZK-web",
                    })
                    break  # jen první buňka s číslem parcely na řádku
    except Exception as e:
        print(f"  [ČÚZK web] Chyba při čtení LV {lv_url}: {e}")
    return parcely


def _web_scrape_parcely(ico: str, nazev: str) -> list[dict]:
    """Scraping Nahlížení do katastru – hledá přes IČO i název firmy."""
    vse: list[dict] = []

    for query in [ico, nazev]:
        lv_urls = _nahled_hledat_vlastnika(query)
        if not lv_urls:
            print(f"    Žádné LV nenalezeny pro dotaz: '{query}'")
            continue
        print(f"    Nalezeno {len(lv_urls)} LV pro dotaz: '{query}'")
        for url in lv_urls:
            parcely = _nahled_parcely_z_lv(url)
            print(f"    LV {url}: {len(parcely)} parcel")
            vse.extend(parcely)

    # Deduplukace
    seen = set()
    unik = []
    for p in vse:
        key = (p["parcel_cislo"], p["lv"])
        if key not in seen:
            seen.add(key)
            unik.append(p)
    return unik


# ── Veřejné rozhraní ──────────────────────────────────────────────────────────

def get_parcely(firmy: list[dict]) -> list[dict]:
    """
    Pro každou firmu ze skupiny zjistí parcely v k.ú. Kukleny.
    Vrátí seznam parcel s info o vlastníkovi.
    """
    print(f"\n[ČÚZK] Hledám parcely v k.ú. {KAT_UZEMI_NAZEV} [{KAT_UZEMI_KOD}]...")

    vsechny: list[dict] = []

    for firma in firmy:
        ico = firma.get("ico", "")
        nazev = firma.get("nazev", "")
        print(f"\n  Firma: {nazev} (IČO {ico})")

        # Pokus 1: WSDP SOAP (pokud jsou credentials)
        parcely = _wsdp_parcely(ico)

        # Pokus 2: web scraping
        if not parcely:
            parcely = _web_scrape_parcely(ico, nazev)

        for p in parcely:
            p["vlastnik_ico"] = ico
            p["vlastnik_nazev"] = nazev

        print(f"  → Celkem nalezeno {len(parcely)} parcel")
        vsechny.extend(parcely)

    # Deduplikace přes firmy
    seen = set()
    unik = []
    for p in vsechny:
        key = (p["parcel_cislo"], p.get("lv", ""))
        if key not in seen:
            seen.add(key)
            unik.append(p)

    print(f"\n[ČÚZK] Celkem unikátních parcel skupiny v k.ú. {KAT_UZEMI_NAZEV}: {len(unik)}")
    return unik


def cuzk_nahled_url(parcel_cislo: str) -> str:
    """Vrátí odkaz na parcelu v Nahlížení do katastru."""
    return (
        f"{NAHLED_BASE}/ZobrazObjekt.aspx"
        f"?typ=P&katastralniUzemiKod={KAT_UZEMI_KOD}"
        f"&cisloParcelni={parcel_cislo}"
    )
