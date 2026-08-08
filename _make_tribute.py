from PIL import Image, ImageDraw

S = 1024
# ---- 渐变底（深图书绿）----
top = (13, 71, 54)     # 0d4736
bot = (20, 98, 74)     # 14624a
base = Image.new("RGBA", (S, S))
bd = base.load()
for y in range(S):
    t = y / (S - 1)
    r = int(top[0] + (bot[0] - top[0]) * t)
    g = int(top[1] + (bot[1] - top[1]) * t)
    b = int(top[2] + (bot[2] - top[2]) * t)
    for x in range(S):
        bd[x, y] = (r, g, b, 255)

# 圆角蒙版
mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).rounded_rectangle([0, 0, S, S], radius=232, fill=255)
img = Image.composite(base, Image.new("RGBA", (S, S), (0, 0, 0, 0)), mask)
d = ImageDraw.Draw(img)

# ---- 翻开的书（奶白，向上图致敬的「馆藏」意象）----
cream = (243, 237, 224, 255)
left = [(228, 432), (512, 500), (512, 706), (228, 694)]
right = [(796, 432), (512, 500), (512, 706), (796, 694)]
d.polygon(left, fill=cream)
d.polygon(right, fill=cream)
# 书脊阴影
d.line([(512, 500), (512, 706)], fill=(178, 168, 148, 255), width=7)
# 页线（淡）
for i in range(3):
    yy = 540 + i * 42
    d.line([(262, yy - 8), (486, yy + 6)], fill=(201, 193, 172, 200), width=4)
    d.line([(538, yy + 6), (762, yy - 8)], fill=(201, 193, 172, 200), width=4)

# ---- 开放数据节点（金色星座，寓意数据从馆藏中流出）----
gold = (227, 179, 65, 255)
hub = (512, 372)
nodes = [(300, 300), (512, 248), (724, 300), (392, 222), (632, 222)]
# 连接线（先画，节点压在上）
for n in nodes:
    d.line([hub, n], fill=(227, 179, 65, 170), width=6)
# 节点圆
for n in nodes:
    d.ellipse([n[0] - 22, n[1] - 22, n[0] + 22, n[1] + 22], fill=gold)
    d.ellipse([n[0] - 8, n[1] - 8, n[0] + 8, n[1] + 8], fill=(245, 238, 222, 255))
# 中心枢纽（稍大）
d.ellipse([hub[0] - 26, hub[1] - 26, hub[0] + 26, hub[1] + 26], fill=gold)
d.ellipse([hub[0] - 9, hub[1] - 9, hub[0] + 9, hub[1] + 9], fill=(245, 238, 222, 255))

# ---- 输出 512 ----
out = img.resize((512, 512), Image.LANCZOS)
out.save("icon_tribute.png")
print("saved icon_tribute.png", out.size)
