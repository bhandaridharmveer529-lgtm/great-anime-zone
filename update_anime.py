import json
import os
import requests
import time
from datetime import datetime

DATA_FILE = "animeData.js"
NAMES_FILE = "anime_names.txt"
ANILIST_URL = "https://graphql.anilist.co"

def read_names():
    if not os.path.exists(NAMES_FILE):
        print(f"❌ {NAMES_FILE} nahi mili")
        return []
    with open(NAMES_FILE, "r", encoding="utf-8") as f:
        names = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    return names

def search_anime(name):
    query = """
    query ($search: String) {
      Media (search: $search, type: ANIME, isAdult: false) {
        id
        title { romaji english native }
        description
        coverImage { large medium }
        bannerImage
        averageScore
        popularity
        episodes
        genres
        seasonYear
        status
      }
    }"""
    try:
        res = requests.post(ANILIST_URL, json={"query": query, "variables": {"search": name}}, timeout=20)
        data = res.json()
        return data.get("data", {}).get("Media")
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

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
                "episodes": [{"ep": 1, "title": "Episode 1", "link": ""}]
            }
        },
        "isNew": is_new,
        "isTrending": True
    }

def read_existing_data():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        start = content.find("const animeDatabase = [")
        if start == -1:
            return []
        start = content.find("[", start)
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
        return json.loads(content[start:end])
    except Exception as e:
        print(f"⚠️ Read error: {e}")
        return []

# YAHAN CHANGE KIYA GAYA HAI - Naya save_data function
def save_data(existing, new_anime):
    existing_map = {a.get("name", "").lower(): a for a in existing}
    added_count = 0
    updated_count = 0
    
    for anime in new_anime:
        name_key = anime["name"].lower()
        if name_key not in existing_map:
            # Naya anime add karo
            existing.append(anime)
            existing_map[name_key] = anime
            added_count += 1
        else:
            # Purane anime me sirf banner update karo (agar khali hai)
            old_anime = existing_map[name_key]
            if not old_anime.get("banner") and anime.get("banner"):
                old_anime["banner"] = anime["banner"]
                updated_count += 1
    
    if added_count == 0 and updated_count == 0:
        print("ℹ️ Koi naya anime ya banner update nahi mila")
        return 0
        
    output = f"const animeDatabase = {json.dumps(existing, indent=4, ensure_ascii=False)};\n"
    
    # Purana heroSlides wala data preserve karo
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            old = f.read()
        hs_start = old.find("const heroSlides =")
        if hs_start != -1:
            output += "\n" + old[hs_start:]
            
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        f.write(output)
        
    print(f"✅ {added_count} naye anime add hue, {updated_count} purane update hue!")
    return added_count + updated_count

def run_auto_updater():
    print("🚀 Anime Auto Updater (Name-based)\n")
    names = read_names()
    if not names:
        print("❌ anime_names.txt khali hai")
        return
    print(f"📝 {len(names)} naam mile\n")
    existing = read_existing_data()
    print(f"📊 Existing: {len(existing)} anime\n")
    found_anime = []
    for i, name in enumerate(names):
        print(f"[{i+1}/{len(names)}] Searching: {name}")
        anime = search_anime(name)
        if anime:
            found_anime.append(anime)
            print(f"  ✅ Mil gaya: {anime['title'].get('romaji', '')}")
        else:
            print(f"  ❌ Nahi mila")
        time.sleep(1)
    if not found_anime:
        print("\n❌ Kuch nahi mila")
        return
    base_id = int(datetime.now().timestamp()) % 100000
    converted = [convert_to_our_format(a, base_id + i) for i, a in enumerate(found_anime)]
    count = save_data(existing, converted)
    print(f"\n✅ Done! {count} anime update/add hue.")

if __name__ == "__main__":
    run_auto_updater()
