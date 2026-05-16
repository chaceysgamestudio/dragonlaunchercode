import requests
import os
import zipfile
import shutil
import threading
import queue
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
import json
from PIL import Image


def load_instance_icon(inst_path):
    icon_path = os.path.join(inst_path, "icon.png")
    if os.path.exists(icon_path):
        try:
            img = Image.open(icon_path)
            img = img.resize((48, 48))
            return ctk.CTkImage(light_image=img, dark_image=img, size=(48, 48))
        except:
            return None
    return None


# -------------------------
# paths
# -------------------------
TEMPLATE = ["bin", "data", "doc", "world"]
BASE_DIR = os.path.join(os.getenv("APPDATA"), "halfdragonlauncher", "games", "Half-Dragon")
INSTANCES_DIR = os.path.join(BASE_DIR, "instances")
LOG_FILE = os.path.join(BASE_DIR, "launcher.log")
STATE_FILE = os.path.join(BASE_DIR, "state.json")

os.makedirs(INSTANCES_DIR, exist_ok=True)

DEFAULT_DOWNLOAD = "https://github.com/chaceysgamestudio/dragonlauncher/releases/download/releases/Half-Dragon-Pre_Alpha-Build_0.14.0.1.zip"
META_FILE = "meta.json"

# -------------------------
# state
# -------------------------
current_view = "list"
selected_instance = None

ACCENT = "#3b82f6"
debug_window = None
debug_text_area = None
cmd_entry = None

settings = {
    "fullscreen": False,
    "download_url": DEFAULT_DOWNLOAD,
    "debug_mode": False
}

ui_queue = queue.Queue()
network_session = requests.Session()

# -------------------------
# theme
# -------------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


# -------------------------
# state save/load
# -------------------------
def load_state():
    global current_view, selected_instance, settings
    if not os.path.exists(STATE_FILE):
        return
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
        current_view = data.get("view", "list")
        selected_instance = data.get("instance")
        settings.update(data.get("settings", {}))

        if settings.get("debug_mode"):
            root.after(200, toggle_debug_terminal)
    except:
        pass


def save_state():
    try:
        with open(STATE_FILE, "w") as f:
            json.dump({
                "view": current_view,
                "instance": selected_instance,
                "settings": settings
            }, f)
    except:
        pass


# -------------------------
# logging & debug terminal
# -------------------------
def log(msg):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)

    if debug_text_area and debug_window and debug_window.winfo_exists():
        try:
            debug_text_area.configure(state="normal")
            debug_text_area.insert(tk.END, line + "\n")
            debug_text_area.see(tk.END)
            debug_text_area.configure(state="disabled")
        except:
            pass

    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except:
        pass


def execute_debug_command(event=None):
    """Handles text commands typed into the terminal window."""
    global cmd_entry, current_view, selected_instance
    if not cmd_entry:
        return

    raw_text = cmd_entry.get().strip()
    if not raw_text:
        return

    cmd_entry.delete(0, tk.END)
    log(f"> {raw_text}")

    parts = raw_text.split()
    cmd = parts[0].lower()
    args = parts[1:]

    if cmd == "help":
        log("Commands: help, clear, status, list, launch [name], delete [name], view [home|create|settings], url [link], exit")
    elif cmd == "clear":
        if debug_text_area and debug_window.winfo_exists():
            debug_text_area.configure(state="normal")
            debug_text_area.delete("1.0", tk.END)
            debug_text_area.configure(state="disabled")
    elif cmd == "status":
        log(f"View: {current_view} | Selected: {selected_instance} | Fullscreen: {settings['fullscreen']}")
        log(f"URL: {settings['download_url']}")
    elif cmd == "list":
        try:
            items = [i for i in os.listdir(INSTANCES_DIR) if os.path.isdir(os.path.join(INSTANCES_DIR, i))]
            log(f"Instances found: {', '.join(items) if items else 'None'}")
        except Exception as e:
            log(f"Error reading instances: {e}")
    elif cmd == "launch":
        if not args:
            log("Error: Provide an instance name.")
        else:
            name = " ".join(args)
            root.after(1, lambda: launch(name))
    elif cmd == "delete":
        if not args:
            log("Error: Provide an instance name.")
        else:
            name = " ".join(args)
            root.after(1, lambda: delete(name))
    elif cmd == "view":
        if not args:
            log("Error: Specify home, create, or settings.")
        else:
            target = args[0].lower()
            if target == "home":
                root.after(1, go_home)
            elif target == "create":
                root.after(1, open_create)
            elif target == "settings":
                root.after(1, open_settings)
            else:
                log("Unknown view target.")
    elif cmd == "url":
        if not args:
            log(f"Current URL: {settings['download_url']}")
        else:
            settings["download_url"] = args[0].strip()
            save_state()
            log("Download URL updated.")
            if current_view == "settings":
                root.after(1, refresh)
    elif cmd == "exit":
        settings["debug_mode"] = False
        root.after(1, toggle_debug_terminal)
        if current_view == "settings":
            root.after(1, refresh)
    else:
        log(f"Unknown command: {cmd}. Type 'help' for options.")


def toggle_debug_terminal():
    global debug_window, debug_text_area, cmd_entry

    if settings["debug_mode"]:
        if debug_window and debug_window.winfo_exists():
            return

        debug_window = ctk.CTkToplevel(root)
        debug_window.title("Launcher Debug Terminal")
        debug_window.geometry("650x450")
        debug_window.protocol("WM_DELETE_WINDOW", lambda: disable_debug_from_window())

        debug_text_area = ctk.CTkTextbox(debug_window, font=("Consolas", 12), text_color="#10b981", fg_color="#09090b")
        debug_text_area.pack(fill="both", expand=True, padx=10, pady=(10, 5))
        debug_text_area.configure(state="disabled")

        input_frame = ctk.CTkFrame(debug_window, fg_color="transparent")
        input_frame.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(input_frame, text=">", font=("Consolas", 14, "bold"), text_color="#10b981").pack(side="left", padx=(5, 5))

        cmd_entry = ctk.CTkEntry(input_frame, font=("Consolas", 12), fg_color="#18181b", border_color="#27272a", placeholder_text="Type a command...")
        cmd_entry.pack(side="left", fill="x", expand=True)
        cmd_entry.bind("<Return>", execute_debug_command)

        log("Debug terminal active.")
    else:
        if debug_window and debug_window.winfo_exists():
            debug_window.destroy()
        debug_window = None
        debug_text_area = None
        cmd_entry = None


def disable_debug_from_window():
    settings["debug_mode"] = False
    toggle_debug_terminal()
    save_state()
    if current_view == "settings":
        refresh()


# -------------------------
# instance meta
# -------------------------
def get_folder_size(path):
    total = 0
    try:
        for r, _, files in os.walk(path):
            for f in files:
                fp = os.path.join(r, f)
                if os.path.exists(fp):
                    total += os.path.getsize(fp)
    except:
        pass
    return round(total / (1024 * 1024), 2)


def get_instance_meta(inst_path):
    meta_path = os.path.join(inst_path, META_FILE)
    if not os.path.exists(meta_path):
        return {"size": get_folder_size(inst_path), "last_played": "Never"}
    try:
        with open(meta_path, "r") as f:
            return json.load(f)
    except:
        return {"size": get_folder_size(inst_path), "last_played": "Never"}


def save_instance_meta(inst_path, meta):
    try:
        with open(os.path.join(inst_path, META_FILE), "w") as f:
            json.dump(meta, f, indent=4)
    except:
        pass


# -------------------------
# UI Clean Up
# -------------------------
def clear_frame():
    for w in frame.winfo_children():
        w.destroy()


# -------------------------
# instance system
# -------------------------
def make_instance(name):
    path = os.path.join(INSTANCES_DIR, name)
    if os.path.exists(path):
        messagebox.showerror("Error", "Instance exists")
        return None
    try:
        os.makedirs(path, exist_ok=True)
        for f in TEMPLATE:
            os.makedirs(os.path.join(path, f), exist_ok=True)
        return path
    except Exception as e:
        messagebox.showerror("Error", f"Failed to allocate space: {e}")
        return None


def install_game_worker(path):
    zip_file = os.path.join(path, "game.zip")
    try:
        ui_queue.put(("status", "Connecting to url...", 0))
        r = network_session.get(settings["download_url"], stream=True, timeout=20)
        r.raise_for_status()

        total_length = r.headers.get('content-length')

        if total_length is None:
            with open(zip_file, "wb") as f:
                f.write(r.content)
            ui_queue.put(("status", "loading game to storage", 0.70))
        else:
            total_length = int(total_length)
            dl = 0
            # Faster downloads: Expanded to 128KB chunk buffers to drop execution overhead
            with open(zip_file, "wb") as f:
                for chunk in r.iter_content(chunk_size=1048576):
                    if chunk:
                        dl += len(chunk)
                        f.write(chunk)
                        ratio = dl / total_length
                        percent = int(ratio * 100)
                        ui_queue.put(("status", f"Downloading game... ({percent}%)", ratio * 0.85))

        ui_queue.put(("status", "Extracting package contents!", 0.90))
        # Faster unpacking: Extracted entirely inside single operation block
        with zipfile.ZipFile(zip_file, "r") as z:
            z.extractall(path)

        try:
            os.remove(zip_file)
        except:
            pass

        meta = {"size": get_folder_size(path), "last_played": "Never"}
        save_instance_meta(path, meta)

        log(f"Successfully deployed build: {os.path.basename(path)}")
        ui_queue.put(("complete", None, 1.0))

    except Exception as e:
        log(f"Asynchronous worker fault: {e}")
        ui_queue.put(("error", f"Installation dropped: {str(e)}", 0))
        if os.path.exists(path):
            try:
                shutil.rmtree(path)
            except:
                pass


def launch(name):
    path = os.path.join(INSTANCES_DIR, name)
    exe = os.path.join(path, "bin", "Half-Dragon.exe")

    if not os.path.exists(exe):
        messagebox.showerror("Error", f"Game not found at target: {name}/bin/Half-Dragon.exe")
        return

    meta = get_instance_meta(path)
    meta["last_played"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_instance_meta(path, meta)

    log(f"Launching instance: {name}")
    os.startfile(exe)


def delete(name):
    path = os.path.join(INSTANCES_DIR, name)
    if messagebox.askyesno("Delete", f"Delete instance '{name}'?"):
        try:
            shutil.rmtree(path)
            log(f"Deleted instance: {name}")
            go_home()
        except Exception as e:
            messagebox.showerror("IO Fault", f"Error removing files: {e}")


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
# Async Queue Monitor
# -------------------------
def process_ui_queue(status_label, progress_bar, action_button, back_button):
    try:
        while True:
            msg_type, data, progress_val = ui_queue.get_nowait()
            if msg_type == "status" and status_label.winfo_exists():
                status_label.configure(text=data)
                if progress_bar and progress_bar.winfo_exists():
                    progress_bar.set(progress_val)
            elif msg_type == "complete":
                go_home()
                return
            elif msg_type == "error":
                messagebox.showerror("Download Interrupt", data)
                go_home()
                return
            ui_queue.task_done()
    except queue.Empty:
        pass

    if current_view == "create" and action_button.cget("state") == "disabled":
        root.after(50, lambda: process_ui_queue(status_label, progress_bar, action_button, back_button))


# -------------------------
# UI Core Refresh Engine
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

        try:
            instances = [i for i in os.listdir(INSTANCES_DIR) if os.path.isdir(os.path.join(INSTANCES_DIR, i))]
        except:
            instances = []

        for i, inst in enumerate(instances):
            inst_path = os.path.join(INSTANCES_DIR, inst)
            meta = get_instance_meta(inst_path)

            card = ctk.CTkFrame(grid, fg_color="#1a1a1a", border_width=1, border_color="#2d2d2d", corner_radius=14, height=160)
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
            ctk.CTkLabel(inner, text=f"{meta['size']} MB • {meta['last_played']}", text_color="#9e9e9e").pack(pady=(2, 8))

            open_btn = ctk.CTkButton(inner, text="Open", fg_color="#27272a", hover_color="#3f3f46", command=lambda n=inst: open_instance(n))
            open_btn.pack()

    elif current_view == "instance":
        name = selected_instance

        ctk.CTkLabel(frame, text=name, font=("Segoe UI", 24, "bold")).pack(pady=20)

        launch_btn = ctk.CTkButton(frame, text="Launch Game", fg_color="#16a34a", hover_color="#15803d", font=("Segoe UI", 14, "bold"), command=lambda: launch(name))
        launch_btn.pack(fill="x", padx=100, pady=8)

        del_btn = ctk.CTkButton(frame, text="Delete Instance", fg_color="#dc2626", hover_color="#b91c1c", command=lambda: delete(name))
        del_btn.pack(fill="x", padx=100, pady=8)

        back_btn = ctk.CTkButton(frame, text="Back to Home", fg_color="#27272a", hover_color="#3f3f46", command=go_home)
        back_btn.pack(pady=20)

    elif current_view == "create":
        name_var = ctk.StringVar()

        ctk.CTkLabel(frame, text="Create New Instance", font=("Segoe UI", 22, "bold")).pack(pady=20)

        card = ctk.CTkFrame(frame, fg_color="#111111", corner_radius=12, border_width=1, border_color="#27272a")
        card.pack(pady=20, padx=120, fill="x")

        entry = ctk.CTkEntry(card, textvariable=name_var, placeholder_text="Enter unique instance name...")
        entry.pack(pady=15, padx=15, fill="x")

        status = ctk.CTkLabel(card, text="", text_color="#a1a1aa")
        status.pack(pady=(0, 5))

        prog_bar = ctk.CTkProgressBar(card, progress_color=ACCENT, height=8)
        prog_bar.set(0)

        def create():
            name = name_var.get().strip()
            if not name:
                status.configure(text="Name field cannot be blank.")
                return

            name = "".join([c for c in name if c.isalnum() or c in (' ', '-', '_')]).strip()
            path = make_instance(name)
            if not path:
                status.configure(text="Instance generation rejected.")
                return

            status.configure(text="Resolving network targets...")
            prog_bar.pack(pady=10, padx=15, fill="x")

            entry.configure(state="disabled")
            btn.configure(state="disabled")
            back_btn.configure(state="disabled")

            threading.Thread(target=install_game_worker, args=(path,), daemon=True).start()
            root.after(100, lambda: process_ui_queue(status, prog_bar, btn, back_btn))

        btn = ctk.CTkButton(card, text="make", command=create, fg_color=ACCENT)
        btn.pack(pady=15)

        back_btn = ctk.CTkButton(frame, text="Back", fg_color="#27272a", hover_color="#3f3f46", command=go_home)
        back_btn.pack(pady=10)

    elif current_view == "settings":
        ctk.CTkLabel(frame, text="settings", font=("Segoe UI", 22, "bold")).pack(pady=20)

        card = ctk.CTkFrame(frame, fg_color="#111111", corner_radius=12, border_width=1, border_color="#27272a")
        card.pack(pady=10, padx=120, fill="x")

        url_var = ctk.StringVar(value=settings["download_url"])
        ctk.CTkLabel(card, text="download url", text_color="#9ca3af", font=("Segoe UI", 12)).pack(pady=(10, 0))

        entry = ctk.CTkEntry(card, textvariable=url_var)
        entry.pack(pady=10, padx=15, fill="x")

        def save():
            settings["download_url"] = url_var.get().strip()
            log("settings saved.")
            messagebox.showinfo("Saved", "Download path updated successfully.")

        def toggle_fullscreen():
            settings["fullscreen"] = not settings["fullscreen"]
            root.attributes("-fullscreen", settings["fullscreen"])
            log(f"Fullscreen mode state: {settings['fullscreen']}")

        def toggle_debug():
            settings["debug_mode"] = debug_switch.get()
            toggle_debug_terminal()

        def wipe():
            if messagebox.askyesno("CRITICAL WARNING", "Wipe ALL existing instances? This cannot be undone."):
                try:
                    shutil.rmtree(INSTANCES_DIR)
                except:
                    pass
                os.makedirs(INSTANCES_DIR, exist_ok=True)
                log("All workspace software packages dropped.")
                go_home()

        ctk.CTkButton(card, text="Commit URL Source Updates", command=save, fg_color=ACCENT).pack(pady=5, padx=15, fill="x")
        ctk.CTkButton(card, text="Toggle Fullscreen", command=toggle_fullscreen, fg_color="#27272a", hover_color="#3f3f46").pack(pady=5, padx=15, fill="x")

        control_frame = ctk.CTkFrame(card, fg_color="transparent")
        control_frame.pack(fill="x", padx=15, pady=10)

        debug_switch = ctk.CTkSwitch(control_frame, text="Debug Mode", command=toggle_debug)
        debug_switch.pack(pady=5, padx=10)
        if settings.get("debug_mode", False): debug_switch.select()

        ctk.CTkButton(card, text="delete all instances", fg_color="#ef4444", hover_color="#b91c1c", command=wipe).pack(pady=15, padx=15, fill="x")

        ctk.CTkButton(frame, text="back", fg_color="#27272a", hover_color="#3f3f46", command=go_home).pack(pady=10)

        ctk.CTkLabel(frame, text="this project is open source", font=("Segoe UI", 14, "italic"), text_color="#71717a").pack(pady=(10, 0))
        ctk.CTkLabel(frame, text="https://github.com/chaceysgamestudio/dragonlauncher", font=("Segoe UI", 12), text_color=ACCENT).pack()

    log("UI refreshed")


# -------------------------
# launcher setup entrance
# -------------------------
root = ctk.CTk()
root.title("Half Dragon Launcher")
root.geometry("1100x650")
icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
if os.path.exists(icon_path):
    try:
        root.iconbitmap(icon_path)
    except:
        pass

sidebar = ctk.CTkFrame(root, width=240, fg_color="#09090b", border_width=1, border_color="#18181b")
sidebar.pack(side="left", fill="y")

ctk.CTkLabel(sidebar, text="HALF DRAGON", font=("Segoe UI", 22, "bold"), text_color="#f4f4f5").pack(pady=25)

home_btn = ctk.CTkButton(sidebar, text="Home", fg_color="transparent", text_color="#a1a1aa", hover_color="#18181b", anchor="w", font=("Segoe UI", 14), command=go_home)
home_btn.pack(fill="x", padx=15, pady=4)

create_btn = ctk.CTkButton(sidebar, text="Create Build", fg_color="transparent", text_color="#a1a1aa", hover_color="#18181b", anchor="w", font=("Segoe UI", 14), command=open_create)
create_btn.pack(fill="x", padx=15, pady=4)

settings_btn = ctk.CTkButton(sidebar, text="Settings", fg_color="transparent", text_color="#a1a1aa", hover_color="#18181b", anchor="w", font=("Segoe UI", 14), command=open_settings)
settings_btn.pack(fill="x", padx=15, pady=4)

main = ctk.CTkFrame(root, fg_color="#09090b")
main.pack(side="left", fill="both", expand=True)

frame = ctk.CTkFrame(main, fg_color="#09090b")
frame.pack(fill="both", expand=True, padx=20, pady=20)

load_state()
log("Launched.")
refresh()
root.mainloop()
