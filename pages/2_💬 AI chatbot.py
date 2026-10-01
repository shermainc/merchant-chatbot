import streamlit as st
import pandas as pd
import re
import os
from datetime import datetime
from helper_functions.llm import get_completion_by_messages
from helper_functions.utility import check_password  


# ── Constants ────────────────────────────────────────────────────────────────
CSV_FILE_PATH = "pages/merchants.csv"

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "on", "at", "by", "for", "with", "about",
    "against", "between", "into", "through", "during", "before", "after",
    "above", "below", "from", "up", "down", "out", "off", "over", "under",
    "again", "further", "then", "once", "and", "but", "or", "nor", "so",
    "yet", "both", "either", "neither", "not", "only", "own", "same",
    "than", "too", "very", "just", "because", "as", "until", "while",
    "i", "me", "my", "we", "our", "you", "your", "he", "she", "it",
    "they", "them", "their", "what", "which", "who", "this", "that",
    "these", "those", "am", "show", "find", "get", "give", "tell",
    "list", "any", "all", "some", "there", "here", "where", "when",
    "how", "want", "looking", "look", "near", "around", "deals", "deal",
    "merchant", "merchants", "available", "please", "hi", "hello",
    "halal", "food",
}

AREA_KEYWORDS = {
    "orchard", "somerset", "dhoby ghaut", "city hall", "raffles place",
    "marina bay", "bugis", "lavender", "kallang", "tampines", "bedok",
    "pasir ris", "simei", "tanah merah", "kembangan", "eunos", "paya lebar",
    "aljunied", "hougang", "serangoon", "kovan", "woodleigh", "potong pasir",
    "boon keng", "farrer park", "little india", "rochor", "dhoby",
    "jurong", "boon lay", "lakeside", "chinese garden", "clementi",
    "dover", "buona vista", "one-north", "kent ridge", "haw par villa",
    "pasir panjang", "labrador park", "harbourfront", "vivocity",
    "ang mo kio", "bishan", "braddell", "toa payoh", "novena", "newton",
    "stevens", "botanic gardens", "caldecott", "marymount", "yishun",
    "khatib", "yio chu kang", "admiralty", "sembawang", "canberra",
    "woodlands", "marsiling", "kranji", "bukit panjang", "choa chu kang",
    "yew tee", "bukit batok", "bukit gombak", "hillview", "beauty world",
    "king albert park", "sixth avenue", "tan kah kee", "botanic",
    "holland village", "one north", "queenstown", "redhill", "tiong bahru",
    "outram", "chinatown", "clarke quay", "fort canning", "bras basah",
    "esplanade", "promenade", "bayfront", "downtown", "telok ayer",
    "tanjong pagar", "harbourfront", "sentosa", "punggol", "sengkang",
    "buangkok", "compassvale", "rivervale", "fernvale", "anchorvale",
    "balestier", "geylang", "ubi", "macpherson", "tai seng", "bartley",
    "upper changi", "expo", "changi", "loyang", "pasir ris",
}

FALLBACK_PROMPTS = (
    "I'm sorry, I'm not sure what you're looking for! Here are some things you can try:\n\n"
    "🔍 **Search by category:** 'Show me food deals', 'spa merchants', 'gym discounts'\n"
    "📍 **Search by location:** 'Snacks near Orchard', 'restaurants in Tampines'\n"
    "🏪 **Find a merchant:** 'Is 4Fingers our merchant?', 'Do you have Subway?'\n"
    "📋 **See all outlets:** 'Old Chang Kee outlets', 'Where are the Starbucks branches?'\n"
    "🥩 **Filter by Halal:** 'List me halal food', 'halal merchants'\n\n"
    "_Try one of the above to get started!_"
)

# ── Data loading ─────────────────────────────────────────────────────────────
@st.cache_data
def load_and_process_database():
    try:
        df = pd.read_csv(CSV_FILE_PATH)
        df.columns = df.columns.str.strip()
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].fillna("").astype(str).str.strip()
        data = df.to_dict(orient="records")

        # Deduplicate merchants by name
        seen_names = set()
        unique_merchants = []
        for row in data:
            name = row.get("name", "").strip()
            if name and name not in seen_names:
                seen_names.add(name)
                unique_merchants.append(name)
        unique_merchants.sort()

        # Build keyword index: keyword -> list of row indices
        keyword_index = {}
        for idx, row in enumerate(data):
            raw_keywords = row.get("Keywords", "")
            for kw in raw_keywords.split(","):
                kw_clean = kw.strip().lower()
                if kw_clean:
                    keyword_index.setdefault(kw_clean, []).append(idx)

        valid_names = [n for n in unique_merchants if n]
        valid_keywords = sorted(keyword_index.keys())

        return data, unique_merchants, keyword_index, valid_names, valid_keywords

    except Exception as e:
        st.error(f"Failed to load database from {CSV_FILE_PATH}: {e}")
        return [], [], {}, [], []


# ── Date validation ───────────────────────────────────────────────────────────
def is_deal_valid(row):
    today = datetime.today()
    for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            start = datetime.strptime(row.get("startDate", ""), fmt)
            end = datetime.strptime(row.get("endDate", ""), fmt)
            return start <= today <= end
        except ValueError:
            continue
    return True  # Include if dates unparseable


# ── Search helpers ────────────────────────────────────────────────────────────
def extract_search_terms(query):
    words = re.findall(r"[a-zA-Z0-9']+", query.lower())
    area_found = None
    filtered = []
    for word in words:
        if word in AREA_KEYWORDS:
            area_found = word
        elif word not in STOPWORDS:
            filtered.append(word)
    # Also check two-word area phrases
    text_lower = query.lower()
    for area in AREA_KEYWORDS:
        if " " in area and area in text_lower:
            area_found = area
    return filtered, area_found


def is_halal_query(query):
    q = query.lower()
    return "halal" in q


def is_merchant_query(query):
    patterns = [
        r"\bis\b.+\b(our|a|an|your)\b.+\bmerchant\b",
        r"\bdo you have\b",
        r"\bdo we have\b",
        r"\bis .+ (listed|included|part of|in the)\b",
    ]
    q = query.lower()
    return any(re.search(p, q) for p in patterns)


def find_merchant_by_name(query, unique_merchants):
    q = query.lower()
    for name in unique_merchants:
        if name.lower() in q:
            return name
    # Partial match
    for name in unique_merchants:
        parts = name.lower().split()
        if any(p in q for p in parts if len(p) > 3):
            return name
    return None


def is_list_all_query(query):
    q = query.lower()
    patterns = [
        r"list all",
        r"show all",
        r"all merchants",
        r"full list",
        r"every merchant",
        r"how many merchants",
    ]
    return any(re.search(p, q) for p in patterns)


def is_outlet_query(query):
    q = query.lower()
    return any(word in q for word in ["outlet", "outlets", "branch", "branches", "location", "locations"])


def find_all_outlets(merchant_name, data):
    name_lower = merchant_name.lower()
    return [row for row in data if row.get("name", "").lower() == name_lower]


def list_merchants_by_keyword(search_terms, area_found, data, keyword_index, halal_only=False, limit=10):
    if not search_terms and not area_found and not halal_only:
        return []

    if search_terms:
        # Score each row by keyword match
        scores = {}
        for term in search_terms:
            for kw, indices in keyword_index.items():
                if term in kw or kw in term:
                    for idx in indices:
                        scores[idx] = scores.get(idx, 0) + 1

        matched = []
        seen_names = set()
        for idx, score in sorted(scores.items(), key=lambda x: -x[1]):
            row = data[idx]
            if not is_deal_valid(row):
                continue
            if area_found and area_found not in row.get("address", "").lower():
                continue
            if halal_only and row.get("Halal", "").strip().lower() != "yes":
                continue
            name = row.get("name", "").strip()
            if name and name not in seen_names:
                seen_names.add(name)
                matched.append(row)
            if len(matched) >= limit:
                break
    else:
        # Area-only or halal-only search
        matched = []
        seen_names = set()
        for row in data:
            if not is_deal_valid(row):
                continue
            if area_found and area_found not in row.get("address", "").lower():
                continue
            if halal_only and row.get("Halal", "").strip().lower() != "yes":
                continue
            name = row.get("name", "").strip()
            if name and name not in seen_names:
                seen_names.add(name)
                matched.append(row)
            if len(matched) >= limit:
                break

    return sorted(matched, key=lambda r: r.get("name", ""))


# ── Formatters ────────────────────────────────────────────────────────────────
def format_outlet_list(merchant_name, outlets):
    if not outlets:
        return f"I'm sorry, I couldn't find any outlets for **{merchant_name}**. I do not know if they have other locations not listed in our system."
    lines = [f"Here are the outlets for **{merchant_name}** ({len(outlets)} found):\n"]
    for i, row in enumerate(outlets, 1):
        address = row.get("address", "N/A")
        postal = row.get("postalC", "")
        postal_str = f" S({postal})" if postal else ""
        desc = row.get("description", "")
        lines.append(f"**{i}. {address}{postal_str}**")
        if desc:
            lines.append(f"   🎁 {desc}")
        lines.append("")
    return "\n".join(lines)


def format_keyword_list(search_terms, area_found, matched_rows, halal_only=False):
    if not matched_rows:
        label_parts = []
        if halal_only:
            label_parts.append("halal")
        if search_terms:
            label_parts.append(", ".join(search_terms))
        if area_found:
            label_parts.append(f"near {area_found.title()}")
        label = " ".join(label_parts) if label_parts else "your search"
        return (
            f"I'm sorry, I do not know of any active merchants matching **{label}** in our programme.\n\n"
            "Here are some things you can try:\n\n"
            "🔍 **Search by category:** 'food', 'spa', 'gym', 'retail', 'entertainment'\n"
            "📍 **Search by location:** 'Orchard', 'Tampines', 'Bugis', 'Jurong'\n"
            "🥩 **Filter by Halal:** 'halal food', 'halal merchants'\n"
            "🏪 **Find a specific merchant:** 'Is 4Fingers our merchant?'\n"
            "📋 **See outlets:** 'Old Chang Kee outlets'\n\n"
            "_Try narrowing down with a keyword or location!_"
        )

    label_parts = []
    if halal_only:
        label_parts.append("Halal")
    if search_terms:
        label_parts.append(", ".join(search_terms))
    if area_found:
        label_parts.append(f"near {area_found.title()}")
    label = " ".join(label_parts) if label_parts else "your search"

    lines = [f"Here are merchants matching **{label}** (showing top {len(matched_rows)}, A–Z):\n"]
    for i, row in enumerate(matched_rows, 1):
        name = row.get("name", "N/A")
        address = row.get("address", "N/A")
        desc = row.get("description", "")
        lines.append(f"**{i}. {name}**")
        lines.append(f"   📍 {address}")
        if desc:
            lines.append(f"   🎁 {desc}")
        lines.append("")
    if len(matched_rows) == 10:
        lines.append("_Showing first 10 results. Try a more specific search to narrow down!_")
    return "\n".join(lines)


# ── LLM wrapper ───────────────────────────────────────────────────────────────
def safe_llm_call(messages):
    try:
        return get_completion_by_messages(messages)
    except Exception as e:
        err = str(e).lower()
        if any(k in err for k in ["ratelimit", "rate_limit", "429", "token", "context_length", "maximum context"]):
            return FALLBACK_PROMPTS
        raise


# ── Main query handler ────────────────────────────────────────────────────────
def handle_user_query(query, data, unique_merchants, keyword_index):
    halal_only = is_halal_query(query)

    # 1. List all merchants
    if is_list_all_query(query) and not halal_only:
        total = len(unique_merchants)
        return (
            f"There are **{total} merchants** in our programme.\n\n"
            "That's a lot to list! Try narrowing down:\n"
            "🔍 'Show me food merchants' or 'spa deals'\n"
            "📍 'Merchants near Orchard' or 'deals in Tampines'\n"
            "🥩 'List me halal food' or 'halal merchants'\n"
            "🏪 'Is [merchant name] our merchant?'"
        )

    # 2. Outlet query — find merchant name first
    if is_outlet_query(query):
        merchant_name = find_merchant_by_name(query, unique_merchants)
        if merchant_name:
            outlets = find_all_outlets(merchant_name, data)
            return format_outlet_list(merchant_name, outlets)
        return (
            "I'm sorry, I do not know which merchant's outlets you're looking for. Try:\n"
            "'Old Chang Kee outlets' or 'Where are the Starbucks branches?'"
        )

    # 3. Is X our merchant?
    if is_merchant_query(query):
        merchant_name = find_merchant_by_name(query, unique_merchants)
        if merchant_name:
            return f"Yes! **{merchant_name}** is one of our merchants. Ask me about their deals or outlets!"
        return (
            "I'm sorry, I do not know of that merchant in our programme. "
            "They may not be listed, or try checking the spelling.\n\n"
            "You can also ask: 'Show me food merchants' to browse what's available."
        )

    # 4. Halal-only query (with or without keyword)
    if halal_only:
        search_terms, area_found = extract_search_terms(query)
        matched = list_merchants_by_keyword(search_terms, area_found, data, keyword_index, halal_only=True)
        return format_keyword_list(search_terms, area_found, matched, halal_only=True)

    # 5. Keyword / area search
    search_terms, area_found = extract_search_terms(query)
    if search_terms or area_found:
        matched = list_merchants_by_keyword(search_terms, area_found, data, keyword_index)
        return format_keyword_list(search_terms, area_found, matched)

    # 6. Fallback
    return FALLBACK_PROMPTS


# ── Streamlit UI ──────────────────────────────────────────────────────────────



    
st.title("💬 Merchant Chatbot")
st.caption("Ask me about our merchant partners, deals, and outlet locations!")

# Load data
data, unique_merchants, keyword_index, valid_names, valid_keywords = load_and_process_database()

# Initialise chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant",
        "content": (
            f"Hi there! 👋 I can help you find merchants and deals.\n\n"
            f"We have **{len(unique_merchants)} merchants** in our programme. Try asking:\n"
            "🔍 'Show me food deals' or 'spa merchants'\n"
            "📍 'Restaurants near Orchard' or 'deals in Tampines'\n"
            "🥩 'List me halal food' or 'halal merchants'\n"
            "🏪 'Is 4Fingers our merchant?'\n"
            "📋 'Old Chang Kee outlets'"
        )
    })

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Handle user input
if prompt := st.chat_input("Ask me about merchants, deals, or locations..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Looking that up..."):
            # Build context from last 5 messages (excluding the current one)
            recent = st.session_state.messages[:-1][-5:]
            context_text = " ".join(
                m["content"] for m in recent if m["role"] == "user"
            )
            # Merge context + current prompt for richer query resolution
            enriched_query = f"{context_text} {prompt}".strip() if context_text else prompt
            response = handle_user_query(enriched_query, data, unique_merchants, keyword_index)
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
})
