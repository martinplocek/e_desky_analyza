"""
Konfigurace analýzy – upravte hodnoty dle potřeby.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Sledovaná firma a skupina ─────────────────────────────────────────────────
ROOT_ICO = "28830628"          # STYLGROUP s.r.o.
ROOT_NAZEV = "STYLGROUP s.r.o."

# Potvrzený seznam firem skupiny STYLGROUP
SKUPINA_FIRMY: list[dict] = [
    {"ico": "25957481", "nazev": "STYLBAU, s.r.o."},
    {"ico": "28830628", "nazev": "STYLGROUP s.r.o."},
    {"ico": "23611464", "nazev": "STYLVISION HK a.s."},
    {"ico": "28860799", "nazev": "STYLREAL HK s.r.o."},
    {"ico": "02379392", "nazev": "STYLHOME HK, s.r.o."},
    {"ico": "07860790", "nazev": "STYLSERVICE HK s.r.o."},
]
SKUPINA_ICOS: list[str] = [f["ico"] for f in SKUPINA_FIRMY]

# ── Katastrální území ─────────────────────────────────────────────────────────
KAT_UZEMI_KOD = "647209"       # Kukleny
KAT_UZEMI_NAZEV = "Kukleny"

# ── eDesky.cz ─────────────────────────────────────────────────────────────────
EDESKY_API_KEY = os.getenv("EDESKY_API_KEY", "")
EDESKY_API_BASE = "https://edesky.cz/api/v2"

# ID úředních desek Hradce Králové v eDesky (stavební úřad + magistrát)
# Zjistíme za běhu, ale pro urychlení lze předvyplnit:
EDESKY_BOARD_IDS: list[str] = []   # prázdné = hledá ve všech deskách HK

# ── ČÚZK WSDP ────────────────────────────────────────────────────────────────
CUZK_WSDP_URL = "https://wsdp.cuzk.cz/WSDP/servis.asmx"
CUZK_WSDP_USER = os.getenv("CUZK_WSDP_USER", "")
CUZK_WSDP_PASS = os.getenv("CUZK_WSDP_PASS", "")

# ── ARES ──────────────────────────────────────────────────────────────────────
ARES_BASE = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest"

# ── Výstup ────────────────────────────────────────────────────────────────────
REPORT_FILE = "report.txt"
