import urllib.parse, urllib.request, os, sys
BASE = ("bold comic vector illustration, clean thick bold linework, cel shaded, high contrast, "
        "dynamic energy splatter accents, dusty rose pink background, modern football fan illustration, "
        "vibrant, single character, centered, waist up")
SUBJ = ("a young West African Manchester United football superfan, deep brown skin, voluminous afro hair, "
        "face painted bold red like a passionate ultra, round mirrored sunglasses, "
        "wearing a red and white football training jacket")
POSES = [
 ("hero-react", "both hands pressed to the sides of his head in an ecstatic disbelief reaction, mouth open mid-roar"),
 ("tension",    "both hands clutching his head in nervous tension while watching a match, anxious wide expression"),
 ("celebrate",  "both arms thrown up celebrating a goal, screaming with pure joy"),
 ("confident",  "arms crossed, proud confident stance, slight smirk, chin up"),
 ("point",      "pointing directly at the viewer, passionate intense expression"),
 ("roar",       "fists clenched, leaning forward roaring with excitement"),
]
out = os.path.dirname(os.path.abspath(__file__))
for i,(name,pose) in enumerate(POSES):
    prompt = f"{SUBJ}, {pose}. {BASE}"
    enc = urllib.parse.quote(prompt)
    seed = i*7+11
    url = f"https://image.pollinations.ai/prompt/{enc}?width=1024&height=1024&nologo=true&model=flux&seed={seed}"
    dst = os.path.join(out, f"hero-{i+1:02d}-{name}.jpg")
    try:
        urllib.request.urlretrieve(url, dst)
        print(f"OK  hero-{i+1:02d}-{name}.jpg  ({os.path.getsize(dst)//1024} KB)")
    except Exception as e:
        print(f"ERR hero-{i+1:02d}-{name}: {e}")
