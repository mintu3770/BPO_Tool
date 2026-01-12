# =====================================================
# BPO LeadGen Pro – HTML DISCOVERY + PHONE EXTRACTION
# =====================================================

import streamlit as st
import requests
import pandas as pd
import time
import io
import random
import re
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="BPO LeadGen Pro",
    page_icon="💼",
    layout="wide"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (LeadGenBot/1.0)"
}

# =====================================================
# HARD BLOCK LISTS
# =====================================================

BLOCKED_DOMAIN_KEYWORDS = [
    "linkedin", "indeed", "glassdoor", "crunchbase", "angel",
    "naukri", "monster", "ambitionbox", "owler", "zoominfo",
    "apollo", "yelp", "facebook", "twitter", "instagram",
    "github", "medium", "wikipedia",
    "gov", "nic", "startupindia", "startuptn",
    "ac.in", "edu", "ac.uk",
    "iit", "iim", "iisc", "university", "college", "institute"
]

# =====================================================
# REGION CONFIG
# =====================================================

REGION_MAP = {
    "UK – Private Companies": {
        "gl": "uk",
        "query": "UK private company official website services site:co.uk",
        "company_type": "Private Company"
    },
    "USA – Private Companies": {
        "gl": "us",
        "query": "US private company official website services -site:.gov -site:.edu",
        "company_type": "Private Company"
    },
    "India – Private Companies": {
        "gl": "in",
        "query": "Indian private company official website services site:.in -gov -ac -edu",
        "company_type": "Private Company"
    }
}

ROLES_BY_SERVICE = {
    "Hiring": ["HR Manager", "Head of Talent"],
    "Customer Support": ["Support Manager", "Head of Operations"],
    "Sourcing": ["Procurement Head"]
}

SERVICE_ANCHORS = {
    "Hiring": ["career", "job", "join", "work"],
    "Customer Support": ["contact", "support", "help"],
    "Sourcing": ["service", "solution", "procurement"]
}

# =====================================================
# UTILITIES
# =====================================================

def rate_limit():
    time.sleep(random.uniform(1.0, 1.5))

def is_blocked_domain(url):
    domain = urlparse(url).netloc.lower()
    return any(b in domain for b in BLOCKED_DOMAIN_KEYWORDS)

def normalize_phone(phone):
    phone = re.sub(r"[^\d+]", "", phone)
    if 9 <= len(phone) <= 15:
        return phone
    return None

def extract_company_from_domain(url):
    domain = urlparse(url).netloc.lower().replace("www.", "")
    domain = re.sub(r"\.(co\.uk|com|in|org|net|io|ai|uk)$", "", domain)
    parts = re.split(r"[-\.]", domain)
    return " ".join(p.capitalize() for p in parts if len(p) > 2)

# =====================================================
# HTML DISCOVERY
# =====================================================

def discover_internal_page(base_url, service):
    try:
        r = requests.get(base_url, headers=HEADERS, timeout=6)
        soup = BeautifulSoup(r.text, "html.parser")

        for a in soup.find_all("a", href=True):
            text = (a.get_text() or "").lower()
            href = a["href"].lower()

            for key in SERVICE_ANCHORS.get(service, []):
                if key in text or key in href:
                    return urljoin(base_url, a["href"])

    except Exception:
        pass

    return base_url

def extract_phone_numbers(url):
    phones = set()
    try:
        r = requests.get(url, headers=HEADERS, timeout=6)
        text = r.text

        matches = re.findall(r'(\+?\d[\d \-\(\)]{8,15})', text)
        for m in matches:
            phone = normalize_phone(m)
            if phone:
                phones.add(phone)

    except Exception:
        pass

    return list(phones)

# =====================================================
# GOOGLE SEARCH
# =====================================================

def search_google(query, api_key, cx, gl):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cx,
        "q": query,
        "num": 10,
        "gl": gl,
        "hl": "en"
    }

    res = requests.get(url, params=params)
    data = res.json()

    if "items" not in data:
        return []

    results = []
    for item in data["items"]:
        results.append(item["link"])

    rate_limit()
    return results

# =====================================================
# PIPELINE
# =====================================================

def process_results(urls, region_key, service, count):
    cfg = REGION_MAP[region_key]
    leads = []

    for base_url in urls:
        if is_blocked_domain(base_url):
            continue

        company = extract_company_from_domain(base_url)

        internal_page = discover_internal_page(base_url, service)
        phones = extract_phone_numbers(internal_page)

        phone = phones[0] if phones else "Visit Website"

        leads.append({
            "Company": company,
            "Decision Maker": random.choice(ROLES_BY_SERVICE[service]),
            "Phone": phone,
            "Source Link": internal_page,
            "Company Type": cfg["company_type"],
            "Lead Type": "Phone Verified" if phone != "Visit Website" else "Link Only"
        })

        if len(leads) >= count:
            break

    return leads

# =====================================================
# UI
# =====================================================

st.title("🛡️ BPO LeadGen Pro — Smart Link Discovery + Phone Extraction")
st.caption("Homepage → Internal Page → Phone Number")

c1, c2, c3 = st.columns(3)
with c1:
    region_key = st.selectbox("Target Market", REGION_MAP.keys())
with c2:
    service = st.selectbox("Service Pitch", ROLES_BY_SERVICE.keys())
with c3:
    count = st.slider("Lead Count", 5, 10, 5)

if st.button("🚀 Generate Leads", type="primary"):

    API_KEY = st.secrets.get("GOOGLE_API_KEY")
    CX_ID = st.secrets.get("SEARCH_ENGINE_ID")

    if not API_KEY or not CX_ID:
        st.error("Missing API credentials.")
        st.stop()

    cfg = REGION_MAP[region_key]
    query = f"{cfg['query']} {service}"

    st.write(f"**Debug Query:** `{query}`")

    with st.status("🔍 Discovering internal pages & phone numbers...", expanded=True):
        urls = search_google(query, API_KEY, CX_ID, cfg["gl"])
        leads = process_results(urls, region_key, service, count)
        df = pd.DataFrame(leads)

    if df.empty:
        st.warning("No valid leads found.")
    else:
        st.dataframe(df, use_container_width=True)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False)

        st.download_button(
            "📥 Download Excel",
            buffer.getvalue(),
            "BPO_Leads_With_Phone_and_Pages.xlsx"
        )
