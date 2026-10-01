import streamlit as st
import pandas as pd
import re
import os
from datetime import datetime
from helper_functions.llm import get_completion, get_completion_by_messages, count_tokens
from helper_functions.utility import check_password

if not check_password():
    st.stop()

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

# ── Multi-word keyword phrases (matched before word-splitting) ────────────────
MULTI_WORD_PHRASES = [
    "bubble tea", "boba tea", "milk tea", "ice cream", "escape room",
    "hot pot", "hot dog", "fried chicken", "roast duck", "dim sum",
    "char kway teow", "nasi lemak", "chicken rice", "fish and chips",
    "beauty salon", "nail art", "hair salon", "hair cut", "hair color",
    "personal trainer", "gym membership", "yoga class", "spin class",
    "board game", "video game", "laser tag", "go kart", "mini golf",
    "fast food", "fine dining", "buffet restaurant", "food court",
    "coffee shop", "cake shop", "bread bakery", "pastry shop",
    "sports wear", "sports equipment", "outdoor gear",
]

# ── Singapore area keywords ───────────────────────────────────────────────────
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
    "tanjong pagar", "sentosa", "punggol", "sengkang",
    "buangkok", "compassvale", "rivervale", "fernvale", "anchorvale",
    "balestier", "geylang", "ubi", "macpherson", "tai seng", "bartley",
    "upper changi", "expo", "changi", "loyang", "whampoa",
}

# ── Region → list of area keywords ───────────────────────────────────────────
SG_REGIONS = {
    "central": [
        "orchard", "somerset", "dhoby ghaut", "city hall", "raffles place",
        "marina bay", "bugis", "lavender", "kallang", "little india", "rochor",
        "dhoby", "novena", "newton", "stevens", "bishan", "braddell", "toa payoh",
        "boon keng", "farrer park", "potong pasir", "woodleigh", "balestier",
        "queenstown", "redhill", "tiong bahru", "outram", "chinatown",
        "clarke quay", "fort canning", "bras basah", "esplanade", "promenade",
        "bayfront", "downtown", "telok ayer", "tanjong pagar", "geylang",
        "ubi", "macpherson", "tai seng", "bartley", "botanic gardens",
        "caldecott", "marymount", "botanic", "holland village", "whampoa",
    ],
    "north": [
        "yishun", "khatib", "yio chu kang", "admiralty", "sembawang",
        "canberra", "woodlands", "marsiling", "kranji",
    ],
    "north east": [
        "sengkang", "punggol", "buangkok", "compassvale", "rivervale",
        "fernvale", "anchorvale", "hougang", "serangoon", "kovan",
        "ang mo kio",
    ],
    "northeast": [
        "sengkang", "punggol", "buangkok", "compassvale", "rivervale",
        "fernvale", "anchorvale", "hougang", "serangoon", "kovan",
        "ang mo kio",
    ],
    "east": [
        "tampines", "bedok", "pasir ris", "simei", "tanah merah",
        "kembangan", "eunos", "paya lebar", "aljunied", "upper changi",
        "expo", "changi", "loyang",
    ],
    "west": [
        "jurong", "boon lay", "lakeside", "chinese garden", "clementi",
        "dover", "buona vista", "one-north", "one north", "kent ridge",
        "haw par villa", "pasir panjang", "labrador park", "harbourfront",
        "vivocity", "bukit panjang", "choa chu kang", "yew tee",
        "bukit batok", "bukit gombak", "hillview", "beauty world",
        "king albert park", "sixth avenue", "tan kah kee",
    ],
    "south": [
        "harbourfront", "vivocity", "labrador park", "sentosa",
        "haw par villa", "pasir panjang", "telok ayer", "tanjong pagar",
        "chinatown", "outram", "tiong bahru", "redhill",
    ],
}

# ── Region label for display ──────────────────────────────────────────────────
REGION_DISPLAY = {
    "central": "🏙️ Central",
    "north": "🧭 North",
    "north east": "🧭 North East",
    "east": "🌅 East",
    "west": "🌇 West",
    "south": "⚓ South",
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

# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data
def load_and_process_database():
    try:
        df = pd.read_csv(CSV_FILE_PATH)
        df.columns = df.columns.str.strip()
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].fillna("").astype(str).str.strip()

        valid_rows = [row for row in df.to_dict(orient="records") if is_deal_valid(row)]
        data = valid_rows

        seen_names = set()
        unique_merchants = []
        for row in data:
            name = row.get("name", "").strip()
            if name and name not in seen_names:
                seen_names.add(name)
                unique_merchants.append(name)
        unique_merchants.sort()

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
    return True


# ── Assign a region label to an address string ───────────────────────────────
def get_region_for_address(address):
    addr_lower = address.lower()
    for region, areas in SG_REGIONS.items():
        if region in ("northeast",):  # skip duplicate alias
            continue
        if any(area in addr_lower for area in areas):
            return region
    return "other"


# ── Search helpers ────────────────────────────────────────────────────────────
def extract_search_terms(query):
    q_lower = query.lower()
    areas = []

    # Detect region names → expand to area lists
    for region, sub_areas in SG_REGIONS.items():
        if region in q_lower:
            for a in sub_areas:
                if a not in areas:
                    areas.append(a)

    # Detect specific area keywords
    for area in sorted(AREA_KEYWORDS, key=len, reverse=True):
        if area in q_lower and area not in areas:
            areas.append(area)

    # ── Multi-word phrase detection (before splitting) ────────────────────────
    remaining = q_lower
    matched_phrases = []
    for phrase in sorted(MULTI_WORD_PHRASES, key=len, reverse=True):
        if phrase in remaining:
            matched_phrases.append(phrase)
            remaining = remaining.replace(phrase, " ")  # remove matched phrase from remaining

    # ── Single-word keyword extraction from what's left ───────────────────────
    area_words = set(w for a in areas for w in a.split())
    single_words = [
        w for w in re.findall(r"\b\w+\b", remaining)
        if w not in STOPWORDS
        and w not in area_words
        and w not in SG_REGIONS
        and len(w) > 2
    ]

    keywords = matched_phrases + single_words
    return keywords, areas


def is_halal_query(query):
    return "halal" in query.lower()


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
            if area_found and not any(area in row.get("address", "").lower() for area in area_found):
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
        matched = []
        seen_names = set()
        for row in data:
            if area_found and not any(area in row.get("address", "").lower() for area in area_found):
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


# ── Count total outlets for a merchant ───────────────────────────────────────
def count_all_outlets(merchant_name, data):
    return sum(1 for row in data if row.get("name", "").strip() == merchant_name)


# ── Formatters ────────────────────────────────────────────────────────────────
def format_outlet_list(merchant_name, outlets, area_filter=None):
    if not outlets:
        return (
            f"I'm sorry, I couldn't find any outlets for **{merchant_name}**. "
            "I do not know if they have other locations not listed in our system."
        )

    display_outlets = outlets
    area_note = ""

    if area_filter:
        filtered = [
            row for row in outlets
            if any(area in row.get("address", "").lower() for area in area_filter)
        ]
        if filtered:
            display_outlets = filtered
        else:
            area_note = "_No outlets found in that area — showing all outlets instead._\n\n"

    # ── Group outlets by region ───────────────────────────────────────────────
    region_order = ["central", "north", "north east", "east", "west", "south", "other"]
    grouped = {r: [] for r in region_order}

    for row in display_outlets:
        region = get_region_for_address(row.get("address", ""))
        grouped[region].append(row)

    lines = [f"{area_note}Here are the outlets for **{merchant_name}** ({len(display_outlets)} found):\n"]

    for region in region_order:
        rows_in_region = grouped[region]
        if not rows_in_region:
            continue
        label = REGION_DISPLAY.get(region, "📍 Other")
        lines.append(f"**{label}**")
        for row in rows_in_region:
            address = row.get("address", "N/A")
            postal = row.get("postalC", "")
            postal_str = f" S({postal})" if postal else ""
            desc = row.get("description", "")
            lines.append(f"• {address}{postal_str}")
            if desc:
                lines.append(f"  🎁 {desc}")
        lines.append("")

    return "\n".join(lines)


def format_keyword_list(matched_rows, data, halal_only=False):
    """
    Lists one address per merchant (the first in the CSV).
    Adds a disclaimer if the merchant has more outlets.
    """
    if not matched_rows:
        return (
            "I'm sorry, I do not know of any active merchants matching your search in our programme.\n\n"
            "Here are some things you can try:\n\n"
            "🔍 **Search by category:** 'food', 'spa', 'gym', 'retail', 'entertainment'\n"
            "📍 **Search by location:** 'Orchard', 'Tampines', 'Bugis', 'Jurong'\n"
            "🥩 **Filter by Halal:** 'halal food', 'halal merchants'\n"
            "🏪 **Find a specific merchant:** 'Is 4Fingers our merchant?'\n"
            "📋 **See outlets:** 'Old Chang Kee outlets'\n\n"
            "_Try narrowing down with a keyword or location!_"
        )

    prefix = "Halal merchants" if halal_only else "Here are some merchants for you"
    lines = [f"{prefix} (showing top {len(matched_rows)}, A–Z):\n"]

    for i, row in enumerate(matched_rows, 1):
        name = row.get("name", "N/A")
        address = row.get("address", "N/A")
        postal = row.get("postalC", "")
        postal_str = f" S({postal})" if postal else ""
        desc = row.get("description", "")

        # Count total outlets for this merchant
        total_outlets = count_all_outlets(name, data)

        lines.append(f"**{i}. {name}**")
        lines.append(f"   📍 {address}{postal_str}")
        if desc:
            lines.append(f"   🎁 {desc}")

        # Disclaimer if merchant has more than 1 outlet
        if total_outlets > 1:
            lines.append(
                f"   ℹ️ _This merchant has **{total_outlets} outlets** in total. "
                f"Ask me which area you're looking at, or try '{name} outlets' to see all locations._"
            )

        lines.append("")

    if len(matched_rows) == 10:
        lines.append("_Showing first 10 results. Try a more specific search to narrow down!_")

    return "\n".join(lines)


# ── LLM wrapper ───────────────────────────────────────────────────────────────
def safe_llm_call(prompt_text):
    try:
        return get_completion(prompt_text)
    except Exception as e:
        err = str(e).lower()
        if any(k in err for k in ["ratelimit", "rate_limit", "429", "token", "context_length", "maximum context"]):
            return FALLBACK_PROMPTS
        raise


# ── Main query handler ────────────────────────────────────────────────────────
def handle_user_query(query, data, unique_merchants, keyword_index, last_context=None):
    halal_only = is_halal_query(query)

    # Reset context on clearly new/unrelated query types
    if is_list_all_query(query) or is_outlet_query(query) or is_merchant_query(query):
        st.session_state.last_search_context = {"keywords": [], "areas": []}

    # 1. List all merchants → show first 10 A–Z + region prompt
    if is_list_all_query(query) and not halal_only:
        total = len(unique_merchants)
        first_10 = unique_merchants[:10]
        lines = [
            f"We have **{total} merchants** in our programme. Here are the first 10 (A–Z):\n"
        ]
        for i, name in enumerate(first_10, 1):
            lines.append(f"**{i}. {name}**")
        lines.append(
            f"\n_Showing 10 of {total}. Want to see more? Try:_\n"
            "- 🗺️ A region: *'merchants in the East'*, *'Central merchants'*, *'North merchants'*\n"
            "- 📍 A specific area: *'merchants near Whampoa'*, *'deals in Tampines'*\n"
            "- 🔍 A category: *'food merchants'*, *'spa deals'*"
        )
        return "\n".join(lines)

    # 2. Outlet query
    if is_outlet_query(query):
        merchant_name = find_merchant_by_name(query, unique_merchants)
        if merchant_name:
            outlets = find_all_outlets(merchant_name, data)
            _, area_filter = extract_search_terms(query)
            return format_outlet_list(merchant_name, outlets, area_filter=area_filter if area_filter else None)
        return (
            "I'm sorry, I do not know which merchant's outlets you're looking for. Try:\n"
            "'Old Chang Kee outlets' or 'Where are the Starbucks branches?'"
        )

    # 3. Is X our merchant?
    if is_merchant_query(query):
        merchant_name = find_merchant_by_name(query, unique_merchants)
        if merchant_name:
            rows = [row for row in data if row.get("name", "").strip() == merchant_name]
            desc_text = ""
            if rows:
                desc = rows[0].get("description", "").strip()
                if desc:
                    desc_text = f"\n\n🎁 {desc}"
            if len(rows) == 1:
                addr = rows[0].get("address", "").strip()
                postal = rows[0].get("postalC", "").strip()
                postal_str = f" S({postal})" if postal else ""
                return (
                    f"Yes! **{merchant_name}** is one of our merchants.\n\n"
                    f"📍 {addr}{postal_str}{desc_text}\n\n"
                    f"Ask me about their deals or outlets!"
                )
            else:
                return (
                    f"Yes! **{merchant_name}** is one of our merchants and has **{len(rows)} outlets**.{desc_text}\n\n"
                    f"Which area are you looking at? For example:\n"
                    f"- 🗺️ A region: *Central, North, South, East, West, North East*\n"
                    f"- 📍 A specific area: *Raffles Place, Tampines, Orchard, Jurong...*\n\n"
                    f"Or ask: *'{merchant_name} outlets'* to see all locations."
                )
        return (
            "I'm sorry, I do not know of that merchant in our programme. "
            "They may not be listed, or try checking the spelling.\n\n"
            "You can also ask: 'Show me food merchants' to browse what's available."
        )

    # 4. Halal-only query
    if halal_only:
        search_terms, area_found = extract_search_terms(query)
        if not search_terms and not area_found and last_context:
            search_terms = last_context.get("keywords", [])
            area_found = last_context.get("areas", [])
        matched = list_merchants_by_keyword(search_terms, area_found, data, keyword_index, halal_only=True)
        st.session_state.last_search_context = {"keywords": search_terms, "areas": area_found}
        return format_keyword_list(matched, data, halal_only=True)

    # 5. Keyword / area search
    search_terms, area_found = extract_search_terms(query)

    if not search_terms and not area_found and last_context:
        search_terms = last_context.get("keywords", [])
        area_found = last_context.get("areas", [])

    if search_terms or area_found:
        matched = list_merchants_by_keyword(search_terms, area_found, data, keyword_index)
        st.session_state.last_search_context = {"keywords": search_terms, "areas": area_found}
        return format_keyword_list(matched, data)

    # 6. Fallback → LLM
    merchant_summary = "\n".join(
        f"- {r['name']}: {r.get('description', '')}" for r in data[:30]
    )
    if count_tokens(merchant_summary) > 3000:
        merchant_summary = "\n".join(
            f"- {r['name']}: {r.get('description', '')}" for r in data[:15]
        )

    prompt = (
        f"You are a helpful assistant for a merchant rewards programme in Singapore.\n"
        f"Here are some active merchants and their deals:\n{merchant_summary}\n\n"
        f"User asked: {query}\n\n"
        f"Answer helpfully and concisely. If the answer is not in the merchant list, "
        f"say you do not know and suggest they try searching by category or location."
    )
    return safe_llm_call(prompt)


# ── Streamlit UI ──────────────────────────────────────────────────────────────
st.title("💬 Merchant Chatbot")
st.caption("Ask me about our merchant partners, deals, and outlet locations!")

st.markdown("""
<style>
[data-testid="stChatMessage"] { max-width: 100% !important; }
[data-testid="stMarkdownContainer"] p { white-space: pre-wrap; word-break: break-word; }
</style>
""", unsafe_allow_html=True)

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

# Initialise search context memory
if "last_search_context" not in st.session_state:
    st.session_state.last_search_context = {"keywords": [], "areas": []}

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
            response = handle_user_query(
                prompt, data, unique_merchants, keyword_index,
                last_context=st.session_state.last_search_context
            )
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
