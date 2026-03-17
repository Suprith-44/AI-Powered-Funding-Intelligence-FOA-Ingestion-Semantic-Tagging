import requests
import json
import csv
import uuid
import re
import os
import argparse
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# ---------------- CONTROLLED ONTOLOGY ----------------

ONTOLOGY = {
    "research_domains": [
        "agriculture", "food safety", "climate change", "public health", 
        "biotechnology", "environmental science", "education", "data science",
        "civic engagement", "international relations", "democratic governance"
    ],

    "methods": [
        "training", "capacity building", "research", "pilot study", 
        "field study", "technology development", "evaluation", "workshop",
        "alumni networking", "community outreach", "mentorship"
    ],

    "populations": [
        "farmers", "government officials", "students", "researchers", 
        "small businesses", "nonprofits", "underserved communities",
       "alumni associations", "youth leaders"
    ],

    "sponsor_themes": [
        "economic development", "innovation", "sustainability", 
        "trade development", "public safety", "health equity",
        "public relations"
    ]
}

# ----------------- RULE-BASED KEYWORDS -----------------

RULE_KEYWORDS = {
    # Existing Keywords
    "food safety": ["food safety", "food regulation", "food standards"],
    "agriculture": ["agriculture", "farming", "agribusiness"],
    "training": ["training program", "training course", "training"],
    "capacity building": ["capacity building", "skills development"],
    "government officials": ["government officials", "public sector"],
    "research": ["research", "study", "investigation"],
    "trade development": ["trade barriers", "international trade"],
    "U.S. policy goals": ["U.S. policy goals", "embassy priorities", "strategic partnership"],
}


# ---------------- RULE-BASED KEYWORDS ----------------

RULE_KEYWORDS = {
    "food safety": ["food safety", "food regulation", "food standards"],
    "agriculture": ["agriculture", "farming", "agribusiness"],
    "training": ["training program", "training course", "training"],
    "capacity building": ["capacity building", "skills development"],
    "government officials": ["government officials", "public sector"],
    "research": ["research", "study", "investigation"],
    "trade development": ["trade barriers", "international trade"]
}


# ---------------- RULE-BASED TAGGING ----------------

def rule_based_tagging(text):

    tags = set()
    text = text.lower()

    for tag, keywords in RULE_KEYWORDS.items():

        for kw in keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", text):
                tags.add(tag)

    return list(tags)

# ---------------- CONFIG ----------------

API_KEY = "Kllj2LydiCp4PJmyzF3hp3LvG"
BASE_URL = "https://api.simpler.grants.gov/v1/opportunities/search"

PAGE_SIZE = 25


# ---------------- TEXT NORMALIZATION ----------------

def normalize_text(text):
    if not text:
        return ""

    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def html_to_text(html):
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")
    return normalize_text(soup.get_text(" "))


# ---------------- DATE NORMALIZATION ----------------

def normalize_date(date_string):

    if not date_string:
        return None

    try:
        return datetime.fromisoformat(date_string.replace("Z", "")).date().isoformat()
    except:
        return None


# ---------------- FOA EXTRACTION ----------------

def extract_foa(record, source_url):

    summary = record.get("summary", {})

    foa = {
        "foa_id": record.get("opportunity_id") or str(uuid.uuid4()),
        "title": record.get("opportunity_title"),
        "agency": record.get("agency_name"),
        "open_date": normalize_date(summary.get("post_date")),
        "close_date": normalize_date(summary.get("close_date")),
        "eligibility_text": normalize_text(summary.get("applicant_eligibility_description")),
        "program_description": html_to_text(summary.get("summary_description")),
        "award_floor": summary.get("award_floor"),
        "award_ceiling": summary.get("award_ceiling"),
        "expected_awards": summary.get("expected_number_of_awards"),
        "funding_category": summary.get("funding_category_description"),
        # Store the provided source URL for traceability in outputs
        "Source URL": source_url,
        "opportunity_number": record.get("opportunity_number"),
        "agency_code": record.get("agency_code")
    }

    # Apply rule-based tagging on relevant textual fields
    text_to_tag = " ".join([
        foa.get("title") or "",
        foa.get("eligibility_text") or "",
        foa.get("program_description") or "",
        foa.get("funding_category") or ""
    ])

    foa["tags"] = rule_based_tagging(text_to_tag)

    return foa


# ---------------- FETCH OPPORTUNITIES ----------------

def fetch_recent_opportunities():

    yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    all_records = []
    page = 1
    total_pages = 1

    while page <= total_pages:

        payload = {
            "filters": {
                "post_date": {
                    "start_date": yesterday_str
                },
                "opportunity_status": {
                    "one_of": ["posted"]
                }
            },
            "pagination": {
                "page_offset": page,
                "page_size": PAGE_SIZE,
                "sort_order": [
                    {
                        "order_by": "post_date",
                        "sort_direction": "descending"
                    }
                ]
            }
        }

        try:

            response = requests.post(BASE_URL, headers=headers, json=payload)

            if response.status_code == 401:
                print("Invalid API key")
                return []

            response.raise_for_status()

            data = response.json()

            opportunities = data.get("data", [])
            all_records.extend(opportunities)

            pagination = data.get("pagination_info", {})
            total_pages = pagination.get("total_pages", 1)

            print(f"Fetched page {page}/{total_pages}")

            page += 1

        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            break

    return all_records


# ---------------- PROCESS DATA ----------------

def process_records(records, source_url):

    foa_list = []

    for record in records:
        foa = extract_foa(record, source_url)
        foa_list.append(foa)

    return foa_list


# ---------------- EXPORT JSON ----------------

def save_json(data, filename="foa_output.json"):

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ---------------- EXPORT CSV ----------------

def save_csv(data, filename="foa_output.csv"):

    if not data:
        return

    keys = data[0].keys()

    with open(filename, "w", newline="", encoding="utf-8") as f:

        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)


# ---------------- MAIN ----------------

def run_pipeline(source_url, out_dir):

    print("Fetching opportunities from last 24 hours...")

    records = fetch_recent_opportunities()

    print(f"Total opportunities fetched: {len(records)}")

    foa_data = process_records(records, source_url)

    # Ensure output directory exists
    os.makedirs(out_dir, exist_ok=True)

    json_path = os.path.join(out_dir, "foa.json")
    csv_path = os.path.join(out_dir, "foa.csv")

    save_json(foa_data, json_path)
    save_csv(foa_data, csv_path)

    print("Saved outputs:")
    print(json_path)
    print(csv_path)


def main():
    parser = argparse.ArgumentParser(description="Fetch FOA opportunities and export to JSON/CSV.")
    parser.add_argument("--url", required=True, help="Source URL to record in outputs.")
    parser.add_argument("--out_dir", default="./out", help="Directory where foa.json and foa.csv will be saved.")

    args = parser.parse_args()

    run_pipeline(source_url=args.url, out_dir=args.out_dir)


if __name__ == "__main__":
    main()