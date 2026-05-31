"""
arlis.am Բնապահպանական Օրենքների Scraper
Հավաքում է ՀՀ բնապահպանական օրենսդրությունը
"""

import httpx
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Optional
import json
import re


SEARCH_URL = "https://www.arlis.am/hy/search"

ECO_KEYWORDS = [
    "շրջակա միջավայր",
    "բնապահպան",
    "ՇՄԱԳ",
    "շինարարություն",
    "հողօգտագործ",
    "թափոն",
    "վտանգավոր նյութ",
    "ջրային ռեսուրս",
    "անտառ",
    "հանքարդյունաբ",
    "մթնոլորտ",
    "աղտոտ",
    "կենսաբազմազ",
    "բնական ռեսուրս",
    "ռադիոակտիվ",
    "քիմիական",
    "էկոլոգ",
]

SECTOR_MAP = {
    "շինարարություն":    "construction",
    "հողօգտագործ":       "land_use",
    "թափոն":             "waste",
    "ջրային":            "water",
    "անտառ":             "forestry",
    "հանքարդյունաբ":     "mining",
    "մթնոլորտ":          "air",
    "կենսաբազմ":         "biodiversity",
    "ռադիոակտիվ":        "radiation",
    "քիմիական":          "chemicals",
    "էկոլոգ":            "ecology",
    "էներգ":             "energy",
}


def detect_sector(text: str) -> str:
    text_lower = text.lower()
    for keyword, sector in SECTOR_MAP.items():
        if keyword in text_lower:
            return sector
    return "general"


async def fetch_document(client: httpx.AsyncClient, doc_id: int) -> Optional[dict]:
    """Ոlora oacf arlis.am document by ID"""
    url = f"https://www.arlis.am/hy/acts/{doc_id}"
    try:
        resp = await client.get(url, timeout=15.0)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # Title
        title_el = soup.find("h1") or soup.find("h2") or soup.find(class_="act-title")
        title = title_el.get_text(strip=True) if title_el else ""

        # Check if eco-related
        if not title:
            return None
        title_lower = title.lower()
        is_eco = any(kw in title_lower for kw in ECO_KEYWORDS)
        if not is_eco:
            return None

        # Body text
        body_el = (
            soup.find(class_="act-body")
            or soup.find(class_="document-content")
            or soup.find("article")
            or soup.find("main")
        )
        body = body_el.get_text(separator="\n", strip=True) if body_el else ""

        # Date
        date_el = soup.find(class_="act-date") or soup.find(class_="date")
        date_str = date_el.get_text(strip=True) if date_el else ""

        # Doc number
        num_match = re.search(r"N\s*([\w-]+)", title)
        doc_number = num_match.group(0) if num_match else f"DOC-{doc_id}"

        return {
            "doc_id":     doc_id,
            "doc_number": doc_number,
            "title":      title,
            "body":       body[:8000],  # cap text size
            "date":       date_str,
            "sector":     detect_sector(title + " " + body[:500]),
            "url":        url,
            "source":     "arlis.am",
            "scraped_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        print(f"[!] doc_id={doc_id}: {e}")
        return None


async def scrape_range(start: int, end: int, delay: float = 0.5) -> list[dict]:
    """Scrape a range of doc IDs from arlis.am"""
    results = []
    async with httpx.AsyncClient(
        headers={"User-Agent": "EcoAgent-Armenia/1.0 Research Bot"},
        follow_redirects=True,
    ) as client:
        for doc_id in range(start, end + 1):
            doc = await fetch_document(client, doc_id)
            if doc:
                results.append(doc)
                print(f"[+] Found: {doc['title'][:60]}...")
            await asyncio.sleep(delay)

    return results


async def scrape_by_keyword_search(keyword: str) -> list[dict]:
    """Search arlis.am by keyword (if search endpoint available)"""
    results = []
    async with httpx.AsyncClient(
        headers={"User-Agent": "EcoAgent-Armenia/1.0 Research Bot"},
        follow_redirects=True,
    ) as client:
        try:
            params = {"q": keyword, "type": "normative"}
            resp = await client.get(SEARCH_URL, params=params, timeout=15.0)
            if resp.status_code != 200:
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            links = soup.find_all("a", href=re.compile(r"/hy/acts/\d+"))

            for link in links[:20]:
                href = link.get("href", "")
                id_match = re.search(r"/acts/(\d+)", href)
                if id_match:
                    doc_id = int(id_match.group(1))
                    doc = await fetch_document(client, doc_id)
                    if doc:
                        results.append(doc)
                    await asyncio.sleep(0.5)

        except Exception as e:
            print(f"[!] Search error: {e}")

    return results


def save_documents(docs: list[dict], path: str = "scraped_laws.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)
    print(f"[✓] Saved {len(docs)} documents to {path}")


# ─── Seed data ──────────────────────────────────────────────────────────────
# Known arlis.am IDs for key environmental laws in Armenia
KNOWN_ECO_LAW_IDS = [
    # Շրջակա միջավայրի վրա ազդեցության գնահատում
    140475,
    # Բնապահպանության մասին օրենք
    149767,
    # Ջրային ռեսուրսների կառ.
    150000,
    # Անտառային օրենսգիրք
    151000,
    # Թափոնների մասին
    152000,
]


if __name__ == "__main__":
    async def main():
        print("🌿 EcoAgent Armenia — arlis.am Scraper")
        print("=" * 40)

        # Try keyword searches for all eco topics
        all_docs = []
        for kw in ECO_KEYWORDS[:5]:  # Start with first 5
            print(f"\n🔍 Searching: '{kw}'")
            docs = await scrape_by_keyword_search(kw)
            all_docs.extend(docs)
            print(f"   Found {len(docs)} documents")

        # Deduplicate by doc_id
        seen = set()
        unique_docs = []
        for d in all_docs:
            if d["doc_id"] not in seen:
                seen.add(d["doc_id"])
                unique_docs.append(d)

        print(f"\n✅ Total unique eco documents: {len(unique_docs)}")
        save_documents(unique_docs)

    asyncio.run(main())
