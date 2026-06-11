#!/usr/bin/env python3
"""Character-led brand assets for The Red Mancunian, built around the hero
illustration (hero-06-roar). Composites the real artwork with PIL.
Outputs: logo-avatar.png, banner.png, ../thumbnails/thumb-ep1..3.png"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
HERO = os.path.join(HERE, "character", "hero-06-roar.jpg")
FONTS = os.path.join(HERE, "fonts")
def font(name, size): return ImageFont.truetype(os.path.join(FONTS, name), size)

src = Image.open(HERO).convert("RGB")
CORAL = src.getpixel((12, 12))
RED   = (198, 36, 30)
DRED  = (120, 20, 20)
WHITE = (255, 255, 255)
CREAM = (255, 226, 222)
INK   = (22, 14, 14)

def circle_mask(size, r=None, ss=4):
    big = size*ss
    m = Image.new("L", (big, big), 0)
    rr = (big//2) if r is None else r*ss
    ImageDraw.Draw(m).ellipse([big//2-rr, big//2-rr, big//2+rr, big//2+rr], fill=255)
    return m.resize((size, size), Image.LANCZOS)

def hgrad(w, h, stops):
    """Fast horizontal gradient via a 1px-tall row resized up."""
    def lerp(a,b,t): return tuple(int(a[i]+(b[i]-a[i])*t) for i in range(3))
    row = Image.new("RGB", (w, 1)); px = row.load()
    for x in range(w):
        t = x/(w-1); col = stops[-1][1]
        for i in range(len(stops)-1):
            p0,c0 = stops[i]; p1,c1 = stops[i+1]
            if p0 <= t <= p1:
                col = lerp(c0,c1,(t-p0)/(p1-p0) if p1>p0 else 0); break
        px[x,0] = col
    return row.resize((w, h))

SPLAT = [(0.12,0.18,40),(0.22,0.62,26),(0.08,0.78,30),(0.30,0.40,18),
         (0.70,0.20,34),(0.82,0.55,24),(0.91,0.30,40),(0.60,0.80,20),
         (0.45,0.12,16),(0.88,0.78,30),(0.05,0.45,22),(0.50,0.90,18)]
def splatter(img, color=DRED, alpha=60):
    w,h = img.size
    ov = Image.new("RGBA",(w,h),(0,0,0,0)); d=ImageDraw.Draw(ov)
    for fx,fy,r in SPLAT:
        x,y=int(fx*w),int(fy*h)
        d.ellipse([x-r,y-r,x+r,y+r],fill=color+(alpha,))
        for ox,oy,rr in [(r,r,r//3),(-r,r//2,r//4),(r//2,-r,r//5)]:
            d.ellipse([x+ox-rr,y+oy-rr,x+ox+rr,y+oy+rr],fill=color+(alpha,))
    img.alpha_composite(ov)

def feather_left(img, fade):
    w,h = img.size
    grow = Image.new("L",(w,1)); gp=grow.load()
    for x in range(w): gp[x,0] = int(255*min(x,fade)/fade) if fade else 255
    mask = grow.resize((w,h))
    img = img.convert("RGBA")
    img.putalpha(ImageChops.multiply(img.split()[3], mask))
    return img

def text(d, xy, s, fnt, fill, anchor="la", stroke=0, sfill=INK, ls=0):
    if ls==0:
        d.text(xy,s,font=fnt,fill=fill,anchor=anchor,stroke_width=stroke,stroke_fill=sfill); return
    x,y=xy
    for ch in s:
        d.text((x,y),ch,font=fnt,fill=fill,anchor="la",stroke_width=stroke,stroke_fill=sfill)
        x += d.textlength(ch,font=fnt)+ls

# ---------- AVATAR / BADGE ----------
def make_badge(size, img=src):
    cv=Image.new("RGBA",(size,size),(0,0,0,0)); c=size//2
    ring=max(2,size//146)
    rs=[(c,INK),(c-ring,WHITE),(c-ring*2,RED),(c-ring*6,WHITE),(c-ring*7,CORAL)]
    for r,col in rs:
        cv=Image.composite(Image.new("RGBA",(size,size),col+(255,)),cv,circle_mask(size,r=r))
    rin=c-ring*7
    char=ImageOps.fit(img,(rin*2,rin*2),Image.LANCZOS,centering=(0.5,0.40))
    char.putalpha(circle_mask(rin*2,r=rin))
    cv.alpha_composite(char,(c-rin,c-rin))
    return cv

def avatar(size=1024):
    make_badge(size).save(os.path.join(HERE,"logo-avatar.png")); print("wrote logo-avatar.png")

# ---------- WORDMARK (transparent, for overlays) ----------
def wordmark():
    W,H=1500,520
    cv=Image.new("RGBA",(W,H),(0,0,0,0))
    cv.alpha_composite(make_badge(470),(10,25))
    d=ImageDraw.Draw(cv)
    text(d,(520,70),"THE RED",font("Anton.ttf",150),WHITE,stroke=9)
    text(d,(520,225),"MANCUNIAN",font("Anton.ttf",150),RED,stroke=9,sfill=WHITE)
    text(d,(524,405),"THE MANCUNIAN WAY",font("BebasNeue.ttf",48),CREAM,ls=14,stroke=2)
    cv.save(os.path.join(HERE,"logo-wordmark.png")); print("wrote logo-wordmark.png")

# ---------- BANNER ----------
def banner():
    W,H=2560,1440
    cv=hgrad(W,H,[(0.0,DRED),(0.30,(150,30,28)),(0.58,CORAL),(1.0,CORAL)]).convert("RGBA")
    splatter(cv,DRED,55)
    s=1620; ch=feather_left(src.resize((s,s),Image.LANCZOS),560)
    cv.alpha_composite(ch,(W-s+120,H//2-s//2+10))
    splatter(cv,DRED,35)
    d=ImageDraw.Draw(cv)
    text(d,(560,468),"THE RED",font("Anton.ttf",172),WHITE,stroke=11)
    text(d,(560,648),"MANCUNIAN",font("Anton.ttf",172),RED,stroke=11,sfill=WHITE)
    text(d,(566,852),"WE DON'T BUY GLORY. WE BUILD IT.",font("BebasNeue.ttf",58),WHITE,ls=10)
    text(d,(566,924),"FOOTBALL MANAGER 2026  ·  THE MANCUNIAN WAY",font("BebasNeue.ttf",40),CREAM,ls=7)
    cv.convert("RGB").save(os.path.join(HERE,"banner.png")); print("wrote banner.png")

# ---------- THUMBNAILS ----------
def thumb(out, hero, epno, kicker, lines, sub, yoff=40):
    W,H=1280,720
    himg=Image.open(os.path.join(HERE,"character",hero)).convert("RGB")
    coral=himg.getpixel((12,12))          # match this pose's own background -> seamless blend
    cv=hgrad(W,H,[(0.0,DRED),(0.30,(150,30,28)),(0.62,coral),(1.0,coral)]).convert("RGBA")
    splatter(cv,DRED,55)
    ov=Image.new("RGBA",(W,H),(0,0,0,0))
    ImageDraw.Draw(ov).text((1245,150),epno,font=font("Anton.ttf",470),fill=(255,255,255,24),anchor="ra")
    cv.alpha_composite(ov)
    s=860; ch=feather_left(himg.resize((s,s),Image.LANCZOS),300)
    cv.alpha_composite(ch,(W-s+70,H-s+yoff))
    d=ImageDraw.Draw(cv)
    text(d,(70,66),kicker,font("BebasNeue.ttf",40),CREAM,ls=6)
    y=146
    for txt,col in lines:
        text(d,(62,y),txt,font("Anton.ttf",130),col,stroke=9,sfill=INK if col!=INK else WHITE)
        y+=126
    d.rectangle([70,y+8,222,y+22],fill=WHITE)
    text(d,(70,y+46),sub,font("BebasNeue.ttf",44),WHITE,ls=2,stroke=2)
    cv.convert("RGB").save(out); print("wrote",os.path.basename(out))

def thumbs():
    t=os.path.join(HERE,"..","thumbnails")
    # matched pose per episode emotion
    thumb(os.path.join(t,"thumb-ep1.png"),"hero-04-confident.jpg","1","THE MANCUNIAN WAY",
          [("NO",WHITE),("SIGNINGS.",WHITE)],"REBUILDING WITH ACADEMY KIDS ONLY",yoff=70)
    thumb(os.path.join(t,"thumb-ep2.png"),"hero-01-react.jpg","2","THE MANCUNIAN WAY",
          [("BETTER",WHITE),("THAN £100M?",RED)],"MY FIRST WONDERKID HAS ARRIVED",yoff=40)
    thumb(os.path.join(t,"thumb-ep3.png"),"hero-06-roar.jpg","3","THE MANCUNIAN WAY",
          [("MUST",WHITE),("WIN.",RED)],"THIS RESULT COULD END THE SAVE",yoff=40)

if __name__=="__main__":
    avatar(); wordmark(); banner(); thumbs()
    print("done")
