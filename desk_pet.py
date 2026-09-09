# -*- coding: utf-8 -*-
"""
桌面西装小人 —— 以视频人物为原型的 Q 版桌面宠物
功能：在屏幕底部左右走动、单击互动(挥手/跳跃/说话)、拖拽、右键菜单
运行：pythonw desk_pet.py
"""
import tkinter as tk
import random
import os
from PIL import Image, ImageTk

BASE = os.path.dirname(os.path.abspath(__file__))
SPR = os.path.join(BASE, "sprites")
CHAR_H = 200          # 角色显示高度(px)
BUBBLE_H = 70         # 顶部气泡区高度
TRANSPARENT = "#010203"
TICK = 340             # 动画帧间隔 ms

GREETINGS = [
    "你好呀！", "老板好！", "今天也要加油哦~",
    "摸鱼时间到！", "嘿嘿，被你发现啦", "西装笔挺，精神抖擞！",
    "要不要喝杯咖啡？", "代码写完了吗？", "休息一下眼睛吧~",
    "我在这看着你哦", "加油！你最棒！", "别熬夜，早点睡",
]


class DeskPet:
    def __init__(self, root):
        self.root = root
        root.overrideredirect(True)
        root.wm_attributes("-topmost", True)
        try:
            root.wm_attributes("-transparentcolor", TRANSPARENT)
        except tk.TclError:
            pass
        root.configure(bg=TRANSPARENT)

        self.screen_w = root.winfo_screenwidth()
        self.screen_h = root.winfo_screenheight()

        # ---- 加载精灵（裁透明边、统一画布居中，消除帧间抖动） ----
        self.frames_r = {}   # 朝右(原图)
        self.frames_l = {}   # 朝左(镜像)
        raw = {}
        for n in ["stand", "walk1", "walk2", "wave", "jump"]:
            path = os.path.join(SPR, n + ".png")
            if not os.path.exists(path):
                raise FileNotFoundError("缺少精灵图: " + path)
            im = Image.open(path).convert("RGBA")
            bbox = im.getbbox()
            if bbox:
                im = im.crop(bbox)
            ratio = CHAR_H / im.height
            raw[n] = im.resize((max(1, int(im.width * ratio)), CHAR_H), Image.LANCZOS)
        cw = max(raw[n].width for n in raw)
        for n, im in raw.items():
            canvas_img = Image.new("RGBA", (cw, CHAR_H), (0, 0, 0, 0))
            canvas_img.paste(im, ((cw - im.width) // 2, 0), im)
            self.frames_r[n] = ImageTk.PhotoImage(canvas_img)
            self.frames_l[n] = ImageTk.PhotoImage(canvas_img.transpose(Image.FLIP_LEFT_RIGHT))

        self.w = cw                     # 窗口宽 = 统一画布宽
        self.h = CHAR_H + BUBBLE_H
        self.char_bottom = self.h - 10      # 角色脚底距窗口顶

        # ---- 画布 ----
        self.canvas = tk.Canvas(root, width=self.w, height=self.h,
                                bg=TRANSPARENT, highlightthickness=0)
        self.canvas.pack()
        self.img_id = self.canvas.create_image(self.w // 2, self.char_bottom - CHAR_H // 2,
                                               image=self.frames_r["stand"])
        # 气泡元素(初始隐藏)
        self.bubble_bg = self.canvas.create_polygon(0, 0, 0, 0, 0, 0, fill="#ffffff",
                                                    outline="#333333", width=2, state="hidden")
        self.bubble_txt = self.canvas.create_text(0, 0, text="", font=("Microsoft YaHei", 12),
                                                  fill="#222222", state="hidden")

        # ---- 状态 ----
        self.x = random.randint(0, max(1, self.screen_w - self.w))
        self.y = self.screen_h - self.h - 45          # 任务栏上方
        self.dir = random.choice([-1, 1])
        self.state = "walk"
        self.frame_i = 0
        self.speed = 1
        self.tick_count = 0
        self.next_break = random.randint(60, 120)     # 走多少 tick 后随机停
        self.bubble_timer = None
        self.drag_off = (0, 0)
        self.moved = False

        # ---- 交互 ----
        self.canvas.tag_bind(self.img_id, "<Button-1>", self.on_press)
        self.canvas.tag_bind(self.img_id, "<ButtonRelease-1>", self.on_release)
        self.canvas.tag_bind(self.img_id, "<Button-3>", self.on_right)
        self.canvas.tag_bind(self.img_id, "<B1-Motion>", self.on_drag)

        self.menu = tk.Menu(root, tearoff=0)
        self.menu.add_command(label="打个招呼", command=self.do_wave)
        self.menu.add_command(label="跳一个", command=self.do_jump)
        self.menu.add_command(label="说句话", command=self.say_random)
        self.menu.add_command(label="原地站定/继续走", command=self.toggle_stop)
        self.menu.add_separator()
        self.menu.add_command(label="退出", command=root.destroy)

        self.move_root()
        self.anim()

    # ---------- 工具 ----------
    def frames(self):
        return self.frames_l if self.dir < 0 else self.frames_r

    def move_root(self):
        self.root.geometry(f"{self.w}x{self.h}+{int(self.x)}+{int(self.y)}")

    def set_img(self, name):
        self.canvas.itemconfig(self.img_id, image=self.frames()[name])

    # ---------- 动画循环 ----------
    def anim(self):
        if self.state == "walk":
            self.frame_i += 1
            # 走-立-走-立 循环，步伐更平滑自然
            seq = ("walk1", "stand", "walk2", "stand")
            self.set_img(seq[self.frame_i % 4])
            self.x += self.dir * self.speed
            if self.x <= 0:
                self.x = 0
                self.turn()
            elif self.x >= self.screen_w - self.w:
                self.x = self.screen_w - self.w
                self.turn()
            self.tick_count += 1
            if self.tick_count >= self.next_break:
                self.tick_count = 0
                self.next_break = random.randint(40, 100)
                r = random.random()
                if r < 0.25:
                    self.state = "idle"
                    self.set_img("stand")
                    self.root.after(random.randint(2500, 6000), self.resume_walk)
        elif self.state == "wave":
            self.set_img("wave")
        elif self.state == "jump":
            self.set_img("jump")
        elif self.state == "idle":
            self.set_img("stand")

        self.move_root()
        self.root.after(TICK, self.anim)

    def turn(self):
        self.dir *= -1
        self.set_img("stand")
        self.root.after(350, self.resume_walk)
        self.state = "paused"

    def resume_walk(self):
        if self.state in ("paused", "idle"):
            self.state = "walk"

    # ---------- 互动 ----------
    def on_press(self, event):
        self.drag_off = (event.x_root - self.x, event.y_root - self.y)
        self.moved = False

    def on_release(self, event):
        if not self.moved:
            self.on_click(event)

    def on_click(self, event):
        r = random.random()
        if r < 0.35:
            self.do_wave()
        elif r < 0.6:
            self.do_jump()
        else:
            self.say_random()

    def toggle_stop(self):
        if self.state == "walk":
            self.state = "idle"
            self.set_img("stand")
            self.say("我歇会儿~")
        else:
            self.resume_walk()
            self.say("走咯走咯！")

    def do_wave(self):
        self.state = "wave"
        self.set_img("wave")
        self.root.after(1400, self.resume_walk)
        if random.random() < 0.5:
            self.say(random.choice(["嗨~", "你好呀！", "See you!"]), 1500)

    def do_jump(self):
        self.state = "jump"
        self.set_img("jump")
        self.root.after(1100, self.resume_walk)
        if random.random() < 0.5:
            self.say(random.choice(["耶！", "好耶！", "开心！"]), 1200)

    def say_random(self):
        self.say(random.choice(GREETINGS))

    def say(self, text, ms=2800):
        cx = self.w // 2
        top = 12
        tw = self.canvas.create_text(0, 0, text=text, font=("Microsoft YaHei", 12),
                                     fill="#222222")
        bbox = self.canvas.bbox(tw)
        self.canvas.delete(tw)
        tw_, th_ = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pad = 10
        bw = tw_ + pad * 2
        bh = th_ + pad
        bx = cx - bw // 2
        by = top
        tail = (bx + bw // 2 - 7, by + bh - 1,
                bx + bw // 2 + 7, by + bh - 1,
                cx, by + bh + 12)
        self.canvas.coords(self.bubble_bg, *tail,
                           bx, by, bx + bw, by, bx + bw, by + bh, bx, by + bh)
        self.canvas.itemconfig(self.bubble_bg, state="normal")
        self.canvas.coords(self.bubble_txt, cx, by + bh // 2)
        self.canvas.itemconfig(self.bubble_txt, text=text, state="normal")
        if self.bubble_timer:
            self.root.after_cancel(self.bubble_timer)
        self.bubble_timer = self.root.after(ms, self.hide_bubble)

    def hide_bubble(self):
        self.canvas.itemconfig(self.bubble_bg, state="hidden")
        self.canvas.itemconfig(self.bubble_txt, state="hidden")

    # ---------- 拖拽 / 菜单 ----------
    def on_drag(self, event):
        self.moved = True
        self.x = event.x_root - self.drag_off[0]
        self.y = event.y_root - self.drag_off[1]
        self.x = max(0, min(self.screen_w - self.w, self.x))
        self.y = max(0, min(self.screen_h - self.h, self.y))
        self.move_root()

    def on_right(self, event):
        self.menu.tk_popup(event.x_root, event.y_root)


def main():
    root = tk.Tk()
    DeskPet(root)
    root.mainloop()


if __name__ == "__main__":
    main()
