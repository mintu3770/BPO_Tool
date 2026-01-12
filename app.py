# =====================================================
# BPO LeadGen Pro – FINAL HARD BLOCK PATCH
# No Academia | No Government | Company Websites Only
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
# HARD BLOCK LISTS (NON-NEGOTIABLE)
# =====================================================

# 1️⃣ Blocked domains & TLDs
BLOCKED_DOMAIN_KEYWORDS = [
    # Aggregators / Social / Directories
    "linkedin", "indeed", "glassdoor", "crunchbase", "angel",
    "naukri", "monster", "ambitionbox", "owler", "zoominfo",
    "apollo", "yelp", "facebook", "twitter", "instagram",
    "github", "medium", "wikipedia",

    # Government
    "gov", "nic", "ministry", "startupindia", "startuptn",

    # Academia
    "ac.in", "edu", "edu.in", "ac.uk",
    "iit", "iim", "iisc", "university", "college",
    "institute", "school", "academy"
]

# 2️⃣ Blocked URL path patterns
BLOCKED_PATH_KEYWORDS = [
    "/company", "/companies", "/profile", "/jobs", "/careers",
    "/listing", "/directory", "/employers", "/reviews"
]

# 3️⃣ Blocked entity keywords (company name + URL text)
BLOCKED_ENTITY_KEYWORDS = [
    "iit", "iim", "iisc", "university", "college",
    "institute", "school", "academy",
    "government", "ministry", "department", "council",
    "authority", "mission"
]

# =====================================================
# REGION CONFIG (SEARCH-LEVEL ENFORCEMENT)
# =====================================================

REGION_MAP = {
    # ---------------- UK ----------------
    "UK – Private Companies": {
        "gl": "uk",
        "query": (
            "UK private company official website services "
            "site:co.uk "
            "-plc -bank -university -college -ac.uk -gov"
        ),
        "company_type": "Private Company"
    },

    # ---------------- USA ----------------
    "USA – Private Companies": {
        "gl": "us",
        "query": (
            "US private company official website services "
            "-site:.gov -site:.edu -site:.mil "
            "-university -college"
        ),
        "company_type": "Private Company"
    },

    # ---------------- INDIA ----------------
    "India – Private Companies": {
        "gl": "in",
        "query": (
            "Indian private company official website services "
            "site:.in "
            "-gov -nic -ac -edu -university -college -institute"
        ),
        "company_type": "Private Company"
    }
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
        ["🌐 Real Google Search", "🛠️ Simulation (Test UI)"],
        index=0
    )

    if mode == "🌐 Real Google Search":
        API_KEY = st.secrets.get("GOOGLE_API_KEY")
        CX_ID = st.secrets.get("SEARCH_ENGINE_ID")

    st.divider()
    st.info(
        "STRICT MODE ENABLED\n\n"
        "• No universities\n"
        "• No government\n"
        "• No aggregators\n"
        "• Company-owned websites only"
    )

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
    return any(b in domain for b in BLOCKED_DOMAIN_KEYWORDS)

def is_blocked_path(url):
    path = urlparse(url).path.lower()
    return any(p in path for p in BLOCKED_PATH_KEYWORDS)

def is_blocked_entity(company, url):
    text = (company + " " + url).lower()
    return any(k in text for k in BLOCKED_ENTITY_KEYWORDS)

def looks_like_company_domain(company, url):
    domain = urlparse(url).netloc.lower().replace("www.", "")
    tokens = re.findall(r"[a-zA-Z]{3,}", company.lower())
    return any(t in domain for t in tokens)

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
# STRICT EXTRACTION (FINAL FILTER)
# =====================================================

def process_results(results, region_key, service, count):
    cfg = REGION_MAP[region_key]
    leads = []

    for r in results:
        url = r["url"]

        # HARD BLOCKS
        if is_blocked_domain(url):
            continue
        if is_blocked_path(url):
            continue

        company = clean_company_name(r["company_raw"])

        if is_blocked_entity(company, url):
            continue
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

st.title("🛡️ BPO LeadGen Pro — STRICT PRIVATE COMPANIES ONLY")
st.caption("Zero academia • Zero government • Zero aggregators")

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

    if mode == "🛠️ Simulation (Test UI)":
        st.info("Simulation mode active.")
        st.stop()

    if not API_KEY or not CX_ID:
        st.error("Missing API credentials.")
        st.stop()

    cfg = REGION_MAP[region_key]
    query = f"{cfg['query']} {service}"

    st.write(f"**Debug Query:** `{query}`")

    with st.status("🔍 Searching strictly private company websites...", expanded=True):
        results = search_google(query, API_KEY, CX_ID, cfg["gl"])
        leads = process_results(results, region_key, service, count)
        df = pd.DataFrame(leads)

    if df.empty:
        st.warning(
            "No private companies found under strict rules.\n\n"
            "This is expected when data purity is enforced."
        )
    else:
        st.dataframe(df, use_container_width=True)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False)

        st.download_button(
            "📥 Download Excel",
            buffer.getvalue(),
            "BPO_Private_Companies_Only.xlsx"
        )
