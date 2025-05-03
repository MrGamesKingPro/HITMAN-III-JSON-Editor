import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Menu, font # Import Menu, font
import json
import os
import re
import pathlib
import webbrowser
from collections import defaultdict
import platform # To check OS for key bindings
import copy # Needed for deepcopy during save if desired, though shallow is used now

# Regular expression to find segments like //(start,end)\\text
# Capture groups: 1: full prefix, 2: text
SEGMENT_REGEX = re.compile(r"(//\([^)]+\)\\\\)(.*?)(?=(//\([^)]+\)\\\\|$)|\Z)", re.DOTALL)

# Regex to find "Language": "en" potentially with variable spacing
LANG_EN_REGEX = re.compile(r'"Language"\s*:\s*"en"')
# Regex to find "String": potentially with variable spacing
STRING_KEY_REGEX = re.compile(r'"String"\s*:')


# --- Constants ---
COL_LINE = "#1"
COL_TIMECODE = "#2"
COL_DIALOGUE = "#3" # Or use a symbolic name like 'dialogue' - using #3 for direct comparison

DIALOGUE_COLUMN_ID = COL_DIALOGUE # Explicitly use #3
FILE_HEADER_TAG = 'file_header' # Define a constant for the tag
SEPARATOR_TAG = 'separator'
SEARCH_HIGHLIGHT_TAG = 'search_highlight' # Tag for search results

# --- Theme Colors ---
THEMES = {
    "Light": {
        "bg": "#F0F0F0",
        "fg": "black",
        "entry_bg": "white",
        "entry_fg": "black",
        "tree_bg": "white",
        "tree_fg": "black",
        "tree_selected_bg": "#0078D7", # System highlight blue
        "tree_selected_fg": "white",
        "header_bg": "#E0E0E0",
        "header_fg": "black",
        "separator_bg": "#F5F5F5",
        "search_bg": "yellow",
        "search_fg": "black",
        "button_bg": "#E1E1E1", # Default button look
        "button_fg": "black",
        "status_bg": "#F0F0F0",
        "status_fg": "black",
        "disabled_fg": "#A0A0A0",
        "menu_bg": "#F0F0F0", # Added for menu
        "menu_fg": "black", # Added for menu
        "menu_active_bg": "#0078D7", # Added for menu
        "menu_active_fg": "white", # Added for menu
    },
    "Dark": {
        "bg": "#2E2E2E",
        "fg": "#EAEAEA",
        "entry_bg": "#3C3C3C",
        "entry_fg": "#EAEAEA",
        "tree_bg": "#252525",
        "tree_fg": "#EAEAEA",
        "tree_selected_bg": "#5E5E5E", # Darker selection
        "tree_selected_fg": "#EAEAEA",
        "header_bg": "#7D7D7D", # file name
        "header_fg": "#EAEAEA",
        "separator_bg": "#333333",
        "search_bg": "#B8860B", # Dark Goldenrod
        "search_fg": "black",
        "button_bg": "#505050",
        "button_fg": "#EAEAEA",
        "status_bg": "#2E2E2E",
        "status_fg": "#EAEAEA",
        "disabled_fg": "#707070",
        "menu_bg": "#2E2E2E", # Added for menu
        "menu_fg": "#EAEAEA", # Added for menu
        "menu_active_bg": "#5E5E5E", # Added for menu
        "menu_active_fg": "#EAEAEA", # Added for menu
    },
        "Red/Dark": {
        "bg": "#D30707", # background window
        "fg": "#EAEAEA", # Text search
        "entry_bg": "#3C3C3C", # box
        "entry_fg": "#FFFFFF", # text s
        "tree_bg": "#252525", # background text
        "tree_fg": "#EAEAEA",# text
        "tree_selected_bg": "#D30707", # Darker selection
        "tree_selected_fg": "#EAEAEA", # text selection
        "header_bg": "#AEAEAE", # background file name
        "header_fg": "#000000", # text file name
        "separator_bg": "#252525", # empty
        "search_bg": "#B8860B", # Dark Goldenrod
        "search_fg": "#FFFFFF",
        "button_bg": "#003948", # button
        "button_fg": "#FFFFFF", #  text box 
        "status_bg": "#2E2E2E", #  box results
        "status_fg": "#E8E8E8", # results
        "disabled_fg": "#FFFFFF", # text save all & box
        "menu_bg": "#2E2E2E", # Added for menu
        "menu_fg": "#EAEAEA", # Added for menu
        "menu_active_bg": "#D30707", # Added for menu
        "menu_active_fg": "#EAEAEA", # Added for menu
    }
}

class JsonEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("HITMAN III JSON Editor v1.1") # Simplified title with version
        self.root.geometry("1100x800")

        self.style = ttk.Style()
        # Use a theme that allows easier color configuration if available
        available_themes = self.style.theme_names()
        if 'clam' in available_themes:
             self.style.theme_use('clam')
        elif 'alt' in available_themes:
             self.style.theme_use('alt')
        # Default theme might be harder to customize fully

        # --- Data Structures ---
        self.input_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.file_data = []
        self.item_id_map = {}

        # --- Editing State ---
        self.edit_entry = None
        self.edit_item_id = None
        self._escape_pressed = False # Track Escape key for edit cancelling

        # --- Search State ---
        self.search_term = tk.StringVar()
        self.search_results = []
        self.current_search_index = -1

        # --- Theme State ---
        self.current_theme = tk.StringVar(value="Red/Dark") # Default theme

        # --- Menu Bar ---
        self.menu_bar = Menu(root)
        root.config(menu=self.menu_bar)

        # File Menu
        self.file_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Select Input Folder...", command=self.select_input_folder)
        self.file_menu.add_command(label="Select Output Folder...", command=self.select_output_folder)
        self.file_menu.add_separator()
        # Add Save command, state managed by _update_save_state using the label
        # The accelerator triggers the command *if* state is NORMAL
        self.file_menu.add_command(label="Save All Changes", command=self.save_all_files, state=tk.DISABLED, accelerator=self._get_accelerator("S"))
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.root.quit)

        # Edit Menu
        self.edit_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Edit", menu=self.edit_menu)
        self.edit_menu.add_command(label="Cut", command=self._cut_selection, accelerator=self._get_accelerator("X"))
        self.edit_menu.add_command(label="Copy", command=self._copy_selection, accelerator=self._get_accelerator("C"))
        self.edit_menu.add_command(label="Paste", command=self._paste_selection, accelerator=self._get_accelerator("V"))
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Find", command=self._focus_search, accelerator=self._get_accelerator("F"))


        # View Menu (for Themes)
        self.view_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="View", menu=self.view_menu)
        self.theme_menu = Menu(self.view_menu, tearoff=0)
        self.view_menu.add_cascade(label="Theme", menu=self.theme_menu)
        self.theme_menu.add_radiobutton(label="Light", variable=self.current_theme, value="Light", command=self._apply_theme)
        self.theme_menu.add_radiobutton(label="Dark", variable=self.current_theme, value="Dark", command=self._apply_theme)
        self.theme_menu.add_radiobutton(label="Red/Dark", variable=self.current_theme, value="Red/Dark", command=self._apply_theme)

        # Help Menu
        self.help_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Help", menu=self.help_menu)
        self.help_menu.add_command(label="Instructions", command=self._show_help)
        self.help_menu.add_command(label="About", command=self._show_about)


        # --- UI Elements ---
        # Frame for folder selection
        self.folder_frame = ttk.Frame(root, padding="10")
        self.folder_frame.pack(fill=tk.X)

        ttk.Button(self.folder_frame, text="Select Input Folder", command=self.select_input_folder).pack(side=tk.LEFT, padx=5)
        self.input_entry = ttk.Entry(self.folder_frame, textvariable=self.input_folder, width=40, state='readonly')
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        ttk.Button(self.folder_frame, text="Select Output Folder", command=self.select_output_folder).pack(side=tk.LEFT, padx=5)
        self.output_entry = ttk.Entry(self.folder_frame, textvariable=self.output_folder, width=40, state='readonly')
        self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # --- Search Frame ---
        self.search_frame = ttk.Frame(root, padding=(10, 0, 10, 5))
        self.search_frame.pack(fill=tk.X)

        self.search_label = ttk.Label(self.search_frame, text="Search Text:")
        self.search_label.pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry = ttk.Entry(self.search_frame, textvariable=self.search_term)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.search_entry.bind("<Return>", self._perform_search)
        self.search_entry.bind("<KP_Enter>", self._perform_search)
        self.search_entry.bind("<KeyRelease>", self._check_clear_search_on_empty)

        self.find_button = ttk.Button(self.search_frame, text="Find", command=self._perform_search)
        self.find_button.pack(side=tk.LEFT, padx=5)
        self.next_button = ttk.Button(self.search_frame, text="Next", command=self._find_next)
        self.next_button.pack(side=tk.LEFT, padx=5)
        self.prev_button = ttk.Button(self.search_frame, text="Previous", command=self._find_previous)
        self.prev_button.pack(side=tk.LEFT, padx=5)

        # --- Treeview Frame ---
        self.tree_frame = ttk.Frame(root, padding="10")
        self.tree_frame.pack(fill=tk.BOTH, expand=True)

        # Define Columns
        columns = (COL_LINE, COL_TIMECODE, DIALOGUE_COLUMN_ID)
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings")

        # Headings
        self.tree.heading(COL_LINE, text="Line #")
        self.tree.heading(COL_TIMECODE, text="Timecode")
        self.tree.heading(DIALOGUE_COLUMN_ID, text="Text (Double-click  to edit, header to open file)")

        # Column Configuration
        self.tree.column(COL_LINE, anchor=tk.E, width=60, stretch=False)
        self.tree.column(COL_TIMECODE, anchor=tk.W, width=150, stretch=False)
        self.tree.column(DIALOGUE_COLUMN_ID, anchor=tk.W, width=700) # Make main column resizable

        # Scrollbars
        self.tree_scrollbar_y = ttk.Scrollbar(self.tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree_scrollbar_x = ttk.Scrollbar(self.tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=self.tree_scrollbar_y.set, xscrollcommand=self.tree_scrollbar_x.set)

        self.tree_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Tag Configuration (Initial setup, colors applied by theme)
        try:
            # Try setting the font for the tag
            header_font = font.Font(family="Courier New", size=10, weight="bold")
            self.tree.tag_configure(FILE_HEADER_TAG, font=header_font)
        except tk.TclError:
            # Fallback if font object isn't supported directly in tag_configure
            # (Might happen on older Tk versions or specific platforms)
            print("Warning: Font object may not be directly supported in tree tag_configure. Using default font.")
            self.tree.tag_configure(FILE_HEADER_TAG, font= ('Courier New', 10, 'bold'))
        except Exception as e:
             print(f"Warning: Could not set header font: {e}")
             self.tree.tag_configure(FILE_HEADER_TAG) # Configure tag without font if error

        self.tree.tag_configure('protected', foreground='#555555') # Less important, might not need theme change
        self.tree.tag_configure(SEPARATOR_TAG)
        self.tree.tag_configure(SEARCH_HIGHLIGHT_TAG) # Colors set by theme

        # --- Context Menu ---
        self.context_menu = Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="Copy", command=self._copy_selection, accelerator=self._get_accelerator("C"))
        self.context_menu.add_command(label="Cut", command=self._cut_selection, accelerator=self._get_accelerator("X"))
        self.context_menu.add_command(label="Paste", command=self._paste_selection, accelerator=self._get_accelerator("V"))

        # --- Bind Treeview Events ---
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree.bind("<Button-1>", self._on_tree_single_click_or_clear_edit)
        self.tree.bind("<Button-3>", self._show_context_menu) # Right-click

        # --- Bind Keyboard Shortcuts (Specific & Global) ---
        modifier = self._get_modifier_key()
        # Bind basic edit shortcuts directly to the tree (for when it has focus)
        self.tree.bind(f"<{modifier}-c>", self._copy_selection)
        self.tree.bind(f"<{modifier}-x>", self._cut_selection)
        self.tree.bind(f"<{modifier}-v>", self._paste_selection)

        # Bind Find globally (more likely to be used anytime)
        self.root.bind_all(f"<{modifier}-f>", lambda e: self._focus_search()) # Find shortcut

        # Note: Ctrl+S/Cmd+S is handled by the menu accelerator directly. No need for bind_all.

        # --- Status Bar ---
        self.status_frame = ttk.Frame(root, padding="10")
        self.status_frame.pack(fill=tk.X)

        self.status_label = ttk.Label(self.status_frame, text="Status: Select input folder.")
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.save_button = ttk.Button(self.status_frame, text="Save All Changes", command=self.save_all_files, state=tk.DISABLED)
        self.save_button.pack(side=tk.RIGHT, padx=5)

        # Configure resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(3, weight=1) # Treeview frame row
        self.folder_frame.columnconfigure(1, weight=1) # Input entry
        self.folder_frame.columnconfigure(3, weight=1) # Output entry
        self.search_frame.columnconfigure(1, weight=1) # Search entry
        self.tree_frame.columnconfigure(0, weight=1) # Treeview widget itself
        self.tree_frame.rowconfigure(0, weight=1)
        self.status_frame.columnconfigure(0, weight=1) # Status label

        # --- Apply Initial Theme ---
        self._apply_theme() # Apply default theme (Light)


    # --- Themeing ---
    def _apply_theme(self):
        theme_name = self.current_theme.get()
        colors = THEMES.get(theme_name, THEMES["Light"]) # Fallback to Light

        # Configure root window background
        self.root.config(bg=colors["bg"])

        # Configure ttk styles
        self.style.configure('.', background=colors["bg"], foreground=colors["fg"])
        self.style.configure('TButton', background=colors["button_bg"], foreground=colors["button_fg"], padding=5)
        self.style.map('TButton', background=[('active', colors["header_bg"]), ('disabled', colors["button_bg"])], foreground=[('disabled', colors["disabled_fg"])]) # Handle disabled state
        self.style.configure('TEntry', fieldbackground=colors["entry_bg"], foreground=colors["entry_fg"], insertcolor=colors["fg"]) # Set cursor color
        self.style.map('TEntry', foreground=[('readonly', colors["disabled_fg"])])
        self.style.configure('TLabel', background=colors["bg"], foreground=colors["fg"])
        self.style.configure('TFrame', background=colors["bg"])
        self.style.configure('Treeview',
                             background=colors["tree_bg"],
                             fieldbackground=colors["tree_bg"], # Important for Treeview background
                             foreground=colors["tree_fg"])
        self.style.map('Treeview',
                       background=[('selected', colors["tree_selected_bg"])],
                       foreground=[('selected', colors["tree_selected_fg"])])
        self.style.configure('Treeview.Heading', background=colors["button_bg"], foreground=colors["button_fg"], font=('TkDefaultFont', 10, 'bold'))
        self.style.map('Treeview.Heading', background=[('active', colors["header_bg"])])

        # Configure specific widgets that might not fully follow style
        self.status_label.config(background=colors["status_bg"], foreground=colors["status_fg"])
        # Readonly entries often inherit fieldbackground, but fg might need explicit setting
        self.input_entry.config(foreground=colors["disabled_fg"])
        self.output_entry.config(foreground=colors["disabled_fg"])

        # Frames backgrounds
        self.folder_frame.config(style='TFrame')
        self.search_frame.config(style='TFrame')
        self.tree_frame.config(style='TFrame')
        self.status_frame.config(style='TFrame')

        # Configure Treeview Tags (Important!)
        self.tree.tag_configure(FILE_HEADER_TAG, background=colors["header_bg"], foreground=colors["header_fg"])
        self.tree.tag_configure(SEPARATOR_TAG, background=colors["separator_bg"])
        # Ensure protected tag also follows theme foreground
        self.tree.tag_configure('protected', foreground=colors.get("disabled_fg", "#555555"))
        self.tree.tag_configure(SEARCH_HIGHLIGHT_TAG, background=colors["search_bg"], foreground=colors["search_fg"])

        # Configure Menu appearance (basic theming)
        menu_elements = [self.menu_bar, self.file_menu, self.edit_menu, self.view_menu, self.theme_menu, self.help_menu, self.context_menu]
        for menu in menu_elements:
             try:
                 menu.config(bg=colors["menu_bg"], fg=colors["menu_fg"],
                             activebackground=colors["menu_active_bg"],
                             activeforeground=colors["menu_active_fg"],
                             activeborderwidth=0,
                             bd=0) # Remove borders for a flatter look
             except tk.TclError as e:
                 print(f"Warning: Could not configure menu theme properties: {e}") # May fail on some platforms/Tk versions

        # Force update of styles on existing widgets if needed (often automatic)
        self.root.update_idletasks()


    # --- OS Specific Key Bindings ---
    def _get_modifier_key(self):
        if platform.system() == "Darwin": return "Command"
        else: return "Control"

    def _get_accelerator(self, key):
        modifier = self._get_modifier_key()
        mod_symbol = "Cmd" if modifier == "Command" else "Ctrl"
        return f"{mod_symbol}+{key.upper()}"

    # --- Folder Selection & State ---
    def select_input_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            if self.output_folder.get() and pathlib.Path(folder).resolve() == pathlib.Path(self.output_folder.get()).resolve():
                 messagebox.showwarning("Warning", "Input folder cannot be the same as the output folder.")
                 return
            self.input_folder.set(folder)
            self._clear_search()
            self.file_data = []
            self.item_id_map = {}
            self.tree.delete(*self.tree.get_children())
            self.load_json_files()
            self._update_save_state() # Use unified state updater

    def select_output_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            if self.input_folder.get() and pathlib.Path(folder).resolve() == pathlib.Path(self.input_folder.get()).resolve():
                 messagebox.showwarning("Warning", "Output folder cannot be the same as the input folder.")
                 return
            self.output_folder.set(folder)
            self._update_save_state() # Use unified state updater

    def _update_save_state(self):
        """Updates the state of the Save button and Save menu item."""
        if self.input_folder.get() and self.output_folder.get() and self.file_data:
            new_state = tk.NORMAL
        else:
            new_state = tk.DISABLED

        self.save_button.config(state=new_state)
        # Update the File menu item state using its LABEL
        try:
            # Use the label which is more robust than index
            self.file_menu.entryconfigure("Save All Changes", state=new_state)
        except tk.TclError as e:
             print(f"Warning: Could not update Save menu item state ('Save All Changes'): {e}")
        except AttributeError:
             # This might happen if called very early before menus are fully built
             print("Warning: File menu not fully initialized when trying to update save state.")


    # --- File Opening Logic ---
    def _open_file_from_header(self, header_iid):
        # (Code identical to the original, no changes needed here)
        try:
            if not header_iid.startswith("header_"):
                print(f"Warning: Unexpected header IID format: {header_iid}")
                return

            file_index_str = header_iid.split('_')[-1]
            file_index = int(file_index_str)

            if not (0 <= file_index < len(self.file_data)):
                print(f"Error: File index {file_index} derived from IID {header_iid} is out of bounds.")
                messagebox.showerror("Error", "Could not open file: Internal data inconsistency.")
                return

            file_path = self.file_data[file_index]['path']

            if file_path and file_path.is_file():
                try:
                    if platform.system() == "Windows":
                        os.startfile(file_path)
                    elif platform.system() == "Darwin": # macOS
                        # Use subprocess for better error handling/backgrounding
                        import subprocess
                        subprocess.run(['open', file_path], check=False)
                        # os.system(f'open "{file_path}"') # Previous method
                    else: # Linux and other Unix-like
                        import subprocess
                        subprocess.run(['xdg-open', file_path], check=False)
                        # os.system(f'xdg-open "{file_path}"') # Previous method
                    print(f"Attempting to open: {file_path}")
                except Exception as e:
                    print(f"Error opening file {file_path} using system handler: {e}")
                    try:
                        file_uri = file_path.as_uri()
                        print(f"Fallback: Attempting to open with webbrowser: {file_uri}")
                        webbrowser.open(file_uri)
                    except Exception as e_web:
                        print(f"Error opening file {file_path} with webbrowser fallback: {e_web}")
                        messagebox.showerror("File Open Error", f"Could not open file:\n{file_path}\n\nError: {e_web} (after primary error: {e})")
            else:
                print(f"Error: Original file path not found or is not a file for index {file_index}: {file_path}")
                messagebox.showerror("File Open Error", f"Could not open file:\nPath: {file_path}")

        except (ValueError, IndexError) as e:
            print(f"Error parsing file index from IID '{header_iid}': {e}")
            messagebox.showerror("Error", "Could not open file: Failed to determine file index.")
        except Exception as e:
            print(f"Unexpected error opening file for IID '{header_iid}': {e}")
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")


    # --- Treeview Click Handlers ---
    def _on_tree_single_click_or_clear_edit(self, event):
        # Check if click was on the edit box itself
        widget = event.widget.winfo_containing(event.x_root, event.y_root)
        is_click_on_edit_entry = (widget == self.edit_entry)

        clicked_item_id = self.tree.identify_row(event.y)

        # Save/clear existing edit *unless* the click was inside the edit box
        if self.edit_entry and not is_click_on_edit_entry:
            if self.edit_item_id and self.tree.exists(self.edit_item_id):
                # Check if the click is outside the currently edited cell
                if clicked_item_id != self.edit_item_id:
                    self._save_edit(self.edit_item_id, DIALOGUE_COLUMN_ID)
                else:
                    # If click is on the same item but not in edit box, maybe focus out occurred?
                    # Let FocusOut handler manage saving if click is outside editor.
                    # If focus remains in editor, do nothing here.
                    pass
            else:
                # Edited item disappeared? Just destroy the editor.
                self._destroy_edit_entry()


    def _on_tree_double_click(self, event):
        # Finish any existing edit first
        if self.edit_entry:
             if self.edit_item_id and self.tree.exists(self.edit_item_id):
                 self._save_edit(self.edit_item_id, DIALOGUE_COLUMN_ID)
             else:
                 self._destroy_edit_entry()

        region = self.tree.identify("region", event.x, event.y)
        item_id = self.tree.identify_row(event.y)
        column_id_clicked = self.tree.identify_column(event.x)

        if not item_id: return

        try:
            item_tags = self.tree.item(item_id, "tags")
        except tk.TclError: return # Item might have disappeared

        # Handle header double-click to open file
        if FILE_HEADER_TAG in item_tags:
            self._open_file_from_header(item_id)
        # Handle data row double-click to start editing
        elif item_id in self.item_id_map:
            # Check if the double-click was specifically on a cell in the Dialogue column
            if region == "cell" and column_id_clicked == DIALOGUE_COLUMN_ID:
                self._start_editing(item_id, column_id_clicked)


    # --- Treeview Editing Logic ---
    def _start_editing(self, item_id, column_id):
        self._destroy_edit_entry() # Ensure any previous editor is gone
        bbox = self.tree.bbox(item_id, column=column_id)
        if not bbox: return # Item might not be visible or exist

        x, y, width, height = bbox
        current_text = self.tree.set(item_id, column_id)

        # Use themed entry colors
        colors = THEMES.get(self.current_theme.get(), THEMES["Light"])

        # Create the Entry widget as a child of the Treeview
        self.edit_entry = ttk.Entry(self.tree, style='Treeview.TEntry') # Use a specific style if needed
        # Configure the specific style (optional, might inherit from TEntry)
        self.style.configure('Treeview.TEntry', fieldbackground=colors["entry_bg"], foreground=colors["entry_fg"])

        # Place the Entry widget exactly over the cell
        self.edit_entry.place(x=x, y=y, width=width, height=height, anchor='nw')

        self.edit_entry.insert(0, current_text)
        self.edit_entry.select_range(0, tk.END)
        self.edit_entry.focus_set()
        self.edit_item_id = item_id
        self._escape_pressed = False # Reset escape flag for new edit

        # Bind events to the Entry widget
        self.edit_entry.bind("<Return>", lambda e: self._save_edit(item_id, column_id))
        self.edit_entry.bind("<KP_Enter>", lambda e: self._save_edit(item_id, column_id))
        self.edit_entry.bind("<FocusOut>", lambda e: self._save_edit_on_focus_out(item_id, column_id))
        self.edit_entry.bind("<Escape>", self._cancel_edit)

    def _save_edit_on_focus_out(self, item_id, column_id):
        # Only save if Escape wasn't pressed
        # This check helps prevent saving when focus is lost *because* Escape was pressed
        if self.edit_entry and not self._escape_pressed:
            if self.edit_item_id == item_id and self.tree.exists(item_id):
                 self._save_edit(item_id, column_id)
            else:
                 # Item might have changed or disappeared, just destroy editor
                 self._destroy_edit_entry()
        elif self.edit_entry: # Escape was pressed, edit_entry still exists
            self._destroy_edit_entry() # Destroy without saving


    def _save_edit(self, item_id, column_id):
        # Check if the editor still exists and corresponds to the intended item
        if not self.edit_entry or item_id != self.edit_item_id:
             # If edit_entry exists but item ID mismatch, maybe focus switched rapidly? Destroy it.
             if self.edit_entry: self._destroy_edit_entry()
             return

        new_text = self.edit_entry.get()
        current_tree_text = ""
        try:
            # Check if the tree item still exists before trying to access it
            if self.tree.exists(item_id):
                 current_tree_text = self.tree.set(item_id, column_id)
            else:
                 print(f"Warning: Item {item_id} disappeared before saving edit.")
                 self._destroy_edit_entry()
                 return
        except tk.TclError:
             # This handles the case where the item might exist but is inaccessible (rare)
             print(f"Warning: TclError accessing item {item_id} before saving edit.")
             self._destroy_edit_entry()
             return

        # Only update if text has actually changed
        if new_text != current_tree_text:
            if self.tree.exists(item_id): # Check again right before setting
                self.tree.set(item_id, column_id, new_text)
            else:
                 print(f"Warning: Item {item_id} disappeared just before updating tree view text.")
                 self._destroy_edit_entry()
                 return # Don't proceed if item vanished

            # Update the backend data structure
            if item_id in self.item_id_map:
                map_info = self.item_id_map[item_id]
                file_idx = map_info.get("file_index")
                string_info_idx = map_info.get("string_info_index")
                seg_idx = map_info.get("segment_index")

                # Enhanced Robust Check for data integrity before update
                if not (isinstance(file_idx, int) and
                        isinstance(string_info_idx, int) and
                        isinstance(seg_idx, int)):
                     print(f"Error: Corrupt map info for IID '{item_id}' during save.")
                     messagebox.showerror("Internal Error", f"Could not save change for item {item_id}.\nMap data inconsistent.")
                     # Destroy editor, but leave inconsistent tree view state as is, maybe add visual error tag?
                     self._destroy_edit_entry()
                     return

                try:
                    # Verify data structure path exists and has correct types before assignment
                    if not (0 <= file_idx < len(self.file_data) and
                            isinstance(self.file_data[file_idx], dict) and
                            isinstance(self.file_data[file_idx].get("en_strings"), list) and
                            0 <= string_info_idx < len(self.file_data[file_idx]["en_strings"]) and
                            isinstance(self.file_data[file_idx]["en_strings"][string_info_idx], dict) and
                            isinstance(self.file_data[file_idx]["en_strings"][string_info_idx].get("segments"), list) and
                            0 <= seg_idx < len(self.file_data[file_idx]["en_strings"][string_info_idx]["segments"]) and
                            isinstance(self.file_data[file_idx]["en_strings"][string_info_idx]["segments"][seg_idx], dict)):
                        # If the structure is broken, raise an error to prevent data corruption
                        raise IndexError("Data structure integrity compromised during save attempt.")

                    # Update the data
                    self.file_data[file_idx]["en_strings"][string_info_idx]["segments"][seg_idx]["text"] = new_text
                except (IndexError, KeyError, TypeError) as e:
                     print(f"Error: Data structure issue during save for IID '{item_id}'. Error: {e}")
                     messagebox.showerror("Internal Error", f"Could not save change for item {item_id}.\nData inconsistent.")
                     # Consider reverting the tree view change here if the data save failed
                     # if self.tree.exists(item_id):
                     #     self.tree.set(item_id, column_id, current_tree_text)
            else:
                 # This should ideally not happen if item_id exists and isn't a header/separator
                 print(f"Error: Could not find map info for IID '{item_id}' during save.")

        # Destroy the editor whether saved or not (unless an error prevented it)
        self._destroy_edit_entry()

    def _cancel_edit(self, event=None):
        self._escape_pressed = True # Set flag to prevent FocusOut save
        self._destroy_edit_entry() # Destroy the editor immediately
        return "break" # Prevent further processing of the Escape key

    def _destroy_edit_entry(self):
        if self.edit_entry:
            # Explicitly unbind events before destroying to prevent race conditions
            try:
                self.edit_entry.unbind("<Return>")
                self.edit_entry.unbind("<KP_Enter>")
                self.edit_entry.unbind("<FocusOut>")
                self.edit_entry.unbind("<Escape>")
            except tk.TclError:
                pass # Widget might already be gone
            self.edit_entry.destroy()
        self.edit_entry = None
        self.edit_item_id = None
        # Don't reset escape_pressed here, FocusOut might need it
        # Give focus back to the tree so keyboard navigation works
        self.tree.focus_set()


    # --- File Loading Logic ---
    def _find_en_string_line_numbers(self, file_path):
        line_numbers = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            in_object = False
            brace_count = 0
            found_lang_en_in_current_object = False
            string_line_num_for_current_object = None
            potential_string_line = None # Track the line where "String" appears

            for i, line in enumerate(lines):
                line_num = i + 1
                stripped_line = line.strip()

                # Simple comment skipping (might need refinement for complex cases)
                if stripped_line.startswith("//") or stripped_line.startswith("#"):
                    continue

                # Handle braces to track object scope
                open_braces = line.count('{')
                close_braces = line.count('}')

                if not in_object:
                    if '{' in line:
                        in_object = True
                        # Reset state for the new object
                        brace_count = 0
                        found_lang_en_in_current_object = False
                        string_line_num_for_current_object = None
                        potential_string_line = None
                        # Calculate initial brace count carefully, handling multiple braces on one line
                        brace_count += open_braces
                        brace_count -= close_braces
                else: # Already inside an object
                    brace_count += open_braces
                    brace_count -= close_braces

                # Inside an object, look for keys
                if in_object:
                    # Check for "Language": "en"
                    if not found_lang_en_in_current_object and LANG_EN_REGEX.search(line):
                        found_lang_en_in_current_object = True
                        # If we already found "String", associate its line number now
                        if potential_string_line is not None:
                            string_line_num_for_current_object = potential_string_line

                    # Check for "String":
                    # Only store the *first* potential "String" line within the current object context
                    if potential_string_line is None and STRING_KEY_REGEX.search(line):
                         potential_string_line = line_num
                         # If we already found "en", associate this line number immediately
                         if found_lang_en_in_current_object:
                             string_line_num_for_current_object = potential_string_line

                # Check for end of object
                # Need brace_count <= 0 because } might be on the same line as the last {
                if in_object and brace_count <= 0 and '}' in line : # Check if a closing brace exists on this line
                    if found_lang_en_in_current_object and string_line_num_for_current_object is not None:
                        line_numbers.append(string_line_num_for_current_object)

                    # Reset for the next potential object
                    in_object = False
                    brace_count = 0
                    found_lang_en_in_current_object = False
                    string_line_num_for_current_object = None
                    potential_string_line = None
                    # Handle cases like { ... } { ... } on one line: If braces remain, stay in object
                    if brace_count > 0: in_object = True

        except Exception as e:
            print(f"Warning: Could not read lines for line number detection in {file_path.name}: {e}")
        return line_numbers


    def load_json_files(self):
        folder_path = self.input_folder.get()
        if not folder_path: return

        self._clear_search() # Clear search results and highlighting
        self.file_data = [] # Reset internal data
        self.item_id_map = {} # Reset item mapping
        self._destroy_edit_entry() # Clear any active edit cell
        for item in self.tree.get_children(): # Clear treeview
            self.tree.delete(item)

        self.status_label.config(text="Status: Loading...")
        self.root.update_idletasks() # Show status update immediately

        segment_count = 0
        files_with_line_num_errors = []
        processed_file_count = 0
        loaded_file_count = 0 # Count files actually added to file_data

        try:
            # Use pathlib for robust path handling
            p_folder_path = pathlib.Path(folder_path)
            if not p_folder_path.is_dir():
                raise FileNotFoundError(f"Input path is not a valid directory: {folder_path}")

            all_items = list(p_folder_path.iterdir())
            json_files = sorted([
                item for item in all_items
                if item.is_file() and item.suffix.lower() == '.json' and not item.name.lower().endswith('.json.meta')
            ])

            if not json_files:
                 self.status_label.config(text="Status: No non-meta .json files found in input folder.")
                 self._update_save_state()
                 return

            temp_file_data_list = [] # Collect valid data before assigning to self.file_data

            for file_path in json_files:
                processed_file_count += 1
                # Get line numbers first (best effort)
                en_string_line_numbers = self._find_en_string_line_numbers(file_path)
                line_num_mismatch_detected = False # Flag for mismatch within this file

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                except (json.JSONDecodeError, Exception) as e:
                    print(f"Warning: Skipping file {file_path.name} due to read/parse error: {e}");
                    continue # Skip to next file

                # Expect content to be a list of objects
                if not isinstance(content, list):
                    print(f"Warning: Skipping file {file_path.name} - content is not a list.");
                    continue # Skip to next file

                file_entry = { "path": file_path, "json_content": content, "en_strings": [] }
                found_en_in_file = False
                current_en_strings_data = [] # Store 'en' strings found in this file
                en_object_counter_in_file = 0 # Track how many 'en' objects we find in JSON

                # Iterate through the items in the JSON list
                for item_idx_in_json, item in enumerate(content):
                     # Check if the item is a dictionary and has "Language": "en"
                     if isinstance(item, dict) and item.get("Language") == "en":
                        found_en_in_file = True
                        original_string = item.get("String", "") # Get the dialogue string
                        segments_data = [] # To store parsed segments

                        # Try to get the corresponding line number
                        line_num = en_string_line_numbers[en_object_counter_in_file] if en_object_counter_in_file < len(en_string_line_numbers) else None

                        # Detect mismatch if we run out of line numbers from parsing
                        if line_num is None and en_object_counter_in_file >= len(en_string_line_numbers):
                             line_num_mismatch_detected = True

                        # Use regex to find segments (prefix + text)
                        matches = list(SEGMENT_REGEX.finditer(original_string))
                        if matches:
                            # If segments found, store each part
                            for seg_idx, match in enumerate(matches):
                                segments_data.append({
                                    "original_prefix": match.group(1),
                                    "text": match.group(2),
                                    "iid": None # Placeholder for Treeview Item ID
                                })
                        else:
                            # If no segments match, treat the whole string as one segment
                            segments_data.append({
                                "original_prefix": None,
                                "text": original_string,
                                "iid": None
                            })

                        # Store the collected info for this "en" string
                        current_en_strings_data.append({
                            "original_item_index": item_idx_in_json, # Index in original JSON list
                            "original_line_number": line_num, # Line number from text parsing (or None)
                            "original_string": original_string, # The full original string
                            "segments": segments_data # List of parsed segments
                        })
                        en_object_counter_in_file += 1 # Increment counter for found 'en' objects

                # After processing the file, check for line number count mismatches
                if found_en_in_file and (en_object_counter_in_file != len(en_string_line_numbers) or line_num_mismatch_detected):
                     if file_path.name not in files_with_line_num_errors:
                         files_with_line_num_errors.append(file_path.name)
                         print(f"Warning: Line number mismatch/issue in {file_path.name}. JSON 'en' count: {en_object_counter_in_file}, Text parse line# count: {len(en_string_line_numbers)}.")

                # If we found any "en" strings, add this file's data to our temporary list
                if found_en_in_file:
                    file_entry["en_strings"] = current_en_strings_data
                    temp_file_data_list.append(file_entry)
                    loaded_file_count += 1


            # --- Populate Treeview from collected data ---
            self.file_data = temp_file_data_list # Assign collected valid data

            for file_index, file_entry in enumerate(self.file_data):
                # Insert a header row for the file
                header_iid = f"header_{file_index}"
                header_display_text = f"--- File: {file_entry['path'].name} (Double-click to open) ---"
                self.tree.insert('', tk.END, iid=header_iid, values=(f"FILE {file_index+1}", "", header_display_text), tags=(FILE_HEADER_TAG,))

                # Iterate through the "en" strings found in this file
                for string_info_idx, string_info in enumerate(file_entry["en_strings"]):
                    line_num_display = str(string_info.get("original_line_number") or "??") # Display line number or '??'
                    # Iterate through the segments of this string
                    for segment_idx, segment in enumerate(string_info["segments"]):
                        # Create a unique Item ID (IID) for the treeview row
                        iid = f"f{file_index}_i{string_info['original_item_index']}_s{segment_idx}"
                        segment['iid'] = iid # Store the IID back in the segment data
                        prefix_display = segment["original_prefix"] if segment["original_prefix"] else ""
                        text_display = segment["text"]
                        # Insert the segment data into the treeview
                        self.tree.insert('', tk.END, iid=iid, values=(line_num_display, prefix_display, text_display))
                        segment_count += 1 # Increment total segment counter
                        # Map the IID to its location in the data structure for easy lookup
                        self.item_id_map[iid] = {
                            "file_index": file_index,
                            "string_info_index": string_info_idx,
                            "segment_index": segment_idx
                        }

                # Insert a separator row after each file's data
                sep_iid = f"filesep_{file_index}"
                # Separator gets empty values and the SEPARATOR_TAG for styling
                self.tree.insert('', tk.END, iid=sep_iid, values=("", "", ""), open=False, tags=(SEPARATOR_TAG,))
            # --- End Populate Treeview ---

            status_msg = f"Status: Loaded {loaded_file_count} files with 'en' strings | Displaying {segment_count} editable segments."
            if files_with_line_num_errors:
                 status_msg += f" | Line# detection issues in {len(files_with_line_num_errors)} file(s) (see console)."
            self.status_label.config(text=status_msg)

        except FileNotFoundError as e:
            messagebox.showerror("Error", str(e))
            self.status_label.config(text="Status: Error - Input folder not found.")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred during loading: {e}")
            self.status_label.config(text=f"Status: Error - {e}")
            print(f"Loading Error Type: {type(e)}\nLoading Error: {e}")
            import traceback; traceback.print_exc()
        finally:
            self._update_save_state() # Update save state after loading (or attempting to)


    # --- Search Logic ---
    def _focus_search(self, event=None):
        """Sets focus to the search entry and selects existing text."""
        self.search_entry.focus_set()
        self.search_entry.select_range(0, tk.END)
        return "break" # Prevent further event processing if bound

    def _check_clear_search_on_empty(self, event=None):
        # If search box is cleared by user, reset search state
        if not self.search_term.get() and self.search_results:
             self._clear_search()

    def _perform_search(self, event=None):
        self._destroy_edit_entry() # Ensure edits are saved/cancelled first
        term = self.search_term.get()
        if not term:
            self._clear_search() # If search term is empty, clear results
            return

        self._clear_search_highlight() # Remove old highlights
        self.search_results = []
        self.current_search_index = -1
        term_lower = term.lower() # Case-insensitive search

        # Iterate through all data items (segments) using the map
        for iid in self.item_id_map.keys():
            try:
                # Ensure the item still exists in the tree
                if not self.tree.exists(iid): continue
                # Get the dialogue text for the item
                dialogue_text = self.tree.set(iid, DIALOGUE_COLUMN_ID)
                # Check if the search term is in the text
                if term_lower in dialogue_text.lower():
                    self.search_results.append(iid) # Add item ID to results list
                    # Add the highlight tag to the item
                    current_tags = list(self.tree.item(iid, "tags")) # Get existing tags as list
                    if SEARCH_HIGHLIGHT_TAG not in current_tags:
                         self.tree.item(iid, tags=current_tags + [SEARCH_HIGHLIGHT_TAG])
            except Exception as e:
                 # Log errors if an item causes issues during search
                 print(f"Error accessing item {iid} during search: {e}")

        # Update status based on search results
        if self.search_results:
            self.current_search_index = 0 # Go to the first result
            self._focus_search_result(self.current_search_index)
            self.status_label.config(text=f"Status: Found {len(self.search_results)} match(es) for '{term}'.")
        else:
            self.status_label.config(text=f"Status: No matches found for '{term}'.")
        # Keep focus in search entry for easy next/prev/new search
        self.search_entry.focus_set()


    def _find_next(self, event=None):
        if not self.search_results: return # No results to cycle through
        self._destroy_edit_entry() # Ensure edits are finished
        # Increment index, wrapping around if needed
        self.current_search_index = (self.current_search_index + 1) % len(self.search_results)
        self._focus_search_result(self.current_search_index)
        # Update status bar
        self.status_label.config(text=f"Status: Showing match {self.current_search_index + 1} of {len(self.search_results)} for '{self.search_term.get()}'.")
        self.search_entry.focus_set()


    def _find_previous(self, event=None):
        if not self.search_results: return # No results to cycle through
        self._destroy_edit_entry() # Ensure edits are finished
        # Decrement index, wrapping around if needed
        self.current_search_index = (self.current_search_index - 1 + len(self.search_results)) % len(self.search_results)
        self._focus_search_result(self.current_search_index)
        # Update status bar
        self.status_label.config(text=f"Status: Showing match {self.current_search_index + 1} of {len(self.search_results)} for '{self.search_term.get()}'.")
        self.search_entry.focus_set()


    def _focus_search_result(self, index):
        # Focuses the treeview on the search result at the given index
        if 0 <= index < len(self.search_results):
            iid = self.search_results[index]
            try:
                # Ensure the item still exists before trying to interact with it
                if self.tree.exists(iid):
                    self.tree.selection_set(iid) # Select the item
                    self.tree.see(iid) # Scroll the item into view
            except tk.TclError:
                print(f"Warning: Could not focus search result - item {iid} may no longer exist.")
            except Exception as e:
                print(f"Error focusing search result {iid}: {e}")

    def _clear_search_highlight(self):
        # Removes the search highlight tag from all items that might have it
        # This is more efficient than iterating through all tree items if search_results is large
        items_to_check = self.search_results # Only need to check previous results
        for iid in items_to_check:
            try:
                 if not self.tree.exists(iid): continue # Skip if item deleted
                 current_tags = list(self.tree.item(iid, "tags"))
                 if SEARCH_HIGHLIGHT_TAG in current_tags:
                     current_tags.remove(SEARCH_HIGHLIGHT_TAG)
                     self.tree.item(iid, tags=current_tags)
            except tk.TclError: pass # Ignore errors if item vanishes during process
            except Exception as e: print(f"Error clearing highlight for {iid}: {e}")

    def _clear_search(self, event=None):
        self._destroy_edit_entry() # Finish edits
        if self.search_term.get(): self.search_term.set("") # Clear search box only if needed
        self._clear_search_highlight() # Remove highlights
        self.search_results = [] # Clear results list
        self.current_search_index = -1 # Reset index

        # Reset status label to reflect general loaded state
        if self.file_data:
             segment_count = len(self.item_id_map)
             loaded_file_count = len(self.file_data)
             self.status_label.config(text=f"Status: Loaded {loaded_file_count} files | {segment_count} segments.")
             # Note: Info about line number errors is lost here; could persist if needed
        else:
            # If no data loaded (e.g., initial state or after clearing input)
            self.status_label.config(text="Status: Select input folder.")

        self.tree.selection_set([]) # Clear treeview selection


    # --- Copy/Cut/Paste Logic ---
    def _show_context_menu(self, event):
        # Shows the right-click context menu
        self._destroy_edit_entry() # Finish any active edit first
        iid = self.tree.identify_row(event.y) # Identify item clicked on

        if iid:
            # Only show menu if a valid item (not empty space) is clicked
            self.tree.selection_set(iid) # Select the clicked item
            # Optional: self.tree.focus_set() # Give tree focus for keyboard nav

            # Determine if the clicked item is a data row (editable segment)
            is_data_row = iid in self.item_id_map

            # Check if pasting is possible (clipboard contains text)
            can_paste = False
            if is_data_row: # Can only paste into data rows
                try:
                    clipboard_content = self.root.clipboard_get()
                    # Allow pasting empty string, check if it's actually string data
                    if isinstance(clipboard_content, str):
                        can_paste = True
                except tk.TclError:
                    # clipboard_get() raises TclError if clipboard is empty or contains non-text data
                    can_paste = False

            # Apply theme colors to context menu just before posting
            colors = THEMES.get(self.current_theme.get(), THEMES["Light"])
            self.context_menu.config(bg=colors["menu_bg"], fg=colors["menu_fg"],
                                     activebackground=colors["menu_active_bg"],
                                     activeforeground=colors["menu_active_fg"],
                                     activeborderwidth=0, bd=0)

            # Enable/disable menu items based on context
            self.context_menu.entryconfig("Copy", state=tk.NORMAL if is_data_row else tk.DISABLED)
            self.context_menu.entryconfig("Cut", state=tk.NORMAL if is_data_row else tk.DISABLED)
            self.context_menu.entryconfig("Paste", state=tk.NORMAL if can_paste else tk.DISABLED)

            # Display the menu at the cursor position
            self.context_menu.post(event.x_root, event.y_root)
        # else: Do nothing if the click was not on an item


    def _copy_selection(self, event=None):
        # Copies the dialogue text of the selected item to the clipboard
        selected_items = self.tree.selection()
        if not selected_items: return "break" # No item selected
        iid = selected_items[0] # Get the first selected item

        # Check if the selected item is a data row
        if iid in self.item_id_map:
            try:
                # Ensure item exists before getting text
                if self.tree.exists(iid):
                    dialogue_text = self.tree.set(iid, DIALOGUE_COLUMN_ID)
                    self.root.clipboard_clear() # Clear previous clipboard content
                    self.root.clipboard_append(dialogue_text) # Add new text
                else:
                    print(f"Warning: Could not copy from item {iid}, it no longer exists.")

            except tk.TclError: # Handle case where item might disappear between checks
                print(f"Warning: TclError during copy for item {iid}.")
            except Exception as e:
                 print(f"Error during copy for {iid}: {e}")
                 messagebox.showerror("Copy Error", f"Could not copy text:\n{e}")
        return "break" # Prevent default text widget copy behavior if applicable

    def _cut_selection(self, event=None):
        # Cuts the dialogue text (copy + clear)
        selected_items = self.tree.selection()
        if not selected_items: return "break"
        iid = selected_items[0]

        if iid in self.item_id_map: # Only cut from data rows
            try:
                # 1. Copy the text
                if not self.tree.exists(iid): # Check existence first
                    print(f"Warning: Could not cut item {iid}, it no longer exists.")
                    return "break"
                dialogue_text = self.tree.set(iid, DIALOGUE_COLUMN_ID)
                self.root.clipboard_clear()
                self.root.clipboard_append(dialogue_text)

                # 2. Clear the text in the Treeview
                self.tree.set(iid, DIALOGUE_COLUMN_ID, "") # Set empty string

                # 3. Clear the text in the backend data structure
                map_info = self.item_id_map[iid]
                file_idx = map_info.get("file_index")
                string_info_idx = map_info.get("string_info_index")
                seg_idx = map_info.get("segment_index")

                # Robust check of data structure before modification
                if not (isinstance(file_idx, int) and
                        isinstance(string_info_idx, int) and
                        isinstance(seg_idx, int)):
                     raise ValueError("Corrupt map info during cut.")

                if not (0 <= file_idx < len(self.file_data) and
                        isinstance(self.file_data[file_idx].get("en_strings"), list) and
                        0 <= string_info_idx < len(self.file_data[file_idx]["en_strings"]) and
                        isinstance(self.file_data[file_idx]["en_strings"][string_info_idx].get("segments"), list) and
                        0 <= seg_idx < len(self.file_data[file_idx]["en_strings"][string_info_idx]["segments"]) and
                        isinstance(self.file_data[file_idx]["en_strings"][string_info_idx]["segments"][seg_idx], dict)):
                     raise IndexError("Data structure integrity compromised during cut.")

                # Update the data store
                self.file_data[file_idx]["en_strings"][string_info_idx]["segments"][seg_idx]["text"] = ""

            except (IndexError, KeyError, TypeError, ValueError) as e:
                 print(f"Error updating data during cut for {iid}: {e}")
                 messagebox.showerror("Cut Error", f"Could not update data structure during cut:\n{e}")
                 # Optionally revert treeview change if data update failed:
                 try:
                     if self.tree.exists(iid):
                         self.tree.set(iid, DIALOGUE_COLUMN_ID, dialogue_text)
                 except tk.TclError: pass # Item might be gone anyway
            except tk.TclError: # Handle case where item might disappear
                 print(f"Warning: TclError during cut for item {iid}.")
            except Exception as e:
                 print(f"Error during cut for {iid}: {e}")
                 messagebox.showerror("Cut Error", f"Could not cut text:\n{e}")
        return "break"

    def _paste_selection(self, event=None):
        # Pastes clipboard text into the selected data row
        selected_items = self.tree.selection()
        if not selected_items: return "break"
        iid = selected_items[0]

        if iid in self.item_id_map: # Only paste into data rows
            try:
                # 1. Get clipboard text
                clipboard_text = self.root.clipboard_get()
                if not isinstance(clipboard_text, str):
                    # This case should ideally be prevented by disabling Paste menu item,
                    # but check anyway.
                    raise TypeError("Clipboard does not contain text.")

                # Ensure item exists before modifying
                if not self.tree.exists(iid):
                    print(f"Warning: Could not paste into item {iid}, it no longer exists.")
                    return "break"

                # 2. Update Treeview display
                self.tree.set(iid, DIALOGUE_COLUMN_ID, clipboard_text)

                # 3. Update backend data structure
                map_info = self.item_id_map[iid]
                file_idx = map_info.get("file_index")
                string_info_idx = map_info.get("string_info_index")
                seg_idx = map_info.get("segment_index")

                # Robust check of data structure before modification
                if not (isinstance(file_idx, int) and
                        isinstance(string_info_idx, int) and
                        isinstance(seg_idx, int)):
                     raise ValueError("Corrupt map info during paste.")

                if not (0 <= file_idx < len(self.file_data) and
                        isinstance(self.file_data[file_idx].get("en_strings"), list) and
                        0 <= string_info_idx < len(self.file_data[file_idx]["en_strings"]) and
                        isinstance(self.file_data[file_idx]["en_strings"][string_info_idx].get("segments"), list) and
                        0 <= seg_idx < len(self.file_data[file_idx]["en_strings"][string_info_idx]["segments"]) and
                        isinstance(self.file_data[file_idx]["en_strings"][string_info_idx]["segments"][seg_idx], dict)):
                     raise IndexError("Data structure integrity compromised during paste.")

                # Update the data store
                self.file_data[file_idx]["en_strings"][string_info_idx]["segments"][seg_idx]["text"] = clipboard_text

            except (IndexError, KeyError, TypeError, ValueError) as e:
                 print(f"Error updating data during paste for {iid}: {e}")
                 messagebox.showerror("Paste Error", f"Could not update data structure during paste:\n{e}")
                 # Optionally revert treeview change if data update failed:
                 # try:
                 #     if self.tree.exists(iid):
                 #         # Need to get the original text *before* the paste attempt from data
                 #         original_text = self.file_data[file_idx]["en_strings"][string_info_idx]["segments"][seg_idx]["text"] # This might now hold pasted text if error was late
                 #         # Safer: Store original text before trying paste
                 #         # self.tree.set(iid, DIALOGUE_COLUMN_ID, original_text)
                 # except tk.TclError: pass
            except tk.TclError: # clipboard_get failed
                messagebox.showwarning("Paste Error", "Clipboard is empty or does not contain text.")
            except Exception as e:
                print(f"Error during paste for {iid}: {e}")
                messagebox.showerror("Paste Error", f"Could not paste text:\n{e}")
        return "break"


    # --- Saving Logic ---
    def save_all_files(self):
        # Check prerequisites
        output_dir = self.output_folder.get()
        if not output_dir:
            messagebox.showerror("Error", "Output folder is not selected.")
            return
        if not self.input_folder.get(): # Also need input to know what was loaded
            messagebox.showerror("Error", "Input folder is not selected (required to know source).")
            return
        if not self.file_data:
            messagebox.showinfo("Info", "No data loaded to save.")
            return

        # Ensure output directory exists or can be created
        p_output_dir = pathlib.Path(output_dir)
        try:
            p_output_dir.mkdir(parents=True, exist_ok=True)
            print(f"Ensured output directory exists: {p_output_dir}")
        except OSError as e:
            messagebox.showerror("Error", f"Output folder path is invalid or could not be created:\n{p_output_dir}\n\nError: {e}")
            return

        # Prevent edits during save
        self._destroy_edit_entry()

        # Start saving process
        self.status_label.config(text="Status: Saving...")
        self.root.update_idletasks() # Show status immediately
        saved_count = 0
        error_files = set() # Keep track of files with save errors
        processed_count = 0

        try:
            # Iterate through the loaded file data
            for file_index, entry in enumerate(self.file_data):
                processed_count += 1
                current_file_path = entry['path']
                current_file_path_name = current_file_path.name

                # Make a copy of the original JSON content to modify.
                # A shallow copy is usually fine if the structure is list[dict]
                # and we only modify string values within the dicts.
                # Use deepcopy if structure is more complex or modifications are deeper.
                # json_content_to_save = copy.deepcopy(entry["json_content"])
                original_json_content = entry["json_content"]
                if not isinstance(original_json_content, list):
                    print(f"Error: Expected list content for file {current_file_path_name}, found {type(original_json_content)}. Skipping file save.")
                    error_files.add(current_file_path_name)
                    continue
                # Create a list of shallow copies of the dictionaries
                json_content_to_save = [item.copy() if isinstance(item, dict) else item for item in original_json_content]


                modified_in_file = False # Track if any changes were made to this file

                # Iterate through the 'en' strings data we extracted for this file
                for string_info_idx, string_info in enumerate(entry["en_strings"]):
                    original_item_index = string_info.get("original_item_index")

                    # --- Robustness Check: Ensure index is valid ---
                    if not isinstance(original_item_index, int) or not (0 <= original_item_index < len(json_content_to_save)):
                        print(f"Error: Invalid original item index ({original_item_index}) for file {current_file_path_name} during save prep. Skipping item update.")
                        error_files.add(current_file_path_name)
                        continue # Skip processing this string_info item

                    target_item = json_content_to_save[original_item_index]

                    # --- Robustness Check: Ensure target item is as expected ---
                    if not (isinstance(target_item, dict) and "String" in target_item and target_item.get("Language") == "en"):
                         print(f"Warning: Item structure at index {original_item_index} in {current_file_path_name} seems to have changed or is not 'en'. Skipping update for this item.")
                         continue # Skip this item, but continue with others in the file

                    # --- Robustness Check: Ensure segments data is valid ---
                    if not isinstance(string_info.get("segments"), list):
                         print(f"Error: Invalid segment structure for item index {original_item_index} in {current_file_path_name}. Skipping update for this item.")
                         error_files.add(current_file_path_name)
                         continue

                    # Reconstruct the "String" value from potentially edited segments
                    reconstructed_parts = []
                    valid_segments_for_item = True
                    for seg_idx, segment in enumerate(string_info["segments"]):
                        # Check segment validity
                        if not isinstance(segment, dict) or "text" not in segment:
                            print(f"Error: Invalid segment format at index {seg_idx} for item index {original_item_index} in {current_file_path_name}. Skipping update for this item.")
                            error_files.add(current_file_path_name)
                            valid_segments_for_item = False
                            break # Stop processing segments for this item

                        edited_text = segment["text"]
                        prefix = segment.get("original_prefix")
                        reconstructed_parts.append(prefix + edited_text if prefix else edited_text)

                    if not valid_segments_for_item:
                        continue # Skip to the next string_info item if segments were invalid

                    # Join the parts to get the final string
                    final_string = "".join(reconstructed_parts)

                    # Compare with the string in the copied JSON data
                    # Use get() for safety, although we checked "String" exists earlier
                    original_string_in_copy = target_item.get("String")
                    if original_string_in_copy != final_string:
                        target_item["String"] = final_string
                        modified_in_file = True # Mark file as modified

                # --- Write the file if it was modified ---
                output_path = p_output_dir / current_file_path_name
                if modified_in_file:
                    try:
                        # Write the potentially modified json_content_to_save
                        with open(output_path, 'w', encoding='utf-8') as f:
                             # Use indent for readability, ensure_ascii=False for proper UTF-8 output
                             json.dump(json_content_to_save, f, indent=4, ensure_ascii=False)
                        saved_count += 1
                    except IOError as e:
                        print(f"Error writing file {output_path}: {e}")
                        messagebox.showerror("Save Error", f"Failed to save {output_path.name}:\n{e}")
                        error_files.add(current_file_path_name)
                    except Exception as e:
                        # Catch other potential errors during dump/write
                        print(f"Unexpected error writing file {output_path}: {e}")
                        messagebox.showerror("Save Error", f"Unexpected error saving {output_path.name}:\n{e}")
                        error_files.add(current_file_path_name)
                # else:
                    # print(f"No modifications detected in {current_file_path_name}, skipping save.")

            # --- Final Status Update ---
            status_text = f"Status: Processed {processed_count} files. Saved {saved_count} modified files."
            if error_files:
                error_list_str = "\n - ".join(sorted(list(error_files)))
                messagebox.showwarning("Save Complete with Issues",
                                       f"Processed {processed_count} file(s).\n"
                                       f"Saved {saved_count} modified file(s) to:\n{output_dir}\n\n"
                                       f"Encountered issues in {len(error_files)} file(s):\n - {error_list_str}\n\n"
                                       "(Check console log for details)")
                status_text += f" | {len(error_files)} file(s) had issues."
            elif saved_count > 0:
                messagebox.showinfo("Success",
                                    f"Processed {processed_count} file(s).\n"
                                    f"Saved {saved_count} modified file(s) to:\n{output_dir}")
            elif processed_count > 0:
                 messagebox.showinfo("Save Complete",
                                     f"Processed {processed_count} file(s).\n"
                                     "No modifications needed saving.")
            else: # Should not happen if save button was enabled, but handle anyway
                 messagebox.showinfo("Save Complete", "No files were processed.")

            self.status_label.config(text=status_text)

        except Exception as e:
            # Catch critical errors during the overall save loop
            messagebox.showerror("Critical Error", f"A critical error occurred during the saving process: {e}")
            self.status_label.config(text=f"Status: Critical error during save - {e}")
            print(f"Saving Process Error: {e}")
            import traceback; traceback.print_exc()
        finally:
             # Update save button state (might be disabled if errors occurred,
             # or if input/output folders changed during save?) - usually remains enabled.
             self._update_save_state()


    # --- Help / About Dialogs ---
    def _show_about(self):
        messagebox.showinfo("About HITMAN III JSON Editor",
                            "HITMAN III JSON Editor v1.1\n\n"
                            "A tool to easily view, search, and edit Text "
                            "within specific JSON file structures.\n\n"
                            "Features:\n"
                            "- Loads 'en' language strings from JSON files.\n"
                            "- Splits strings by //(timecode)\\\\ segments.\n"
                            "- Allows direct editing of text segments.\n"
                            "- Search functionality with highlighting.\n"
                            "- Saves changes to a separate output folder.\n"
                            "- DarkRed/Light/Dark theme support.\n\n"
                            "All rights reserved by MrGamesKingPro\n\n"
                            "https://github.com/MrGamesKingPro")

    def _show_help(self):
         messagebox.showinfo("Help",
                            "Basic Usage:\n\n"
                            "1. Select Input Folder: Choose the folder containing your .json files.\n"
                            "2. Select Output Folder: Choose a *different* folder where modified files will be saved.\n"
                            "3. Browse Data: Files containing '\"Language\": \"en\"' strings will be loaded. Segments are displayed in the table.\n"
                            "4. Edit: Double-click a cell in the 'Text' column to edit it. Press Enter to save or Escape to cancel.\n"
                            "5. Open Original File: Double-click a grey file header row to open the source JSON file in your default editor.\n"
                            "6. Search: Type in the 'Search Text' box and press Enter or click 'Find'. Use 'Next'/'Previous' to navigate matches.\n"
                            "7. Copy/Cut/Paste: Use the Edit menu, context menu (right-click), or keyboard shortcuts (Ctrl+C/X/V or Cmd+C/X/V).\n"
                            "8. Save Changes: Click 'Save All Changes' or use File > Save (Ctrl+S/Cmd+S). Only modified files will be written to the output folder.\n"
                            "9. Theme: Change the appearance via View > Theme."
                           )

if __name__ == "__main__":
    root = tk.Tk()
    app = JsonEditorApp(root)
    root.mainloop()
