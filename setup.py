import tkinter as tk
from tkinter import messagebox
from pathlib import Path

ENV_PATH = Path(__file__).parent / ".env"

def load_existing_key():
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip()
    return ""

def save_key():
    key = entry.get().strip()
    if not key:
        messagebox.showerror("Error", "Please enter an API key.")
        return
    ENV_PATH.write_text(f"GEMINI_API_KEY={key}\n")
    messagebox.showinfo("Saved", "API key saved! You can now restart Claude Desktop.")
    root.destroy()

root = tk.Tk()
root.title("Gemini Research MCP — Setup")
root.resizable(False, False)
root.geometry("520x220")

tk.Label(root, text="Gemini Research MCP Setup", font=("Segoe UI", 14, "bold")).pack(pady=(20, 4))
tk.Label(
    root,
    text="Get a free API key at: aistudio.google.com/apikey",
    font=("Segoe UI", 9),
    fg="#555"
).pack()

tk.Label(root, text="Paste your Gemini API key below:", font=("Segoe UI", 10)).pack(pady=(16, 4))

entry = tk.Entry(root, width=55, font=("Segoe UI", 10), show="*")
entry.pack(ipady=4)
entry.insert(0, load_existing_key())

frame = tk.Frame(root)
frame.pack(pady=14)

def toggle_show():
    current = entry.cget("show")
    entry.config(show="" if current == "*" else "*")
    btn_show.config(text="Hide" if current == "*" else "Show")

btn_show = tk.Button(frame, text="Show", width=8, command=toggle_show)
btn_show.pack(side="left", padx=6)

tk.Button(frame, text="Save", width=8, command=save_key, bg="#4CAF50", fg="white").pack(side="left", padx=6)
tk.Button(frame, text="Cancel", width=8, command=root.destroy).pack(side="left", padx=6)

root.mainloop()
