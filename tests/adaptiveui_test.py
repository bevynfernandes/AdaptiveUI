import adaptiveui.ui as ui

HELP_TEXT_ENABLED = False

manager = ui.UserInterface("AdaptiveUI Test System V1.2", (850, 400), resizable=True)

def get_story(orginal: bool = False) -> str:
    with open(f"data/story/{"story.md" if not orginal else "orginal.md"}", "r") as f:
        return f.read()

def remove_help_text(label: ui.tk.Text, label2: ui.tk.Text, scrollbar: ui.ttk.Scrollbar, ui_right_click: ui.tk.Menu) -> None:
    label.destroy()
    label2.pack(fill="both", expand=True, padx=8, pady=8)
    scrollbar.pack(side=ui.tk.RIGHT, fill=ui.tk.Y, pady=8)
    manager.ui_right_click.delete('Remove Help text')

def main():
    manager.mount_ui_rc_menu()
    label = ui.Tools.text(
        "To test AdaptiveUI, use the right-click menu.",
        window=manager.frame,
        font=("Segoe UI", 22),
    )
    if HELP_TEXT_ENABLED:
        label.pack(fill="both", padx=8)

    scrollbar = ui.ttk.Scrollbar(manager.frame)
    scrollbar.pack(side=ui.tk.RIGHT, fill=ui.tk.Y, pady=8 if HELP_TEXT_ENABLED else 0)

    label2 = ui.Tools.text(get_story(), window=manager.frame, markdown=True)
    label2["yscrollcommand"] = scrollbar.set
    label2.bind("<ButtonPress-1>", lambda _: "break")
    label2.pack(fill="both", expand=True, padx=8, pady=8 if HELP_TEXT_ENABLED else 0)
    scrollbar.config(command=label2.yview)

    if HELP_TEXT_ENABLED:
        manager.ui_right_click.add_separator()
        manager.ui_right_click.add_command(label="Remove Help text", command=lambda: remove_help_text(label, label2, scrollbar, manager.ui_right_click))
    manager.run()


if __name__ == "__main__":
    main()
