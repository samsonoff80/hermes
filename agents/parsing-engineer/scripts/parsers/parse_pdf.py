#!/usr/bin/env python3
"""
Парсер PDF каталогов выставок ProdExpo.
Извлекает: название, страна, телефон, email, сайт, описание.
"""

import csv, json, logging, re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional
import fitz
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

COUNTRY_KEYWORDS = [
    "россия", "турция", "италия", "индия", "китай", "бразилия", "германия",
    "франция", "испания", "польша", "республика корея", "юар", "азербайджан",
    "армения", "грузия", "казахстан", "узбекистан", "беларусь", "украина",
    "вьетнам", "таиланд", "индонезия", "швейцария", "австрия", "нидерланды",
    "бельгия", "португалия", "швеция", "норвегия", "дания", "финляндия",
    "япония", "великобритания", "сша", "канада", "мексика", "австралия",
    "израиль", "оаэ", "египет", "греция", "сербия", "лаtvия", "литва",
    "эстония", "молдова", "таджикистан", "кыргызстан", "туркменистан",
    "монголия", "сингапур", "ирландия", "republic", "republic of",
]

RE_TEL = re.compile(r"TEL[:\s/]+([+\d\s\(\)\-]+)", re.IGNORECASE)
RE_FAX = re.compile(r"FAX[:\s]+([+\d\s\(\)\-]+)", re.IGNORECASE)
RE_EMAIL = re.compile(r"E[-\s]?mail[:\s]*([\w.+-]+@[\w.-]+\.\w+)", re.IGNORECASE)
RE_WEB = re.compile(r"Internet[:\s]*(https?://[^\s]+|www\.[^\s]+)", re.IGNORECASE)
RE_STAND = re.compile(r"ПАВ\.\s*([\w\s]+?),?\s*ЗАЛ\s*(\d+),?\s*СТЕНД\s*([\w\d]+)", re.IGNORECASE)

SKIP_PREFIXES = ("официальный каталог", "official catalogue", "продэкспо", "prodexpo",
                 "алфавитный список", "alphabetical list", "реклама", "advertisement")
SKIP_LINE_RE = re.compile(r"^\d+$")

@dataclass
class Company:
    name: str = ""; name_en: str = ""; country: str = ""; address: str = ""
    phone: str = ""; fax: str = ""; email: str = ""; website: str = ""
    description: str = ""; description_en: str = ""; stand: str = ""
    source: str = ""; page: int = 0
    def to_dict(self) -> dict: return asdict(self)

def is_header_line(line: str) -> bool:
    low = line.strip().lower()
    return any(low.startswith(p) for p in SKIP_PREFIXES) or bool(SKIP_LINE_RE.match(line.strip()))

def extract_country(line: str) -> Optional[str]:
    stripped = line.strip(); low = stripped.lower()
    republic_match = re.match(r'^(Republic\s+of\s+\w+(?:\s+\w+)?)', stripped, re.IGNORECASE)
    if republic_match: return republic_match.group(1)
    for country in COUNTRY_KEYWORDS:
        if low.startswith(country):
            idx = low.find(country)
            return stripped[:idx + len(country)]
    return None

def has_cyrillic(text: str) -> bool:
    return bool(re.search(r"[А-ЯЁа-яё]", text))

def extract_contacts(text: str) -> dict:
    contacts = {"phone": "", "fax": "", "email": "", "website": ""}
    m = RE_TEL.search(text)
    if m: contacts["phone"] = m.group(1).strip()
    m = RE_FAX.search(text)
    if m: contacts["fax"] = m.group(1).strip()
    m = RE_EMAIL.search(text)
    if m: contacts["email"] = m.group(1).strip().lower()
    m = RE_WEB.search(text)
    if m:
        url = m.group(1).strip()
        if url.startswith("www.") and not url.startswith("http"): url = "http://" + url
        contacts["website"] = url
    return contacts

def extract_stand(text: str) -> str:
    m = RE_STAND.search(text)
    return f"Pavilion {m.group(1).strip()}, Hall {m.group(2)}, Stand {m.group(3)}" if m else ""

def looks_like_company_name(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) < 2: return False
    if any(stripped.upper().startswith(p) for p in ["TEL", "FAX", "E-MAIL", "EMAIL", "INTERNET", "ПАВ.", "PAV.", "WWW", "HTTP"]): return False
    if re.match(r"^\d+$", stripped): return False
    return any(c.isalpha() for c in stripped)

def parse_company_block(lines: list, page_num: int, source: str) -> Optional[Company]:
    if not lines: return None
    company = Company(source=source, page=page_num)
    country_idx = -1
    for i, line in enumerate(lines):
        country = extract_country(line)
        if country: country_idx = i; company.country = country; break
    if country_idx == -1: return None
    name_lines = [lines[i] for i in range(country_idx) if not is_header_line(lines[i]) and looks_like_company_name(lines[i])]
    if not name_lines: return None
    ru_names = [ln for ln in name_lines if has_cyrillic(ln)]
    en_names = [ln for ln in name_lines if not has_cyrillic(ln)]
    company.name = " ".join(ru_names) if ru_names else name_lines[0]
    company.name_en = " ".join(en_names) if en_names else ""
    if not company.name and company.name_en: company.name = company.name_en; company.name_en = ""
    address_lines, desc_ru, desc_en, contacts_text, stand_line = [], [], [], [], ""
    in_address, contacts_found = True, False
    for i in range(country_idx + 1, len(lines)):
        line = lines[i]; up = line.upper()
        if any(up.startswith(p) for p in ["TEL", "FAX", "E-MAIL", "EMAIL", "INTERNET"]):
            in_address = False; contacts_found = True; contacts_text.append(line); continue
        if up.startswith(("ПАВ.", "PAV.")): stand_line = line; continue
        if contacts_found:
            (desc_ru if has_cyrillic(line) else desc_en).append(line)
        elif in_address: address_lines.append(line)
    company.address = " ".join(address_lines)
    company.description = " ".join(desc_ru) or " ".join(desc_en)
    company.stand = extract_stand(stand_line)
    contacts = extract_contacts("\n".join(contacts_text))
    company.phone = contacts["phone"]; company.fax = contacts["fax"]
    company.email = contacts["email"]; company.website = contacts["website"]
    if not company.name or not company.country: return None
    if not company.phone and not company.email and len(company.description) < 10: return None
    return company

def parse_page(text: str, page_num: int, source: str) -> list:
    companies = []
    lines = [ln.rstrip() for ln in text.split("\n")]
    blocks, current_block, pending_lines = [], [], []
    for line in lines:
        if not line.strip() or is_header_line(line): continue
        country = extract_country(line)
        if country:
            if current_block and any(m in "\n".join(current_block).upper() for m in ["TEL", "E-MAIL", "EMAIL"]):
                blocks.append(current_block)
            current_block = pending_lines + [line]; pending_lines = []; continue
        if any(marker in line.upper() for marker in ["TEL", "E-MAIL", "EMAIL", "INTERNET", "FAX"]):
            current_block.append(line); continue
        if line.strip().upper().startswith(("ПАВ.", "PAV.")):
            current_block.append(line)
            if current_block and any(m in "\n".join(current_block).upper() for m in ["TEL", "E-MAIL", "EMAIL"]):
                blocks.append(current_block)
            current_block = []; continue
        if not current_block: pending_lines.append(line)
        else: current_block.append(line)
    if current_block and any(m in "\n".join(current_block).upper() for m in ["TEL", "E-MAIL", "EMAIL"]):
        blocks.append(current_block)
    for block in blocks:
        company = parse_company_block(block, page_num, source)
        if company: companies.append(company)
    return companies

def parse_pdf(pdf_path: str, output_csv: Optional[str] = None, output_json: Optional[str] = None,
              start_page: int = 0, end_page: Optional[int] = None) -> list:
    pdf_path = Path(pdf_path)
    if not pdf_path.exists(): raise FileNotFoundError(f"PDF не найден: {pdf_path}")
    source_name = pdf_path.stem
    logger.info(f"Открываем PDF: {pdf_path}")
    doc = fitz.open(str(pdf_path))
    total_pages = doc.page_count
    if end_page is None or end_page > total_pages: end_page = total_pages
    logger.info(f"Страниц: {total_pages}, обрабатываем: {start_page + 1}-{end_page}")
    all_companies, errors = [], 0
    for page_num in tqdm(range(start_page, end_page), desc="Парсинг", unit=" стр"):
        try:
            text = doc[page_num].get_text()
            if text.strip():
                all_companies.extend(parse_page(text, page_num + 1, source_name))
        except Exception as e:
            errors += 1; logger.warning(f"Ошибка стр {page_num + 1}: {e}")
    doc.close()
    logger.info(f"✅ Извлечено: {len(all_companies)} компаний")
    if output_csv and all_companies:
        Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
        with open(output_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_companies[0].to_dict().keys())
            writer.writeheader(); writer.writerows([c.to_dict() for c in all_companies])
    if output_json and all_companies:
        Path(output_json).parent.mkdir(parents=True, exist_ok=True)
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump([c.to_dict() for c in all_companies], f, ensure_ascii=False, indent=2)
    return [c.to_dict() for c in all_companies]

if __name__ == "__main__":
    import argparse, sys
    parser = argparse.ArgumentParser(description='Парсер PDF каталогов ProdExpo')
    parser.add_argument('pdf', help='Путь к PDF')
    parser.add_argument('--csv', default='data/parsed_companies.csv', help='CSV вывод')
    parser.add_argument('--json', help='JSON вывод')
    parser.add_argument('--start-page', type=int, default=1)
    parser.add_argument('--end-page', type=int)
    args = parser.parse_args()
    start = max(0, args.start_page - 1)
    try:
        companies = parse_pdf(args.pdf, args.csv, args.json, start, args.end_page)
        if companies:
            logger.info(f"\nПример: {companies[0]['name']} | {companies[0]['country']} | {companies[0]['phone']}")
        logger.info("\n✅ Готово!")
    except Exception as e:
        logger.error(f"❌ {e}")
        sys.exit(1)
