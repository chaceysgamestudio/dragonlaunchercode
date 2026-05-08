import requests
import os
import zipfile
import shutil
import threading
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
import json
from PIL import Image

def load_instance_icon(inst_path):
    icon_path = os.path.join(inst_path, "icon.png")

    if os.path.exists(icon_path):
        img = Image.open(icon_path)
        img = img.resize((48, 48))
        return ctk.CTkImage(light_image=img, dark_image=img, size=(48, 48))

    return None


# -------------------------
# paths
# -------------------------

BASE_DIR = os.path.join(os.getenv("APPDATA"), "modragon", "games", "Half-Dragon")
INSTANCES_DIR = os.path.join(BASE_DIR, "instances")
LOG_FILE = os.path.join(BASE_DIR, "launcher.log")
STATE_FILE = os.path.join(BASE_DIR, "state.json")

os.makedirs(INSTANCES_DIR, exist_ok=True)

TEMPLATE = ["bin", "data", "doc", "mods", "world"]

DEFAULT_DOWNLOAD = "https://github.com/chaceysgamestudio/dragonlauncher/releases/download/releases/Half-Dragon-Pre_Alpha-Build_0.14.0.1.zip"

META_FILE = "meta.json"

# -------------------------
# state
# -------------------------

current_view = "list"
selected_instance = None

loading = False
loading_message = ""
loading_tick = 0

ACCENT = "#3b82f6"

active_animations = []

settings = {
    "fullscreen": False,
    "download_url": DEFAULT_DOWNLOAD
}

# -------------------------
# theme
# -------------------------

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# -------------------------
# state save/load
# -------------------------

def load_state():
    global current_view, selected_instance

    if not os.path.exists(STATE_FILE):
        return

    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
        current_view = data.get("view", "list")
        selected_instance = data.get("instance")
    except:
        pass


def save_state():
    try:
        with open(STATE_FILE, "w") as f:
            json.dump({
                "view": current_view,
                "instance": selected_instance
            }, f)
    except:
        pass

# -------------------------
# logging
# -------------------------

def log(msg):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# -------------------------
# instance meta
# -------------------------

def get_folder_size(path):
    total = 0
    for r, _, files in os.walk(path):
        for f in files:
            fp = os.path.join(r, f)
            if os.path.exists(fp):
                total += os.path.getsize(fp)
    return round(total / (1024 * 1024), 2)


def get_instance_meta(inst_path):
    meta_path = os.path.join(inst_path, META_FILE)

    if not os.path.exists(meta_path):
        return {
            "size": get_folder_size(inst_path),
            "last_played": "Never"
        }

    try:
        with open(meta_path, "r") as f:
            return json.load(f)
    except:
        return {
            "size": get_folder_size(inst_path),
            "last_played": "Never"
        }


def save_instance_meta(inst_path, meta):
    with open(os.path.join(inst_path, META_FILE), "w") as f:
        json.dump(meta, f, indent=4)

# -------------------------
# animations (SAFE)
# -------------------------

def clear_frame():
    global active_animations

    for job in active_animations:
        try:
            root.after_cancel(job)
        except:
            pass

    active_animations.clear()

    for w in frame.winfo_children():
        w.destroy()


def type_text(label, text, i=0):
    if not label.winfo_exists():
        return

    if i <= len(text):
        label.configure(text=text[:i])
        job = root.after(40, lambda: type_text(label, text, i + 1))
        active_animations.append(job)


def slide_in(widget, step=0):
    if not widget.winfo_exists():
        return

    if step > 10:
        return

    try:
        widget.pack_configure(pady=(step * 2, 5))
    except:
        return

    job = root.after(25, lambda: slide_in(widget, step + 1))
    active_animations.append(job)


def pop(widget, delay):
    root.after(delay, lambda: widget.configure(fg_color=ACCENT))

# -------------------------
# instance system
# -------------------------

def make_instance(name):
    path = os.path.join(INSTANCES_DIR, name)

    if os.path.exists(path):
        messagebox.showerror("Error", "Instance exists")
        return None

    os.makedirs(path, exist_ok=True)

    for f in TEMPLATE:
        os.makedirs(os.path.join(path, f), exist_ok=True)

    return path


def install_game(path):
    zip_file = os.path.join(path, "game.zip")

    r = requests.get(settings["download_url"], stream=True)
    r.raise_for_status()

    with open(zip_file, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)

    with zipfile.ZipFile(zip_file, "r") as z:
        z.extractall(path)

    os.remove(zip_file)


def launch(name):
    path = os.path.join(INSTANCES_DIR, name)
    exe = os.path.join(path, "bin", "Half-Dragon.exe")

    if not os.path.exists(exe):
        messagebox.showerror("Error", "Game not found")
        return

    meta = get_instance_meta(path)
    meta["last_played"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_instance_meta(path, meta)

    os.startfile(exe)


def delete(name):
    path = os.path.join(INSTANCES_DIR, name)
    if messagebox.askyesno("Delete", "Delete instance?"):
        shutil.rmtree(path)
        go_home()

# -------------------------
# stats
# -------------------------

def get_all_instances():
    return [os.path.join(INSTANCES_DIR, i) for i in os.listdir(INSTANCES_DIR)]


def get_stats():
    total = len(os.listdir(INSTANCES_DIR))
    size = 0

    for p in get_all_instances():
        for r, _, files in os.walk(p):
            for f in files:
                size += os.path.getsize(os.path.join(r, f))

    return {
        "instances": total,
        "size_mb": round(size / (1024 * 1024), 2)
    }

# -------------------------
# navigation
# -------------------------

def go_home():
    global current_view, selected_instance
    current_view = "list"
    selected_instance = None
    refresh()


def open_instance(name):
    global current_view, selected_instance
    current_view = "instance"
    selected_instance = name
    refresh()


def open_create():
    global current_view
    current_view = "create"
    refresh()


def open_settings():
    global current_view
    current_view = "settings"
    refresh()

# -------------------------
# UI
# -------------------------

root = ctk.CTk()
root.title("Half Dragon Launcher")
root.geometry("1100x650")
icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
root.iconbitmap(icon_path)

sidebar = ctk.CTkFrame(root, width=240)
sidebar.pack(side="left", fill="y")

ctk.CTkLabel(sidebar, text="HALF DRAGON", font=("Segoe UI", 20, "bold")).pack(pady=20)

ctk.CTkButton(sidebar, text="Home", command=go_home).pack(fill="x", padx=10, pady=5)
ctk.CTkButton(sidebar, text="Create", command=open_create).pack(fill="x", padx=10, pady=5)
ctk.CTkButton(sidebar, text="Settings", command=open_settings).pack(fill="x", padx=10, pady=5)

main = ctk.CTkFrame(root)
main.pack(side="left", fill="both", expand=True)

frame = ctk.CTkFrame(main)
frame.pack(fill="both", expand=True, padx=20, pady=20)

# -------------------------
# refresh
# -------------------------

def refresh():
    clear_frame()
    save_state()

    if current_view == "list":
        title = ctk.CTkLabel(frame, text="Instances", font=("Segoe UI", 26, "bold"))
        title.pack(pady=10)

        grid = ctk.CTkFrame(frame, fg_color="transparent")
        grid.pack(fill="both", expand=True)

        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)

        instances = os.listdir(INSTANCES_DIR)

        for i, inst in enumerate(instances):
            inst_path = os.path.join(INSTANCES_DIR, inst)
            meta = get_instance_meta(inst_path)

            card = ctk.CTkFrame(grid, fg_color="#1a1a1a", corner_radius=14, height=160)
            card.grid(row=i // 2, column=i % 2, padx=12, pady=12, sticky="nsew")
            card.grid_propagate(False)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="both", expand=True, padx=10, pady=10)

            icon_img = load_instance_icon(inst_path)

            if icon_img:
                ctk.CTkLabel(inner, image=icon_img, text="").pack()
            else:
                ctk.CTkLabel(inner, text="🧩", font=("Segoe UI", 26)).pack()

            ctk.CTkLabel(inner, text=inst, font=("Segoe UI", 15, "bold")).pack()

            ctk.CTkLabel(
                inner,
                text=f"{meta['size']} MB • {meta['last_played']}",
                text_color="#9e9e9e"
            ).pack(pady=(2, 8))

            ctk.CTkButton(inner, text="Open", command=lambda n=inst: open_instance(n)).pack()

    elif current_view == "instance":
        name = selected_instance

        ctk.CTkLabel(frame, text=name, font=("Segoe UI", 24, "bold")).pack(pady=20)

        ctk.CTkButton(frame, text="Launch", command=lambda: launch(name)).pack(fill="x", padx=100)
        ctk.CTkButton(frame, text="Delete", fg_color="red", command=lambda: delete(name)).pack(fill="x", padx=100)
        ctk.CTkButton(frame, text="Back", command=go_home).pack(pady=10)

    elif current_view == "create":
        name_var = ctk.StringVar()

        ctk.CTkLabel(frame, text="Create Instance", font=("Segoe UI", 22, "bold")).pack(pady=20)

        card = ctk.CTkFrame(frame, fg_color="#111111", corner_radius=12)
        card.pack(pady=20, padx=120, fill="x")

        entry = ctk.CTkEntry(card, textvariable=name_var, placeholder_text="Instance name")
        entry.pack(pady=15, padx=15, fill="x")

        status = ctk.CTkLabel(card, text="", text_color="#9ca3af")
        status.pack(pady=(0, 10))

        def create():
            name = name_var.get().strip()
            if not name:
                status.configure(text="Type a name first")
                return

            path = make_instance(name)
            if not path:
                status.configure(text="Instance already exists")
                return

            status.configure(text="Installing...")

            def task():
                install_game(path)
                go_home()

            threading.Thread(target=task, daemon=True).start()

        ctk.CTkButton(card, text="Create Instance", command=create, fg_color=ACCENT).pack(pady=10)

        ctk.CTkButton(frame, text="Back", command=go_home).pack(pady=10)


    elif current_view == "settings":

        ctk.CTkLabel(frame, text="Settings", font=("Segoe UI", 22, "bold")).pack(pady=20)

        card = ctk.CTkFrame(frame, fg_color="#111111", corner_radius=12)

        card.pack(pady=20, padx=120, fill="x")

        url_var = ctk.StringVar(value=settings["download_url"])

        ctk.CTkLabel(card, text="Download URL", text_color="#9ca3af").pack(pady=(10, 0))

        entry = ctk.CTkEntry(card, textvariable=url_var)

        entry.pack(pady=10, padx=15, fill="x")

        def save():

            settings["download_url"] = url_var.get()

            log("Settings saved")

        def fullscreen():

            settings["fullscreen"] = not settings["fullscreen"]

            root.attributes("-fullscreen", settings["fullscreen"])

        def wipe():

            if messagebox.askyesno("DANGER", "Delete ALL instances?"):
                shutil.rmtree(INSTANCES_DIR)

                os.makedirs(INSTANCES_DIR, exist_ok=True)

                go_home()

        ctk.CTkButton(card, text="Save URL", command=save, fg_color=ACCENT).pack(pady=5, padx=15, fill="x")

        ctk.CTkButton(card, text="Toggle Fullscreen", command=fullscreen).pack(pady=5, padx=15, fill="x")

        ctk.CTkButton(card, text="Wipe Instances", fg_color="#ef4444", command=wipe).pack(pady=5, padx=15, fill="x")

        ctk.CTkButton(frame, text="Back", command=go_home).pack(pady=10)

    log("UI refreshed")
# -------------------------
# start
# -------------------------

load_state()
log("Launcher started")
refresh()
root.mainloop()
