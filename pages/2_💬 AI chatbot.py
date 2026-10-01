import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import re
from datetime import datetime
from difflib import SequenceMatcher
from helper_functions.utility import check_password
from helper_functions.llm import get_completion, get_completion_by_messages, count_tokens

# ── Password protection ──────────────────────────────────────────────────────
if not check_password():
    st.stop()

# ── Page config ──────────────────────────────────────────────────────────────
st.title("💬 Merchant AI Chatbot")
st.caption("Ask me about our merchant partners — deals, locations, categories and more!")

st.markdown("""
<style>
[data-testid="stChatMessage"] .stMarkdown p {
    white-space: normal !important;
    word-break: break-word !important;
}
</style>
""", unsafe_allow_html=True)

# ── Constants ────────────────────────────────────────────────────────────────
MAX_LLM_CONTEXT_TOKENS = 1500
FALLBACK_PROMPTS = "I'm sorry, I do not know the answer to that."

WELCOME_MESSAGE = """
👋 Hi! I'm your Merchant AI Assistant. Here's what I can help you with:

- 🔍 **Find merchants by category or keyword**
  *e.g. "bubble tea", "spa"*

- 📍 **Find merchants by area or region**
  *e.g. "food in Tampines"*

- 🏪 **Check if a merchant is in our list**
  *e.g. "Is Playmade our merchant?"*

- 📋 **See all outlets for a merchant**
  *e.g. "Old Chang Kee outlets", "Playmade outlets in the east"*

- 📜 **List all merchants**
  *e.g. "List all merchants"*

- ☪️ **Filter by Halal**
  *e.g. "list halal merchants"*

What would you like to know?
"""

MULTI_WORD_PHRASES = [
    "bubble tea", "ice cream", "escape room", "board game", "fast food",
    "fried chicken", "dim sum", "hot pot", "hotpot", "milk tea",
    "frozen yogurt", "frozen yoghurt", "fish and chips", "fish & chips",
    "chicken rice", "char kway teow", "bak kut teh", "nasi lemak",
    "roti prata", "laksa", "wanton mee", "wonton mee",
]

AREA_KEYWORDS = {
    # Central
    "orchard", "somerset", "dhoby ghaut", "city hall", "raffles place",
    "marina bay", "marina", "tanjong pagar", "chinatown", "bugis",
    "bras basah", "clarke quay", "robertson quay", "river valley",
    "novena", "newton", "bishan", "toa payoh", "braddell", "marymount",
    "caldecott", "ang mo kio", "serangoon", "potong pasir", "boon keng",
    "farrer park", "little india", "rochor", "dhoby", "bendemeer",
    "geylang", "aljunied", "paya lebar", "macpherson", "tai seng",
    "whampoa",
    # North
    "woodlands", "admiralty", "sembawang", "canberra", "yishun",
    "khatib", "yio chu kang", "lentor", "springleaf", "upper thomson",
    "thomson", "sin ming", "marymount", "bright hill",
    "punggol", "sengkang", "hougang", "kovan", "serangoon north",
    "buangkok", "rivervale", "compassvale",
    # East
    "tampines", "simei", "tanah merah", "bedok", "kembangan",
    "eunos", "kembangan", "expo", "changi", "pasir ris", "loyang",
    "upper changi", "flora", "downtown east",
    # South
    "harbourfront", "vivocity", "sentosa", "labrador park",
    "pasir panjang", "west coast", "telok blangah",
    # West
    "jurong", "boon lay", "lakeside", "chinese garden", "clementi",
    "dover", "buona vista", "one-north", "one north", "kent ridge",
    "bukit batok", "bukit gombak", "choa chu kang", "yew tee",
    "pioneer", "joo koon", "gul circle", "tuas", "hillview",
    "beauty world", "king albert park", "sixth avenue", "tan kah kee",
    "botanic gardens", "farrer road",
}

SG_REGIONS = {
    "central": [
        "orchard", "somerset", "dhoby ghaut", "city hall", "raffles place",
        "marina bay", "marina", "tanjong pagar", "chinatown", "bugis",
        "bras basah", "clarke quay", "robertson quay", "river valley",
        "novena", "newton", "bishan", "toa payoh", "braddell", "marymount",
        "caldecott", "ang mo kio", "serangoon", "potong pasir", "boon keng",
        "farrer park", "little india", "rochor", "dhoby", "bendemeer",
        "geylang", "aljunied", "paya lebar", "macpherson", "tai seng",
        "whampoa",
    ],
    "north": [
        "woodlands", "admiralty", "sembawang", "canberra", "yishun",
        "khatib", "yio chu kang", "lentor", "springleaf", "upper thomson",
        "thomson", "sin ming", "marymount", "bright hill",
        "punggol", "sengkang", "hougang", "kovan", "serangoon north",
        "buangkok", "rivervale", "compassvale",
    ],
    "east": [
        "tampines", "simei", "tanah merah", "bedok", "kembangan",
        "eunos", "expo", "changi", "pasir ris", "loyang",
        "upper changi", "flora", "downtown east",
    ],
    "south": [
        "harbourfront", "vivocity", "sentosa", "labrador park",
        "pasir panjang", "west coast", "telok blangah",
    ],
    "west": [
        "jurong", "boon lay", "lakeside", "chinese garden", "clementi",
        "dover", "buona vista", "one-north", "one north", "kent ridge",
        "bukit batok", "bukit gombak", "choa chu kang", "yew tee",
        "pioneer", "joo koon", "gul circle", "tuas", "hillview",
        "beauty world", "king albert park", "sixth avenue", "tan kah kee",
        "botanic gardens", "farrer road",
    ],
}

POSTAL_DISTRICT_REGION = {
    **{str(d): "central" for d in [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21]},
    **{str(d): "east"    for d in [14,15,16,17,18]},
    **{str(d): "west"    for d in [22,23,24,25,26,27]},
    **{str(d): "north"   for d in [25,26,27,28]},
    **{str(d): "south"   for d in [9]},
}

STOPWORDS = {
    "a","an","the","is","are","was","were","be","been","being",
    "have","has","had","do","does","did","will","would","could","should",
    "may","might","shall","can","need","dare","ought","used",
    "i","me","my","we","our","you","your","they","their","it","its",
    "this","that","these","those","what","which","who","whom","whose",
    "where","when","why","how","all","any","both","each","few","more",
    "most","other","some","such","no","not","only","same","so","than",
    "too","very","just","but","and","or","if","in","on","at","to",
    "for","of","with","about","against","between","into","through",
    "during","before","after","above","below","from","up","down","out",
    "off","over","under","again","further","then","once","here","there",
    "show","find","get","give","tell","list","look","search","want",
    "need","like","know","see","make","go","take","come","use",
    "merchant","merchants","deal","deals","outlet","outlets","store",
    "stores","shop","shops","near","nearby","around","area","region",
    "singapore","sg","please","thanks","thank","hi","hello","hey",
    "halal",
}

# ── CSV loading ───────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv("pages/merchants.csv")
    df.columns = df.columns.str.strip()
    df = df.fillna("")
    df = df[df.apply(is_deal_valid, axis=1)].reset_index(drop=True)
    return df

def is_deal_valid(row):
    end = str(row.get("endDate", "")).strip()
    if not end:
        return True
    for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(end, fmt) >= datetime.now()
        except ValueError:
            continue
    return True

df = load_data()

# ── Keyword index — Keywords column ONLY ─────────────────────────────────────
@st.cache_data
def build_keyword_index(df):
    index = {}
    for i, row in df.iterrows():
        kw_field = str(row.get("Keywords", "")).lower()
        for token in re.findall(r"[a-z0-9&']+", kw_field):
            index.setdefault(token, []).append(i)
    return index

keyword_index = build_keyword_index(df)

# ── Helpers ───────────────────────────────────────────────────────────────────
def normalise(text):
    text = text.lower().strip()
    text = text.replace("&", "and")
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text

def fuzzy_match_merchant(query, names, threshold=0.82):
    q = normalise(query)
    best_name, best_score = None, 0.0
    for name in names:
        n = normalise(name)
        if n in q or q in n:
            return name
        win = len(n.split())
        q_words = q.split()
        for i in range(max(1, len(q_words) - win + 1)):
            window = " ".join(q_words[i:i+win])
            score = SequenceMatcher(None, window, n).ratio()
            if score > best_score:
                best_score, best_name = score, name
    return best_name if best_score >= threshold else None

def get_unique_merchants(df):
    return df.drop_duplicates(subset="name").sort_values("name").reset_index(drop=True)

def extract_search_terms(query):
    q = query.lower()
    phrases_found = []
    for phrase in MULTI_WORD_PHRASES:
        if phrase in q:
            phrases_found.append(phrase)
            q = q.replace(phrase, " ")
    words = re.findall(r"[a-z0-9&']+", q)
    keywords = [w for w in words if w not in STOPWORDS and len(w) > 1]
    areas = []
    regions = []
    for kw in list(keywords):
        if kw in AREA_KEYWORDS:
            areas.append(kw)
            keywords.remove(kw)
        elif kw in SG_REGIONS:
            regions.append(kw)
            keywords.remove(kw)
    for region in regions:
        areas.extend(SG_REGIONS[region])
    keywords.extend(phrases_found)
    return list(set(keywords)), list(set(areas))

def is_halal_query(query):
    return "halal" in query.lower()

def get_region_for_address(address, postal=""):
    addr_lower = address.lower()
    for region_order in ["central", "north", "east", "south", "west"]:
        for kw in SG_REGIONS[region_order]:
            if kw in addr_lower:
                return region_order
    if postal:
        district = str(postal).strip()[:2].lstrip("0") or str(postal).strip()[:1]
        if district in POSTAL_DISTRICT_REGION:
            return POSTAL_DISTRICT_REGION[district]
    return "other"

def count_all_outlets(name, df):
    return len(df[df["name"].str.lower() == name.lower()])

def is_header_line(line):
    stripped = line.strip()
    return bool(re.match(r'^[A-Z0-9][A-Z0-9\s/&,\-\.\']+:$', stripped)) and len(stripped) > 3

def format_description_lines(raw_desc):
    lines = [l.rstrip() for l in raw_desc.strip().splitlines()]
    result = []
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        if i == 0 or is_header_line(line):
            result.append((True, f"**{line.strip()}**"))
        else:
            result.append((False, line.strip()))
    return result

def detect_outlet_query(query):
    q_norm = normalise(query)
    merchant_names = df["name"].unique().tolist()
    outlet_triggers = ["outlet", "outlets", "store", "stores", "branch", "branches", "location", "locations", "where"]
    if not any(t in q_norm for t in outlet_triggers):
        return None, None
    matched = fuzzy_match_merchant(query, merchant_names)
    if not matched:
        return None, None
    area_filter = None
    keywords, areas = extract_search_terms(query)
    if areas:
        area_filter = areas[0]
    return matched, area_filter

def find_all_outlets(merchant_name, df):
    return df[df["name"].str.lower() == merchant_name.lower()].reset_index(drop=True)

def format_outlet_list(merchant_name, outlets_df, area_filter=None):
    if area_filter:
        filtered = outlets_df[
            outlets_df["address"].str.lower().str.contains(area_filter, na=False)
        ]
        if filtered.empty:
            lines = [
                f"I do not know of any **{merchant_name}** outlets in **{area_filter.title()}**.",
                f"Here are all {len(outlets_df)} outlet(s) I have instead:",
                ""
            ]
            filtered = outlets_df
        else:
            lines = [f"**{merchant_name}** outlets in **{area_filter.title()}**:", ""]
            outlets_df = filtered
    else:
        lines = [f"**{merchant_name}** has {len(outlets_df)} outlet(s):", ""]

    descs = outlets_df["description"].unique()
    shared_desc = descs[0] if len(descs) == 1 and descs[0] else None
    if shared_desc:
        parsed = format_description_lines(shared_desc)
        lines.append("")
        first_desc = True
        for is_hdr, text in parsed:
            if is_hdr:
                if not first_desc:
                    lines.append("")
                lines.append(f"🎁 {text}")
            else:
                lines.append(f"   {text}")
            first_desc = False
        lines.append("")

    region_groups = {"central": [], "north": [], "east": [], "south": [], "west": [], "other": []}
    for _, row in outlets_df.iterrows():
        region = get_region_for_address(str(row.get("address", "")), str(row.get("postalC", "")))
        region_groups[region].append(row)

    region_labels = {
        "central": "🏙️ Central",
        "north":   "🧭 North",
        "east":    "🌅 East",
        "south":   "⚓ South",
        "west":    "🌇 West",
        "other":   "📍 Other",
    }

    for region_key in ["central", "north", "east", "south", "west", "other"]:
        rows = region_groups[region_key]
        if not rows:
            continue
        lines.append(f"**{region_labels[region_key]}**")
        lines.append("")
        for row in rows:
            addr = str(row.get("address", "")).strip()
            postal = str(row.get("postalC", "")).strip()
            desc = str(row.get("description", "")).strip()
            if addr:
                loc = f"{addr} (S{postal})" if postal else addr
                lines.append(f"📍 {loc}")
            if desc and not shared_desc:
                parsed = format_description_lines(desc)
                lines.append("")
                first_desc = True
                for is_hdr, text in parsed:
                    if is_hdr:
                        if not first_desc:
                            lines.append("")
                        lines.append(f"🎁 {text}")
                    else:
                        lines.append(f"   {text}")
                    first_desc = False
            lines.append("")

    return "\n".join(lines).strip()

def list_merchants_by_keyword(query_keywords, query_areas, df, halal_only=False):
    single_keywords = [kw for kw in query_keywords if " " not in kw]
    phrase_keywords  = [kw for kw in query_keywords if " " in kw]

    scores = {}

    # Single-word keywords → token index (Keywords column only)
    for kw in single_keywords:
        matched_indices = set()
        for token, indices in keyword_index.items():
            if kw in token:
                matched_indices.update(indices)
        for idx in matched_indices:
            scores[idx] = scores.get(idx, 0) + 1

    # Multi-word phrases → Keywords column only
    for phrase in phrase_keywords:
        for i, row in df.iterrows():
            kw_field = str(row.get("Keywords", "")).lower()
            if phrase in kw_field:
                scores[i] = scores.get(i, 0) + 1

    results = []
    seen_names = set()
    for idx, score in sorted(scores.items(), key=lambda x: (-x[1], df.loc[x[0], "name"])):
        if idx not in df.index:
            continue
        row = df.loc[idx]
        if halal_only and str(row.get("Halal", "")).strip().lower() != "yes":
            continue
        if query_areas:
            addr = str(row.get("address", "")).lower()
            if not any(area in addr for area in query_areas):
                continue
        name = str(row.get("name", "")).strip()
        if name.lower() not in seen_names:
            seen_names.add(name.lower())
            results.append((score, row))
        if len(results) >= 10:
            break

    return results

def format_keyword_list(results, df):
    if not results:
        return FALLBACK_PROMPTS
    count = len(results)
    lines = [f"Here are the top {count} merchants matching your search, ranked by relevance:", ""]
    for _, row in results:
        name = str(row.get("name", "")).strip()
        addr = str(row.get("address", "")).strip()
        postal = str(row.get("postalC", "")).strip()
        raw_desc = str(row.get("description", "")).strip()

        lines.append(f"##### 🏪 {name}")
        if addr:
            loc = f"{addr} (S{postal})" if postal else addr
            lines.append(f"📍 {loc}")

        if raw_desc:
            parsed = format_description_lines(raw_desc)
            lines.append("")
            first_desc = True
            for is_hdr, text in parsed:
                if is_hdr:
                    if not first_desc:
                        lines.append("")
                    lines.append(f"🎁 {text}")
                else:
                    lines.append(f"   {text}")
                first_desc = False

        outlet_count = count_all_outlets(name, df)
        if outlet_count > 1:
            lines.append("")
            lines.append(
                f"> ℹ️ *This merchant has {outlet_count} outlets in total. "
                f"Ask me which area you're looking at, or try '**{name} outlets**' to see all locations.*"
            )

        lines.append("")
        lines.append("---")
        lines.append("")

    if count >= 10:
        lines.append("_Showing top 10 results by relevance — there may be more. Try a more specific search to narrow down!_")

    return "\n".join(lines).strip()

def build_llm_context(candidates, df):
    context_entries = []
    total_tokens = 0
    for _, row in candidates:
        entry = {
            "name": str(row.get("name", "")),
            "address": str(row.get("address", "")),
            "description": str(row.get("description", "")),
        }
        entry_str = json.dumps(entry)
        tokens = count_tokens(entry_str)
        if total_tokens + tokens > MAX_LLM_CONTEXT_TOKENS:
            break
        context_entries.append(entry_str)
        total_tokens += tokens
    return "\n".join(context_entries)

def safe_llm_call(prompt):
    try:
        return get_completion(prompt)
    except Exception as e:
        err = str(e).lower()
        if "rate limit" in err or "token" in err or "quota" in err:
            return FALLBACK_PROMPTS
        raise

def handle_user_query(query, df, last_context=None):
    q_lower = query.lower().strip()

    # 1. List all merchants
    if re.search(r"\blist\b.*\bmerchant", q_lower) or re.search(r"\ball\b.*\bmerchant", q_lower):
        unique = get_unique_merchants(df)
        names = unique["name"].tolist()[:10]
        name_list = "\n".join(f"- {n}" for n in names)
        total = len(unique)
        return (
            f"Here are the first 10 of {total} merchants (A–Z):\n\n{name_list}\n\n"
            "_Want to narrow it down? Try specifying a region (e.g. 'merchants in the east') "
            "or a category (e.g. 'food merchants')._"
        )

    # 2. Outlet query
    merchant_name, area_filter = detect_outlet_query(query)
    if merchant_name:
        outlets = find_all_outlets(merchant_name, df)
        if outlets.empty:
            return f"I do not know of any outlets for **{merchant_name}** in our list."
        return format_outlet_list(merchant_name, outlets, area_filter=area_filter)

    # 3. Merchant name check
    merchant_names = df["name"].unique().tolist()
    matched = fuzzy_match_merchant(query, merchant_names)
    if matched:
        rows = df[df["name"].str.lower() == matched.lower()]
        outlet_count = len(rows)
        if outlet_count == 1:
            row = rows.iloc[0]
            addr = str(row.get("address", "")).strip()
            postal = str(row.get("postalC", "")).strip()
            raw_desc = str(row.get("description", "")).strip()
            loc = f"{addr} (S{postal})" if postal else addr
            lines = [f"Yes, **{matched}** is one of our merchant partners! 🎉", f"📍 {loc}", ""]
            if raw_desc:
                parsed = format_description_lines(raw_desc)
                first_desc = True
                for is_hdr, text in parsed:
                    if is_hdr:
                        if not first_desc:
                            lines.append("")
                        lines.append(f"🎁 {text}")
                    else:
                        lines.append(f"   {text}")
                    first_desc = False
            return "\n".join(lines)
        else:
            return (
                f"Yes, **{matched}** is one of our merchant partners, "
                f"with **{outlet_count} outlets** across Singapore! 🎉\n\n"
                f"_Which area are you in? Or try '**{matched} outlets**' to see all locations._"
            )

    # 4. Keyword / area search
    halal_only = is_halal_query(query)
    keywords, areas = extract_search_terms(query)

    if not keywords and not areas and last_context:
        keywords = last_context.get("keywords", [])
        areas = last_context.get("areas", [])

    if keywords or areas:
        results = list_merchants_by_keyword(keywords, areas, df, halal_only=halal_only)
        if results:
            return format_keyword_list(results, df)
        return FALLBACK_PROMPTS

    # 5. LLM fallback
    candidates = list_merchants_by_keyword(keywords or [], areas or [], df)
    if not candidates:
        candidates = [(0, df.iloc[i]) for i in range(min(20, len(df)))]
    context = build_llm_context(candidates, df)
    prompt = (
        f"You are a helpful assistant for a merchant loyalty programme in Singapore.\n"
        f"Answer the user's question using only the merchant data below.\n"
        f"If you cannot answer from the data, say you do not know.\n\n"
        f"Merchant data:\n{context}\n\n"
        f"User question: {query}"
    )
    return safe_llm_call(prompt)

# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": WELCOME_MESSAGE}]
if "last_search_context" not in st.session_state:
    st.session_state.last_search_context = None

# ── Chat UI ───────────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask about merchants, deals, or locations..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching..."):
            response = handle_user_query(
                prompt, df,
                last_context=st.session_state.last_search_context
            )

        # Update session context
        keywords, areas = extract_search_terms(prompt)
        if keywords or areas:
            st.session_state.last_search_context = {"keywords": keywords, "areas": areas}
        elif re.search(r"\blist\b|\boutlet|\bstore|\bmerchant\b", prompt.lower()):
            st.session_state.last_search_context = None

        st.markdown(response)

        # FIX: Auto-scroll — interval retries every 300 ms up to 5 times,
        # ensuring the scroll fires after Streamlit finishes rendering
        components.html("""
        <script>
        (function() {
            var attempts = 0;
            var maxAttempts = 5;
            var interval = setInterval(function() {
                var el = window.parent.document.querySelector(
                    '[data-testid="stChatMessageContainer"]'
                );
                if (el) {
                    el.scrollTop = el.scrollHeight;
                }
                attempts++;
                if (attempts >= maxAttempts) {
                    clearInterval(interval);
                }
            }, 300);
        })();
        </script>
        """, height=0)

    st.session_state.messages.append({"role": "assistant", "content": response})
