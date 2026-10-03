import json

DATA_FILE = "animeData.js"

def read_existing_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    start = content.find("const animeDatabase = [")
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
    return json.loads(content[start:end]), content, start, end

def main():
    anime_db, content, start, end = read_existing_data()
    
    for anime in anime_db:
        total_eps = int(anime.get("eps", 0) or 0)
        
        current_count = 0
        max_ep = 0
        if "seasons" in anime:
            for season in anime["seasons"].values():
                for ep in season.get("episodes", []):
                    if ep.get("link"):  # Sirf wahi episodes count karo jinka link hai
                        current_count += 1
                        if ep.get("ep", 0) > max_ep:
                            max_ep = ep.get("ep", 0)
        
        if current_count == 0:
            anime["latestUpdate"] = "New Ep Added"
            anime["isSeasonCompleted"] = False
        elif total_eps > 0 and current_count >= total_eps:
            anime["latestUpdate"] = "Completed"
            anime["isSeasonCompleted"] = True
        else:
            anime["latestUpdate"] = f"EP {max_ep} Added"
            anime["isSeasonCompleted"] = False
        
        print(f"{anime['name']}: {anime['latestUpdate']} (Total: {total_eps}, Added: {current_count})")
    
    new_db = json.dumps(anime_db, indent=4, ensure_ascii=False)
    new_content = content[:start] + new_db + content[end:]
    
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)
    
    print("\n✅ Saare badges reset ho gaye!")

if __name__ == "__main__":
    main()
