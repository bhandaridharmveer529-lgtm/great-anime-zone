import os
import re
import json
import base64
import requests
from datetime import datetime

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = "bhandaridharmveer529-lgtm/great-anime-zone"
GITHUB_FILE = "animeData.js"
LINKS_FILE = "links.txt"

def get_github_file():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
    r = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    if r.status_code != 200:
        return None, None
    d = r.json()
    return requests.get(d["download_url"]).text, d["sha"]

def update_github(content, sha, msg):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
    enc = base64.b64encode(content.encode()).decode()
    r = requests.put(url, headers={"Authorization": f"token {GITHUB_TOKEN}"},
                     json={"message": msg, "content": enc, "sha": sha})
    return r.status_code

def main():
    # 1. Links padho
    links = {}
    if not os.path.exists(LINKS_FILE):
        return
    with open(LINKS_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) != 4:
                continue
            anime_name, ep, stream, download = parts
            m = re.search(r'S(\d+)E(\d+)', ep, re.IGNORECASE)
            if not m:
                continue
            season = int(m.group(1))
            ep_num = int(m.group(2))
            if anime_name not in links:
                links[anime_name] = {}
            if season not in links[anime_name]:
                links[anime_name][season] = []
            links[anime_name][season].append({
                "ep": ep_num, "link": stream, "download": download
            })

    if not links:
        print("Koi link nahi mila")
        return

    # 2. AnimeData padho
    content, sha = get_github_file()
    if not content:
        return
    start = content.find("const animeDatabase = [")
    start = content.find("[", start)
    depth, end = 0, -1
    for i in range(start, len(content)):
        if content[i] == "[":
            depth += 1
        elif content[i] == "]":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    anime_db = json.loads(content[start:end])

    added_count = 0

    for anime_name, seasons in links.items():
        # 🎯 STRICT MATCH: Sirf exact naam dhundho
        found_anime = None
        for a in anime_db:
            if a.get("name", "").strip().lower() == anime_name.strip().lower():
                found_anime = a
                break
                
        if not found_anime:
            print(f"❌ Skip: Exact match nahi mila '{anime_name}'")
            continue

        print(f"✅ Found: {anime_name}")

        if "seasons" not in found_anime:
            found_anime["seasons"] = {}

        for season_num, eps in seasons.items():
            sk = f"s{season_num}"
            
            # 🎯 CRITICAL FIX: Agar anime S2 hai, lekin S1 me ghusne ki koshish kar raha hai, toh ROKO
            if season_num == 2 and ("season 2" not in anime_name.lower() and " ii" not in anime_name.lower()):
                print(f"❌ Galti pakdi: S1 me S2 ka link daalne ki koshish. Skip.")
                continue
            
            # Agar block pehle se nahi hai, toh naya banao
            if sk not in found_anime["seasons"]:
                found_anime["seasons"][sk] = {
                    "seasonName": f"Season {season_num}",
                    "seasonZip": "",
                    "episodes": []
                }
            
            existing_eps = found_anime["seasons"][sk]["episodes"]
            for new_ep in eps:
                existing = next((e for e in existing_eps if e["ep"] == new_ep["ep"]), None)
                if existing:
                    existing["link"] = new_ep["link"]
                    existing["download"] = new_ep["download"]
                else:
                    existing_eps.append({
                        "ep": new_ep["ep"],
                        "title": f"Episode {new_ep['ep']}",
                        "link": new_ep["link"],
                        "download": new_ep["download"]
                    })
                added_count += 1
            existing_eps.sort(key=lambda x: x["ep"])

        # Time update karo
        found_anime["addedDate"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 3. Save karo
    new_db = json.dumps(anime_db, indent=4, ensure_ascii=False)
    new_content = content[:start] + new_db + content[end:]
    s = update_github(new_content, sha, f"Strict Update: {added_count} eps")
    print(f"GitHub: {'Updated!' if s in [200,201] else 'Failed: ' + str(s)}")

if __name__ == "__main__":
    main()
    import reset_badges 
    reset_badges.main()
