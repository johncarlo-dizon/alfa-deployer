def adjust_window_geometry(root):
    root.update_idletasks()

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    target_width = min(1100, screen_width - 40)
    target_height = min(760, screen_height - 80)

    center_x = int((screen_width / 2) - (target_width / 2))
    center_y = int((screen_height / 2) - (target_height / 2))

    root.geometry(f"{target_width}x{target_height}+{center_x}+{center_y}")
    root.minsize(900, 680)
    root.resizable(True, True)
