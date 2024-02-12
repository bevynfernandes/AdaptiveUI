import adaptiveui.ui as ui

manager = ui.UserInterface("AdaptiveUI Test System V1.1", (850, 400), resizable=True)

def get_story(orginal: bool = False) -> str:
    with open(f"data/story/{"story.md" if not orginal else "orginal.md"}", "r") as f:
        return f.read()

def main():
    manager.mount_ui_rc_menu()
    label = ui.Tools.text(
        "To test AdaptiveUI, use the right-click menu.",
        window=manager.frame,
        font=("Segoe UI", 22),
    )
    label.pack(fill="both", padx=8)
    manager.ui_right_click.add_separator()
    manager.ui_right_click.add_command(label="Remove Help text", command=label.destroy)

    scrollbar = ui.ttk.Scrollbar(manager.frame)
    scrollbar.pack(side=ui.tk.RIGHT, fill=ui.tk.Y)

    label2 = ui.Tools.text(get_story(), window=manager.frame, markdown=True)
    label2["yscrollcommand"] = scrollbar.set
    label2.bind("<ButtonPress-1>", lambda _: "break")
    label2.pack(fill="both", expand=True, padx=8)
    scrollbar.config(command=label2.yview)

    manager.frame.pack()
    manager.run()


if __name__ == "__main__":
    main()
