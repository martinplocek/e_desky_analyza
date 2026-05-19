"""
Konfigurace analýzy – upravte hodnoty dle potřeby.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Sledovaná firma a skupina ─────────────────────────────────────────────────
ROOT_ICO = "28830628"          # STYLGROUP s.r.o.
ROOT_NAZEV = "STYLGROUP s.r.o."

# IČO dalších firem skupiny – doplní se automaticky z ARES, nebo přidejte ručně
SKUPINA_ICOS: list[str] = []   # např. ["12345678", "87654321"]

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
