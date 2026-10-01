import streamlit as st
import pandas as pd
import json
import re
from difflib import SequenceMatcher
from helper_functions.utility import check_password
from helper_functions.llm import get_completion, get_completion_by_messages, count_tokens

if not check_password():
    st.stop()

# ── Constants ──────────────────────────────────────────────────────────────────

CSV_PATH = "pages/merchants.csv"
MAX_RESULTS = 10
MAX_LLM_CONTEXT_TOKENS = 1500

FALLBACK_PROMPTS = (
    "I do not know the answer to that. Try asking about a specific merchant, "
    "category (e.g. 'bubble tea', 'Japanese food'), or area (e.g. 'Orchard', 'Tampines')."
)

WELCOME_MESSAGE = """👋 Hi! I'm your merchant deals assistant. Here are some things you can ask me:

- 🔍 **Search by category:** `bubble tea`, `Japanese food`, `desserts`
- 📍 **Search by area:** `Orchard`, `Tampines`, `central`, `north`
- 🏪 **Find a merchant:** `Is Subway our merchant?`
- 📋 **List outlets:** `Old Chang Kee outlets`, `Subway outlets in Orchard`
- 🥗 **Halal options:** `halal food`, `halal desserts in east`
- 📜 **List all merchants:** `list all merchants`

What would you like to find today?"""

MULTI_WORD_PHRASES = [
    "bubble tea", "ice cream", "escape room", "hot pot", "dim sum",
    "fish and chips", "fried chicken", "roast duck", "char siew",
    "bak kut teh", "laksa", "chicken rice", "nasi lemak", "roti prata",
    "frozen yogurt", "soft serve", "milk tea", "fruit tea", "cheese tea",
    "board game", "laser tag", "rock climbing", "indoor cycling",
    "nail art", "hair salon", "beauty salon", "spa treatment",
    "personal training", "gym membership",
]

AREA_KEYWORDS = {
    # Central
    "orchard", "somerset", "dhoby ghaut", "city hall", "raffles place",
    "marina bay", "tanjong pagar", "chinatown", "bugis", "bras basah",
    "novena", "newton", "bishan", "toa payoh", "ang mo kio", "braddell",
    "marymount", "caldecott", "botanic gardens", "farrer road", "holland",
    "buona vista", "one north", "kent ridge", "haw par villa", "pasir panjang",
    "clementi", "dover", "commonwealth", "queenstown", "redhill", "tiong bahru",
    "outram", "harbourfront", "vivocity", "sentosa", "labrador park",
    "telok blangah", "west coast", "alexandra", "river valley", "great world",
    "dempsey", "tanglin", "stevens", "napier", "nassim", "scotts",
    "mount elizabeth", "gleneagles", "forum", "wheelock", "ion",
    "wisma", "lucky plaza", "plaza singapura", "cathay", "balmoral",
    "adam", "sixth avenue", "bukit timah", "beauty world", "king albert park",
    "upper bukit timah", "hillview", "cashew", "phoenix", "choa chu kang",
    "yew tee", "kranji", "marsiling", "woodlands", "admiralty", "sembawang",
    "canberra", "yishun", "khatib", "little india", "rochor", "jalan besar",
    "bendemeer", "geylang bahru", "whampoa", "boon keng", "potong pasir",
    "woodleigh", "serangoon", "lorong chuan", "bartley", "tai seng",
    "macpherson", "ubi", "kaki bukit", "bedok north", "bedok reservoir",
    "tampines west", "tampines", "tampines east", "upper changi", "expo",
    "changi airport", "pasir ris", "simei", "tanah merah", "bedok",
    "kembangan", "eunos", "paya lebar", "aljunied", "kallang", "lavender",
    "nicoll highway", "promenade", "esplanade", "bayfront", "downtown",
    "telok ayer", "maxwell", "shenton way", "tanjong pagar plaza",
    "arab street", "kampong glam", "haji lane", "bussorah",
    "upper paya lebar", "kovan", "hougang", "buangkok", "sengkang",
    "punggol", "northshore", "fernvale", "thanggam", "cheng lim",
    "ranggung", "kupang", "rivervale", "compassvale", "anchorvale",
    "jurong east", "jurong west", "jurong lake", "lakeside", "boon lay",
    "pioneer", "joo koon", "gul circle", "tuas", "bukit batok",
    "bukit gombak", "tengah", "hong kah", "bukit panjang", "fajar",
    "senja", "jelapang", "bangkit", "pending", "petir", "segar",
    "saujana", "senja", "bukit panjang",
    "kampong bahru", "killiney", "holland drive", "bukit merah",
}

SG_REGIONS = {
    "central": [
        "orchard", "somerset", "dhoby ghaut", "city hall", "raffles place",
        "marina bay", "tanjong pagar", "chinatown", "bugis", "bras basah",
        "novena", "newton", "bishan", "toa payoh", "ang mo kio", "braddell",
        "marymount", "caldecott", "botanic gardens", "farrer road", "holland",
        "buona vista", "one north", "kent ridge", "haw par villa",
        "clementi", "dover", "commonwealth", "queenstown", "redhill", "tiong bahru",
        "outram", "alexandra", "river valley", "great world",
        "dempsey", "tanglin", "stevens", "napier", "nassim", "scotts",
        "mount elizabeth", "gleneagles", "forum", "wheelock", "ion",
        "wisma", "lucky plaza", "plaza singapura", "cathay", "balmoral",
        "adam", "sixth avenue", "bukit timah", "beauty world", "king albert park",
        "upper bukit timah", "hillview", "cashew", "phoenix",
        "little india", "rochor", "jalan besar", "bendemeer",
        "geylang bahru", "whampoa", "boon keng", "potong pasir",
        "woodleigh", "serangoon", "lorong chuan", "bartley", "tai seng",
        "macpherson", "arab street", "kampong glam", "haji lane", "bussorah",
        "telok ayer", "maxwell", "shenton way", "tanjong pagar plaza",
        "nicoll highway", "promenade", "esplanade", "bayfront", "downtown",
        "kampong bahru", "killiney", "holland drive", "bukit merah",
        "upper paya lebar",
    ],
    "north": [
        "choa chu kang", "yew tee", "kranji", "marsiling", "woodlands",
        "admiralty", "sembawang", "canberra", "yishun", "khatib",
        "kovan", "hougang", "buangkok", "sengkang", "punggol",
        "northshore", "fernvale", "thanggam", "cheng lim",
        "ranggung", "kupang", "rivervale", "compassvale", "anchorvale",
    ],
    "east": [
        "tampines", "tampines west", "tampines east", "upper changi", "expo",
        "changi airport", "pasir ris", "simei", "tanah merah", "bedok",
        "kembangan", "eunos", "paya lebar", "aljunied", "kallang", "lavender",
        "bedok north", "bedok reservoir", "kaki bukit", "ubi",
        "macpherson", "geylang",
    ],
    "south": [
        "harbourfront", "vivocity", "sentosa", "labrador park",
        "pasir panjang", "west coast", "telok blangah",
    ],
    "west": [
        "jurong east", "jurong west", "jurong lake", "lakeside", "boon lay",
        "pioneer", "joo koon", "gul circle", "tuas", "bukit batok",
        "bukit gombak", "tengah", "hong kah", "bukit panjang", "fajar",
        "senja", "jelapang", "bangkit", "pending", "petir", "segar",
        "saujana", "bukit panjang",
    ],
}

REGION_EMOJI = {
    "central": "🏙️ Central",
    "east": "🌅 East",
    "west": "🌇 West",
    "south": "⚓ South",
    "north": "🧭 North",
}

POSTAL_DISTRICT_REGION = {
    **{d: "central" for d in [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21]},
    **{d: "west"    for d in [22,23,24,25,26,27]},
    **{d: "north"   for d in [28,29,30,31,32,33,34,35,36,37,38,39,40,41,72,73,74,75,76,77,78,79,80,81,82,83,84]},
    **{d: "east"    for d in [42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71]},
    **{d: "south"   for d in [9]},  # Sentosa / HarbourFront area
}

# ── Data loading ───────────────────────────────────────────────────────────────

from datetime import datetime

def is_deal_valid(start_str, end_str):
    formats = ["%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d"]
    today = datetime.today()
    try:
        for fmt in formats:
            try:
                end_dt = datetime.strptime(str(end_str).strip(), fmt)
                break
            except ValueError:
                continue
        else:
            return True  # unparseable → include
        return end_dt >= today
    except Exception:
        return True

@st.cache_data
def load_data():
    df = pd.read_csv(CSV_PATH)
    df.columns = df.columns.str.strip()
    df = df.fillna("")
    df = df[df.apply(lambda r: is_deal_valid(r.get("startDate",""), r.get("endDate","")), axis=1)]
    df = df.reset_index(drop=True)
    return df

@st.cache_data
def build_keyword_index(_df):
    index = {}
    for i, row in _df.iterrows():
        kw_field = str(row.get("Keywords", "")).lower()
        desc_field = str(row.get("description", "")).lower()
        addr_field = str(row.get("address", "")).lower()
        tokens = set(re.split(r"[,\s]+", kw_field + " " + desc_field + " " + addr_field))
        for tok in tokens:
            tok = tok.strip()
            if tok:
                index.setdefault(tok, []).append(i)
    return index

@st.cache_data
def get_unique_merchants(_df):
    seen = set()
    result = []
    for _, row in _df.sort_values("name").iterrows():
        name = row["name"].strip()
        if name and name not in seen:
            seen.add(name)
            result.append(name)
    return result

# ── Text helpers ───────────────────────────────────────────────────────────────

STOPWORDS = {
    "a","an","the","is","are","was","were","be","been","being",
    "have","has","had","do","does","did","will","would","could","should",
    "may","might","shall","can","need","dare","ought","used",
    "i","me","my","we","our","you","your","he","she","it","they","them","their",
    "this","that","these","those","what","which","who","whom","whose",
    "where","when","why","how","all","any","both","each","few","more",
    "most","other","some","such","no","nor","not","only","own","same",
    "so","than","too","very","just","but","and","or","if","in","on",
    "at","to","for","of","with","by","from","up","about","into","through",
    "during","before","after","above","below","between","out","off","over",
    "under","again","further","then","once","here","there","s","t",
    "find","show","tell","give","list","get","look","search","want",
    "need","know","like","near","around","area","place","places",
    "merchant","merchants","deal","deals","offer","offers","promo","promos",
    "promotion","promotions","discount","discounts","voucher","vouchers",
    "available","singapore","sg",
}

def normalise(text: str) -> str:
    text = text.lower().replace("&", "and")
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def extract_search_terms(query: str):
    q = query.lower()
    phrases_found = []
    for phrase in MULTI_WORD_PHRASES:
        if phrase in q:
            phrases_found.append(phrase)
            q = q.replace(phrase, " ")

    words = re.split(r"[\s,]+", q)
    words = [w.strip() for w in words if w.strip() and w not in STOPWORDS]

    keywords = list(phrases_found)
    areas = []
    regions_found = []

    for w in words:
        if w in SG_REGIONS:
            regions_found.append(w)
        elif w in AREA_KEYWORDS:
            areas.append(w)
        else:
            keywords.append(w)

    for r in regions_found:
        areas.extend(SG_REGIONS[r])

    return keywords, list(set(areas))

# ── Fuzzy matching ─────────────────────────────────────────────────────────────

def fuzzy_match_merchant(query_norm: str, merchant_names: list, threshold=0.82):
    query_norm = normalise(query_norm)
    best_name, best_score = None, 0.0
    for name in merchant_names:
        name_norm = normalise(name)
        if name_norm in query_norm:
            return name
        wlen = len(name_norm.split())
        qwords = query_norm.split()
        if len(qwords) < wlen:
            continue
        for i in range(len(qwords) - wlen + 1):
            window = " ".join(qwords[i:i+wlen])
            score = SequenceMatcher(None, name_norm, window).ratio()
            if score > best_score:
                best_score, best_name = score, name
    return best_name if best_score >= threshold else None

def detect_outlet_query(query: str, merchant_names: list):
    q_norm = normalise(query)
    outlet_pattern = re.compile(
        r"(.+?)\s+outlets?\b(?:\s+in\s+(.+))?$", re.IGNORECASE
    )
    m = outlet_pattern.search(q_norm)
    if not m:
        return None, None
    candidate = m.group(1).strip()
    area_part = m.group(2).strip() if m.group(2) else ""
    matched = fuzzy_match_merchant(candidate, merchant_names)
    if not matched:
        return None, None
    area_filter = area_part if area_part else ""
    return matched, area_filter

# ── Region detection ───────────────────────────────────────────────────────────

def get_region_for_address(address: str, postal: str = "") -> str:
    addr_lower = address.lower()
    for region in ["central", "north", "east", "south", "west"]:
        for kw in SG_REGIONS[region]:
            if kw in addr_lower:
                return region
    if postal:
        try:
            district = int(str(postal).strip()[:2])
            return POSTAL_DISTRICT_REGION.get(district, "central")
        except Exception:
            pass
    return "central"

# ── Merchant lookup helpers ────────────────────────────────────────────────────

def find_all_outlets(df, merchant_name: str):
    return df[df["name"].str.strip().str.lower() == merchant_name.lower()].to_dict("records")

def count_all_outlets(df, merchant_name: str) -> int:
    return len(find_all_outlets(df, merchant_name))

def is_halal_query(query: str) -> bool:
    return "halal" in query.lower()

# ── Description formatting ─────────────────────────────────────────────────────

def is_header_line(line: str) -> bool:
    """True if the line looks like a section header (ALL CAPS ending with ':')."""
    stripped = line.strip()
    return bool(stripped) and stripped.endswith(":") and stripped == stripped.upper()

def format_description_lines(desc: str):
    """
    Returns a list of (is_header, text) tuples.
    is_header=True  → render with 🎁 prefix and bold.
    is_header=False → render as body text (indented).
    """
    if not desc:
        return []
    lines = [l.strip() for l in desc.splitlines() if l.strip()]
    if not lines:
        return []
    result = []
    for i, line in enumerate(lines):
        if i == 0 or is_header_line(line):
            result.append((True, f"**{line}**"))
        else:
            result.append((False, line))
    return result

# ── Keyword search ─────────────────────────────────────────────────────────────

def list_merchants_by_keyword(df, keyword_index, keywords, areas, halal_only=False):
    scores = {}
    candidate_rows = set()

    if keywords:
        for kw in keywords:
            for tok, idxs in keyword_index.items():
                if kw in tok or tok in kw:
                    candidate_rows.update(idxs)
    else:
        candidate_rows = set(df.index)

    for idx in candidate_rows:
        row = df.loc[idx]
        if halal_only and str(row.get("Halal", "")).strip().lower() != "yes":
            continue
        addr = str(row.get("address", "")).lower()
        if areas:
            if not any(a in addr for a in areas):
                continue
        score = 0
        for kw in keywords:
            kw_field = str(row.get("Keywords", "")).lower()
            desc_field = str(row.get("description", "")).lower()
            if kw in kw_field:
                score += 2
            elif kw in desc_field:
                score += 1
        scores[idx] = scores.get(idx, 0) + score

    ranked = sorted(scores.items(), key=lambda x: (-x[1], df.loc[x[0], "name"]))
    seen_names = set()
    results = []
    for idx, _ in ranked:
        name = df.loc[idx, "name"].strip()
        if name not in seen_names:
            seen_names.add(name)
            results.append(df.loc[idx].to_dict())
        if len(results) >= MAX_RESULTS:
            break
    return results

# ── Formatting helpers ─────────────────────────────────────────────────────────

def format_keyword_list(results, df):
    if not results:
        return FALLBACK_PROMPTS
    count = len(results)
    lines = [f"Here are the top {count} merchants matching your search, ranked by relevance:\n"]
    for r in results:
        name = r.get("name", "").strip()
        address = r.get("address", "").strip()
        postal = r.get("postalC", "")
        postal_str = f" S({postal})" if postal else ""
        raw_desc = r.get("description", "").strip()

        lines.append(f"---\n#### 🏪 {name}")
        lines.append(f"📍 {address}{postal_str}")

        if raw_desc:
            parsed = format_description_lines(raw_desc)
            lines.append("")
            for is_hdr, text in parsed:
                if is_hdr:
                    lines.append(f"🎁 {text}")
                else:
                    lines.append(f"   {text}")

        outlet_count = count_all_outlets(df, name)
        if outlet_count > 1:
            lines.append("")
            lines.append(
                f"ℹ️ This merchant has {outlet_count} outlets in total. "
                f"Ask me which area you're looking at, or try '**{name} outlets**' to see all locations."
            )

    if count >= MAX_RESULTS:
        lines.append(
            "\n_Showing top 10 results by relevance — there may be more. "
            "Try a more specific search to narrow down!_"
        )
    return "\n".join(lines)

def format_outlet_list(outlets, merchant_name, area_filter=""):
    if not outlets:
        return f"I do not know of any outlets for **{merchant_name}**."

    if area_filter:
        filtered = [o for o in outlets if area_filter.lower() in o.get("address","").lower()]
        if not filtered:
            note = f"_No outlets found in '{area_filter}'. Showing all outlets instead._\n\n"
            filtered = outlets
        else:
            note = ""
            outlets = filtered
    else:
        note = ""

    # Check if all outlets share the same description
    descs = [o.get("description","").strip() for o in outlets]
    shared_desc = descs[0] if len(set(descs)) == 1 and descs[0] else ""

    lines = [f"### 🏪 {merchant_name}"]
    lines.append(f"_{len(outlets)} outlet(s) found_\n")

    if note:
        lines.append(note)

    if shared_desc:
        parsed = format_description_lines(shared_desc)
        for is_hdr, text in parsed:
            if is_hdr:
                lines.append(f"🎁 {text}")
            else:
                lines.append(f"   {text}")
        lines.append("")

    # Group by region
    region_order = ["central", "north", "east", "south", "west"]
    region_buckets = {r: [] for r in region_order}
    for row in outlets:
        region = get_region_for_address(row.get("address",""), str(row.get("postalC","")))
        region_buckets[region].append(row)

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

            lines.append("")                                        # blank line before each outlet
            lines.append(f"• **{address}{postal_str}**")           # bold address

            if desc and not shared_desc:
                parsed = format_description_lines(desc)
                lines.append("")
                for is_hdr, text in parsed:
                    if is_hdr:
                        lines.append(f"  🎁 {text}")
                    else:
                        lines.append(f"     {text}")

    return "\n".join(lines)

# ── LLM helpers ────────────────────────────────────────────────────────────────

def build_llm_context(candidates, df):
    context_rows = []
    token_count = 0
    for c in candidates:
        name = c.get("name","")
        address = c.get("address","")
        desc = c.get("description","")
        entry = f"Merchant: {name}\nAddress: {address}\nDescription: {desc}\n"
        entry_tokens = count_tokens(entry)
        if token_count + entry_tokens > MAX_LLM_CONTEXT_TOKENS:
            break
        context_rows.append(entry)
        token_count += entry_tokens
    return "\n".join(context_rows)

def safe_llm_call(prompt: str) -> str:
    try:
        return get_completion(prompt)
    except Exception as e:
        err = str(e).lower()
        if "rate limit" in err or "token" in err or "quota" in err:
            return FALLBACK_PROMPTS
        raise

# ── Halal filter ───────────────────────────────────────────────────────────────

def filter_halal(df):
    return df[df["Halal"].str.strip().str.lower() == "yes"]

# ── Main query handler ─────────────────────────────────────────────────────────

def handle_user_query(query: str, df, keyword_index, unique_merchants, last_context=None):
    q_lower = query.lower().strip()
    halal = is_halal_query(query)

    # ── 1. List all merchants ──────────────────────────────────────────────────
    if re.search(r"\blist\s+all\b", q_lower) or q_lower in ("all merchants", "all deals"):
        sample = unique_merchants[:MAX_RESULTS]
        resp = "Here are the first 10 merchants (A–Z):\n\n"
        resp += "\n".join(f"• {m}" for m in sample)
        resp += (
            "\n\n_There may be more merchants available. "
            "Try searching by category (e.g. 'Japanese food') or area (e.g. 'Orchard') "
            "to narrow down results._"
        )
        return resp, {"keywords": [], "areas": []}

    # ── 2. Outlet query ────────────────────────────────────────────────────────
    merchant_name, area_filter = detect_outlet_query(query, unique_merchants)
    if merchant_name:
        outlets = find_all_outlets(df, merchant_name)
        if halal:
            outlets = [o for o in outlets if str(o.get("Halal","")).strip().lower() == "yes"]
        return format_outlet_list(outlets, merchant_name, area_filter=area_filter), {"keywords": [], "areas": []}

    # ── 3. Merchant name check ─────────────────────────────────────────────────
    matched = fuzzy_match_merchant(query, unique_merchants)
    if matched:
        outlets = find_all_outlets(df, matched)
        if len(outlets) == 1:
            o = outlets[0]
            address = o.get("address","").strip()
            postal = o.get("postalC","")
            postal_str = f" S({postal})" if postal else ""
            raw_desc = o.get("description","").strip()
            resp = f"Yes, **{matched}** is one of our merchants! 🎉\n\n📍 {address}{postal_str}"
            if raw_desc:
                parsed = format_description_lines(raw_desc)
                for is_hdr, text in parsed:
                    if is_hdr:
                        resp += f"\n\n🎁 {text}"
                    else:
                        resp += f"\n   {text}"
            return resp, {"keywords": [], "areas": []}
        else:
            return (
                f"Yes, **{matched}** is one of our merchants with **{len(outlets)} outlets**! 🎉\n\n"
                f"Which area are you in? Or try '**{matched} outlets**' to see all locations."
            ), {"keywords": [], "areas": []}

    # ── 4. Keyword / area search ───────────────────────────────────────────────
    keywords, areas = extract_search_terms(query)

    # Inherit last context if current query has no keywords/areas
    if not keywords and not areas and last_context:
        keywords = last_context.get("keywords", [])
        areas = last_context.get("areas", [])

    if keywords or areas or halal:
        working_df = filter_halal(df) if halal else df
        results = list_merchants_by_keyword(working_df, keyword_index, keywords, areas, halal_only=halal)
        return format_keyword_list(results, df), {"keywords": keywords, "areas": areas}

    # ── 5. LLM fallback ────────────────────────────────────────────────────────
    kw_fallback, area_fallback = extract_search_terms(query)
    candidates = list_merchants_by_keyword(df, keyword_index, kw_fallback, area_fallback)
    if not candidates:
        candidates = df.sample(min(20, len(df))).to_dict("records")

    context = build_llm_context(candidates, df)
    prompt = (
        f"You are a helpful assistant for a merchant deals directory.\n"
        f"Answer the user's question using only the merchant data below.\n"
        f"Do not reveal Halal status or Keywords unless the user asks.\n\n"
        f"Merchant data:\n{context}\n\n"
        f"User question: {query}\n\n"
        f"Answer:"
    )
    answer = safe_llm_call(prompt)
    return answer, {"keywords": kw_fallback, "areas": area_fallback}

# ── Streamlit UI ───────────────────────────────────────────────────────────────

st.set_page_config(page_title="Merchant Deals Chatbot", page_icon="🛍️")
st.title("🛍️ Merchant Deals Chatbot")
st.caption("Ask me about merchant deals, categories, or locations!")

st.markdown("""
<style>
    .stChatMessage { max-width: 100% !important; }
    .stMarkdown p { white-space: pre-wrap; }
</style>
""", unsafe_allow_html=True)

# Load data
df = load_data()
keyword_index = build_keyword_index(df)
unique_merchants = get_unique_merchants(df)

# Session state init
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": WELCOME_MESSAGE}]
if "last_search_context" not in st.session_state:
    st.session_state.last_search_context = None

# Render chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Handle new input
if prompt := st.chat_input("Ask about merchants, deals, or locations..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching..."):
            response, new_context = handle_user_query(
                prompt, df, keyword_index, unique_merchants,
                last_context=st.session_state.last_search_context
            )
            if new_context["keywords"] or new_context["areas"]:
                st.session_state.last_search_context = new_context
            else:
                st.session_state.last_search_context = None
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
