# Analýza stavebních řízení – STYLGROUP / k.ú. Kukleny

Automatizovaný skript pro zjištění, zda jsou na parcelách skupiny **STYLGROUP s.r.o.**
(IČO 28830628) v katastrálním území **Kukleny [647209]** podány žádosti,
zahájeno řízení nebo povolena stavba.

## Co skript dělá

| Krok | Zdroj | Co zjistí |
|------|-------|-----------|
| 1 | **ARES** (gov.cz) | Firmy skupiny – název, IČO, stav, propojené subjekty |
| 2 | **ČÚZK** (katastr) | Parcely vlastněné skupinou v k.ú. Kukleny |
| 3 | **eDesky.cz** | Dokumenty stavebních řízení publikované na úředních deskách |

## Instalace a spuštění

```bash
# 1. Nainstalujte závislosti
pip install -r requirements.txt

# 2. Vytvořte konfiguraci
cp .env.example .env
# Otevřete .env a doplňte EDESKY_API_KEY

# 3. Spusťte analýzu
python main.py
```

Výstup se zobrazí v konzoli a uloží do `report.txt`.

## Přihlašovací údaje

### eDesky.cz API klíč (povinné)
- Získáte na: https://edesky.cz/stranka/api
- Vložte do `.env` jako `EDESKY_API_KEY=...`

### ČÚZK WSDP (volitelné, ale doporučené)
- Bezplatná registrace: https://katastr.cuzk.cz/Pristup/Login.aspx
- Bez registrace skript zkusí veřejné nahlížení (méně spolehlivé)
- Po registraci doplňte do `.env`: `CUZK_WSDP_USER=...` a `CUZK_WSDP_PASS=...`

## Ruční doplnění parcel

Pokud automatické načítání z ČÚZK selže, zjistěte parcely ručně:
1. Jděte na https://nahlizenidokn.cuzk.cz/
2. Vyhledat → Vlastník → zadejte „STYLGROUP" nebo IČO 28830628
3. Filtrujte k.ú. Kukleny
4. Čísla parcel doplňte přímo do `config.py`

## Omezení

- eDesky.cz indexuje dokumenty zveřejněné na **úředních deskách** – tj. zahájení
  řízení, veřejné vyhlášky apod. Nepokrývá interní spisy stavebního úřadu.
- ČÚZK web scraping může selhat při změně struktury stránek (ČÚZK mění rozhraní).
  Spolehlivější je WSDP přístup.
- Propojené subjekty z ARES jsou pouze automaticky zjištěné – vždy ověřte
  ručně na https://or.justice.cz/.
