import json
import os
import requests
from datetime import datetime

# Link/File ke liye Short Name Generator
def shorten_title(title, ep_num, quality="720P"):
    words = title.split()
    acronym = ".".join([w[0].upper() for w in words if w.isalnum()])
    return f"{acronym}. Ep{ep_num}. {quality}"

# Self-Healing: Broken Link Detector
def is_link_working(url):
    try:
        res = requests.head(url, timeout=5, allow_redirects=True)
        return res.status_code == 200
    except Exception:
        return False

def run_auto_updater():
    file_path = "episodes.js"
    data = {}

    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                raw_content = f.read().replace("const allAnimeData = ", "").rstrip(";")
                data = json.loads(raw_content)
            except Exception:
                data = {}

    # Main Anime Name
    full_anime_title = "The Elusive Samurai"
    ep_num = 1
    
    short_link_name = shorten_title(full_anime_title, ep_num)

    # Video Player Embed Links
    server1_url = "https://morencius.com/embed/0u2nsg1qq574"
    server2_url = "https://streamtape.com/e/backup_sample"

    # Auto Healing Check
    if not is_link_working(server1_url):
        print(f"⚠️ Server 1 broken! Replacing with fallback link...")
        server1_url = "https://morencius.com/embed/working_fallback_link"

    # Anime Object Entry (Badge aur Timestamp ke sath)
    if full_anime_title not in data:
        data[full_anime_title] = {
            "title": full_anime_title,
            "banner": f"banners/{full_anime_title.lower().replace(' ', '_')}.jpg",
            "lang": "Hindi Dubbed",
            "latest_badge": f"EP {ep_num} Added",
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "seasons": {
                "s1": {
                    "seasonName": "Season 1",
                    "seasonZip": "#",
                    "episodes": []
                }
            }
        }

    ep_list = data[full_anime_title]["seasons"]["s1"]["episodes"]
    
    # Episode Add / Update
    ep_updated = False
    for ep in ep_list:
        if ep["ep"] == f"Ep {ep_num}":
            ep["watch"] = [server1_url, server2_url]
            ep["title"] = short_link_name
            ep_updated = True
            break

    if not ep_updated:
        ep_list.append({
            "ep": f"Ep {ep_num}",
            "title": short_link_name,
            "watch": [server1_url, server2_url],
            "download": server1_url
        })

    # Badge aur Time refresh karein jab bhi koi episode update ho
    data[full_anime_title]["latest_badge"] = f"EP {ep_num} Added"
    data[full_anime_title]["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"const allAnimeData = {json.dumps(data, indent=4, ensure_ascii=False)};")
    
    print(f"✅ Full Name '{full_anime_title}' preserved. Episode '{short_link_name}' added with badge 'EP {ep_num} Added'.")

if __name__ == "__main__":
    run_auto_updater()
    
