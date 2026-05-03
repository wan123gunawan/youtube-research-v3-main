import streamlit as st
import requests
from datetime import datetime, timedelta, timezone
import re

# ===== CONFIG =====
st.set_page_config(page_title="YouTube Research Tool PRO", layout="wide")

st.title("🔍 YouTube Research Tool PRO")
st.caption("Anti error • Riset kompetitor • Deteksi video viral")

# ===== INPUT =====
api_key = st.text_input("🔑 API Key YouTube", type="password")
query = st.text_input("🔎 Keyword", value="anak anak")
max_results = st.slider("📊 Jumlah video", 5, 50, 10)
days = st.slider("⏱️ Dalam berapa hari terakhir?", 1, 30, 7)

video_filter = st.selectbox(
    "🎬 Filter Tipe Video",
    ["Semua", "Short (<60 detik)", "Long (>60 detik)"]
)

# ===== FILTER DURASI (UP TO 2 JAM) =====
min_duration = st.number_input("Durasi minimum (detik)", 0, 7200, 0)
max_duration = st.number_input("Durasi maksimum (detik)", 0, 7200, 7200)

# ===== HELPER =====
def safe_int(value):
    try:
        return int(value)
    except:
        return 0

def safe_request(url, params):
    try:
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 200:
            return res.json()
        else:
            return {}
    except:
        return {}

def is_short(duration):
    return duration <= 60

# ===== API FUNCTIONS =====
def search_youtube(api_key, query, max_results, days):
    url = "https://www.googleapis.com/youtube/v3/search"

    now = datetime.now(timezone.utc)
    past = now - timedelta(days=days)

    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "publishedAfter": past.isoformat(),
        "key": api_key
    }

    return safe_request(url, params)

def get_video_details(api_key, video_ids):
    if not video_ids:
        return {}

    url = "https://www.googleapis.com/youtube/v3/videos"

    params = {
        "part": "statistics,contentDetails",
        "id": ",".join(video_ids),
        "key": api_key
    }

    return safe_request(url, params)

def get_channel_details(api_key, channel_ids):
    if not channel_ids:
        return {}

    url = "https://www.googleapis.com/youtube/v3/channels"

    params = {
        "part": "statistics",
        "id": ",".join(channel_ids),
        "key": api_key
    }

    return safe_request(url, params)

# ===== PARSE DURATION =====
def parse_duration(duration):
    try:
        if not duration:
            return 0

        pattern = re.compile(r'^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$')
        match = pattern.match(duration)

        if not match:
            return 0

        hours = safe_int(match.group(1))
        minutes = safe_int(match.group(2))
        seconds = safe_int(match.group(3))

        return hours * 3600 + minutes * 60 + seconds
    except:
        return 0

# ===== MAIN =====
if st.button("🚀 Cari Sekarang"):
    if not api_key:
        st.warning("Masukkan API key dulu!")
        st.stop()

    with st.spinner("Mengambil data..."):
        data = search_youtube(api_key, query, max_results, days)
        items = data.get("items", [])

        if not items:
            st.warning("Tidak ada video ditemukan")
            st.stop()

        # ===== VIDEO IDS =====
        video_ids = [
            item.get("id", {}).get("videoId")
            for item in items
            if item.get("id", {}).get("videoId")
        ]

        # ===== VIDEO DETAILS =====
        details = get_video_details(api_key, video_ids)

        stats_map = {}
        for d in details.get("items", []):
            vid = d.get("id")
            stats = d.get("statistics", {})
            duration_raw = d.get("contentDetails", {}).get("duration")

            stats_map[vid] = {
                "views": safe_int(stats.get("viewCount")),
                "likes": safe_int(stats.get("likeCount")),
                "comments": safe_int(stats.get("commentCount")),
                "duration": parse_duration(duration_raw)
            }

        # ===== CHANNEL IDS =====
        channel_ids = list(set([
            item.get("snippet", {}).get("channelId")
            for item in items
            if item.get("snippet", {}).get("channelId")
        ]))

        # ===== CHANNEL DETAILS =====
        channel_data = get_channel_details(api_key, channel_ids)

        channel_map = {
            c.get("id"): safe_int(c.get("statistics", {}).get("subscriberCount"))
            for c in channel_data.get("items", [])
        }

        st.success(f"Ditemukan {len(items)} video")

        # ===== KUMPULKAN DATA =====
        results = []

        for item in items:
            snippet = item.get("snippet", {})
            vid = item.get("id", {}).get("videoId")

            if not vid:
                continue

            stat = stats_map.get(vid, {})
            duration = stat.get("duration", 0)

            # ===== FILTER SHORT / LONG =====
            if video_filter == "Short (<60 detik)" and not is_short(duration):
                continue
            elif video_filter == "Long (>60 detik)" and is_short(duration):
                continue

            # ===== FILTER DURASI (MAX 2 JAM) =====
            if duration < min_duration or duration > max_duration:
                continue

            title = snippet.get("title", "No Title")
            channel = snippet.get("channelTitle", "Unknown")
            channel_id = snippet.get("channelId")

            views = stat.get("views", 0)
            likes = stat.get("likes", 0)
            comments = stat.get("comments", 0)
            subs = channel_map.get(channel_id, 0)

            viral_rate = (views / subs) if subs > 0 else 0
            engagement = ((likes + comments) / views * 100) if views > 0 else 0

            video_type = "⚡ Short" if duration <= 60 else "🎬 Long"

            results.append({
                "title": title,
                "channel": channel,
                "subs": subs,
                "views": views,
                "likes": likes,
                "comments": comments,
                "viral_rate": viral_rate,
                "engagement": engagement,
                "video_type": video_type,
                "duration_sec": duration,
                "url": f"https://youtube.com/watch?v={vid}"
            })

        # ===== SORT PALING VIRAL =====
        results = sorted(
            results,
            key=lambda x: (x["viral_rate"], x["engagement"]),
            reverse=True
        )

        # ===== OUTPUT =====
        for r in results:
            st.markdown(f"### {r['video_type']} - 🎬 {r['title']}")
            st.write(f"📺 Channel: {r['channel']}")
            st.write(f"👥 Subscriber: {r['subs']:,}")
            st.write(f"👁️ Views: {r['views']:,}")
            st.write(f"⏱️ Durasi: {r['duration_sec']} detik")
            st.write(f"🔥 Viral Rate: {r['viral_rate']:.2f}x")
            st.write(f"💬 Engagement: {r['engagement']:.2f}%")
            st.markdown(f"[▶️ Tonton Video]({r['url']})")
            st.divider()