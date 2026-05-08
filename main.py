import os
import sys
import requests
import zipfile
import shutil
import threading
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from datetime import datetime
import winsound

# -------------------------
# file locations (where everything lives)
# -------------------------

BASE_DIR = os.path.join(os.getenv("APPDATA"), "modragon", "games", "Half-Dragon")
INSTANCES_DIR = os.path.join(BASE_DIR, "instances")
LOG_FILE = os.path.join(BASE_DIR, "launcher.log")

os.makedirs(INSTANCES_DIR, exist_ok=True)

# default structure every instance gets
TEMPLATE = ["bin", "data", "doc", "mods", "world"]

# fallback download link (can be changed in settings)
DEFAULT_DOWNLOAD = "https://github.com/chaceysgamestudio/dragonlauncher/releases/download/releases/Half-Dragon-Pre_Alpha-Build_0.14.0.1.zip"

# -------------------------
# runtime state (what screen we're on, what's selected, etc)
# -------------------------

current_view = "list"
selected_instance = None

loading = False
loading_message = ""
loading_tick = 0

settings = {
    "fullscreen": False,
    "download_url": DEFAULT_DOWNLOAD
}

# -------------------------
# colours (simple dark theme)
# -------------------------

BG = "#0f0f0f"
PANEL = "#161616"
CARD = "#222222"
ACCENT = "#7c4dff"
TEXT = "#ffffff"

# -------------------------
# logging helper (so we know what broke later)
# -------------------------

def log(msg):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# -------------------------
# navigation between screens
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
# loading system (simple animated text)
# -------------------------

def show_loading(text):
    global loading, loading_message, loading_tick
    loading = True
    loading_message = text
    loading_tick = 0
    spin_loading()
    refresh()

def hide_loading():
    global loading
    loading = False
    refresh()

def spin_loading():
    global loading_tick
    if not loading:
        return

    loading_tick = (loading_tick + 1) % 4
    refresh()
    root.after(350, spin_loading)

# -------------------------
# instance handling (create / install / launch / delete)
# -------------------------

def make_instance(name):
    path = os.path.join(INSTANCES_DIR, name)

    if os.path.exists(path):
        messagebox.showerror("Error", "That instance already exists")
        winsound.PlaySound("SystemHand", winsound.SND_ALIAS)
        return None


    os.makedirs(path, exist_ok=True)

    for folder in TEMPLATE:
        os.makedirs(os.path.join(path, folder), exist_ok=True)

    return path


def install_game(path):
    zip_file = os.path.join(path, "game.zip")

    r = requests.get(settings["download_url"], stream=True)
    r.raise_for_status()

    with open(zip_file, "wb") as f:
        for chunk in r.iter_content(8192):
            if chunk:
                f.write(chunk)

    with zipfile.ZipFile(zip_file, "r") as z:
        z.extractall(path)

    os.remove(zip_file)


def launch(name):
    exe = os.path.join(INSTANCES_DIR, name, "bin", "Half-Dragon.exe")

    if not os.path.exists(exe):
        messagebox.showerror("Error", "Game not found")
        return

    os.chdir(os.path.join(INSTANCES_DIR, name))
    os.startfile(exe)


def delete(name):
    winsound.PlaySound("SystemHand", winsound.SND_ALIAS)
    path = os.path.join(INSTANCES_DIR, name)

    if messagebox.askyesno("Delete", f"Delete '{name}'?"):
        shutil.rmtree(path)
        go_home()

# -------------------------
# UI setup
# -------------------------
def resource_path(filename):
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, filename)
root = tk.Tk()
root.title("Half Dragon Launcher")
root.geometry("900x500")
root.configure(bg=BG)
img = tk.PhotoImage(file=resource_path("icon.png"))
root.iconphoto(True, img)


# sidebar (left menu)
sidebar = tk.Frame(root, bg=PANEL, width=160)
sidebar.pack(side="left", fill="y")

tk.Label(sidebar, text="HALF DRAGON LAUNCHER", bg=PANEL, fg=TEXT,
         font=("Arial", 22, "bold")).pack(pady=15)

tk.Button(sidebar, text="Create", bg=ACCENT, fg="white",
          command=open_create).pack(fill="x", padx=10, pady=5)

tk.Button(sidebar, text="Home", bg="#2a2a2a", fg="white",
          command=go_home).pack(fill="x", padx=10, pady=5)

tk.Button(sidebar, text="Settings", bg="#2a2a2a", fg="white",
          command=open_settings).pack(fill="x", padx=10, pady=5)

# main content area
main = tk.Frame(root, bg=BG)
main.pack(side="left", fill="both", expand=True)

frame = tk.Frame(main, bg=BG)
frame.pack(fill="both", expand=False)

# -------------------------
# redraw UI
# -------------------------

def refresh():
    for w in frame.winfo_children():
        w.destroy()

    # loading screen
    if loading:
        tk.Label(frame, text=loading_message + "." * loading_tick,
                 bg=BG, fg=TEXT,
                 font=("Arial", 16, "bold")).pack(pady=30)

        bar = ttk.Progressbar(frame, mode="indeterminate")
        bar.pack(fill="x", padx=120)
        bar.start()
        return

    # instance list
    if current_view == "list":
        tk.Label(frame, text="Instances",
                 bg=BG, fg=TEXT,
                 font=("Arial", 16, "bold")).pack(pady=10)

        for inst in os.listdir(INSTANCES_DIR):
            tk.Button(frame, text=inst,
                      bg=CARD, fg=TEXT,
                      command=lambda n=inst: open_instance(n)).pack(fill="x", padx=60, pady=5)

    # instance page
    elif current_view == "instance":
        name = selected_instance

        tk.Label(frame, text=name,
                 bg=BG, fg=TEXT,
                 font=("Arial", 18, "bold")).pack(pady=10)

        tk.Button(frame, text="Launch",
                  bg=ACCENT, fg="white",
                  command=lambda: launch(name)).pack(fill="x", padx=120, pady=5)

        tk.Button(frame, text="Delete",
                  bg="red", fg="white",
                  command=lambda: delete(name)).pack(fill="x", padx=120, pady=5)

        tk.Button(frame, text="Back",
                  bg="#333", fg="white",
                  command=go_home).pack(pady=10)

    # create page
    elif current_view == "create":
        name_var = tk.StringVar()

        tk.Label(frame, text="Create Instance",
                 bg=BG, fg=TEXT,
                 font=("Arial", 16, "bold")).pack(pady=10)

        tk.Entry(frame, textvariable=name_var,
                 bg="#1f1f1f", fg=TEXT).pack(fill="x", padx=120, pady=10)

        def create():
            name = name_var.get().strip()
            if not name:
                return

            path = make_instance(name)
            if not path:
                return

            show_loading("Installing Game")

            def task():
                try:
                    install_game(path)
                finally:
                    hide_loading()
                    go_home()

            threading.Thread(target=task, daemon=True).start()

        tk.Button(frame, text="Create + Install",
                  bg=ACCENT, fg="white",
                  command=create).pack(fill="x", padx=120, pady=5)


    # settings page
    elif current_view == "settings":
        url_var = tk.StringVar(value=settings["download_url"])

        tk.Label(frame, text="Settings",
                 bg=BG, fg=TEXT,
                 font=("Arial", 18, "bold")).pack(pady=15)

        tk.Entry(frame, textvariable=url_var,
                 bg="#1f1f1f", fg=TEXT).pack(fill="x", padx=120, pady=10)

        def save():
            settings["download_url"] = url_var.get()


        def fullscreen():
            settings["fullscreen"] = not settings["fullscreen"]
            root.attributes("-fullscreen", settings["fullscreen"])
        def wipe():
            if messagebox.askyesno("DANGER", "Delete EVERYTHING?"):
                shutil.rmtree(INSTANCES_DIR)
                os.makedirs(INSTANCES_DIR, exist_ok=True)
                go_home()

        def reload_instances():
                    refresh()
                    log("Instances reloaded")

        tk.Button(frame, text="Save URL", bg=ACCENT, fg="white",
                  command=save).pack(fill="x", padx=120, pady=5)

        tk.Button(frame, text="Fullscreen", bg="#333", fg="white",
                  command=fullscreen).pack(fill="x", padx=120, pady=5)

        tk.Button(frame, text="reload", bg="#333", fg="white",
                  command=reload_instances).pack(fill="x", padx=120, pady=5)

        tk.Button(frame, text="Wipe Instances", bg="red", fg="white",
                  command=wipe).pack(fill="x", padx=120, pady=5)

        tk.Button(frame, text="Back", bg="#222", fg="white",
                  command=go_home).pack(pady=10)


    log("UI refreshed")

# -------------------------
# start app
# -------------------------
winsound.PlaySound("SystemDefault", winsound.SND_ALIAS)
log("Launcher started")
refresh()
root.mainloop()