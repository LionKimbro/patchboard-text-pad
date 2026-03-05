import json
import time
import uuid
import tkinter as tk
from tkinter import ttk
from datetime import datetime

import lionscliapp as app


# ---- declarations ----

app.declare_app("patchboard-text-pad", "0.1.0")
app.describe_app("Simple Patchboard text emitter and receiver")
app.declare_projectdir(".textpad")
app.declare_key("path.inbox", ".textpad/inbox")
app.declare_key("path.outbox", ".textpad/outbox")
app.declare_key("component.title", "Text Pad")
app.describe_key("path.inbox", "Directory to poll for incoming Patchboard messages")
app.describe_key("path.outbox", "Directory to write outgoing Patchboard messages")
app.describe_key("component.title", "Human-readable title for this component instance")


# ---- globals ----

g = {}


# ---- patchboard ----

def write_message_to_outbox(channel, signal):
    msg = {
        "channel": channel,
        "signal": signal,
        "timestamp": str(time.time()),
    }
    filename = f"{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}.json"
    path = g["outbox"] / filename
    path.write_text(json.dumps(msg), encoding="utf-8")


def poll_inbox():
    for path in list(g["inbox"].glob("*.json")):
        try:
            msg = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        path.unlink()
        if msg.get("channel") == "text":
            handle_incoming_text(str(msg.get("signal", "")))
    g["root"].after(500, poll_inbox)


def handle_incoming_text(text):
    widget = g["text"]
    widget.delete("1.0", tk.END)
    widget.insert("1.0", text)


# ---- status ----

def set_status(msg):
    g["status_var"].set(msg)
    if g["status_job"]:
        g["root"].after_cancel(g["status_job"])
    g["status_job"] = g["root"].after(10000, clear_status)


def clear_status():
    g["status_var"].set("")
    g["status_job"] = None


# ---- button handlers ----

def on_clear_clicked():
    g["text"].delete("1.0", tk.END)


def build_id_card():
    inbox = g["inbox"]
    outbox = g["outbox"]
    return {
        "schema_version": 1,
        "title": app.ctx["component.title"],
        "inbox": str(inbox.resolve()),
        "outbox": str(outbox.resolve()),
        "channels": {
            "in": ["text"],
            "out": ["text", "component-id-card"],
        },
    }


def emit_id_card():
    card = build_id_card()
    write_message_to_outbox("component-id-card", card)
    project_dir = g["inbox"].parent
    (project_dir / "component-id-card.json").write_text(
        json.dumps(card, indent=2), encoding="utf-8"
    )


def on_emit_card_clicked():
    emit_id_card()
    now = datetime.now().strftime("%H:%M:%S")
    set_status(f"emitted component-id-card, at {now}")


def on_emit_text_clicked():
    text = g["text"].get("1.0", tk.END).rstrip("\n")
    write_message_to_outbox("text", text)
    now = datetime.now().strftime("%H:%M:%S")
    set_status(f"emitted to channel 'text', at {now}")


# ---- GUI ----

def build_gui():
    root = tk.Tk()
    root.title("patchboard-text-pad")
    root.withdraw()
    g["root"] = root
    g["status_job"] = None

    # menubar
    menubar = tk.Menu(root, tearoff=False)
    file_menu = tk.Menu(menubar, tearoff=False)
    file_menu.add_command(label="Quit", command=root.destroy, underline=0)
    menubar.add_cascade(label="File", menu=file_menu, underline=0)
    patchboard_menu = tk.Menu(menubar, tearoff=False)
    patchboard_menu.add_command(label="Emit: text", command=on_emit_text_clicked,
                                underline=6, accelerator="Ctrl+Enter")
    patchboard_menu.add_command(label="Emit: card", command=on_emit_card_clicked,
                                underline=6)
    menubar.add_cascade(label="Patchboard", menu=patchboard_menu, underline=0)
    root.config(menu=menubar)

    root.bind("<Control-Return>", lambda e: on_emit_text_clicked())

    # outer frame
    frame = ttk.Frame(root, padding=4)
    frame.grid(row=0, column=0, sticky="nsew")
    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)

    # text area + vertical scrollbar
    text = tk.Text(frame, wrap=tk.WORD, undo=True, width=80, height=24)
    scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text.yview)
    text.configure(yscrollcommand=scrollbar.set)
    text.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")
    g["text"] = text

    # button row
    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))
    ttk.Button(btn_frame, text="Clear", command=on_clear_clicked).grid(row=0, column=0, padx=(0, 4))
    ttk.Button(btn_frame, text="emit: text", command=on_emit_text_clicked).grid(row=0, column=1)

    # status bar
    status_var = tk.StringVar()
    status_bar = ttk.Label(frame, textvariable=status_var, anchor="w", relief="sunken", padding=(4, 2))
    status_bar.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 0))
    g["status_var"] = status_var

    root.deiconify()


# ---- command ----

def run_gui():
    inbox = app.ctx["path.inbox"]
    outbox = app.ctx["path.outbox"]
    inbox.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)
    g["inbox"] = inbox
    g["outbox"] = outbox

    build_gui()
    emit_id_card()
    g["root"].after(500, poll_inbox)
    g["root"].mainloop()


app.declare_cmd("", run_gui)
app.describe_cmd("", "Launch the text pad GUI")


def main():
    app.main()


if __name__ == "__main__":
    main()
