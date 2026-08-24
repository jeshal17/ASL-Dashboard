import re
import collections

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="ASL Meet Analytics",
    page_icon="▣",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================================================
# COLOR PALETTE
# =========================================================

NAVY = "#0F1F3A"
DARK_TEAL = "#2C4A52"
TEAL = "#527277"
GREY_GREEN = "#8C9A96"
CORAL = "#F3544A"
BEIGE = "#F4EBDD"
PURPLE = "#727077"
LIGHT_CORAL = "#E99787"
WHITE = "#FFFFFF"
LIGHT_BG = "#F5F7F7"
DARK_TEXT = "#243238"

# Fixed color mapping so colors mean the same thing on every chart,
# regardless of which ratings/sentiments are present after filtering.
RATING_COLORS = {
    1: "#B23A32",
    2: CORAL,
    3: GREY_GREEN,
    4: TEAL,
    5: NAVY,
}

SENTIMENT_COLORS = {
    "Positive": TEAL,
    "Neutral": GREY_GREEN,
    "Negative": CORAL,
}

NPS_COLORS = {
    "Promoter": TEAL,
    "Passive": GREY_GREEN,
    "Detractor": CORAL,
}


# =========================================================
# APP PASSWORD GATE
# The password itself is never stored in the source — only its
# SHA-256 hash is. To set/change the password, run once:
#   python3 -c "import hashlib; print(hashlib.sha256(b'yourpassword').hexdigest())"
# and paste the result into APP_PASSWORD_HASH below.
# For a public deploy, move the hash into st.secrets["app_password_hash"]
# instead of hardcoding it here.
# =========================================================

import hashlib

# hash of: a#12355@projectAAAJ
APP_PASSWORD_HASH = "80da1e121150a9c60bbbd284903abd095797c3079a0a26e92d1536c8e815285c"


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def check_password() -> bool:
    """Returns True once the correct password has been entered."""

    if st.session_state.get("password_correct", False):
        return True

    st.markdown(
        '<div class="main-title">ASL Meet Analytics</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="subtitle">Enter the access password to continue</div>',
        unsafe_allow_html=True,
    )

    def _on_submit():
        entered = st.session_state.get("password_input", "")
        if _hash(entered) == APP_PASSWORD_HASH:
            st.session_state["password_correct"] = True
        else:
            st.session_state["password_correct"] = False
        # Don't keep the typed password sitting in session state
        st.session_state["password_input"] = ""

    st.text_input(
        "Password",
        type="password",
        key="password_input",
        on_change=_on_submit,
    )

    if st.session_state.get("password_correct") is False:
        st.error("Incorrect password. Please try again.")

    return False


# =========================================================
# CUSTOM CSS  (applied before the password gate too, so the
# gate itself is styled consistently with the rest of the app)
# =========================================================

st.markdown(
    f"""
    <style>

    .stApp {{
        background-color: {LIGHT_BG};
        color: {DARK_TEXT};
    }}

    section[data-testid="stSidebar"] {{
        background-color: {NAVY};
    }}

    section[data-testid="stSidebar"] * {{
        color: white !important;
    }}

    .main-title {{
        font-size: 34px;
        font-weight: 700;
        color: {NAVY};
        margin-bottom: 4px;
    }}

    .subtitle {{
        font-size: 15px;
        color: {PURPLE};
        margin-bottom: 25px;
    }}

    .metric-card {{
        background: {WHITE};
        border-radius: 14px;
        padding: 18px;
        min-height: 120px;
        border-left: 5px solid {TEAL};
        box-shadow: 0 3px 12px rgba(15, 31, 58, 0.08);
    }}

    .metric-card.coral {{ border-left-color: {CORAL}; }}
    .metric-card.navy {{ border-left-color: {NAVY}; }}
    .metric-card.beige {{ border-left-color: {GREY_GREEN}; }}
    .metric-card.purple {{ border-left-color: {PURPLE}; }}

    .metric-title {{
        font-size: 12px;
        color: {PURPLE};
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}

    .metric-value {{
        font-size: 27px;
        font-weight: 700;
        color: {NAVY};
        margin-top: 6px;
    }}

    .metric-sub {{
        font-size: 12px;
        color: {GREY_GREEN};
        margin-top: 2px;
    }}

    .section-title {{
        color: {NAVY};
        font-size: 21px;
        font-weight: 700;
        margin-top: 25px;
        margin-bottom: 10px;
    }}

    .info-box {{
        background-color: {BEIGE};
        padding: 15px;
        border-radius: 12px;
        color: {DARK_TEXT};
        border-left: 5px solid {GREY_GREEN};
    }}

    /* Sidebar section heading (e.g. "Data Source") */
    .sidebar-heading {{
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 0.6px;
        text-transform: uppercase;
        color: {WHITE} !important;
        opacity: 0.95;
        margin: 4px 0 12px 0;
    }}

    /* Sidebar footnote — readable contrast on the navy background,
       styled as a small chip instead of a bare caption */
    .sidebar-note {{
        font-size: 12.5px;
        line-height: 1.5;
        color: {WHITE} !important;
        opacity: 0.85;
        background-color: rgba(255, 255, 255, 0.06);
        border-left: 3px solid {CORAL};
        border-radius: 8px;
        padding: 10px 12px;
        margin-top: 14px;
    }}

    [data-testid="stFileUploader"] {{
        background-color: {WHITE};
        border-radius: 12px;
        padding: 4px;
    }}

    /* Give the uploaded-file row (icon, filename, size, remove
       button) proper breathing room instead of a cramped default */
    [data-testid="stFileUploaderFile"] {{
        padding: 10px 8px;
        gap: 10px;
    }}

    [data-testid="stFileUploaderFile"] small {{
        opacity: 0.7;
        font-size: 12px;
    }}

    /* Drop the awkward floating tooltip "?" icon wherever it appears */
    [data-testid="stFileUploader"] [data-testid="stTooltipIcon"] {{
        display: none;
    }}

    .stButton > button {{
        background-color: {NAVY};
        color: white;
        border-radius: 8px;
        border: none;
    }}

    .stButton > button:hover {{
        background-color: {DARK_TEAL};
        color: white;
    }}

    /* Top filter bar */
    .filter-bar-label {{
        font-size: 13px;
        font-weight: 700;
        color: {NAVY};
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 6px;
    }}

    div[data-testid="stExpander"] {{
        background-color: {WHITE};
        border-radius: 14px;
        border: 1px solid rgba(15, 31, 58, 0.08);
        box-shadow: 0 3px 12px rgba(15, 31, 58, 0.06);
        margin-bottom: 10px;
    }}

    /* Tabs */
    button[data-baseweb="tab"] {{
        font-size: 15px;
        font-weight: 600;
        color: {PURPLE};
    }}

    button[data-baseweb="tab"][aria-selected="true"] {{
        color: {NAVY} !important;
    }}

    div[data-baseweb="tab-highlight"] {{
        background-color: {CORAL} !important;
    }}

    /* Give the dataframe toolbar room so it never overlaps content below */
    div[data-testid="stElementToolbar"] {{
        z-index: 5;
    }}

    </style>
    """,
    unsafe_allow_html=True
)


if not check_password():
    st.stop()


# =========================================================
# HEADER
# =========================================================

st.markdown('<div class="main-title">ASL Meet Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">User Feedback & Analytics Dashboard</div>', unsafe_allow_html=True)


# =========================================================
# FILE UPLOAD
# =========================================================

st.sidebar.markdown('<div class="sidebar-heading">Data Source</div>', unsafe_allow_html=True)

uploaded_file = st.sidebar.file_uploader(
    "Upload JSON Feedback File",
    type=["json"],
    label_visibility="collapsed",
)

st.sidebar.markdown(
    """<div class="sidebar-note">
    Rating, category, sentiment, date and search filters are at the
    top of the main page, above the Overview section.
    </div>""",
    unsafe_allow_html=True
)

if uploaded_file is None:
    st.markdown(
        """
        <div class="info-box">
        <b>Upload your feedback data</b><br><br>
        Select the latest JSON file from the sidebar.
        The dashboard will automatically calculate all
        statistics and charts from the uploaded data.
        </div>
        """,
        unsafe_allow_html=True
    )
    st.stop()


# =========================================================
# LOAD JSON
# =========================================================

try:
    raw_data = json.load(uploaded_file)

    if isinstance(raw_data, list):
        data = raw_data
    elif isinstance(raw_data, dict):
        if "feedback" in raw_data:
            data = raw_data["feedback"]
        elif "data" in raw_data:
            data = raw_data["data"]
        else:
            st.error("JSON format not recognised. Expected a list of feedback records.")
            st.stop()
    else:
        st.error("Invalid JSON format.")
        st.stop()

    df = pd.DataFrame(data)

except Exception as e:
    st.error(f"Unable to read JSON file: {e}")
    st.stop()


# =========================================================
# VALIDATE REQUIRED COLUMNS
# =========================================================

required_columns = ["rating", "categories", "message", "contactOptIn", "timestamp"]
missing_columns = [c for c in required_columns if c not in df.columns]

if missing_columns:
    st.error("The uploaded JSON is missing these fields: " + ", ".join(missing_columns))
    st.stop()


# =========================================================
# DATA CLEANING
# =========================================================

df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

before_drop = len(df)
df = df.dropna(subset=["rating", "timestamp"])
dropped_rows = before_drop - len(df)

df["date"] = df["timestamp"].dt.date
df["hour"] = df["timestamp"].dt.hour
df["day_of_week"] = df["timestamp"].dt.day_name()

df["message"] = df["message"].fillna("").astype(str)
df["message_length"] = df["message"].str.len()

df["categories"] = df["categories"].apply(
    lambda x: x if isinstance(x, list) else ([x] if pd.notna(x) else [])
)

df["rating"] = df["rating"].round().astype(int).clip(1, 5)


# =========================================================
# SENTIMENT ANALYSIS (VADER) — cached so it only runs once
# per unique set of messages, not on every filter change.
# =========================================================

@st.cache_data(show_spinner="Analysing feedback sentiment...")
def score_sentiment(messages: tuple) -> list:
    analyzer = SentimentIntensityAnalyzer()
    return [analyzer.polarity_scores(m)["compound"] for m in messages]


def label_sentiment(compound: float) -> str:
    if compound >= 0.05:
        return "Positive"
    if compound <= -0.05:
        return "Negative"
    return "Neutral"


df["sentiment_score"] = score_sentiment(tuple(df["message"].tolist()))
df["sentiment"] = df["sentiment_score"].apply(label_sentiment)


# =========================================================
# NPS-STYLE SEGMENTATION
# 5-star scale mapped to promoter/passive/detractor bands:
# 5 = Promoter, 4 = Passive, 1-3 = Detractor.
# =========================================================

def nps_segment(rating: int) -> str:
    if rating == 5:
        return "Promoter"
    if rating == 4:
        return "Passive"
    return "Detractor"


df["nps_segment"] = df["rating"].apply(nps_segment)


# =========================================================
# KEYWORD EXTRACTION FROM MESSAGES
# ============================================================

STOPWORDS = set("""
a about above after again against all am an and any are aren't as at be
because been before being below between both but by can't cannot could
couldn't did didn't do does doesn't doing don't down during each few for
from further had hadn't has hasn't have haven't having he he'd he'll he's
her here here's hers herself him himself his how how's i i'd i'll i'm i've
if in into is isn't it it's its itself let's me more most mustn't my
myself no nor not of off on once only or other ought our ours ourselves
out over own same shan't she she'd she'll she's should shouldn't so some
such than that that's the their theirs them themselves then there there's
these they they'd they'll they're they've this those through to too under
until up very was wasn't we we'd we'll we're we've were weren't what
what's when when's where where's which while who who's whom why why's
with won't would wouldn't you you'd you'll you're you've your yours
yourself yourselves it's app really just also lot bit sometimes really
""".split())


def extract_keywords(messages: pd.Series, top_n: int = 15) -> pd.DataFrame:
    counter = collections.Counter()
    for msg in messages:
        words = re.findall(r"[a-zA-Z']+", msg.lower())
        for w in words:
            if len(w) > 2 and w not in STOPWORDS:
                counter[w] += 1
    top = counter.most_common(top_n)
    return pd.DataFrame(top, columns=["Keyword", "Mentions"])


# =========================================================
# FILTERS — MAIN PAGE, ALWAYS VISIBLE
# (moved out of the sidebar so they can't be missed/collapsed)
# =========================================================

rating_options = sorted(df["rating"].unique())
all_categories = sorted(set(c for cats in df["categories"] for c in cats))
sentiment_options = ["Positive", "Neutral", "Negative"]
min_date = df["date"].min()
max_date = df["date"].max()

FILTER_KEYS = [
    "filter_rating", "filter_category", "filter_sentiment",
    "filter_date", "filter_search",
]

with st.expander("🔎  Filters", expanded=True):
    f_col1, f_col2, f_col3 = st.columns(3)

    with f_col1:
        st.markdown('<div class="filter-bar-label">Rating</div>', unsafe_allow_html=True)
        selected_ratings = st.multiselect(
            "Rating", rating_options, default=rating_options,
            key="filter_rating", label_visibility="collapsed"
        )

    with f_col2:
        st.markdown('<div class="filter-bar-label">Category</div>', unsafe_allow_html=True)
        selected_categories = st.multiselect(
            "Category", all_categories, default=all_categories,
            key="filter_category", label_visibility="collapsed"
        )

    with f_col3:
        st.markdown('<div class="filter-bar-label">Sentiment</div>', unsafe_allow_html=True)
        selected_sentiments = st.multiselect(
            "Sentiment", sentiment_options, default=sentiment_options,
            key="filter_sentiment", label_visibility="collapsed"
        )

    f_col4, f_col5 = st.columns([1, 1])

    with f_col4:
        st.markdown('<div class="filter-bar-label">Date Range</div>', unsafe_allow_html=True)
        date_range = st.date_input(
            "Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date,
            key="filter_date", label_visibility="collapsed"
        )

    with f_col5:
        st.markdown('<div class="filter-bar-label">Search Feedback Text</div>', unsafe_allow_html=True)
        keyword_search = st.text_input(
            "Search feedback text", placeholder="e.g. crash, lighting, voice",
            key="filter_search", label_visibility="collapsed"
        )

    if st.button("Reset filters"):
        for k in FILTER_KEYS:
            st.session_state.pop(k, None)
        st.rerun()


# =========================================================
# APPLY FILTERS
# =========================================================

filtered_df = df.copy()

filtered_df = filtered_df[filtered_df["rating"].isin(selected_ratings)]

filtered_df = filtered_df[
    filtered_df["categories"].apply(
        lambda cats: any(c in selected_categories for c in cats)
    )
]

filtered_df = filtered_df[filtered_df["sentiment"].isin(selected_sentiments)]

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
    filtered_df = filtered_df[
        (filtered_df["date"] >= start_date) & (filtered_df["date"] <= end_date)
    ]

if keyword_search.strip():
    filtered_df = filtered_df[
        filtered_df["message"].str.contains(keyword_search.strip(), case=False, na=False)
    ]


if filtered_df.empty:
    st.warning("No feedback matches the selected filters. Try widening your filters above.")
    st.stop()


# =========================================================
# KPI CALCULATIONS
# =========================================================

total_feedback = len(filtered_df)
average_rating = filtered_df["rating"].mean()
median_rating = filtered_df["rating"].median()
positive_percentage = (filtered_df["rating"] >= 4).mean() * 100
contact_optin = filtered_df["contactOptIn"].astype(bool).sum()
contact_optin_pct = filtered_df["contactOptIn"].astype(bool).mean() * 100

promoters_pct = (filtered_df["nps_segment"] == "Promoter").mean() * 100
detractors_pct = (filtered_df["nps_segment"] == "Detractor").mean() * 100
nps_score = promoters_pct - detractors_pct

positive_sentiment_pct = (filtered_df["sentiment"] == "Positive").mean() * 100
negative_sentiment_pct = (filtered_df["sentiment"] == "Negative").mean() * 100

avg_message_length = filtered_df["message_length"].mean()


# =========================================================
# KPI CARDS — always visible, above the tabs
# =========================================================

st.markdown('<div class="section-title">Overview</div>', unsafe_allow_html=True)

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(
        f"""<div class="metric-card navy">
            <div class="metric-title">Total Feedback</div>
            <div class="metric-value">{total_feedback:,}</div>
            <div class="metric-sub">of {len(df):,} total records</div>
        </div>""",
        unsafe_allow_html=True
    )

with col2:
    st.markdown(
        f"""<div class="metric-card">
            <div class="metric-title">Average Rating</div>
            <div class="metric-value">{average_rating:.2f} / 5</div>
            <div class="metric-sub">median {median_rating:.0f} / 5</div>
        </div>""",
        unsafe_allow_html=True
    )

with col3:
    st.markdown(
        f"""<div class="metric-card coral">
            <div class="metric-title">Positive Ratings</div>
            <div class="metric-value">{positive_percentage:.1f}%</div>
            <div class="metric-sub">rated 4 or 5 stars</div>
        </div>""",
        unsafe_allow_html=True
    )

with col4:
    st.markdown(
        f"""<div class="metric-card purple">
            <div class="metric-title">NPS Score</div>
            <div class="metric-value">{nps_score:+.0f}</div>
            <div class="metric-sub">{promoters_pct:.0f}% promoters, {detractors_pct:.0f}% detractors</div>
        </div>""",
        unsafe_allow_html=True
    )

with col5:
    st.markdown(
        f"""<div class="metric-card beige">
            <div class="metric-title">Contact Opt-In</div>
            <div class="metric-value">{contact_optin:,}</div>
            <div class="metric-sub">{contact_optin_pct:.1f}% of respondents</div>
        </div>""",
        unsafe_allow_html=True
    )

col6, col7, col8 = st.columns(3)

with col6:
    st.markdown(
        f"""<div class="metric-card" style="border-left-color:{TEAL}">
            <div class="metric-title">Positive Sentiment</div>
            <div class="metric-value">{positive_sentiment_pct:.1f}%</div>
            <div class="metric-sub">from message text (VADER)</div>
        </div>""",
        unsafe_allow_html=True
    )

with col7:
    st.markdown(
        f"""<div class="metric-card" style="border-left-color:{CORAL}">
            <div class="metric-title">Negative Sentiment</div>
            <div class="metric-value">{negative_sentiment_pct:.1f}%</div>
            <div class="metric-sub">from message text (VADER)</div>
        </div>""",
        unsafe_allow_html=True
    )

with col8:
    st.markdown(
        f"""<div class="metric-card" style="border-left-color:{GREY_GREEN}">
            <div class="metric-title">Avg. Message Length</div>
            <div class="metric-value">{avg_message_length:.0f} chars</div>
            <div class="metric-sub">{dropped_rows} record(s) dropped as invalid</div>
        </div>""",
        unsafe_allow_html=True
    )


# =========================================================
# DERIVED TABLES USED BY MULTIPLE CHARTS
# =========================================================

rating_counts = filtered_df["rating"].value_counts().sort_index().reset_index()
rating_counts.columns = ["Rating", "Count"]

category_df = filtered_df.explode("categories")

category_counts = category_df["categories"].value_counts().reset_index()
category_counts.columns = ["Category", "Count"]

sentiment_counts = filtered_df["sentiment"].value_counts().reset_index()
sentiment_counts.columns = ["Sentiment", "Count"]

nps_counts = filtered_df["nps_segment"].value_counts().reset_index()
nps_counts.columns = ["Segment", "Count"]


# =========================================================
# TABS — each tab is self-contained, so nothing overlaps and
# the page never turns into one giant scroll.
# =========================================================

tab_dist, tab_trends, tab_categories, tab_feedback = st.tabs(
    ["📊  Distribution", "📈  Trends", "🗂️  Categories", "💬  Feedback Explorer"]
)


# ---------------------------------------------------------
# TAB: DISTRIBUTION
# ---------------------------------------------------------

with tab_dist:
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        fig_rating_pie = px.pie(
            rating_counts, names="Rating", values="Count", hole=0.45,
            color="Rating", color_discrete_map=RATING_COLORS,
        )
        fig_rating_pie.update_layout(
            title="Rating Distribution", title_font_color=NAVY,
            paper_bgcolor=WHITE, plot_bgcolor=WHITE, legend_title="Rating"
        )
        fig_rating_pie.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_rating_pie, use_container_width=True)

    with chart_col2:
        fig_category = px.bar(category_counts, x="Category", y="Count", text="Count")
        fig_category.update_layout(
            title="Feedback by Category", title_font_color=NAVY,
            paper_bgcolor=WHITE, plot_bgcolor=WHITE,
            xaxis_title="Category", yaxis_title="Number of Feedback"
        )
        fig_category.update_traces(marker_color=TEAL, textposition="outside")
        st.plotly_chart(fig_category, use_container_width=True)

    chart_col_s1, chart_col_s2 = st.columns(2)

    with chart_col_s1:
        fig_sentiment = px.pie(
            sentiment_counts, names="Sentiment", values="Count", hole=0.45,
            color="Sentiment", color_discrete_map=SENTIMENT_COLORS,
        )
        fig_sentiment.update_layout(
            title="Message Sentiment (VADER)", title_font_color=NAVY,
            paper_bgcolor=WHITE, plot_bgcolor=WHITE
        )
        fig_sentiment.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_sentiment, use_container_width=True)

    with chart_col_s2:
        fig_nps = px.pie(
            nps_counts, names="Segment", values="Count", hole=0.45,
            color="Segment", color_discrete_map=NPS_COLORS,
        )
        fig_nps.update_layout(
            title=f"Promoter / Passive / Detractor  (NPS {nps_score:+.0f})",
            title_font_color=NAVY, paper_bgcolor=WHITE, plot_bgcolor=WHITE
        )
        fig_nps.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_nps, use_container_width=True)


# ---------------------------------------------------------
# TAB: TRENDS
# ---------------------------------------------------------

with tab_trends:
    daily_feedback = filtered_df.groupby("date").size().reset_index(name="Feedback Count")

    fig_trend = px.line(daily_feedback, x="date", y="Feedback Count", markers=True)
    fig_trend.update_layout(
        title="Daily Feedback Volume", title_font_color=NAVY,
        paper_bgcolor=WHITE, plot_bgcolor=WHITE, xaxis_title="Date", yaxis_title="Feedback Count"
    )
    fig_trend.update_traces(line_color=DARK_TEAL, marker_color=CORAL, line_width=3)
    st.plotly_chart(fig_trend, use_container_width=True)

    rating_trend = filtered_df.groupby("date")["rating"].mean().reset_index()
    rating_trend.columns = ["Date", "Average Rating"]
    rating_trend["3-day moving avg"] = rating_trend["Average Rating"].rolling(3, min_periods=1).mean()

    fig_rating_trend = go.Figure()
    fig_rating_trend.add_trace(go.Scatter(
        x=rating_trend["Date"], y=rating_trend["Average Rating"],
        mode="lines+markers", name="Daily average",
        line=dict(color=NAVY, width=2), marker=dict(color=CORAL)
    ))
    fig_rating_trend.add_trace(go.Scatter(
        x=rating_trend["Date"], y=rating_trend["3-day moving avg"],
        mode="lines", name="3-day moving average",
        line=dict(color=TEAL, width=3, dash="dash")
    ))
    fig_rating_trend.update_layout(
        title="Average Rating Over Time", title_font_color=NAVY,
        paper_bgcolor=WHITE, plot_bgcolor=WHITE,
        xaxis_title="Date", yaxis_title="Average Rating",
        yaxis_range=[1, 5]
    )
    st.plotly_chart(fig_rating_trend, use_container_width=True)

    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    heatmap_data = (
        filtered_df.groupby(["day_of_week", "hour"]).size().reset_index(name="Count")
    )
    heatmap_pivot = heatmap_data.pivot(index="day_of_week", columns="hour", values="Count").reindex(day_order)
    heatmap_pivot = heatmap_pivot.reindex(columns=range(24), fill_value=0).fillna(0)

    fig_heatmap = px.imshow(
        heatmap_pivot,
        labels=dict(x="Hour of Day", y="Day of Week", color="Feedback Count"),
        color_continuous_scale=[LIGHT_BG, TEAL, NAVY],
        aspect="auto",
    )
    fig_heatmap.update_layout(
        title="Feedback Volume by Day & Hour", title_font_color=NAVY,
        paper_bgcolor=WHITE, plot_bgcolor=WHITE
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)


# ---------------------------------------------------------
# TAB: CATEGORIES
# ---------------------------------------------------------

with tab_categories:
    chart_col3, chart_col4 = st.columns(2)

    with chart_col3:
        category_rating = category_df.groupby("categories")["rating"].mean().reset_index()
        category_rating.columns = ["Category", "Average Rating"]
        category_rating = category_rating.sort_values("Average Rating")

        fig_category_rating = px.bar(
            category_rating, x="Average Rating", y="Category", orientation="h", text="Average Rating"
        )
        fig_category_rating.update_layout(
            title="Average Rating by Category", title_font_color=NAVY,
            paper_bgcolor=WHITE, plot_bgcolor=WHITE,
            xaxis_title="Average Rating", yaxis_title="", xaxis_range=[0, 5]
        )
        fig_category_rating.update_traces(
            marker_color=PURPLE, texttemplate="%{text:.2f}", textposition="outside"
        )
        st.plotly_chart(fig_category_rating, use_container_width=True)

    with chart_col4:
        category_sentiment = (
            category_df.groupby(["categories", "sentiment"]).size().reset_index(name="Count")
        )
        fig_cat_sentiment = px.bar(
            category_sentiment, x="categories", y="Count", color="sentiment",
            color_discrete_map=SENTIMENT_COLORS, barmode="stack"
        )
        fig_cat_sentiment.update_layout(
            title="Sentiment Mix by Category", title_font_color=NAVY,
            paper_bgcolor=WHITE, plot_bgcolor=WHITE,
            xaxis_title="Category", yaxis_title="Feedback Count", legend_title="Sentiment"
        )
        st.plotly_chart(fig_cat_sentiment, use_container_width=True)

    chart_col5, chart_col6 = st.columns(2)

    with chart_col5:
        keywords_df = extract_keywords(filtered_df["message"])
        if keywords_df.empty:
            st.info("Not enough text to extract keywords for the current filters.")
        else:
            keywords_df = keywords_df.sort_values("Mentions")
            fig_keywords = px.bar(keywords_df, x="Mentions", y="Keyword", orientation="h")
            fig_keywords.update_layout(
                title="Most Mentioned Words in Feedback", title_font_color=NAVY,
                paper_bgcolor=WHITE, plot_bgcolor=WHITE, xaxis_title="Mentions", yaxis_title=""
            )
            fig_keywords.update_traces(marker_color=CORAL)
            st.plotly_chart(fig_keywords, use_container_width=True)

    with chart_col6:
        fig_length = px.box(
            filtered_df, x="rating", y="message_length", color="rating",
            color_discrete_map=RATING_COLORS,
        )
        fig_length.update_layout(
            title="Message Length by Rating", title_font_color=NAVY,
            paper_bgcolor=WHITE, plot_bgcolor=WHITE,
            xaxis_title="Rating", yaxis_title="Message Length (characters)",
            showlegend=False
        )
        st.plotly_chart(fig_length, use_container_width=True)


# ---------------------------------------------------------
# TAB: FEEDBACK EXPLORER
# ---------------------------------------------------------

with tab_feedback:
    display_df = filtered_df[
        ["rating", "categories", "message", "sentiment", "nps_segment", "contactOptIn", "timestamp"]
    ].copy()

    display_df["categories"] = display_df["categories"].apply(lambda x: ", ".join(x))
    display_df = display_df.sort_values("timestamp", ascending=False)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=480,
        column_config={
            "rating": st.column_config.NumberColumn("Rating", min_value=1, max_value=5),
            "categories": st.column_config.TextColumn("Category"),
            "message": st.column_config.TextColumn("User Feedback", width="large"),
            "sentiment": st.column_config.TextColumn("Sentiment"),
            "nps_segment": st.column_config.TextColumn("Segment"),
            "contactOptIn": st.column_config.CheckboxColumn("Contact Opt-In"),
            "timestamp": st.column_config.DatetimeColumn("Date & Time"),
        }
    )

    st.download_button(
        "Download filtered data as CSV",
        data=display_df.to_csv(index=False).encode("utf-8"),
        file_name="asl_feedback_filtered.csv",
        mime="text/csv",
    )


# =========================================================
# FOOTER
# =========================================================

st.markdown("---")
st.caption(
    f"Showing {len(filtered_df):,} of {len(df):,} feedback records from {uploaded_file.name}"
)
