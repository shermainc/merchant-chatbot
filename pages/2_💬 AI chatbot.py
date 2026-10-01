import streamlit as st
import pandas as pd
import re
from helper_functions.llm import get_completion, get_completion_by_messages, count_tokens
from helper_functions.utility import check_password

if not check_password():
    st.stop()

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Merchant Chatbot", page_icon="🛍️")
st.title("🛍️ Merchant Chatbot")
st.caption("Ask me about our merchants, deals, and locations!")

st.markdown("""
<style>
[data-testid="stChatMessage"] { max-width: 100% !important; }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
FALLBACK_PROMPTS = (
    "I do not know the answer to that. You can try asking me:\n"
    "- *What merchants are available?*\n"
    "- *Show me food merchants in Orchard*\n"
    "- *Is Old Chang Kee our merchant?*\n"
    "- *List halal merchants near Tampines*"
)

MULTI_WORD_PHRASES = [
    "bubble tea", "ice cream", "escape room", "hot pot", "hot dogs",
    "fried chicken", "fish and chips", "dim sum", "char kway teow",
    "bak kut teh", "nasi lemak", "laksa", "chicken rice",
    "north east", "north west",
]

AREA_KEYWORDS = {
    # Central
    "orchard", "somerset", "dhoby ghaut", "city hall", "raffles", "marina",
    "tanjong pagar", "chinatown", "outram", "tiong bahru", "redhill",
    "queenstown", "commonwealth", "buona vista", "holland", "farrer road",
    "botanic gardens", "stevens", "newton", "novena", "toa payoh", "braddell",
    "bishan", "marymount", "caldecott", "bras basah", "bugis", "rochor",
    "little india", "lavender", "kallang", "aljunied", "geylang", "paya lebar",
    "macpherson", "tai seng", "potong pasir", "woodleigh", "serangoon",
    "whampoa", "bendemeer", "boon keng", "farrer park", "dhoby",
    # North
    "yishun", "khatib", "yio chu kang", "ang mo kio", "amk", "sembawang",
    "canberra", "admiralty", "woodlands", "marsiling", "kranji",
    # North East
    "punggol", "sengkang", "buangkok", "hougang", "kovan", "serangoon north",
    "compassvale", "rivervale", "fernvale", "northshore",
    # East
    "tampines", "simei", "tanah merah", "bedok", "kembangan", "eunos",
    "changi", "expo", "pasir ris", "loyang", "upper changi",
    # West
    "jurong", "boon lay", "lakeside", "chinese garden", "clementi",
    "dover", "one-north", "one north", "kent ridge", "haw par villa",
    "bukit panjang", "choa chu kang", "yew tee", "bukit batok",
    "bukit gombak", "hillview", "beauty world", "king albert park",
    "sixth avenue", "tan kah kee",
    # South
    "harbourfront", "vivocity", "sentosa", "labrador park",
    "pasir panjang", "west coast", "telok blangah",
}

SG_REGIONS = {
    "central": [
        "orchard", "somerset", "dhoby ghaut", "city hall", "raffles", "marina",
        "tanjong pagar", "chinatown", "outram", "tiong bahru", "redhill",
        "queenstown", "commonwealth", "buona vista", "holland", "farrer road",
        "botanic gardens", "stevens", "newton", "novena", "toa payoh", "braddell",
        "bishan", "marymount", "caldecott", "bras basah", "bugis", "rochor",
        "little india", "lavender", "kallang", "aljunied", "geylang", "paya lebar",
        "macpherson", "tai seng", "potong pasir", "woodleigh", "serangoon",
        "whampoa", "bendemeer", "boon keng", "farrer park", "dhoby",
    ],
    "north": [
        "yishun", "khatib", "yio chu kang", "ang mo kio", "amk", "sembawang",
        "canberra", "admiralty", "woodlands", "marsiling", "kranji",
    ],
    "north east": [
        "punggol", "sengkang", "buangkok", "hougang", "kovan", "serangoon north",
        "compassvale", "rivervale", "fernvale", "northshore",
    ],
    "east": [
        "tampines", "simei", "tanah merah", "bedok", "kembangan", "eunos",
        "changi", "expo", "pasir ris", "loyang", "upper changi",
    ],
    "south": [
        "harbourfront", "vivocity", "sentosa", "labrador park",
        "pasir panjang", "west coast", "telok blangah",
    ],
    "west": [
        "jurong", "boon lay", "lakeside", "chinese garden", "clementi",
        "dover", "one-north", "one north", "kent ridge", "haw par villa",
        "bukit panjang", "choa chu kang", "yew tee", "bukit batok",
        "bukit gombak", "hillview", "beauty world", "king albert park",
        "sixth avenue", "tan kah kee",
    ],
}

POSTAL_DISTRICT_REGION = {
    # Central
    "01": "central", "02": "central", "03": "central", "04": "central",
    "05": "central", "06": "central", "07": "central", "08": "central",
    "09": "central", "10": "central", "11": "central", "12": "central",
    "13": "central", "14": "central", "15": "central", "16": "central",
    "17": "central", "18": "central", "19": "central", "20": "central",
    "21": "central", "22": "central", "23": "central",
    # South
    "24": "south", "25": "south", "26": "south", "27": "south",
    "28": "south", "29": "south", "30": "south",
    "31": "south", "32": "south", "33": "south",
    # East
    "34": "east", "35": "east", "36": "east", "37": "east",
    "38": "east", "39": "east", "40": "east", "41": "east",
    "42": "east", "43": "east", "44": "east", "45": "east",
    "46": "east", "47": "east", "48": "east",
    "49": "east", "50": "east", "51": "east", "52": "east",
    # North East
    "53": "north east", "54": "north east", "55": "north east",
    "56": "north east", "57": "north east",
    "79": "north east", "80": "north east",
    "81": "north east", "82": "north east", "83": "north east", "84": "north east",
    # West
    "60": "west", "61": "west", "62": "west", "63": "west", "64": "west",
    "65": "west", "66": "west", "67": "west", "68": "west", "69": "west",
    "70": "west", "71": "west",
    # North
    "72": "north", "73": "north", "74": "north", "75": "north", "76": "north",
    "77": "north", "78": "north",
}

REGION_EMOJI = {
    "central": "🏙️ Central",
    "north": "🧭 North",
    "north east": "🧭 North East",
    "east": "🌅 East",
    "west": "🌇 West",
    "south": "⚓ South",
    "other": "📍 Other",
}

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
    "these", "those", "am", "any", "show", "find", "get", "give", "tell",
    "list", "near", "around", "want", "looking", "look", "like", "know",
    "there", "here", "where", "when", "how", "all", "some", "no", "if",
    "merchant", "merchants", "deal", "deals", "outlet", "outlets",
    "store", "stores", "shop", "shops", "available", "singapore",
}

# ── CSV loading ───────────────────────────────────────────────────────────────
from datetime import datetime

def is_deal_valid(row):
    today = datetime.today()
    for col in ["startDate", "endDate"]:
        val = str(row.get(col, "")).strip()
        if not val:
            return True
        for fmt in ["%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d"]:
            try:
                datetime.strptime(val, fmt)
                break
            except ValueError:
                continue
    end_val = str(row.get("endDate", "")).strip()
    if not end_val:
        return True
    for fmt in ["%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d"]:
        try:
            end_date = datetime.strptime(end_val, fmt)
            return end_date >= today
        except ValueError:
            continue
    return True

@st.cache_data
def load_data():
    df = pd.read_csv("pages/merchants.csv", dtype=str)
    df.columns = df.columns.str.strip()
    df = df.fillna("")
    df = df[df.apply(is_deal_valid, axis=1)].reset_index(drop=True)
    return df

@st.cache_data
def build_keyword_index(_df):
    index = {}
    for i, row in _df.iterrows():
        kw_field = str(row.get("Keywords", "")).lower()
        desc_field = str(row.get("description", "")).lower()
        addr_field = str(row.get("address", "")).lower()
        tokens = set()
        for field in [kw_field, desc_field, addr_field]:
            for phrase in MULTI_WORD_PHRASES:
                if phrase in field:
                    tokens.add(phrase)
            for word in re.split(r"[,\s]+", field):
                word = word.strip().lower()
                if word and word not in STOPWORDS:
                    tokens.add(word)
        for token in tokens:
            index.setdefault(token, []).append(i)
    return index

df = load_data()
keyword_index = build_keyword_index(df)
unique_merchants = sorted(df["name"].dropna().unique().tolist())

# ── Helper functions ──────────────────────────────────────────────────────────

def format_description(desc):
    if not desc:
        return ""
    lines = [l.strip() for l in desc.splitlines() if l.strip()]
    if len(lines) <= 1:
        return desc
    result = [f"**{lines[0]}**"]
    for line in lines[1:]:
        result.append(line)
    return "  \n   ".join(result)

def get_region_for_address(address, postal=""):
    addr_lower = address.lower()

    # 1. Keyword matching — South checked before West to avoid VivoCity/Harbourfront clash
    region_order = ["central", "north", "north east", "east", "south", "west"]
    for region in region_order:
        areas = SG_REGIONS.get(region, [])
        if any(area in addr_lower for area in areas):
            return region

    # 2. Postal code fallback — use postalC column value directly
    code = postal.strip() if postal else ""
    if not code:
        m = re.search(r"S\((\d{6})\)|(?<!\d)(\d{6})(?!\d)", address)
        if m:
            code = m.group(1) or m.group(2)
    if code and len(code) >= 2:
        district = code[:2]
        if district in POSTAL_DISTRICT_REGION:
            return POSTAL_DISTRICT_REGION[district]

    return "other"

def extract_search_terms(query):
    q = query.lower()
    found_phrases = []
    for phrase in MULTI_WORD_PHRASES:
        if phrase in q:
            found_phrases.append(phrase)
            q = q.replace(phrase, " ")

    words = re.split(r"[,\s]+", q)
    words = [w.strip() for w in words if w.strip() and w not in STOPWORDS]

    area_found = []
    non_area_terms = []
    for w in words:
        if w in AREA_KEYWORDS:
            area_found.append(w)
        else:
            non_area_terms.append(w)

    for phrase in found_phrases:
        parts = phrase.split()
        if all(p in AREA_KEYWORDS for p in parts):
            area_found.append(phrase)
        else:
            non_area_terms.append(phrase)

    # Expand region names
    region_map = {
        "central": SG_REGIONS["central"],
        "north": SG_REGIONS["north"],
        "south": SG_REGIONS["south"],
        "east": SG_REGIONS["east"],
        "west": SG_REGIONS["west"],
        "northeast": SG_REGIONS["north east"],
        "north east": SG_REGIONS["north east"],
    }
    expanded_areas = []
    for a in area_found:
        if a in region_map:
            expanded_areas.extend(region_map[a])
        else:
            expanded_areas.append(a)

    return non_area_terms, expanded_areas

def is_halal_query(query):
    return "halal" in query.lower()

def find_merchant_by_name(name):
    name_lower = name.lower()
    matches = df[df["name"].str.lower() == name_lower]
    return matches

def find_all_outlets(name):
    name_lower = name.lower()
    return df[df["name"].str.lower() == name_lower]

def count_all_outlets(name):
    return len(find_all_outlets(name))

def list_merchants_by_keyword(keywords, areas, halal_only=False):
    candidate_sets = []

    if keywords:
        for kw in keywords:
            matched = set()
            for idx_kw, indices in keyword_index.items():
                if kw in idx_kw or idx_kw in kw:
                    matched.update(indices)
            candidate_sets.append(matched)
        if candidate_sets:
            combined = candidate_sets[0]
            for s in candidate_sets[1:]:
                combined = combined.intersection(s)
        else:
            combined = set()
    else:
        combined = set(df.index.tolist())

    if areas:
        area_indices = set()
        for area in areas:
            for idx_kw, indices in keyword_index.items():
                if area in idx_kw or idx_kw in area:
                    area_indices.update(indices)
        combined = combined.intersection(area_indices)

    results = df.loc[list(combined)]

    if halal_only:
        results = results[results["Halal"].str.strip().str.lower() == "yes"]

    seen_names = set()
    unique_results = []
    for _, row in results.iterrows():
        name = row["name"]
        if name not in seen_names:
            seen_names.add(name)
            unique_results.append(row)

    unique_results.sort(key=lambda r: r["name"])
    return unique_results[:10], len(unique_results)

def format_keyword_list(results, total_count):
    if not results:
        return FALLBACK_PROMPTS

    lines = [f"Here are merchants matching your search ({min(len(results), 10)} shown):\n"]
    for row in results:
        name = row["name"]
        address = row.get("address", "")
        postal = row.get("postalC", "")
        postal_str = f" S({postal})" if postal else ""
        desc = format_description(row.get("description", ""))
        outlet_count = count_all_outlets(name)

        lines.append(f"**{name}**")
        lines.append(f"📍 {address}{postal_str}")
        if desc:
            lines.append(f"🎁 {desc}")
        if outlet_count > 1:
            lines.append("")
            lines.append(
                f"ℹ️ This merchant has {outlet_count} outlets in total. "
                f"Ask me which area you're looking at, or try '*{name} outlets*' to see all locations."
            )
        lines.append("")

    if total_count == 10:
        lines.append("_Showing first 10 results. Try a more specific search to narrow down!_")

    return "\n".join(lines)

def format_outlet_list(outlets_df, merchant_name, area_filter=None):
    if area_filter:
        filtered = outlets_df[
            outlets_df["address"].str.lower().str.contains(area_filter.lower(), na=False)
        ]
        if filtered.empty:
            note = f"_(No outlets found specifically in {area_filter.title()}. Showing all outlets instead.)_\n\n"
            filtered = outlets_df
        else:
            note = ""
            outlets_df = filtered
    else:
        note = ""

    total = len(outlets_df)
    lines = [f"Here are the outlets for **{merchant_name}** ({total} found):\n"]
    if note:
        lines.append(note)

    # Check if all outlets share the same description
    descs = outlets_df["description"].str.strip().unique()
    shared_desc = descs[0] if len(descs) == 1 and descs[0] else None
    if shared_desc:
        lines.append(f"🎁 {format_description(shared_desc)}\n")

    # Group by region
    region_buckets = {}
    for _, row in outlets_df.iterrows():
        region = get_region_for_address(row.get("address", ""), row.get("postalC", ""))
        region_buckets.setdefault(region, []).append(row)

    region_order = ["central", "north", "north east", "east", "west", "south", "other"]
    for region in region_order:
        rows = region_buckets.get(region, [])
        if not rows:
            continue
        lines.append(f"\n{REGION_EMOJI[region]}")
        for row in rows:
            address = row.get("address", "")
            postal = row.get("postalC", "")
            postal_str = f" S({postal})" if postal else ""
            desc = row.get("description", "").strip()
            lines.append(f"• {address}{postal_str}")
            if desc and not shared_desc:
                lines.append(f"  🎁 {format_description(desc)}")

    return "\n".join(lines)

def safe_llm_call(prompt, context):
    try:
        response = get_completion(prompt)
        return response
    except Exception as e:
        err = str(e).lower()
        if "rate" in err or "token" in err or "limit" in err or "quota" in err:
            return FALLBACK_PROMPTS
        return FALLBACK_PROMPTS

def handle_user_query(query, last_context=None):
    q = query.lower().strip()
    halal = is_halal_query(q)

    # ── List all merchants ────────────────────────────────────────────────────
    if re.search(r"\b(list|show|all)\b.*\bmerchants?\b", q) and not any(
        w in q for w in AREA_KEYWORDS
    ) and not halal:
        sample = unique_merchants[:10]
        result = "Here are some of our merchants (A–Z):\n\n"
        result += "\n".join(f"- {m}" for m in sample)
        result += "\n\n_Specify a region or category to narrow down, e.g. 'food merchants in Tampines'._"
        return result, {"keywords": [], "areas": []}

    # ── Outlet listing ────────────────────────────────────────────────────────
    outlet_match = re.search(
        r"(.+?)\s+outlets?(?:\s+in\s+(.+))?$", q, re.IGNORECASE
    )
    if outlet_match:
        name_candidate = outlet_match.group(1).strip()
        area_filter = outlet_match.group(2).strip() if outlet_match.group(2) else None
        matched = find_all_outlets(name_candidate)
        if not matched.empty:
            return format_outlet_list(matched, matched.iloc[0]["name"], area_filter), {"keywords": [], "areas": []}

    # ── Merchant name check ───────────────────────────────────────────────────
    for name in unique_merchants:
        if name.lower() in q:
            rows = find_merchant_by_name(name)
            if not rows.empty:
                if len(rows) == 1:
                    row = rows.iloc[0]
                    address = row.get("address", "")
                    postal = row.get("postalC", "")
                    postal_str = f" S({postal})" if postal else ""
                    desc = format_description(row.get("description", ""))
                    resp = f"✅ Yes, **{name}** is one of our merchants!\n\n📍 {address}{postal_str}"
                    if desc:
                        resp += f"\n\n🎁 {desc}"
                    return resp, {"keywords": [], "areas": []}
                else:
                    return (
                        f"✅ Yes, **{name}** is one of our merchants! "
                        f"They have **{len(rows)} outlets** across Singapore. "
                        f"Which area are you looking at? Or try '*{name} outlets*' to see all locations.",
                        {"keywords": [], "areas": []},
                    )

    # ── Keyword / area search ─────────────────────────────────────────────────
    keywords, areas = extract_search_terms(q)

    if not keywords and not areas and last_context:
        keywords = last_context.get("keywords", [])
        areas = last_context.get("areas", [])

    if keywords or areas or halal:
        results, total = list_merchants_by_keyword(keywords, areas, halal_only=halal)
        if results:
            return format_keyword_list(results, total), {"keywords": keywords, "areas": areas}
        else:
            return FALLBACK_PROMPTS, {"keywords": keywords, "areas": areas}

    # ── LLM fallback ──────────────────────────────────────────────────────────
    merchant_names = ", ".join(unique_merchants[:50])
    summary = f"We have the following merchants: {merchant_names}."
    if count_tokens(summary) > 3000:
        summary = f"We have the following merchants: {', '.join(unique_merchants[:15])}."

    prompt = (
        f"You are a helpful merchant chatbot. Answer based only on this information:\n\n"
        f"{summary}\n\n"
        f"User question: {query}\n\n"
        f"If you do not know, say 'I do not know'."
    )
    return safe_llm_call(prompt, summary), {"keywords": [], "areas": []}


# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_search_context" not in st.session_state:
    st.session_state.last_search_context = None

# ── Chat display ──────────────────────────────────────────────────────────────
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ── Chat input ────────────────────────────────────────────────────────────────
if prompt := st.chat_input("Ask me about our merchants..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response, new_context = handle_user_query(
                prompt, last_context=st.session_state.last_search_context
            )
            st.session_state.last_search_context = new_context
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
