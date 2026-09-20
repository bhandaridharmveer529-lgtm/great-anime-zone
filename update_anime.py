import json
import os
import requests
from datetime import datetime

# ============================================
# CONFIG
# ============================================
DATA_FILE = "animeData.js"
ANILIST_URL = "https://graphql.anilist.co"

# ============================================
# 1. ANILIST SE ANIME LAO
# ============================================
def fetch_from_anilist(sort="TRENDING_DESC", status=None, per_page=10):
    query = """
    query ($sort: [MediaSort], $status: MediaStatus, $perPage: Int) {
      Page (page: 1, perPage: $perPage) {
        media (type: ANIME, sort: $sort, status: $status) {
          id
          title { romaji english native }
          description
          coverImage { large medium }
          bannerImage
          averageScore
          episodes
          genres
          seasonYear
          status
        }
      }
    }"""
    variables = {"sort": [sort], "status": status, "perPage": per_page}
    
    try:
        res = requests.post(ANILIST_URL, json={"query": query, "variables": variables}, timeout=15)
        data = res.json()
        return data.get("data", {}).get("Page", {}).get("media", [])
    except Exception as e:
        print(f"❌ AniList error: {e}")
        return []

# ============================================
# 2. SELF-HEALING: BROKEN LINK CHECK
# ============================================
def is_link_working(url):
    if not url or url == "#":
        return False
    try:
        res = requests.head(url, timeout=5, allow_redirects=True)
        return res.status_code == 200
    except Exception:
        return False

# ============================================
# 3. ANILIST DATA KO HAMARE FORMAT ME BADLO
# ============================================
def convert_to_our_format(anime, base_id):
    title = anime.get("title", {}).get("english") or \
            anime.get("title", {}).get("romaji") or \
            anime.get("title", {}).get("native") or "Unknown"
    
    year = str(anime.get("seasonYear") or "2024")
    eps = str(anime.get("episodes") or "?")
    rating = str(round((anime.get("averageScore") or 85) / 10, 1))
    img = anime.get("coverImage", {}).get("large") or anime.get("coverImage", {}).get("medium") or ""
    banner = anime.get("bannerImage") or img
    desc = (anime.get("description") or "").replace("<br>", " ").replace("<i>", "").replace("</i>", "")
    desc = desc.replace("<b>", "").replace("</b>", "").strip()
    genres = anime.get("genres") or ["Action"]
    is_new = anime.get("status") == "RELEASING"
    
    return {
        "id": base_id,
        "name": title,
        "title": title,
        "banner": banner,
        "img": img,
        "sub": "Hindi Dubbed",
        "lang": "Hindi Dubbed",
        "rating": rating,
        "year": year,
        "eps": eps,
        "addedDate": datetime.now().strftime("%Y-%m-%d"),
        "latestUpdate": "New Ep Added" if is_new else "Completed",
        "isSeasonCompleted": not is_new,
        "desc": desc,
        "genres": genres,
        "genre": genres[0] if genres else "Action",
        "seasons": {
            "s1": {
                "seasonName": "Season 1",
                "seasonZip": "",
                "episodes": [
                    {"ep": 1, "title": "Episode 1", "link": ""}
                ]
            }
        },
        "isNew": is_new,
        "isTrending": True
    }

# ============================================
# 4. ANIMEDATA.JS READ KARO
# ============================================
def read_existing_data():
    if not os.path.exists(DATA_FILE):
        return []
    
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        
        # animeDatabase array nikaalo
        start = content.find("const animeDatabase = [")
        if start == -1:
            return []
        
        start = content.find("[", start)
        # bracket matching se end dhoondo
        depth = 0
        end = -1
        for i in range(start, len(content)):
            if content[i] == "[":
                depth += 1
            elif content[i] == "]":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        
        if end == -1:
            return []
        
        array_str = content[start:end]
        return json.loads(array_str)
    except Exception as e:
        print(f"⚠️ Read error: {e}")
        return []

# ============================================
# 5. ANIMEDATA.JS ME SAVE KARO
# ============================================
def save_data(existing, new_anime):
    # Duplicate check
    existing_names = {a.get("name", "").lower() for a in existing}
    added = []
    
    for anime in new_anime:
        if anime["name"].lower() not in existing_names:
            existing.append(anime)
            added.append(anime)
            existing_names.add(anime["name"].lower())
    
    if not added:
        print("ℹ️ Koi naya anime nahi mila")
        return 0
    
    # File likho
    output = f"const animeDatabase = {json.dumps(existing, indent=4, ensure_ascii=False)};\n"
    
    # heroSlides preserve karo agar hai
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            old = f.read()
        hs_start = old.find("const heroSlides =")
        if hs_start != -1:
            output += "\n" + old[hs_start:]
    
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        f.write(output)
    
    print(f"✅ {len(added)} naye anime add hue!")
    return len(added)

# ============================================
# 6. MAIN FUNCTION
# ============================================
def run_auto_updater():
    print("🚀 Anime Auto Updater shuru...\n")
    
    existing = read_existing_data()
    print(f"📊 Existing anime: {len(existing)}")
    
    all_anime = []
    
    # 1. Trending
    print("🔥 Trending fetch...")
    all_anime.extend(fetch_from_anilist(sort="TRENDING_DESC", per_page=10))
    
    # 2. Famous
    print("⭐ Famous fetch...")
    all_anime.extend(fetch_from_anilist(sort="POPULARITY_DESC", per_page=10))
    
    # 3. Naye releasing
    print("🆕 New releases fetch...")
    all_anime.extend(fetch_from_anilist(sort="START_DATE_DESC", status="RELEASING", per_page=10))
    
    if not all_anime:
        print("❌ Kuch nahi mila")
        return
    
    # Duplicate hataao (AniList ID se)
    unique = {}
    for a in all_anime:
        if a["id"] not in unique:
            unique[a["id"]] = a
    unique_anime = list(unique.values())
    
    print(f"📥 Total {len(unique_anime)} unique anime mile")
    
    # Format me badlo
    base_id = int(datetime.now().timestamp()) % 100000
    converted = [convert_to_our_format(a, base_id + i) for i, a in enumerate(unique_anime)]
    
    # Save karo
    count = save_data(existing, converted)
    
    print(f"\n✅ Done! {count} naye anime add hue.")

if __name__ == "__main__":
    run_auto_updater()
