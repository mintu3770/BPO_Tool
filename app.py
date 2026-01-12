# =====================================================
# BPO LeadGen Pro – FINAL PATCH
# Country + Company-Type Search Enforcement
# =====================================================

import streamlit as st
import requests
import pandas as pd
import time
import io
import random
import re
import logging

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="BPO LeadGen Pro",
    page_icon="💼",
    layout="wide"
)

logging.basicConfig(level=logging.INFO)

# =====================================================
# REGION + COMPANY TYPE (SEARCH-LEVEL ENFORCEMENT)
# =====================================================

REGION_MAP = {
    # ---------------- UK ----------------
    "UK – Startups": {
        "gl": "uk",
        "query": (
            "UK startup technology company founded "
            "site:co.uk -plc -bank -council -nhs -gov"
        ),
        "company_type": "Startup (Growth)"
    },
    "UK – Top Companies": {
        "gl": "uk",
        "query": (
            "FTSE 100 plc corporate headquarters contact "
            "site:co.uk -startup"
        ),
        "company_type": "Enterprise (Established)"
    },

    # ---------------- USA ----------------
    "USA – Startups": {
        "gl": "us",
        "query": (
            "US startup technology company founded "
            "-site:.gov -site:.edu -site:.mil"
        ),
        "company_type": "Startup (Growth)"
    },
    "USA – Top Companies": {
        "gl": "us",
        "query": (
            "S&P 500 company corporate headquarters contact "
            "-site:.gov -site:.edu -site:.mil"
        ),
        "company_type": "Enterprise (Established)"
    },

    # ---------------- INDIA ----------------
    "India – Startups": {
        "gl": "in",
        "query": (
            "Indian startup technology company founded "
            "site:.in -bank -gov -nic"
        ),
        "company_type": "Startup (Growth)"
    },
    "India – Top Companies": {
        "gl": "in",
        "query": (
            "NIFTY 50 listed company corporate office contact "
            "site:.in -startup"
        ),
        "company_type": "Enterprise (Established)"
    },
}

ROLES_BY_SERVICE = {
    "Hiring": ["HR Manager", "Head of Talent", "Chief People Officer"],
    "Customer Support": ["Head of Operations", "Support Director"],
    "Sourcing": ["Procurement Head", "VP Procurement"]
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
        "Hunter Mode enabled. If a phone number is hidden, "
        "the direct contact page link is saved instead."
    )

# =====================================================
# UTILITIES
# =====================================================

def rate_limit():
    time.sleep(random.uniform(0.8, 1.3))

def normalize_phone(phone):
    phone = re.sub(r"[^\d+]", "", phone)
    return phone if len(phone) >= 8 else "Visit Website"

def clean_company_name(name):
    name = re.sub(r"\|.*", "", name)
    name = re.sub(r"-.*", "", name)
    name = re.sub(r"Contact.*", "", name, flags=re.I)
    return name.strip()

def is_us_government(url):
    return any(x in url for x in [".gov", ".edu", ".mil"])

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
        return None

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
# EXTRACTION (SAFE & GLOBAL)
# =====================================================

def process_results(results, region_key, service, count):
    cfg = REGION_MAP[region_key]
    leads = []

    for r in results:
        company = clean_company_name(r["company_raw"])
        snippet = r["snippet"]
        url = r["url"]

        # Block US government entities explicitly
        if "USA" in region_key and is_us_government(url):
            continue

        phones = re.findall(r'(\+?\d[\d \-]{8,15})', snippet)
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

st.title("🛡️ BPO LeadGen Pro")
st.caption("Country-locked, company-type enforced BPO lead intelligence")

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

    with st.status("🔍 Hunting qualified leads...", expanded=True):
        results = search_google(query, API_KEY, CX_ID, cfg["gl"])

        if not results:
            st.error("No results found.")
            st.stop()

        leads = process_results(results, region_key, service, count)
        df = pd.DataFrame(leads)

    if df.empty:
        st.warning("No qualified leads found.")
    else:
        st.dataframe(df, use_container_width=True)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False)

        st.download_button(
            "📥 Download Excel",
            buffer.getvalue(),
            "BPO_Qualified_Leads.xlsx"
        )
