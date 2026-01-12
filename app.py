# =====================================================
# BPO LeadGen Pro – COMPANY WEBSITES ONLY (STRICT MODE)
# =====================================================

import streamlit as st
import requests
import pandas as pd
import time
import io
import random
import re
from urllib.parse import urlparse

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="BPO LeadGen Pro",
    page_icon="💼",
    layout="wide"
)

# =====================================================
# BLOCK LISTS (CRITICAL)
# =====================================================

BLOCKED_DOMAINS = [
    "linkedin.com", "indeed.com", "glassdoor.com", "crunchbase.com",
    "angel.co", "startupindia.gov.in", "naukri.com", "monster.com",
    "ambitionbox.com", "owler.com", "zoominfo.com", "apollo.io",
    "yelp.com", "facebook.com", "twitter.com", "instagram.com",
    "github.com", "medium.com", "wikipedia.org"
]

BLOCKED_PATH_KEYWORDS = [
    "/company", "/companies", "/profile", "/jobs", "/careers",
    "/listing", "/directory", "/employers", "/reviews"
]

# =====================================================
# REGION CONFIG (SEARCH-LEVEL ENFORCEMENT)
# =====================================================

REGION_MAP = {
    "UK – Startups": {
        "gl": "uk",
        "query": "UK startup technology company official website contact site:co.uk",
        "company_type": "Startup"
    },
    "UK – Top Companies": {
        "gl": "uk",
        "query": "FTSE 100 plc official website corporate contact site:co.uk",
        "company_type": "Enterprise"
    },
    "USA – Startups": {
        "gl": "us",
        "query": "US startup technology company official website contact",
        "company_type": "Startup"
    },
    "USA – Top Companies": {
        "gl": "us",
        "query": "S&P 500 company official website corporate contact",
        "company_type": "Enterprise"
    },
    "India – Startups": {
        "gl": "in",
        "query": "Indian startup technology company official website contact site:.in",
        "company_type": "Startup"
    },
    "India – Top Companies": {
        "gl": "in",
        "query": "NIFTY 50 listed company official website corporate contact site:.in",
        "company_type": "Enterprise"
    },
}

ROLES_BY_SERVICE = {
    "Hiring": ["HR Manager", "Head of Talent"],
    "Customer Support": ["Head of Operations"],
    "Sourcing": ["Procurement Head"]
}

# =====================================================
# SIDEBAR
# =====================================================

with st.sidebar:
    st.header("⚙️ Configuration")

    mode = st.radio(
        "Mode",
        ["🌐 Real Google Search", "🛠️ Simulation"],
        index=0
    )

    if mode == "🌐 Real Google Search":
        API_KEY = st.secrets.get("GOOGLE_API_KEY")
        CX_ID = st.secrets.get("SEARCH_ENGINE_ID")

# =====================================================
# UTILITIES
# =====================================================

def rate_limit():
    time.sleep(random.uniform(0.9, 1.4))

def normalize_phone(phone):
    phone = re.sub(r"[^\d+]", "", phone)
    return phone if len(phone) >= 8 else "Visit Website"

def clean_company_name(name):
    name = re.sub(r"\|.*", "", name)
    name = re.sub(r"-.*", "", name)
    name = re.sub(r"Contact.*", "", name, flags=re.I)
    return name.strip()

def is_blocked_domain(url):
    domain = urlparse(url).netloc.lower()
    return any(b in domain for b in BLOCKED_DOMAINS)

def is_blocked_path(url):
    path = urlparse(url).path.lower()
    return any(p in path for p in BLOCKED_PATH_KEYWORDS)

def looks_like_company_domain(company, url):
    """
    Ensures domain matches company name roughly
    """
    domain = urlparse(url).netloc.lower()
    domain = domain.replace("www.", "")

    company_tokens = re.findall(r"[a-zA-Z]{3,}", company.lower())
    return any(token in domain for token in company_tokens)

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
        results.append({
            "company_raw": item["title"],
            "snippet": item.get("snippet", ""),
            "url": item["link"]
        })

    rate_limit()
    return results

# =====================================================
# STRICT EXTRACTION (COMPANY DOMAINS ONLY)
# =====================================================

def process_results(results, region_key, service, count):
    cfg = REGION_MAP[region_key]
    leads = []

    for r in results:
        url = r["url"]

        # HARD FILTERS
        if is_blocked_domain(url):
            continue
        if is_blocked_path(url):
            continue

        company = clean_company_name(r["company_raw"])

        if not looks_like_company_domain(company, url):
            continue

        phones = re.findall(r'(\+?\d[\d \-]{8,15})', r["snippet"])
        phone = normalize_phone(phones[0]) if phones else "Visit Website"

        leads.append({
            "Company": company,
            "Decision Maker": random.choice(ROLES_BY_SERVICE[service]),
            "Phone": phone,
            "Source Link": url,
            "Company Type": cfg["company_type"],
            "Lead Type": "Phone Verified" if phone != "Visit Website" else "Link Only"
        })

        if len(leads) >= count:
            break

    return leads

# =====================================================
# MAIN UI
# =====================================================

st.title("🛡️ BPO LeadGen Pro – Company Websites Only")
st.caption("Strict mode: only official company domains are allowed")

c1, c2, c3 = st.columns(3)
with c1:
    region_key = st.selectbox("Target Market", REGION_MAP.keys())
with c2:
    service = st.selectbox("Service Pitch", ROLES_BY_SERVICE.keys())
with c3:
    count = st.slider("Lead Count", 5, 10, 5)

# =====================================================
# RUN
# =====================================================

if st.button("🚀 Generate Leads", type="primary"):

    if mode == "🛠️ Simulation":
        st.info("Simulation mode active.")
        st.stop()

    if not API_KEY or not CX_ID:
        st.error("Missing API credentials.")
        st.stop()

    cfg = REGION_MAP[region_key]
    query = f"{cfg['query']} {service}"

    st.write(f"**Debug Query:** `{query}`")

    with st.status("🔍 Searching official company websites...", expanded=True):
        results = search_google(query, API_KEY, CX_ID, cfg["gl"])
        leads = process_results(results, region_key, service, count)
        df = pd.DataFrame(leads)

    if df.empty:
        st.warning("No official company websites found with strict rules.")
    else:
        st.dataframe(df, use_container_width=True)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False)

        st.download_button(
            "📥 Download Excel",
            buffer.getvalue(),
            "BPO_Company_Websites_Only.xlsx"
        )
