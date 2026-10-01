import streamlit as st
import pandas as pd
import re
from difflib import SequenceMatcher
from helper_functions.llm import get_completion, get_completion_by_messages, count_tokens
from helper_functions.utility import check_password

if not check_password():
    st.stop()

# ── Page config ───────────────────────────────────────────────────────────────
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

WELCOME_MESSAGE = (
    "👋 Hi! I'm your Merchant Chatbot. Here are some things you can ask me — feel free to copy and paste!\n\n"
    "---\n"
    "🔍 **Browse merchants**\n"
    "> List all merchants\n\n"
    "📍 **Search by area**\n"
    "> Show me merchants in Tampines\n\n"
    "> Show me merchants in the North\n\n"
    "🍽️ **Search by category**\n"
    "> Show me food merchants\n\n"
    "> Any bubble tea merchants?\n\n"
    "🕌 **Halal options**\n"
    "> List halal merchants near Jurong\n\n"
    "🏪 **Check a specific merchant**\n"
    "> Is Old Chang Kee our merchant?\n\n"
    "> Old Chang Kee outlets\n\n"
    "---\n"
    "_Type your question below or copy one of the prompts above!_"
)

MULTI_WORD_PHRASES = [
    "bubble tea", "ice cream", "escape room", "hot pot", "hot dogs",
    "fried chicken", "fish and chips", "dim sum", "char kway teow",
    "bak kut teh", "nasi lemak", "laksa", "chicken rice",
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
    # North (includes former North East)
    "yishun", "khatib", "yio chu kang", "ang mo kio", "amk", "sembawang",
    "canberra", "admiralty", "woodlands", "marsiling", "kranji",
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
        "punggol", "sengkang", "buangkok", "hougang", "kovan", "serangoon north",
        "compassvale", "rivervale", "fernvale", "northshore",
    ],
    "east": [
        "tampines", "simei", "tanah merah", "bedok", "kembangan", "eunos",
        "changi", "expo", "pasir ris", "loyang", "upper changi",
    ],
    "west": [
        "jurong", "boon lay", "lakeside", "chinese garden", "clementi",
        "dover", "one-north", "one north", "kent ridge", "haw par villa",
        "bukit panjang", "choa chu kang", "yew tee", "bukit batok",
        "bukit gombak", "hillview", "beauty world", "king albert park",
        "sixth avenue", "tan kah kee",
    ],
    "south": [
        "harbourfront", "vivocity", "sentosa", "labrador park",
        "pasir panjang", "west coast", "telok blangah",
    ],
}

POSTAL_DISTRICT_REGION = {
    "01": "central", "02": "central", "03": "central", "04": "central",
    "05": "central", "06": "central", "07": "central", "08": "central",
    "09": "central", "10": "central", "11": "central", "12": "central",
    "13": "central", "14": "central", "15": "central", "16": "central",
    "17": "central", "18": "central", "19": "central", "20": "central",
    "21": "central", "22": "central", "23": "central",
    "24": "south", "25": "south", "26": "south", "27": "south",
    "28": "south", "29": "south", "30": "south",
    "31": "south", "32": "south", "33": "south",
    "34": "east", "35": "east", "36": "east", "37": "east",
    "38": "east", "39": "east", "40": "east", "41": "east",
    "42": "east", "43": "east", "44": "east", "45": "east",
    "46": "east", "47": "east", "48": "east",
    "49": "east", "50": "east", "51": "east", "52": "east",
    "53": "north", "54": "north", "55": "north",
    "56": "north", "57": "north",
    "60": "west", "61": "west", "62": "west", "63": "west", "64": "west",
    "65": "west", "66": "west", "67": "west", "68": "west", "69": "west",
    "70": "west", "71": "west",
    "72": "north", "73": "north", "74": "north", "75": "north", "76": "north",
    "77": "north", "78": "north",
    "79": "north", "80": "north",
    "81": "north", "82": "north", "83": "north", "84": "north",
}

REGION_EMOJI = {
    "central": "🏙️ Central",
    "north":   "🧭 North",
    "east":    "🌅 East",
    "west":    "🌇 West",
    "south":   "⚓ South",
    "other":   "📍 Other",
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

def normalise(text: str) -> str:
    """Lowercase, replace & with 'and', strip punctuation, collapse whitespace."""
    text = text.lower()
    text = text.replace("&", "and")
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def fuzzy_match_merchant(query_norm: str, threshold: float = 0.82) -> str | None:
    """
    Returns the best-matching merchant name if similarity is above threshold,
    else None. Checks exact substring first, then sliding-window fuzzy match.
    """
    best_name = None
    best_score = 0.0

    for name in unique_merchants:
        name_norm = normalise(name)

        # Exact substring match always wins immediately
        if name_norm in query_norm:
            return name

        # Sliding-window similarity: compare name against same-length windows in query
        score = 0.0
        name_len = len(name_norm)
        query_len = len(query_norm)

        if query_len >= name_len:
            for start in range(query_len - name_len + 1):
                window = query_norm[start:start + name_len]
                s = SequenceMatcher(None, name_norm, window).ratio()
                if s > score:
                    score = s
        else:
            # Query is shorter than merchant name — compare directly
            score = SequenceMatcher(None, name_norm, query_norm).ratio()

        if score > best_score:
            best_score = score
            best_name = name

    return best_name if best_score >= threshold else None

def format_description_lines(desc):
    """Returns (header_line, [subsequent_lines]) — caller handles 🎁 placement."""
    if not desc:
        return "", []
    lines = [l.strip() for l in desc.splitlines() if l.strip()]
    if not lines:
        return "", []
    header = f"**{lines[0]}**"
    rest = lines[1:]
    return header, rest

def get_region_for_address(address, postal=""):
    addr_lower = address.lower()
    region_order = ["central", "north", "east", "south", "west"]
    for region in region_order:
        areas = SG_REGIONS.get(region, [])
        if any(area in addr_lower for area in areas):
            return region
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

    region_map = {
        "central":    SG_REGIONS["central"],
        "north":      SG_REGIONS["north"],
        "south":      SG_REGIONS["south"],
        "east":       SG_REGIONS["east"],
        "west":       SG_REGIONS["west"],
        "northeast":  SG_REGIONS["north"],
        "north east": SG_REGIONS["north"],
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

def detect_outlet_query(query: str):
    """
    Returns (merchant_name, area_filter) if the query is asking for outlets
    of a specific merchant, else (None, None).
    Uses normalised fuzzy matching to handle special characters and typos.
    """
    q_norm = normalise(query)
    if "outlet" not in q_norm:
        return None, None

    matched_name = fuzzy_match_merchant(q_norm)
    if not matched_name:
        return None, None

    area_filter = None
    area_match = re.search(
        r"outlets?\s+(?:in|at|near|around)\s+(.+)$", query, re.IGNORECASE
    )
    if area_match:
        area_filter = area_match.group(1).strip()

    return matched_name, area_filter

# ── Scoring-based search ──────────────────────────────────────────────────────
def list_merchants_by_keyword(keywords, areas, halal_only=False):
    if keywords:
        kw_scores: dict[int, int] = {}
        for kw in keywords:
            kw_lower = kw.lower()
            for idx_kw, indices in keyword_index.items():
                if kw_lower in idx_kw or idx_kw in kw_lower:
                    for i in indices:
                        kw_scores[i] = kw_scores.get(i, 0) + 1
        candidate_indices = set(kw_scores.keys())
    else:
        kw_scores = {i: 0 for i in df.index}
        candidate_indices = set(df.index.tolist())

    if areas:
        area_indices: set[int] = set()
        for area in areas:
            area_lower = area.lower()
            for idx_kw, indices in keyword_index.items():
                if area_lower in idx_kw or idx_kw in area_lower:
                    area_indices.update(indices)
        candidate_indices = candidate_indices & area_indices

    if not candidate_indices:
        return [], 0

    results = df.loc[sorted(candidate_indices)].copy()
    if halal_only:
        results = results[results["Halal"].str.strip().str.lower() == "yes"]

    if results.empty:
        return [], 0

    seen: dict[str, dict] = {}
    for i, row in results.iterrows():
        name = row["name"]
        score = kw_scores.get(i, 0)
        if name not in seen or score > seen[name]["_score"]:
            seen[name] = {**row.to_dict(), "_score": score}

    ranked = sorted(seen.values(), key=lambda r: (-r["_score"], r["name"]))
    total = len(ranked)
    return ranked[:10], total


def format_keyword_list(results, total_count):
    if not results:
        return FALLBACK_PROMPTS

    count = min(len(results), 10)
    lines = [f"Here are the top {count} merchants matching your search, ranked by relevance:\n"]

    for row in results:
        name = row["name"]
        address = row.get("address", "")
        postal = row.get("postalC", "")
        postal_str = f" S({postal})" if postal else ""
        raw_desc = row.get("description", "")
        outlet_count = count_all_outlets(name)

        lines.append(f"#### 🏪 {name}")
        lines.append(f"📍 {address}{postal_str}")

        if raw_desc:
            header_line, rest_lines = format_description_lines(raw_desc)
            lines.append("")
            lines.append(f"🎁 {header_line}")
            for rl in rest_lines:
                lines.append(f"   {rl}")

        if outlet_count > 1:
            lines.append("")
            lines.append(
                f"ℹ️ This merchant has {outlet_count} outlets in total. "
                f"Ask me which area you're looking at, or try '*{name} outlets*' to see all locations."
            )

        lines.append("")
        lines.append("---")
        lines.append("")

    if total_count >= 10:
        lines.append(
            "_Showing top 10 results by relevance — there may be more. "
            "Try a more specific search to narrow down!_"
        )

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

    descs = outlets_df["description"].str.strip().unique()
    shared_desc = descs[0] if len(descs) == 1 and descs[0] else None
    if shared_desc:
        header_line, rest_lines = format_description_lines(shared_desc)
        lines.append(f"🎁 {header_line}")
        for rl in rest_lines:
            lines.append(f"   {rl}")
        lines.append("")

    region_buckets: dict[str, list] = {}
    for _, row in outlets_df.iterrows():
        region = get_region_for_address(row.get("address", ""), row.get("postalC", ""))
        region_buckets.setdefault(region, []).append(row)

    region_order = ["central", "north", "east", "west", "south", "other"]
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
                header_line, rest_lines = format_description_lines(desc)
                lines.append("")
                lines.append(f"  🎁 {header_line}")
                for rl in rest_lines:
                    lines.append(f"     {rl}")

    return "\n".join(lines)


def safe_llm_call(prompt):
    try:
        return get_completion(prompt)
    except Exception as e:
        err = str(e).lower()
        if any(w in err for w in ("rate", "token", "limit", "quota")):
            return FALLBACK_PROMPTS
        return FALLBACK_PROMPTS

# ── Token-budgeted LLM context ────────────────────────────────────────────────
MAX_LLM_CONTEXT_TOKENS = 1500

def build_llm_context(candidate_names: list[str]) -> str:
    lines = []
    running = 0
    for name in candidate_names:
        chunk = f"- {name}\n"
        cost = count_tokens(chunk)
        if running + cost > MAX_LLM_CONTEXT_TOKENS:
            break
        lines.append(chunk)
        running += cost
    return "We have the following merchants:\n" + "".join(lines)

def handle_user_query(query, last_context=None):
    q = query.lower().strip()
    q_norm = normalise(query)
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

    # ── Outlet listing (fuzzy + special char tolerant) ────────────────────────
    matched_name, area_filter = detect_outlet_query(query)
    if matched_name:
        outlets = find_all_outlets(matched_name)
        if not outlets.empty:
            return format_outlet_list(outlets, matched_name, area_filter), {"keywords": [], "areas": []}

    # ── Merchant name check (normalised + fuzzy) ──────────────────────────────
    matched_name = fuzzy_match_merchant(q_norm)
    if matched_name:
        rows = find_merchant_by_name(matched_name)
        if not rows.empty:
            if len(rows) == 1:
                row = rows.iloc[0]
                address = row.get("address", "")
                postal = row.get("postalC", "")
                postal_str = f" S({postal})" if postal else ""
                raw_desc = row.get("description", "")
                resp = f"✅ Yes, **{matched_name}** is one of our merchants!\n\n📍 {address}{postal_str}"
                if raw_desc:
                    header_line, rest_lines = format_description_lines(raw_desc)
                    resp += f"\n\n🎁 {header_line}"
                    for rl in rest_lines:
                        resp += f"\n   {rl}"
                return resp, {"keywords": [], "areas": []}
            else:
                return (
                    f"✅ Yes, **{matched_name}** is one of our merchants! "
                    f"They have **{len(rows)} outlets** across Singapore. "
                    f"Which area are you looking at? Or try '*{matched_name} outlets*' to see all locations.",
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

    # ── LLM fallback (token-budgeted) ─────────────────────────────────────────
    kw_candidates, _ = list_merchants_by_keyword(keywords, [], halal_only=False)
    candidate_names = [r["name"] for r in kw_candidates] if kw_candidates else unique_merchants

    context = build_llm_context(candidate_names)
    prompt = (
        f"You are a helpful merchant chatbot. Answer based only on this information:\n\n"
        f"{context}\n\n"
        f"User question: {query}\n\n"
        f"If you do not know, say 'I do not know'."
    )
    return safe_llm_call(prompt), {"keywords": [], "areas": []}


# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": WELCOME_MESSAGE}
    ]
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
