import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Menu, font
import json
import os
import re
import pathlib
import webbrowser
from collections import defaultdict, deque # Import deque for Undo/Redo
import platform # To check OS for key bindings
import copy # Needed for deepcopy during save if desired, though shallow is used now
import subprocess # Needed for opening folders on macOS/Linux
import configparser # Added for saving/loading state
import csv # Added for TSV export/import
import traceback # For more detailed error logging if needed

# Regular expression to find segments like //(start,end)\\text
# Capture groups: 1: full prefix, 2: text
SEGMENT_REGEX = re.compile(r"(//\([^)]+\)\\\\)(.*?)(?=(//\([^)]+\)\\\\|$)|\Z)", re.DOTALL)

# Regex to find "Language": "en" potentially with variable spacing
LANG_EN_REGEX = re.compile(r'"Language"\s*:\s*"en"')
# Regex to find "String": potentially with variable spacing
STRING_KEY_REGEX = re.compile(r'"String"\s*:')


# --- Constants ---
COL_LINE = "#1"
COL_ID = "#2" # Renamed from COL_TIMECODE
COL_DIALOGUE = "#3" # Or use a symbolic name like 'dialogue' - using #3 for direct comparison

DIALOGUE_COLUMN_ID = COL_DIALOGUE # Explicitly use #3
ID_COLUMN_ID = COL_ID # Explicitly use #2 for Timecode/Hash
FILE_HEADER_TAG = 'file_header' # Define a constant for the tag
SEPARATOR_TAG = 'separator'
SEARCH_HIGHLIGHT_TAG = 'search_highlight' # Tag for search results
CONFIG_FILE_NAME = "H-III-Config.ini" # Config file name
APP_VERSION = "1.3" # <<<< Slightly incremented version for new feature

# --- File Formats ---
FORMAT_DLGE = 'DLGE'
FORMAT_LOCR = 'LOCR'
FORMAT_UNKNOWN = 'UNKNOWN'

# --- Theme Colors (Unchanged) ---
THEMES = {
    "Light": {
        "bg": "#F0F0F0", "fg": "black", "entry_bg": "white", "entry_fg": "black",
        "tree_bg": "white", "tree_fg": "black", "tree_selected_bg": "#0078D7", "tree_selected_fg": "white",
        "header_bg": "#E0E0E0", "header_fg": "black", "separator_bg": "#F5F5F5",
        "search_bg": "yellow", "search_fg": "black", "button_bg": "#E1E1E1", "button_fg": "black",
        "status_bg": "#F0F0F0", "status_fg": "black", "disabled_fg": "#A0A0A0",
        "menu_bg": "#F0F0F0", "menu_fg": "black", "menu_active_bg": "#0078D7", "menu_active_fg": "white",
        "entry_context_bg": "#FFFFFF", "entry_context_fg": "#000000",
        "entry_context_active_bg": "#0078D7", "entry_context_active_fg": "#FFFFFF",
    },
    "Dark": {
        "bg": "#2E2E2E", "fg": "#EAEAEA", "entry_bg": "#3C3C3C", "entry_fg": "#EAEAEA",
        "tree_bg": "#252525", "tree_fg": "#EAEAEA", "tree_selected_bg": "#5E5E5E", "tree_selected_fg": "#EAEAEA",
        "header_bg": "#7D7D7D", "header_fg": "#EAEAEA", "separator_bg": "#333333",
        "search_bg": "#B8860B", "search_fg": "black", "button_bg": "#505050", "button_fg": "#EAEAEA",
        "status_bg": "#2E2E2E", "status_fg": "#EAEAEA", "disabled_fg": "#707070",
        "menu_bg": "#2E2E2E", "menu_fg": "#EAEAEA", "menu_active_bg": "#5E5E5E", "menu_active_fg": "#EAEAEA",
        "entry_context_bg": "#3C3C3C", "entry_context_fg": "#EAEAEA",
        "entry_context_active_bg": "#5E5E5E", "entry_context_active_fg": "#EAEAEA",
    },
    "Red/Dark": {
        "bg": "#D30707", "fg": "#EAEAEA", "entry_bg": "#3C3C3C", "entry_fg": "#FFFFFF",
        "tree_bg": "#252525", "tree_fg": "#EAEAEA", "tree_selected_bg": "#D30707", "tree_selected_fg": "#EAEAEA",
        "header_bg": "#AEAEAE", "header_fg": "#000000", "separator_bg": "#252525",
        "search_bg": "#B8860B", "search_fg": "#FFFFFF", "button_bg": "#003948", "button_fg": "#FFFFFF",
        "status_bg": "#2E2E2E", "status_fg": "#E8E8E8", "disabled_fg": "#FFFFFF",
        "menu_bg": "#2E2E2E", "menu_fg": "#EAEAEA", "menu_active_bg": "#D30707", "menu_active_fg": "#EAEAEA",
        "entry_context_bg": "#3C3C3C", "entry_context_fg": "#EAEAEA",
        "entry_context_active_bg": "#D30707", "entry_context_active_fg": "#EAEAEA",
    }
}

# --- Helper functions for string escaping/unescaping for editor display ---
def custom_escape_for_editor(text_from_json):
    """Converts special characters from JSON string to editor-displayable version.
    - Literal backslashes '\\' become '\\\\'
    - Newlines '\n' become '\\n'
    - Carriage returns '\r' become '\\r'
    - Tabs '\t' become '\\t'
    """
    if not isinstance(text_from_json, str): # Ensure input is a string
        return str(text_from_json)
    text = text_from_json.replace('\\', '\\\\') # Must be first
    text = text.replace('\n', '\\n')
    text = text.replace('\r', '\\r')
    text = text.replace('\t', '\\t')
    return text

def custom_unescape_from_editor(text_from_editor):
    """Converts editor-displayable version of string back to JSON string format."""
    if not isinstance(text_from_editor, str):
        return str(text_from_editor)
    
    # Using a unique placeholder (Private Use Area Unicode character)
    # to temporarily mark already-escaped backslashes (\\).
    # This prevents '\\n' (literal backslash-n) from being unescaped as a newline.
    temp_placeholder = "\uE001" # Using a single PUA character as a placeholder

    # Step 1: Protect '\\' sequences by replacing them with placeholder + 'TEMP_ESCAPED_SLASH'
    # This specifically targets '\\\\' which represents a single literal backslash in editor_text.
    text = text_from_editor.replace('\\\\', temp_placeholder)

    # Step 2: Unescape \n, \r, \t
    # These should now correctly unescape sequences like '\n' to a newline,
    # without affecting what was originally '\\n' (now 'placeholder' + 'n').
    text = text.replace('\\n', '\n')
    text = text.replace('\\r', '\r')
    text = text.replace('\\t', '\t')

    # Step 3: Restore the original literal backslashes
    text = text.replace(temp_placeholder, '\\')
    return text


class JsonEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"HITMAN JSON Editor v{APP_VERSION}") # Use constant
        # Default geometry, will be overridden by config if available
        self.root.geometry("1200x850")

        self.style = ttk.Style()
        available_themes = self.style.theme_names()
        # Prefer clam for better consistency if available
        if 'clam' in available_themes:
             self.style.theme_use('clam')
        elif 'alt' in available_themes: # Fallback to alt
             self.style.theme_use('alt')
        # Otherwise, use the system default

        # --- Data Structures ---
        self.input_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        # self.file_data stores list of dicts, each dict representing a file:
        # {
        #   "path": pathlib.Path,
        #   "format": FORMAT_DLGE | FORMAT_LOCR,
        #   "json_content": original loaded JSON structure (for reference),
        #   "en_strings": [  # List of extracted 'en' text data
        #     # DLGE format entry:
        #     { "original_item_index": int, "original_line_number": int|None,
        #       "original_string": str, # Raw string from JSON (with actual newlines, etc.)
        #       "segments": [ {"original_prefix": str|None,
        #                      "text": str, # Escaped for editor display (e.g., '\\n')
        #                      "iid": str}, ... ] },
        #     # LOCR format entry:
        #     { "original_lang_block_index": int, "original_string_item_index": int, "original_line_number": int|None,
        #       "string_hash": int|str|None,
        #       "text": str, # Escaped for editor display (e.g., '\\n')
        #       "original_text": str, # Raw string from JSON (with actual newlines, etc.)
        #       "iid": str }
        #   ]
        # }
        self.file_data = []
        # self.item_id_map maps treeview iid to data location:
        # {
        #   iid: { "file_index": int, "string_info_index": int, "segment_index": int|None } # segment_index is None for LOCR
        # }
        self.item_id_map = {}

        # --- Editing State ---
        self.edit_entry = None
        self.edit_item_id = None
        self._escape_pressed = False

        # --- Undo/Redo State ---
        self.undo_stack = deque(maxlen=100) # Store up to 100 actions
        self.redo_stack = deque(maxlen=100)

        # --- Search & Replace State ---
        self.search_term = tk.StringVar()
        self.replace_term = tk.StringVar()
        self.search_results = []
        self.current_search_index = -1
        self._last_search_was_findall = False # Track if the last search was Find All

        # --- Theme State ---
        self.current_theme = tk.StringVar(value="Red/Dark") # Default theme, may be overridden by config

        # --- Config ---
        self.config_parser = configparser.ConfigParser()
        self.config_file_path = pathlib.Path(CONFIG_FILE_NAME)
        self._load_config() # Load settings early, including geometry, folders, theme, search terms

        # --- Menu Bar ---
        self.menu_bar = Menu(root)
        root.config(menu=self.menu_bar)

        # File Menu
        self.file_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Select Input Folder...", command=self.select_input_folder)
        self.file_menu.add_command(label="Open Input Folder Location", command=self._open_input_folder_location, state=tk.DISABLED) # Initial state updated later
        self.file_menu.add_command(label="Select Output Folder...", command=self.select_output_folder)
        self.file_menu.add_command(label="Open Output Folder Location", command=self._open_output_folder_location, state=tk.DISABLED) # Initial state updated later
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Export Text...", command=self._export_dialogue, state=tk.DISABLED)
        self.file_menu.add_command(label="Import Text...", command=self._import_dialogue, state=tk.DISABLED)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Save All Changes", command=self.save_all_files, state=tk.DISABLED, accelerator=self._get_accelerator("S"))
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self._on_closing) # Use closing handler

        # Edit Menu
        self.edit_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Edit", menu=self.edit_menu)
        self.edit_menu.add_command(label="Undo", command=self._undo_action, state=tk.DISABLED, accelerator=self._get_accelerator("Z"))
        self.edit_menu.add_command(label="Redo", command=self._redo_action, state=tk.DISABLED, accelerator=self._get_redo_accelerator())
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Cut", command=self._cut_selection, accelerator=self._get_accelerator("X"))
        self.edit_menu.add_command(label="Copy", command=self._copy_selection, accelerator=self._get_accelerator("C"))
        self.edit_menu.add_command(label="Paste", command=self._paste_selection, accelerator=self._get_accelerator("V"))
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Find / Focus Search", command=self._focus_search, accelerator=self._get_accelerator("F"))
        self.edit_menu.add_command(label="Find All", command=self._find_all, accelerator="Shift+"+self._get_accelerator("F"))
        self.edit_menu.add_command(label="Find Next", command=self._find_next, accelerator=self._get_accelerator("G")) # Or F3
        self.edit_menu.add_command(label="Find Previous", command=self._find_previous, accelerator="Shift+"+self._get_accelerator("G")) # Or Shift+F3

        # View Menu (for Themes)
        self.view_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="View", menu=self.view_menu)
        self.theme_menu = Menu(self.view_menu, tearoff=0)
        self.view_menu.add_cascade(label="Theme", menu=self.theme_menu)
        for theme_name in THEMES:
             self.theme_menu.add_radiobutton(label=theme_name, variable=self.current_theme, value=theme_name, command=self._apply_theme_and_save_config)

        # Help Menu
        self.help_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Help", menu=self.help_menu)
        self.help_menu.add_command(label="Instructions", command=self._show_help)
        self.help_menu.add_command(label="About", command=self._show_about)

        # --- UI Elements ---
        # Frame for folder selection
        self.folder_frame = ttk.Frame(root, padding="10")
        self.folder_frame.pack(fill=tk.X, side=tk.TOP) # Ensure packed at top

        # Input Folder Section
        ttk.Button(self.folder_frame, text="Select Input Folder", command=self.select_input_folder).pack(side=tk.LEFT, padx=(0, 5))
        self.input_entry = ttk.Entry(self.folder_frame, textvariable=self.input_folder, width=35, state='readonly')
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.open_input_button = ttk.Button(self.folder_frame, text="Open", width=5, command=self._open_input_folder_location, state=tk.DISABLED)
        self.open_input_button.pack(side=tk.LEFT, padx=(0, 15))

        # Output Folder Section
        ttk.Button(self.folder_frame, text="Select Output Folder", command=self.select_output_folder).pack(side=tk.LEFT, padx=(0, 5))
        self.output_entry = ttk.Entry(self.folder_frame, textvariable=self.output_folder, width=35, state='readonly')
        self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.open_output_button = ttk.Button(self.folder_frame, text="Open", width=5, command=self._open_output_folder_location, state=tk.DISABLED)
        self.open_output_button.pack(side=tk.LEFT, padx=0)

        # --- Search and Replace Frame ---
        self.search_replace_frame = ttk.Frame(root, padding=(10, 5, 10, 5)) # Adjusted padding
        self.search_replace_frame.pack(fill=tk.X, side=tk.TOP) # Ensure packed below folders

        self.search_label = ttk.Label(self.search_replace_frame, text="Search Text:")
        self.search_label.pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry = ttk.Entry(self.search_replace_frame, textvariable=self.search_term)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        # Bindings for search entry
        self.search_entry.bind("<Return>", self._perform_search)
        self.search_entry.bind("<KP_Enter>", self._perform_search)
        self.search_entry.bind("<KeyRelease>", self._check_clear_search_on_empty)
        self.search_entry.bind("<Button-3>", self._show_entry_context_menu)

        self.find_button = ttk.Button(self.search_replace_frame, text="Find", command=self._perform_search)
        self.find_button.pack(side=tk.LEFT, padx=5)
        self.find_all_button = ttk.Button(self.search_replace_frame, text="Find All", command=self._find_all)
        self.find_all_button.pack(side=tk.LEFT, padx=5)
        self.next_button = ttk.Button(self.search_replace_frame, text="Next", command=self._find_next, state=tk.DISABLED)
        self.next_button.pack(side=tk.LEFT, padx=5)
        self.prev_button = ttk.Button(self.search_replace_frame, text="Previous", command=self._find_previous, state=tk.DISABLED)
        self.prev_button.pack(side=tk.LEFT, padx=5)

        self.replace_label = ttk.Label(self.search_replace_frame, text="Replace with:")
        self.replace_label.pack(side=tk.LEFT, padx=(10, 5))
        self.replace_entry = ttk.Entry(self.search_replace_frame, textvariable=self.replace_term)
        self.replace_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.replace_entry.bind("<Button-3>", self._show_entry_context_menu)

        self.replace_button = ttk.Button(self.search_replace_frame, text="Replace", command=self._replace_current, state=tk.DISABLED)
        self.replace_button.pack(side=tk.LEFT, padx=5)
        self.replace_all_button = ttk.Button(self.search_replace_frame, text="Replace All", command=self._replace_all, state=tk.DISABLED)
        self.replace_all_button.pack(side=tk.LEFT, padx=5)

        # --- Status Bar --- (Packed at the bottom)
        self.status_frame = ttk.Frame(root, padding=(10, 5, 10, 10)) # Adjusted padding
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_label = ttk.Label(self.status_frame, text="Status: Initializing...")
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.save_button = ttk.Button(self.status_frame, text="Save All Changes", command=self.save_all_files, state=tk.DISABLED)
        self.save_button.pack(side=tk.RIGHT, padx=5)

        # --- Treeview Frame --- (Packed last, takes remaining space)
        self.tree_frame = ttk.Frame(root, padding=(10, 0, 10, 0)) # Adjusted padding
        self.tree_frame.pack(fill=tk.BOTH, expand=True, side=tk.TOP)

        columns = (COL_LINE, COL_ID, DIALOGUE_COLUMN_ID) # Use constants
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings")

        self.tree.heading(COL_LINE, text="Line / ID") # Updated Heading
        self.tree.heading(COL_ID, text="Timecode / Hash") # Updated Heading
        self.tree.heading(DIALOGUE_COLUMN_ID, text="Text (Double-click to edit, header to open file)")

        self.tree.column(COL_LINE, anchor=tk.E, width=120, stretch=False) # Wider for potential hash
        self.tree.column(COL_ID, anchor=tk.W, width=150, stretch=False)
        self.tree.column(DIALOGUE_COLUMN_ID, anchor=tk.W, width=600) # Adjusted width

        self.tree_scrollbar_y = ttk.Scrollbar(self.tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree_scrollbar_x = ttk.Scrollbar(self.tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=self.tree_scrollbar_y.set, xscrollcommand=self.tree_scrollbar_x.set)

        self.tree_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Tag configuration (fonts, colors applied via theme later)
        try:
            # Use a standard, widely available font for the header
            header_font = font.nametofont("TkDefaultFont").copy()
            header_font.configure(weight="bold")
            self.tree.tag_configure(FILE_HEADER_TAG, font=header_font)
        except Exception as e:
             print(f"Warning: Could not set header font reliably: {e}")
             self.tree.tag_configure(FILE_HEADER_TAG) # Apply tag anyway for color

        self.tree.tag_configure('protected') # Colors set by theme
        self.tree.tag_configure(SEPARATOR_TAG) # Colors set by theme
        self.tree.tag_configure(SEARCH_HIGHLIGHT_TAG) # Colors set by theme

        # --- Context Menu (Treeview) ---
        self.tree_context_menu = Menu(self.tree, tearoff=0)
        self.tree_context_menu.add_command(label="Copy", command=self._copy_selection, accelerator=self._get_accelerator("C"))
        self.tree_context_menu.add_command(label="Cut", command=self._cut_selection, accelerator=self._get_accelerator("X"))
        self.tree_context_menu.add_command(label="Paste", command=self._paste_selection, accelerator=self._get_accelerator("V"))

        # --- Context Menu (Entries) ---
        self.entry_context_menu = Menu(root, tearoff=0)
        self.entry_context_menu.add_command(label="Undo", command=self._undo_action, accelerator=self._get_accelerator("Z"))
        self.entry_context_menu.add_command(label="Redo", command=self._redo_action, accelerator=self._get_redo_accelerator())
        self.entry_context_menu.add_separator()
        self.entry_context_menu.add_command(label="Cut", command=lambda: self._entry_action(self.root.focus_get(), 'Cut'))
        self.entry_context_menu.add_command(label="Copy", command=lambda: self._entry_action(self.root.focus_get(), 'Copy'))
        self.entry_context_menu.add_command(label="Paste", command=lambda: self._entry_action(self.root.focus_get(), 'Paste'))

        # --- Bind Treeview Events ---
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree.bind("<Button-1>", self._on_tree_single_click_or_clear_edit)
        self.tree.bind("<Button-3>", self._show_tree_context_menu) # Right-click for Treeview context

        # --- Bind Keyboard Shortcuts (Specific & Global) ---
        modifier = self._get_modifier_key()
        # Tree specific clipboard (Ensure focus is on tree for these)
        self.tree.bind(f"<{modifier}-c>", self._copy_selection)
        self.tree.bind(f"<{modifier}-x>", self._cut_selection)
        self.tree.bind(f"<{modifier}-v>", self._paste_selection)
        # Global actions (use bind_all)
        self.root.bind_all(f"<{modifier}-s>", lambda e: self.save_all_files()) # Save All
        self.root.bind_all(f"<{modifier}-f>", self._focus_search) # Focus Search (pass event)
        self.root.bind_all(f"<Shift-{modifier}-F>", self._find_all) # Find All (pass event)
        self.root.bind_all(f"<{modifier}-g>", self._find_next) # Find Next (pass event)
        self.root.bind_all(f"<Shift-{modifier}-G>", self._find_previous) # Find Previous (pass event)
        self.root.bind_all(f"<{modifier}-z>", self._undo_action) # Undo (pass event)
        self.root.bind_all(self._get_redo_binding(), self._redo_action) # Redo (pass event)


        # --- Configure Resizing --- (Focus on TreeView and Entries)
        self.root.columnconfigure(0, weight=1) # Allow main column to expand
        self.root.rowconfigure(2, weight=1) # Allow Treeview Frame row to expand (0:folder, 1:search, 2:tree, 3:status)

        # Adjust column weights in folder_frame for entries
        self.folder_frame.columnconfigure(1, weight=1) # Input entry
        self.folder_frame.columnconfigure(4, weight=1) # Output entry

        # Adjust weights in search_replace_frame for entries
        self.search_replace_frame.columnconfigure(1, weight=3) # Search entry
        self.search_replace_frame.columnconfigure(7, weight=3) # Replace entry

        # Tree frame resizing
        self.tree_frame.columnconfigure(0, weight=1) # Treeview widget itself
        self.tree_frame.rowconfigure(0, weight=1) # Treeview widget itself

        # Status frame resizing (Label takes space)
        self.status_frame.columnconfigure(0, weight=1) # Status label

        # --- Final Initialization Steps ---
        self._apply_theme() # Apply theme loaded from config (or default)
        self._update_folder_open_button_states() # Update based on loaded paths
        self._update_search_replace_button_states() # Update based on loaded data (none yet)
        self._update_undo_redo_state() # Should be disabled initially
        self._update_import_export_state() # Should be disabled initially
        self._update_save_state() # Initial save state check

        # Set status after loading config and applying theme
        if not self.input_folder.get():
             self.status_label.config(text="Status: Select input folder.")
        else:
             # If input folder loaded from config, try loading files
             self.status_label.config(text="Status: Input folder loaded from config. Loading files...")
             self.root.after(100, self.load_json_files) # Load files shortly after UI is up

        # --- Set Closing Protocol ---
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    # --- Config Saving/Loading ---
    def _load_config(self):
        """Loads settings from the config file."""
        try:
            if self.config_file_path.is_file():
                self.config_parser.read(self.config_file_path, encoding='utf-8') # Specify encoding
                if 'Settings' in self.config_parser:
                    settings = self.config_parser['Settings']
                    self.input_folder.set(settings.get('InputFolder', ''))
                    self.output_folder.set(settings.get('OutputFolder', ''))
                    # Theme
                    loaded_theme = settings.get('Theme', 'Red/Dark')
                    self.current_theme.set(loaded_theme if loaded_theme in THEMES else 'Red/Dark')
                    # Search/Replace Terms
                    self.search_term.set(settings.get('SearchTerm', ''))
                    self.replace_term.set(settings.get('ReplaceTerm', ''))
                    # Window Geometry
                    geometry = settings.get('WindowGeometry', None)
                    if geometry:
                        try:
                            # Basic validation for geometry string format (e.g., "1200x800+100+100")
                            if re.fullmatch(r"\d+x\d+\+\d+\+\d+", geometry):
                                self.root.geometry(geometry)
                            else:
                                print(f"Warning: Invalid geometry string in config: {geometry}")
                        except tk.TclError as e:
                            print(f"Warning: Could not apply geometry '{geometry}' from config: {e}")

                    print(f"Loaded config from {self.config_file_path}")
                else:
                    print(f"Config file {self.config_file_path} found but missing [Settings] section.")
            else:
                print(f"Config file {self.config_file_path} not found. Using defaults.")

        except (configparser.Error, FileNotFoundError, Exception) as e: # Catch more specific errors
             print(f"Error reading config file {self.config_file_path}: {e}")

    def _save_config(self):
        """Saves current settings to the config file."""
        try:
            if not self.config_parser.has_section('Settings'):
                self.config_parser.add_section('Settings')

            settings_data = {
                'InputFolder': self.input_folder.get(),
                'OutputFolder': self.output_folder.get(),
                'Theme': self.current_theme.get(),
                'SearchTerm': self.search_term.get(),
                'ReplaceTerm': self.replace_term.get(),
                'WindowGeometry': self.root.winfo_geometry()
            }
            for key, value in settings_data.items():
                self.config_parser.set('Settings', key, value)

            with open(self.config_file_path, 'w', encoding='utf-8') as configfile: # Specify encoding
                self.config_parser.write(configfile)
            # print(f"Saved config to {self.config_file_path}") # Optional: uncomment for debug
        except (IOError, configparser.Error, Exception) as e: # Catch more specific errors
            print(f"Error writing config file {self.config_file_path}: {e}")
            # Optionally show a non-blocking warning
            # messagebox.showwarning("Config Save Error", f"Could not save settings to {self.config_file_path}:\n{e}", parent=self.root)


    def _on_closing(self):
        """Handles application closing: saves config and quits."""
        print("Closing application and saving config...")
        self._save_config()
        self.root.destroy()

    # --- Themeing ---
    def _apply_theme_and_save_config(self):
        """Applies the theme and saves the config immediately."""
        self._apply_theme()
        self._save_config() # Save theme change immediately

    def _apply_theme(self):
        theme_name = self.current_theme.get()
        colors = THEMES.get(theme_name, THEMES["Red/Dark"]) # Fallback

        self.root.config(bg=colors["bg"])

        # --- Configure ttk styles ---
        self.style.configure('.',
                             background=colors["bg"],
                             foreground=colors["fg"],
                             fieldbackground=colors["entry_bg"], # Default field background
                             insertcolor=colors["fg"]) # Default cursor color

        # Button Style
        self.style.configure('TButton',
                             background=colors["button_bg"],
                             foreground=colors["button_fg"],
                             padding=5,
                             relief=tk.FLAT,
                             borderwidth=1)
        self.style.map('TButton',
                       background=[('active', colors["header_bg"]),
                                   ('disabled', colors["button_bg"])],
                       foreground=[('disabled', colors["disabled_fg"])],
                       relief=[('pressed', tk.SUNKEN), ('!pressed', tk.FLAT)])

        # Entry Style (includes Treeview inline editor via 'Treeview.TEntry')
        self.style.configure('TEntry',
                             fieldbackground=colors["entry_bg"],
                             foreground=colors["entry_fg"],
                             insertcolor=colors["fg"],
                             borderwidth=1,
                             relief=tk.SUNKEN)
        self.style.map('TEntry',
                       foreground=[('readonly', colors["disabled_fg"])],
                       fieldbackground=[('readonly', colors["bg"])])

        # Treeview Style
        self.style.configure('Treeview',
                             background=colors["tree_bg"],
                             fieldbackground=colors["tree_bg"],
                             foreground=colors["tree_fg"],
                             borderwidth=0,
                             relief=tk.FLAT)
        self.style.map('Treeview',
                       background=[('selected', colors["tree_selected_bg"])],
                       foreground=[('selected', colors["tree_selected_fg"])])

        # Treeview Heading Style
        self.style.configure('Treeview.Heading',
                             background=colors["button_bg"],
                             foreground=colors["button_fg"],
                             font=('TkDefaultFont', 10, 'bold'),
                             relief=tk.RAISED,
                             padding=(5, 3))
        self.style.map('Treeview.Heading',
                       background=[('active', colors["header_bg"])])

        # Label Style
        self.style.configure('TLabel', background=colors["bg"], foreground=colors["fg"])

        # Frame Style
        self.style.configure('TFrame', background=colors["bg"])

        # Scrollbar Style
        if theme_name != "Light":
            self.style.configure('Vertical.TScrollbar',
                                 background=colors["button_bg"], troughcolor=colors["bg"],
                                 arrowcolor=colors["fg"], bordercolor=colors["bg"], relief=tk.FLAT)
            self.style.map('Vertical.TScrollbar', background=[('active', colors["header_bg"])])
            self.style.configure('Horizontal.TScrollbar',
                                 background=colors["button_bg"], troughcolor=colors["bg"],
                                 arrowcolor=colors["fg"], bordercolor=colors["bg"], relief=tk.FLAT)
            self.style.map('Horizontal.TScrollbar', background=[('active', colors["header_bg"])])
        else:
            # Reset scrollbar style for light theme
            self.style.configure('Vertical.TScrollbar', background='', troughcolor='', arrowcolor='', bordercolor='', relief='')
            self.style.map('Vertical.TScrollbar', background=[])
            self.style.configure('Horizontal.TScrollbar', background='', troughcolor='', arrowcolor='', bordercolor='', relief='')
            self.style.map('Horizontal.TScrollbar', background=[])


        # --- Apply to specific non-ttk widgets or tags ---
        self.status_label.config(background=colors["status_bg"], foreground=colors["status_fg"])
        self.input_entry.config(style='TEntry')
        self.output_entry.config(style='TEntry')
        self.folder_frame.config(style='TFrame')
        self.search_replace_frame.config(style='TFrame')
        self.tree_frame.config(style='TFrame')
        self.status_frame.config(style='TFrame')

        # Treeview Tags
        self.tree.tag_configure(FILE_HEADER_TAG, background=colors["header_bg"], foreground=colors["header_fg"])
        self.tree.tag_configure(SEPARATOR_TAG, background=colors["separator_bg"])
        self.tree.tag_configure('protected', foreground=colors.get("disabled_fg", "#A0A0A0"))
        self.tree.tag_configure(SEARCH_HIGHLIGHT_TAG, background=colors["search_bg"], foreground=colors["search_fg"])

        # --- Menu appearance ---
        menu_elements = [self.menu_bar, self.file_menu, self.edit_menu, self.view_menu, self.theme_menu, self.help_menu, self.tree_context_menu, self.entry_context_menu]
        for menu in menu_elements:
             try:
                 is_context = menu in [self.entry_context_menu, self.tree_context_menu]
                 menu_bg = colors.get("entry_context_bg" if is_context else "menu_bg", colors["menu_bg"])
                 menu_fg = colors.get("entry_context_fg" if is_context else "menu_fg", colors["menu_fg"])
                 active_bg = colors.get("entry_context_active_bg" if is_context else "menu_active_bg", colors["menu_active_bg"])
                 active_fg = colors.get("entry_context_active_fg" if is_context else "menu_active_fg", colors["menu_active_fg"])

                 menu.config(bg=menu_bg, fg=menu_fg,
                             activebackground=active_bg,
                             activeforeground=active_fg,
                             activeborderwidth=0, bd=0,
                             relief=tk.FLAT)
             except tk.TclError as e:
                 print(f"Warning: Could not configure some menu theme properties: {e}")

        # Force update of the UI
        self.root.update_idletasks()


    # --- OS Specific Key Bindings ---
    def _get_modifier_key(self):
        return "Command" if platform.system() == "Darwin" else "Control"

    def _get_accelerator(self, key):
        modifier = self._get_modifier_key()
        mod_symbol = "Cmd" if modifier == "Command" else "Ctrl"
        return f"{mod_symbol}+{key.upper()}"

    def _get_redo_accelerator(self):
        modifier = self._get_modifier_key()
        mod_symbol = "Cmd" if modifier == "Command" else "Ctrl"
        return f"Shift+{mod_symbol}+Z" if platform.system() == "Darwin" else f"{mod_symbol}+Y"

    def _get_redo_binding(self):
        modifier = self._get_modifier_key()
        return f"<Shift-{modifier}-z>" if platform.system() == "Darwin" else f"<{modifier}-y>"

    # --- Folder Selection & State ---
    def select_input_folder(self):
        folder = filedialog.askdirectory(initialdir=self.input_folder.get() or pathlib.Path.home()) # Start at home if unset
        if folder:
            folder_path = pathlib.Path(folder).resolve()
            output_path_str = self.output_folder.get()
            if output_path_str:
                 output_path = pathlib.Path(output_path_str).resolve()
                 if folder_path == output_path:
                     messagebox.showwarning("Warning", "Input folder cannot be the same as the output folder.", parent=self.root)
                     return
            self.input_folder.set(str(folder_path))
            self._clear_search()
            self.file_data = []
            self.item_id_map = {}
            self.tree.delete(*self.tree.get_children())
            self._clear_undo_redo()
            self.load_json_files()
            self._update_folder_open_button_states()
            self._save_config() # Save new folder path

    def select_output_folder(self):
        folder = filedialog.askdirectory(initialdir=self.output_folder.get() or self.input_folder.get() or pathlib.Path.home())
        if folder:
            folder_path = pathlib.Path(folder).resolve()
            input_path_str = self.input_folder.get()
            if input_path_str:
                input_path = pathlib.Path(input_path_str).resolve()
                if folder_path == input_path:
                    messagebox.showwarning("Warning", "Output folder cannot be the same as the input folder.", parent=self.root)
                    return
            self.output_folder.set(str(folder_path))
            self._update_save_state()
            self._update_folder_open_button_states()
            self._save_config() # Save new folder path

    def _update_save_state(self):
        """Updates the state of the Save button and Save menu item."""
        # Enable save only if both folders are set and there is data loaded
        new_state = tk.NORMAL if self.input_folder.get() and self.output_folder.get() and self.file_data else tk.DISABLED
        if hasattr(self, 'save_button'):
             self.save_button.config(state=new_state)
        if hasattr(self, 'file_menu'):
            try:
                save_index = self.file_menu.index("Save All Changes")
                if save_index is not None and save_index != tk.NONE:
                    self.file_menu.entryconfigure(save_index, state=new_state)
            except (tk.TclError, AttributeError): pass # Ignore if menu not ready/found


    def _update_folder_open_button_states(self):
        """Updates the state of the 'Open' buttons and corresponding menu items."""
        input_path = self.input_folder.get()
        output_path = self.output_folder.get()

        # Check if paths are valid directories
        input_state = tk.NORMAL if input_path and pathlib.Path(input_path).is_dir() else tk.DISABLED
        output_state = tk.NORMAL if output_path and pathlib.Path(output_path).is_dir() else tk.DISABLED

        # Update Buttons (check existence first)
        if hasattr(self, 'open_input_button'):
            self.open_input_button.config(state=input_state)
        if hasattr(self, 'open_output_button'):
            self.open_output_button.config(state=output_state)

        # Update Menu Items (use try-except for robustness)
        if hasattr(self, 'file_menu'):
            try:
                input_index = self.file_menu.index("Open Input Folder Location")
                if input_index is not None and input_index != tk.NONE:
                    self.file_menu.entryconfigure(input_index, state=input_state)
                output_index = self.file_menu.index("Open Output Folder Location")
                if output_index is not None and output_index != tk.NONE:
                    self.file_menu.entryconfigure(output_index, state=output_state)
            except (tk.TclError, AttributeError) as e:
                 print(f"Warning: Could not update Open Folder menu item states: {e}")


    def _update_import_export_state(self):
        """Updates the state of the Import/Export menu items."""
        new_state = tk.NORMAL if self.file_data and self.item_id_map else tk.DISABLED
        if hasattr(self, 'file_menu'):
            try:
                export_index = self.file_menu.index("Export Text...")
                if export_index is not None and export_index != tk.NONE:
                    self.file_menu.entryconfigure(export_index, state=new_state)
                import_index = self.file_menu.index("Import Text...")
                if import_index is not None and import_index != tk.NONE:
                     self.file_menu.entryconfigure(import_index, state=new_state)
            except (tk.TclError, AttributeError):
                 pass # Menu might not be fully initialized

    # --- Open Folder Location Logic ---
    def _open_folder_location(self, folder_path_str):
        """Opens the specified folder path in the system's file explorer."""
        if not folder_path_str:
            messagebox.showwarning("Open Folder", "No folder path is selected.", parent=self.root)
            return

        folder_path = pathlib.Path(folder_path_str)

        # Check if it's a file first for the header double-click case
        is_file = folder_path.is_file()
        target_path = folder_path.parent if is_file else folder_path # Get dir if it's a file

        if not target_path.is_dir():
            messagebox.showerror("Open Folder Error", f"The path is not a valid directory or file:\n{folder_path}", parent=self.root)
            return

        try:
            print(f"Attempting to open: {folder_path}") # Open the original path (file or folder)
            system = platform.system()
            if system == "Windows":
                os.startfile(folder_path)
            elif system == "Darwin": # macOS
                subprocess.run(['open', str(folder_path)], check=True)
            else: # Linux and other Unix-like
                subprocess.run(['xdg-open', str(folder_path)], check=True)
        except FileNotFoundError:
            cmd = 'open' if system == 'Darwin' else 'xdg-open' if system != 'Windows' else 'startfile mechanism'
            messagebox.showerror("Open Folder Error", f"Could not find the command to open folders/files on this system ('{cmd}').", parent=self.root)
        except subprocess.CalledProcessError as e:
             messagebox.showerror("Open Folder Error", f"The command to open the item failed:\n{e}", parent=self.root)
        except Exception as e:
            print(f"Error opening item {folder_path}: {e}")
            messagebox.showerror("Open Folder Error", f"An unexpected error occurred:\n{e}", parent=self.root)

    def _open_input_folder_location(self):
        """Command for the 'Open Input Folder' button/menu item."""
        self._open_folder_location(self.input_folder.get())

    def _open_output_folder_location(self):
        """Command for the 'Open Output Folder' button/menu item."""
        self._open_folder_location(self.output_folder.get())


    # --- Centralized Update Logic (Handles Undo/Redo & Formats) ---
    def _update_tree_and_data(self, iid, new_text, is_undo_redo=False):
        """Updates the treeview and backend data for a given item IID.

        Args:
            iid: The Treeview item ID.
            new_text: The new text value (this is the editor-escaped version).
            is_undo_redo: Flag to prevent logging undo/redo actions themselves.

        Returns:
            True if the update was successful, False otherwise.
        """
        # --- Pre-checks ---
        if not self.tree.exists(iid):
            print(f"Warning: Attempted to update non-existent item {iid}.")
            return False
        if iid not in self.item_id_map:
            print(f"Error: Item {iid} exists in Treeview but not in item_id_map.")
            messagebox.showerror("Internal Error", f"Data mapping missing for item {iid}.\nPlease reload the folder.", parent=self.root)
            return False

        current_tree_text = "" # Initialize
        try:
            current_tree_text = self.tree.set(iid, DIALOGUE_COLUMN_ID)

            # Only proceed if text actually changed
            if new_text == current_tree_text:
                # print(f"Skipping update for {iid}, text unchanged.") # Debugging
                return True # No change needed

            # --- Get Data Location & Format ---
            map_info = self.item_id_map[iid]
            file_idx = map_info.get("file_index")
            string_info_idx = map_info.get("string_info_index")
            seg_idx = map_info.get("segment_index") # Will be None for LOCR

            # Verify basic indices
            if not (isinstance(file_idx, int) and isinstance(string_info_idx, int)):
                 print(f"Error: Corrupt map info (base indices) for IID '{iid}' during update: {map_info}")
                 messagebox.showerror("Internal Error", f"Could not save change for item {iid}.\nMap data indices invalid.", parent=self.root)
                 return False

            # Get file format and verify file data structure
            if not (0 <= file_idx < len(self.file_data) and isinstance(self.file_data[file_idx], dict)):
                 print(f"Error: Invalid file index {file_idx} for IID '{iid}'.")
                 messagebox.showerror("Internal Error", "Data structure error (file index).", parent=self.root)
                 return False
            file_format = self.file_data[file_idx].get("format")
            en_strings = self.file_data[file_idx].get("en_strings")

            if not (file_format in [FORMAT_DLGE, FORMAT_LOCR] and isinstance(en_strings, list) and
                    0 <= string_info_idx < len(en_strings) and isinstance(en_strings[string_info_idx], dict)):
                print(f"Error: Data structure integrity path check failed (file/string_info level) for IID '{iid}'.")
                messagebox.showerror("Internal Error", f"Could not save change for item {iid}.\nData structure inconsistent.", parent=self.root)
                return False

            string_data = en_strings[string_info_idx]

            # --- Undo/Redo Handling ---
            if not is_undo_redo:
                # Store the *old* state before changing it (current_tree_text is editor-escaped)
                self.undo_stack.append({'iid': iid, 'old_value': current_tree_text, 'new_value': new_text})
                self.redo_stack.clear() # Clear redo stack on new user action
                self._update_undo_redo_state()

            # --- Perform Updates (Format Specific) ---
            data_updated = False
            if file_format == FORMAT_DLGE:
                if isinstance(seg_idx, int) and \
                   isinstance(string_data.get("segments"), list) and \
                   0 <= seg_idx < len(string_data["segments"]) and \
                   isinstance(string_data["segments"][seg_idx], dict):
                    # UPDATE the 'text' field of the specific segment (new_text is already editor-escaped)
                    string_data["segments"][seg_idx]["text"] = new_text
                    data_updated = True
                else:
                    print(f"Error: Invalid segment index or structure for DLGE item {iid}.")
                    messagebox.showerror("Internal Error", f"Data structure inconsistent (DLGE segment {iid}).", parent=self.root)

            elif file_format == FORMAT_LOCR:
                if "text" in string_data: # LOCR stores text directly in string_info
                    # UPDATE the 'text' field directly (new_text is already editor-escaped)
                    string_data["text"] = new_text
                    data_updated = True
                else:
                     print(f"Error: Missing 'text' key for LOCR item {iid}.")
                     messagebox.showerror("Internal Error", f"Data structure inconsistent (LOCR text {iid}).", parent=self.root)

            # --- Update Treeview (if data update succeeded) ---
            if data_updated:
                self.tree.set(iid, DIALOGUE_COLUMN_ID, new_text)
                # print(f"Backend/Treeview updated for {iid} ({file_format}) to '{new_text}'") # Debugging
                return True
            else:
                # Data update failed, revert undo stack change if made
                if not is_undo_redo and self.undo_stack and self.undo_stack[-1]['iid'] == iid:
                    self.undo_stack.pop()
                    self._update_undo_redo_state()
                return False # Update failed

        except KeyError as e:
             print(f"Error updating item {iid}: Missing key {e} in data structure.")
             messagebox.showerror("Internal Error", f"Data structure error updating item {iid}: Missing key {e}", parent=self.root)
             if not is_undo_redo and self.undo_stack and self.undo_stack[-1]['iid'] == iid: self.undo_stack.pop(); self._update_undo_redo_state()
             if current_tree_text and self.tree.exists(iid): self.tree.set(iid, DIALOGUE_COLUMN_ID, current_tree_text) # Revert UI if possible
             return False
        except IndexError as e:
            print(f"Error updating item {iid}: Index out of bounds {e}.")
            messagebox.showerror("Internal Error", f"Data structure error updating item {iid}: Index out of bounds.", parent=self.root)
            if not is_undo_redo and self.undo_stack and self.undo_stack[-1]['iid'] == iid: self.undo_stack.pop(); self._update_undo_redo_state()
            if current_tree_text and self.tree.exists(iid): self.tree.set(iid, DIALOGUE_COLUMN_ID, current_tree_text)
            return False
        except tk.TclError as e:
             print(f"Error updating Treeview item {iid}: {e}")
             messagebox.showerror("UI Error", f"Failed to update display for item {iid}:\n{e}", parent=self.root)
             # Assume data update failed if UI failed right after
             if not is_undo_redo and self.undo_stack and self.undo_stack[-1]['iid'] == iid: self.undo_stack.pop(); self._update_undo_redo_state()
             return False
        except Exception as e:
             print(f"Unexpected error updating item {iid}: {type(e).__name__}: {e}")
             traceback.print_exc() # Print full traceback for unexpected errors
             messagebox.showerror("Unexpected Error", f"An unexpected error occurred updating item {iid}:\n{e}", parent=self.root)
             if not is_undo_redo and self.undo_stack and self.undo_stack[-1]['iid'] == iid: self.undo_stack.pop(); self._update_undo_redo_state()
             if current_tree_text and self.tree.exists(iid): self.tree.set(iid, DIALOGUE_COLUMN_ID, current_tree_text)
             return False


    # --- File Opening Logic ---
    def _open_file_from_header(self, header_iid):
        """Opens the original JSON file associated with a header row."""
        try:
            if not header_iid.startswith("header_"):
                print(f"Warning: Unexpected header IID format for file open: {header_iid}")
                return

            file_index_str = header_iid.split('_')[-1]
            file_index = int(file_index_str)

            if not (0 <= file_index < len(self.file_data)):
                print(f"Error: File index {file_index} (from IID {header_iid}) is out of bounds for self.file_data (len {len(self.file_data)}).")
                messagebox.showerror("Error", "Cannot open file: Internal data index is invalid.", parent=self.root)
                return

            # Get the path stored in our data structure
            file_path = self.file_data[file_index].get('path')

            if not file_path or not isinstance(file_path, pathlib.Path):
                 print(f"Error: Invalid or missing file path for index {file_index} in self.file_data.")
                 messagebox.showerror("Error", "Cannot open file: Path information is missing or corrupt.", parent=self.root)
                 return

            if not file_path.is_file():
                print(f"Error: Original file path not found or is not a file: {file_path}")
                messagebox.showerror("File Open Error", f"Cannot open file: The original file seems to be missing or moved.\nPath: {file_path}", parent=self.root)
                return

            # Attempt to open using platform-specific methods
            self._open_folder_location(str(file_path)) # Reuse the folder opening logic for files

        except (ValueError, IndexError) as e:
            print(f"Error parsing file index from header IID '{header_iid}': {e}")
            messagebox.showerror("Error", "Could not open file: Failed to determine file index from selection.", parent=self.root)
        except Exception as e:
            print(f"Unexpected error opening file for header IID '{header_iid}': {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"An unexpected error occurred trying to open the file:\n{e}", parent=self.root)


    # --- Treeview Click Handlers ---
    def _on_tree_single_click_or_clear_edit(self, event):
        """Handles single clicks on the tree. Clears editor if click is outside."""
        target_widget = self.root.winfo_containing(event.x_root, event.y_root)
        clicked_item_id = self.tree.identify_row(event.y)

        if self.edit_entry:
            if target_widget != self.edit_entry:
                if clicked_item_id != self.edit_item_id:
                    if self.edit_item_id and self.tree.exists(self.edit_item_id):
                        # Clicked elsewhere while editing, save current edit
                        self._save_edit(self.edit_item_id, DIALOGUE_COLUMN_ID)
                    else:
                        # Edit entry exists but no valid item, just destroy
                        self._destroy_edit_entry()
                # If clicked back on the *same* item being edited, do nothing here
                # (Let the edit entry handle it, or maybe save/cancel via its bindings)


    def _on_tree_double_click(self, event):
        """Handles double-clicks to open files (header) or start editing (cell)."""
        # Save any existing edit first
        if self.edit_entry:
             if self.edit_item_id and self.tree.exists(self.edit_item_id):
                 self._save_edit(self.edit_item_id, DIALOGUE_COLUMN_ID)
             else:
                 self._destroy_edit_entry()

        region = self.tree.identify("region", event.x, event.y)
        item_id = self.tree.identify_row(event.y)
        column_id_clicked = self.tree.identify_column(event.x)

        if not item_id: return # Clicked outside of any item

        try:
            if not self.tree.exists(item_id): return
            item_tags = self.tree.item(item_id, "tags")
        except tk.TclError:
            print(f"Warning: TclError getting tags for item {item_id} on double-click.")
            return

        if FILE_HEADER_TAG in item_tags:
            self._open_file_from_header(item_id)
        elif item_id in self.item_id_map:
            if region == "cell" and column_id_clicked == DIALOGUE_COLUMN_ID:
                self._start_editing(item_id, column_id_clicked)

    # --- Treeview Editing Logic ---
    def _start_editing(self, item_id, column_id):
        """Creates an Entry widget over the selected cell to allow editing."""
        self._destroy_edit_entry() # Clean up any previous editor

        bbox = self.tree.bbox(item_id, column=column_id)
        if not bbox: return # Item not visible or gone

        x, y, width, height = bbox
        current_text = self.tree.set(item_id, column_id) # This is editor-escaped text
        self.edit_entry = ttk.Entry(self.tree, style='TEntry')

        self.edit_entry.place(x=x, y=y, width=width, height=height, anchor='nw')

        self.edit_entry.insert(0, current_text)
        self.edit_entry.select_range(0, tk.END)
        self.edit_entry.focus_set()
        self.edit_item_id = item_id
        self._escape_pressed = False # Reset escape flag

        self.edit_entry.bind("<Return>", lambda e: self._save_edit(item_id, column_id))
        self.edit_entry.bind("<KP_Enter>", lambda e: self._save_edit(item_id, column_id))
        self.edit_entry.bind("<FocusOut>", self._save_edit_on_focus_out)
        self.edit_entry.bind("<Escape>", self._cancel_edit)
        self.edit_entry.bind("<Button-3>", self._show_entry_context_menu)

    def _save_edit_on_focus_out(self, event=None):
        """Callback for FocusOut: saves edit if Escape wasn't pressed."""
        # Check if focus is moving away from the edit entry itself
        if event and self.edit_entry and event.widget == self.edit_entry and not self._escape_pressed:
             if self.edit_item_id and self.tree.exists(self.edit_item_id):
                 self._save_edit(self.edit_item_id, DIALOGUE_COLUMN_ID)
             else:
                 # Edit item ID became invalid somehow, just destroy
                 self._destroy_edit_entry()
        elif self.edit_entry and not self._escape_pressed:
            # This handles cases where focus out happens without an event object
            # or the event widget isn't the edit entry (less common)
            # Still save if Escape wasn't the reason for losing focus
            if self.edit_item_id and self.tree.exists(self.edit_item_id):
                 self._save_edit(self.edit_item_id, DIALOGUE_COLUMN_ID)
            else:
                 self._destroy_edit_entry()
        elif self.edit_entry and self._escape_pressed:
            # If escape was pressed, FocusOut should just destroy without saving
            self._destroy_edit_entry()

    def _save_edit(self, item_id, column_id):
        """Saves the text from the edit entry back to the tree and data."""
        if not self.edit_entry or item_id != self.edit_item_id:
             if self.edit_entry: self._destroy_edit_entry()
             return

        new_text = self.edit_entry.get() # This is editor-escaped text
        # Update function handles tree update, data update, and undo logging
        update_successful = self._update_tree_and_data(item_id, new_text)
        self._destroy_edit_entry() # Destroy the entry regardless of success

    def _cancel_edit(self, event=None):
        """Cancels the current edit operation without saving."""
        self._escape_pressed = True # Set flag to prevent save on focus out
        self._destroy_edit_entry()
        if self.tree.winfo_exists(): self.tree.focus_set() # Return focus to tree
        return "break" # Stop further event propagation

    def _destroy_edit_entry(self):
        """Safely destroys the editing widget and resets state."""
        if self.edit_entry:
            entry = self.edit_entry
            self.edit_entry = None # Clear reference first
            self.edit_item_id = None
            try:
                if entry.winfo_exists():
                    # Unbind specific events to prevent callbacks after destroy
                    entry.unbind("<Return>")
                    entry.unbind("<KP_Enter>")
                    entry.unbind("<FocusOut>")
                    entry.unbind("<Escape>")
                    entry.unbind("<Button-3>")
                    entry.destroy()
            except tk.TclError: pass # Ignore errors during destroy
            except Exception as e: print(f"Error destroying edit entry: {e}")
        self._escape_pressed = False # Reset escape flag


    # --- File Loading Logic ---
    def _detect_format(self, data):
        """Detects if the JSON data matches DLGE or LOCR format."""
        if isinstance(data, list) and data:
            first_item = data[0]
            # DLGE Check: List of Dicts with "Language" and "String"
            if isinstance(first_item, dict) and "Language" in first_item and "String" in first_item:
                if all(isinstance(item, dict) and "Language" in item and "String" in item for item in data):
                    return FORMAT_DLGE
            # LOCR Check: List of Lists, where inner list starts with {"Language": ...}
            elif isinstance(first_item, list) and first_item:
                 first_inner_item = first_item[0]
                 if isinstance(first_inner_item, dict) and "Language" in first_inner_item:
                     # Check if subsequent elements are string/hash dicts (basic check)
                     is_likely_locr = True
                     if len(first_item) > 1:
                         is_likely_locr = isinstance(first_item[1], dict) and "String" in first_item[1] and "StringHash" in first_item[1]

                     if is_likely_locr:
                          # Check if all top-level items follow this list pattern
                          if all(isinstance(outer_item, list) and outer_item and isinstance(outer_item[0], dict) and "Language" in outer_item[0] for outer_item in data):
                              return FORMAT_LOCR
        return FORMAT_UNKNOWN

    def _find_en_string_line_numbers(self, file_path, file_format):
        """Finds line numbers for 'String' keys within 'en' language sections.

        Returns:
            A dictionary mapping index information to line numbers.
            DLGE: {original_item_index: line_number}
            LOCR: {(original_lang_block_index, original_string_item_index): line_number}
            Returns an empty dict on error or if no 'en' strings found.
        """
        line_map = {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            if file_format == FORMAT_DLGE:
                object_index = -1 # Index in the outer list
                in_object = False
                is_current_object_en = False
                brace_level = 0
                found_string_in_current_object = False

                for i, line in enumerate(lines):
                    line_num = i + 1
                    stripped_line = line.strip()
                    if stripped_line.startswith("//") or stripped_line.startswith("#"): continue

                    # Detect object start/end based on braces at level 0
                    if '{' in line and brace_level == 0:
                        object_index += 1
                        in_object = True
                        is_current_object_en = False
                        found_string_in_current_object = False # Reset flag for new object
                        brace_level += line.count('{') - line.count('}') # Handle braces on the same line
                        if brace_level < 0: brace_level = 0 # Safety
                        if brace_level == 0: in_object = False # Object starts and ends on the same line
                    elif in_object:
                        brace_level += line.count('{')
                        brace_level -= line.count('}')

                    if in_object:
                        # Check for language *within* the current object
                        if not is_current_object_en and LANG_EN_REGEX.search(line):
                            is_current_object_en = True

                        # Check for the string key *within* the current 'en' object
                        # Only map the *first* "String": line found within an 'en' object
                        if is_current_object_en and not found_string_in_current_object and STRING_KEY_REGEX.search(line):
                             line_map[object_index] = line_num
                             found_string_in_current_object = True # Mark as found for this object

                    # Reset object state if brace level drops to 0
                    if brace_level <= 0 and in_object:
                        in_object = False
                        is_current_object_en = False
                        found_string_in_current_object = False
                        brace_level = 0

            elif file_format == FORMAT_LOCR:
                lang_block_idx = -1
                item_idx_in_block = 0 # 0=Lang dict, 1=first string dict, etc.
                in_lang_block_list = False # Inside the outer [...]
                in_item_list = False     # Inside the inner [...]
                is_current_block_en = False
                bracket_level = 0
                brace_level_locr = 0 # To track dicts inside the inner list

                for i, line in enumerate(lines):
                    line_num = i + 1
                    stripped_line = line.strip()
                    if stripped_line.startswith("//") or stripped_line.startswith("#"): continue

                    # Track bracket levels for lists
                    open_brackets = line.count('[')
                    close_brackets = line.count(']')

                    if open_brackets > 0:
                        if bracket_level == 0: # Entering outer list
                            in_lang_block_list = True
                        elif bracket_level == 1: # Entering inner list
                            in_item_list = True
                            lang_block_idx += 1
                            item_idx_in_block = 0 # Reset item counter for new block
                            is_current_block_en = False
                            brace_level_locr = 0 # Reset brace level for items in this block
                        bracket_level += open_brackets

                    # Track brace levels for dictionaries *inside* the item list
                    if in_item_list:
                         # Count dictionaries starting *after* the language dictionary
                        if '{' in line and brace_level_locr == 0:
                            item_idx_in_block += 1 # Increment dict count (1st dict is lang, 2nd is first string item, etc.)
                        brace_level_locr += line.count('{')
                        brace_level_locr -= line.count('}')
                        if brace_level_locr < 0: brace_level_locr = 0

                    # Process based on state
                    if in_item_list:
                        # Check for Language: en only on the first item's dict (item_idx_in_block == 1)
                        if item_idx_in_block == 1 and LANG_EN_REGEX.search(line):
                             is_current_block_en = True

                        # Check for String: on subsequent items (index > 1) IF it's an 'en' block
                        # The index here needs to map to the *string item index* (1st string = index 1, etc.)
                        # So we use `item_idx_in_block - 1` for the map key.
                        string_item_map_idx = item_idx_in_block - 1
                        if is_current_block_en and string_item_map_idx > 0 and STRING_KEY_REGEX.search(line):
                             map_key = (lang_block_idx, string_item_map_idx) # Key is (block_index, 1-based index *among string items*)
                             if map_key not in line_map: # Store first occurrence for this specific item index
                                 line_map[map_key] = line_num

                    # Track closing brackets
                    if close_brackets > 0:
                        original_level = bracket_level
                        bracket_level -= close_brackets
                        if bracket_level < 0: bracket_level = 0 # Safety

                        if original_level == 2 and bracket_level == 1: # Leaving inner list
                             in_item_list = False
                             is_current_block_en = False # Reset language flag when leaving inner list
                        elif original_level == 1 and bracket_level == 0: # Leaving outer list
                             in_lang_block_list = False

        except Exception as e:
            print(f"Warning: Could not parse lines for accurate line number detection in {file_path.name}: {e}")
            traceback.print_exc() # More detail on error

        # print(f"Debug: Line map for {file_path.name} ({file_format}): {line_map}") # Debugging
        return line_map


    def load_json_files(self):
        """Loads JSON files, detects format, parses 'en' strings, and populates treeview."""
        folder_path = self.input_folder.get()
        if not folder_path:
            self.status_label.config(text="Status: No input folder selected.")
            return

        # --- Reset State ---
        self._clear_search()
        self.file_data = []
        self.item_id_map = {}
        self._destroy_edit_entry()
        if self.tree.winfo_exists(): self.tree.delete(*self.tree.get_children())
        self._clear_undo_redo()

        self.status_label.config(text="Status: Loading files...")
        self.root.update_idletasks()

        # --- Initialization ---
        loaded_items_count = 0
        processed_file_count = 0
        loaded_file_count = 0
        error_files_load = []
        unsupported_files = []

        try:
            p_folder_path = pathlib.Path(folder_path)
            if not p_folder_path.is_dir():
                messagebox.showerror("Error", f"Input path is not a valid directory:\n{folder_path}", parent=self.root)
                self.status_label.config(text="Status: Error - Input folder not found or invalid.")
                return

            json_files = sorted([
                item for item in p_folder_path.glob('*.json')
                if item.is_file() and not item.name.lower().endswith('.json.meta')
            ])

            if not json_files:
                 self.status_label.config(text="Status: No non-meta .json files found in input folder.")
                 self._update_save_state(); self._update_search_replace_button_states(); self._update_import_export_state()
                 return

            # --- Process Each File ---
            temp_file_data_list = []
            for file_path in json_files:
                processed_file_count += 1
                file_format = FORMAT_UNKNOWN
                en_string_line_map = {} # Initialize map for this file

                try:
                    # Load JSON content first to detect format
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = json.load(f)

                    file_format = self._detect_format(content)

                    if file_format == FORMAT_UNKNOWN:
                         print(f"Warning: Skipping file {file_path.name} - Unrecognized or unsupported JSON structure.")
                         unsupported_files.append(file_path.name)
                         continue

                    # *** GET LINE NUMBER MAP ***
                    try:
                        en_string_line_map = self._find_en_string_line_numbers(file_path, file_format)
                    except Exception as e_ln:
                         print(f"Error getting line numbers for {file_path.name}: {e_ln}")

                    # --- Prepare data structure for this file ---
                    # Store original content for reference/saving, but primarily work with en_strings
                    file_entry = {"path": file_path, "format": file_format, "json_content": content, "en_strings": []}
                    current_en_strings_data = []
                    found_en_in_file = False

                    # --- Process based on detected format ---
                    if file_format == FORMAT_DLGE:
                        for item_idx, item in enumerate(content):
                            if isinstance(item, dict) and item.get("Language") == "en":
                                found_en_in_file = True
                                raw_original_string = item.get("String", "") # Raw string from JSON
                                segments_data = []
                                line_num = en_string_line_map.get(item_idx, None) # Lookup by item index

                                matches = list(SEGMENT_REGEX.finditer(raw_original_string))
                                if matches:
                                    for seg_idx, match in enumerate(matches):
                                        raw_segment_text = match.group(2)
                                        segments_data.append({
                                            "original_prefix": match.group(1),
                                            "text": custom_escape_for_editor(raw_segment_text), # Escaped for editor
                                            "iid": None
                                        })
                                else:
                                    # No segments, store the whole string as one editable segment
                                    segments_data.append({
                                        "original_prefix": None,
                                        "text": custom_escape_for_editor(raw_original_string), # Escaped for editor
                                        "iid": None
                                    })

                                current_en_strings_data.append({
                                    "original_item_index": item_idx,
                                    "original_line_number": line_num,
                                    "original_string": raw_original_string, # Store raw original
                                    "segments": segments_data
                                })

                    elif file_format == FORMAT_LOCR:
                        for lang_block_idx, lang_block in enumerate(content):
                            if isinstance(lang_block, list) and len(lang_block) > 0 and \
                               isinstance(lang_block[0], dict) and lang_block[0].get("Language") == "en":
                                found_en_in_file = True
                                # Iterate through the string items in this 'en' block (index 1 onwards)
                                for string_item_list_idx, string_item in enumerate(lang_block[1:], start=1):
                                    if isinstance(string_item, dict) and "String" in string_item:
                                        raw_text = string_item.get("String", "") # Raw string from JSON
                                        string_hash = string_item.get("StringHash", None) # Keep hash
                                        map_key = (lang_block_idx, string_item_list_idx)
                                        line_num = en_string_line_map.get(map_key, None)
                                        original_string_item_index_in_list = string_item_list_idx

                                        current_en_strings_data.append({
                                            "original_lang_block_index": lang_block_idx,
                                            "original_string_item_index": original_string_item_index_in_list,
                                            "original_line_number": line_num,
                                            "string_hash": string_hash,
                                            "text": custom_escape_for_editor(raw_text), # Escaped for editor
                                            "original_text": raw_text, # Store raw original
                                            "iid": None
                                        })

                    # Add file's data if 'en' strings were found
                    if found_en_in_file:
                        file_entry["en_strings"] = current_en_strings_data
                        temp_file_data_list.append(file_entry)
                        loaded_file_count += 1
                    # Else: No 'en' strings found, file is processed but not added to editable data


                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    print(f"Warning: Skipping file {file_path.name} due to JSON/encoding error: {e}")
                    error_files_load.append(f"{file_path.name} (Parse Error)")
                except IOError as e:
                    print(f"Warning: Skipping file {file_path.name} due to I/O error: {e}")
                    error_files_load.append(f"{file_path.name} (I/O Error)")
                except Exception as e:
                    print(f"Error processing file {file_path.name} ({file_format}): {type(e).__name__}: {e}")
                    traceback.print_exc()
                    error_files_load.append(f"{file_path.name} (Processing Error: {type(e).__name__})")

            # --- Populate Treeview from Processed Data ---
            self.file_data = temp_file_data_list
            tree_row_count = 0

            for file_index, file_entry in enumerate(self.file_data):
                file_format = file_entry["format"]
                file_path_name = file_entry['path'].name
                header_iid = f"header_{file_index}"
                header_display_text = f"--- File: {file_path_name} ({file_format}) (Double-click to open) ---"
                self.tree.insert('', tk.END, iid=header_iid, values=(f"FILE {file_index+1}", "", header_display_text), tags=(FILE_HEADER_TAG,))

                # Add data rows based on format
                for string_info_idx, string_info in enumerate(file_entry["en_strings"]):
                    line_num_display = str(string_info.get("original_line_number") or "??")

                    if file_format == FORMAT_DLGE:
                        for segment_idx, segment in enumerate(string_info["segments"]):
                            # Unique IID for DLGE segment
                            iid = f"f{file_index}_i{string_info['original_item_index']}_s{segment_idx}"
                            segment['iid'] = iid # Store IID back in the segment data
                            prefix_display = segment.get("original_prefix", "") or ""
                            text_display = segment["text"] # This is the editor-escaped text

                            # Column values: Line#, Prefix, Editable Text
                            self.tree.insert('', tk.END, iid=iid, values=(line_num_display, prefix_display, text_display))
                            tree_row_count += 1
                            loaded_items_count += 1

                            # Map IID for DLGE
                            self.item_id_map[iid] = {
                                "file_index": file_index,
                                "string_info_index": string_info_idx,
                                "segment_index": segment_idx # Store segment index
                            }

                    elif file_format == FORMAT_LOCR:
                        # Unique IID for LOCR string item
                        lang_block_idx = string_info["original_lang_block_index"]
                        # Use the absolute item index in the list for uniqueness
                        item_idx_in_list = string_info["original_string_item_index"]
                        iid = f"f{file_index}_lb{lang_block_idx}_si{item_idx_in_list}"
                        string_info['iid'] = iid # Store IID back in the string info data
                        string_hash_display = str(string_info.get("string_hash") or "NO HASH")
                        text_display = string_info["text"] # This is the editor-escaped text

                        # Display line number (if found) or hash in the first column (Line / ID)
                        col1_display = line_num_display if string_info.get("original_line_number") else f"H:{string_hash_display}"
                        # Column values: Line#/Hash, Hash, Editable Text
                        self.tree.insert('', tk.END, iid=iid, values=(col1_display, string_hash_display, text_display))
                        tree_row_count += 1
                        loaded_items_count += 1

                        # Map IID for LOCR
                        self.item_id_map[iid] = {
                            "file_index": file_index,
                            "string_info_index": string_info_idx,
                            "segment_index": None # No segment index for LOCR
                        }

                # Add separator row between files if more files exist
                if file_index < len(self.file_data) - 1:
                    sep_iid = f"filesep_{file_index}"
                    self.tree.insert('', tk.END, iid=sep_iid, values=("", "", ""), tags=(SEPARATOR_TAG,), open=False)
                    tree_row_count += 1


            # --- Final Status Update ---
            status_msg = f"Status: Loaded {loaded_file_count}/{processed_file_count} files | Displaying {loaded_items_count} items."
            if unsupported_files:
                 status_msg += f" | {len(unsupported_files)} unsupported format(s)."
            if error_files_load:
                 status_msg += f" | {len(error_files_load)} file(s) failed to load/process."
            self.status_label.config(text=status_msg)

            if error_files_load or unsupported_files:
                 error_list = "\n - ".join(error_files_load + [f"{n} (Unsupported)" for n in unsupported_files])
                 messagebox.showwarning("Loading Issues", f"Finished loading, but some files had issues:\n\n - {error_list}\n\nCheck console for details.", parent=self.root)

        except FileNotFoundError as e:
            messagebox.showerror("Error", str(e), parent=self.root)
            self.status_label.config(text="Status: Error - Input folder not found.")
        except Exception as e:
            messagebox.showerror("Critical Loading Error", f"An unexpected error occurred during the loading process: {e}", parent=self.root)
            self.status_label.config(text=f"Status: Critical error during load - {e}")
            print(f"Loading Process Error Type: {type(e)}\nLoading Error: {e}")
            traceback.print_exc()
        finally:
            # Update states regardless of success or failure
            self._update_save_state()
            self._update_search_replace_button_states()
            self._update_import_export_state()
            self._update_folder_open_button_states()

    # --- Search & Replace Logic ---
    def _update_search_replace_button_states(self):
        """Updates the enabled/disabled state of search and replace buttons."""
        has_results = bool(self.search_results)
        has_data = bool(self.item_id_map) # Check if any editable data is loaded

        # Find buttons depend only on having data to search
        find_state = tk.NORMAL if has_data else tk.DISABLED
        if hasattr(self, 'find_button'): self.find_button.config(state=find_state)
        if hasattr(self, 'find_all_button'): self.find_all_button.config(state=find_state)
        if hasattr(self, 'edit_menu'):
            try:
                find_menu_index = self.edit_menu.index("Find / Focus Search")
                if find_menu_index is not None and find_menu_index != tk.NONE: self.edit_menu.entryconfigure(find_menu_index, state=find_state)
                findall_menu_index = self.edit_menu.index("Find All")
                if findall_menu_index is not None and findall_menu_index != tk.NONE: self.edit_menu.entryconfigure(findall_menu_index, state=find_state)
            except (tk.TclError, AttributeError): pass

        # Next/Prev/Replace buttons depend on having search results
        results_state = tk.NORMAL if has_results else tk.DISABLED
        if hasattr(self, 'next_button'): self.next_button.config(state=results_state)
        if hasattr(self, 'prev_button'): self.prev_button.config(state=results_state)
        if hasattr(self, 'replace_button'): self.replace_button.config(state=results_state)
        if hasattr(self, 'replace_all_button'): self.replace_all_button.config(state=results_state)
        if hasattr(self, 'edit_menu'):
            try:
                next_menu_index = self.edit_menu.index("Find Next")
                if next_menu_index is not None and next_menu_index != tk.NONE: self.edit_menu.entryconfigure(next_menu_index, state=results_state)
                prev_menu_index = self.edit_menu.index("Find Previous")
                if prev_menu_index is not None and prev_menu_index != tk.NONE: self.edit_menu.entryconfigure(prev_menu_index, state=results_state)
            except (tk.TclError, AttributeError): pass

    def _focus_search(self, event=None):
        """Sets focus to the search entry."""
        if hasattr(self, 'search_entry'):
             self.search_entry.focus_set()
             self.search_entry.select_range(0, tk.END)
        if event: return "break" # Prevent further event processing if called from binding

    def _check_clear_search_on_empty(self, event=None):
        """Clears search results if the search term becomes empty."""
        if not self.search_term.get() and (self.search_results or self._last_search_was_findall):
             self._clear_search()

    def _perform_search(self, event=None):
        """Performs a sequential search (Find)."""
        self._destroy_edit_entry() # Finish any edit first
        term = self.search_term.get()
        if not term:
            self._clear_search()
            return "break" if event else None

        self._clear_search_highlight() # Remove previous single highlights
        self.search_results = []
        self.current_search_index = -1
        # Search term does not need special escaping here, user types what they see (e.g., \\n for newline)
        term_lower = term.lower()
        self._last_search_was_findall = False # Mark as regular find

        all_iids_in_order = []
        if self.tree.winfo_exists(): all_iids_in_order = self.tree.get_children('')
        editable_iids = [iid for iid in all_iids_in_order if iid in self.item_id_map]

        for iid in editable_iids:
            try:
                if not self.tree.exists(iid): continue
                dialogue_text = self.tree.set(iid, DIALOGUE_COLUMN_ID) # This is editor-escaped
                if term_lower in dialogue_text.lower():
                    self.search_results.append(iid)
            except tk.TclError:
                 print(f"Warning: TclError accessing item {iid} during search.")
            except Exception as e:
                 print(f"Error accessing item {iid} during search: {e}")

        if self.search_results:
            self.current_search_index = 0
            self._focus_search_result(self.current_search_index)
            self.status_label.config(text=f"Status: Found {len(self.search_results)} match(es) for '{term}'. Showing 1.")
        else:
            self.status_label.config(text=f"Status: No matches found for '{term}'.")

        self._update_search_replace_button_states()
        return "break" if event else None

    def _find_all(self, event=None):
        """Finds and highlights all occurrences."""
        self._destroy_edit_entry() # Finish any edit first
        term = self.search_term.get()
        if not term:
            self._clear_search()
            return "break" if event else None

        self._clear_search_highlight()
        self.search_results = []
        self.current_search_index = -1
        term_lower = term.lower() # User types what they see
        self._last_search_was_findall = True

        found_count = 0
        all_iids_in_order = []
        if self.tree.winfo_exists(): all_iids_in_order = self.tree.get_children('')
        editable_iids = [iid for iid in all_iids_in_order if iid in self.item_id_map]

        for iid in editable_iids:
            try:
                if not self.tree.exists(iid): continue
                dialogue_text = self.tree.set(iid, DIALOGUE_COLUMN_ID) # editor-escaped
                if term_lower in dialogue_text.lower():
                    self.search_results.append(iid)
                    current_tags = list(self.tree.item(iid, "tags"))
                    if SEARCH_HIGHLIGHT_TAG not in current_tags:
                         self.tree.item(iid, tags=current_tags + [SEARCH_HIGHLIGHT_TAG])
                    found_count += 1
            except tk.TclError:
                 print(f"Warning: TclError accessing item {iid} during Find All.")
            except Exception as e:
                 print(f"Error accessing item {iid} during Find All: {e}")

        if self.search_results:
            self.current_search_index = 0
            self._focus_search_result(self.current_search_index)
            self.status_label.config(text=f"Status: Found and highlighted {found_count} match(es) for '{term}'.")
        else:
            self.status_label.config(text=f"Status: No matches found for '{term}'.")

        self._update_search_replace_button_states()
        return "break" if event else None

    def _find_next(self, event=None):
        """Moves focus to the next search result."""
        if not self.search_results: return "break" if event else None
        self._destroy_edit_entry() # Ensure edit isn't active
        self.current_search_index = (self.current_search_index + 1) % len(self.search_results)
        self._focus_search_result(self.current_search_index)
        self.status_label.config(text=f"Status: Showing match {self.current_search_index + 1} of {len(self.search_results)} for '{self.search_term.get()}'.")
        return "break" if event else None

    def _find_previous(self, event=None):
        """Moves focus to the previous search result."""
        if not self.search_results: return "break" if event else None
        self._destroy_edit_entry() # Ensure edit isn't active
        self.current_search_index = (self.current_search_index - 1 + len(self.search_results)) % len(self.search_results)
        self._focus_search_result(self.current_search_index)
        self.status_label.config(text=f"Status: Showing match {self.current_search_index + 1} of {len(self.search_results)} for '{self.search_term.get()}'.")
        return "break" if event else None

    def _focus_search_result(self, index):
        """Scrolls to, selects, and highlights the search result at the given index."""
        if 0 <= index < len(self.search_results):
            iid = self.search_results[index]
            try:
                if self.tree.winfo_exists() and self.tree.exists(iid):
                    self.tree.see(iid)
                    self.tree.selection_set(iid) # Select the item

                    # If not find all, only highlight the current one
                    if not self._last_search_was_findall:
                        self._clear_search_highlight() # Clear previous single highlight
                        current_tags = list(self.tree.item(iid, "tags"))
                        if SEARCH_HIGHLIGHT_TAG not in current_tags:
                             self.tree.item(iid, tags=current_tags + [SEARCH_HIGHLIGHT_TAG])
            except tk.TclError:
                print(f"Warning: Could not focus search result - TclError for item {iid}.")
            except Exception as e:
                print(f"Error focusing search result {iid}: {e}")

    def _clear_search_highlight(self):
        """Removes the search highlight tag from all items that have it."""
        if not self.tree.winfo_exists(): return
        try:
            items_with_tag = self.tree.tag_has(SEARCH_HIGHLIGHT_TAG)
            for iid in items_with_tag:
                 try:
                     if not self.tree.exists(iid): continue
                     current_tags = list(self.tree.item(iid, "tags"))
                     if SEARCH_HIGHLIGHT_TAG in current_tags:
                         current_tags.remove(SEARCH_HIGHLIGHT_TAG)
                         self.tree.item(iid, tags=current_tags)
                 except tk.TclError: pass # Ignore if item vanished mid-operation
                 except Exception as e: print(f"Error clearing highlight tag for {iid}: {e}")
        except tk.TclError: pass # Ignore if tree is gone

    def _clear_search(self, event=None):
        """Clears search results, highlights, and resets state."""
        self._destroy_edit_entry() # Ensure edit isn't active
        self._clear_search_highlight()
        self.search_results = []
        self.current_search_index = -1
        self._last_search_was_findall = False
        self._update_search_replace_button_states()
        if self.tree.winfo_exists(): # Check if tree still exists
             try: self.tree.selection_set([]) # Clear selection
             except tk.TclError: pass # Ignore if tree is gone

        # Update status bar to reflect loaded state
        if self.file_data:
             item_count = len(self.item_id_map)
             loaded_file_count = len(self.file_data)
             self.status_label.config(text=f"Status: Loaded {loaded_file_count} files | {item_count} items.")
        else:
             if not self.input_folder.get():
                  self.status_label.config(text="Status: Select input folder.")
             else:
                  self.status_label.config(text="Status: Ready.")

    def _replace_current(self, event=None):
        """Replaces the currently selected search match."""
        self._destroy_edit_entry() # Ensure edit isn't active
        if not self.search_results or self.current_search_index < 0:
            messagebox.showinfo("Replace", "No active search result selected. Use Find first.", parent=self.root)
            return

        iid = self.search_results[self.current_search_index]
        search_term_val = self.search_term.get() # User types what they see (e.g., \\n for newline)
        replace_term_val = self.replace_term.get() # User types what they see

        if not search_term_val:
            messagebox.showwarning("Replace Error", "Search term is empty.", parent=self.root)
            return

        try:
            if not self.tree.winfo_exists() or not self.tree.exists(iid):
                 print(f"Warning: Item {iid} for replacement no longer exists.")
                 self._remove_result_and_advance(self.current_search_index)
                 return

            current_text_escaped = self.tree.set(iid, DIALOGUE_COLUMN_ID) # editor-escaped
            
            # For case-insensitive replacement, we need to find the match in the lowercased version
            # then apply the replacement to the original-cased (but editor-escaped) version.
            search_term_lower = search_term_val.lower()
            current_text_lower = current_text_escaped.lower()
            match_index = current_text_lower.find(search_term_lower)

            if match_index != -1:
                # Perform replacement on the editor-escaped string
                new_text_escaped = (current_text_escaped[:match_index] +
                                    replace_term_val +
                                    current_text_escaped[match_index + len(search_term_val):])

                # Update data, tree, and log undo (pass editor-escaped string)
                if self._update_tree_and_data(iid, new_text_escaped):
                    # Check if the replacement removed the term or if it still exists
                    if search_term_lower not in new_text_escaped.lower():
                        self._remove_result_and_advance(self.current_search_index)
                    else:
                         self.status_label.config(text=f"Status: Replaced. Item still contains term. Match {self.current_search_index + 1} of {len(self.search_results)}.")
                         self._focus_search_result(self.current_search_index)
                else:
                     print(f"Warning: Replacement failed for item {iid} due to update error.")
                     self.status_label.config(text=f"Status: Replace failed for current item.")
            else:
                 print(f"Warning: Search term '{search_term_val}' not found in selected item {iid} text '{current_text_escaped}'. Advancing.")
                 self._remove_result_and_advance(self.current_search_index, advance_only=True)

        except tk.TclError as e:
             print(f"Error during replace operation for {iid}: {e}")
             messagebox.showerror("Replace Error", f"A TclError occurred replacing text in item {iid}:\n{e}", parent=self.root)
        except Exception as e:
             print(f"Unexpected error during replace for {iid}: {e}")
             traceback.print_exc()
             messagebox.showerror("Replace Error", f"An unexpected error occurred:\n{e}", parent=self.root)
        finally:
            self._update_search_replace_button_states()

    def _remove_result_and_advance(self, index_to_remove, advance_only=False):
        """Helper to remove a result and navigate appropriately."""
        if not self.search_results: return

        iid_removed = None
        if not advance_only and 0 <= index_to_remove < len(self.search_results):
             # Remove the item from the results list
             iid_removed = self.search_results.pop(index_to_remove)
             # If Find All was used, remove the highlight from the removed item
             if self._last_search_was_findall and iid_removed:
                try:
                    if self.tree.winfo_exists() and self.tree.exists(iid_removed):
                        current_tags = list(self.tree.item(iid_removed, "tags"))
                        if SEARCH_HIGHLIGHT_TAG in current_tags:
                            current_tags.remove(SEARCH_HIGHLIGHT_TAG)
                            self.tree.item(iid_removed, tags=current_tags)
                except tk.TclError: pass # Ignore if item vanished

        # Check if results remain
        if not self.search_results:
            # No results left, clear search state
            self.current_search_index = -1
            self._clear_search_highlight() # Should be empty anyway, but be sure
            term = self.search_term.get()
            self.status_label.config(text=f"Status: Replaced last match for '{term}'. No more matches.")
        else:
            # Results remain, adjust index and focus
            # Ensure the index wraps around correctly after removal
            self.current_search_index = index_to_remove % len(self.search_results)
            self._focus_search_result(self.current_search_index)
            self.status_label.config(text=f"Status: Replaced match. {len(self.search_results)} remaining. Showing match {self.current_search_index + 1}.")

        self._update_search_replace_button_states()

    def _replace_all(self, event=None):
        """Replaces all occurrences in all currently found search results."""
        self._destroy_edit_entry()
        search_term_val = self.search_term.get() # Editor-escaped form
        replace_term_val = self.replace_term.get() # Editor-escaped form

        if not search_term_val:
            messagebox.showwarning("Replace Error", "Search term is empty.", parent=self.root)
            return
        if not self.search_results:
            messagebox.showinfo("Replace All", "No search results to replace. Use Find or Find All first.", parent=self.root)
            return

        items_to_process = list(self.search_results)
        confirm = messagebox.askyesno(
            "Confirm Replace All",
            f"Replace ALL occurrences of '{search_term_val}' with '{replace_term_val}'\n"
            f"in {len(items_to_process)} currently found item(s)?\n\n"
            "(This action can be undone as a single step.)",
            parent=self.root
        )
        if not confirm: return

        count = 0; errors = 0
        initial_states, final_states = {}, {}

        try:
            # Regex for replacement on editor-escaped strings
            # User types search_term_val as they see it (e.g. \\n for newline)
            # re.escape will ensure it's treated literally in regex context
            regex = re.compile(re.escape(search_term_val), re.IGNORECASE)
        except re.error as e:
             messagebox.showerror("Regex Error", f"Invalid search term for replacement: {e}", parent=self.root)
             return

        self.status_label.config(text="Status: Preparing Replace All...")
        self.root.update_idletasks()
        for iid in items_to_process:
             try:
                 if not self.tree.winfo_exists() or not self.tree.exists(iid) or iid not in self.item_id_map: continue
                 current_text_escaped = self.tree.set(iid, DIALOGUE_COLUMN_ID) # editor-escaped
                 new_text_escaped_preview = regex.sub(replace_term_val, current_text_escaped)
                 if new_text_escaped_preview != current_text_escaped:
                     initial_states[iid] = current_text_escaped
                     final_states[iid] = new_text_escaped_preview
             except tk.TclError: errors += 1; print(f"Warning: TclError pre-checking replace all for {iid}")
             except Exception as e: print(f"Error pre-checking item {iid}: {e}"); errors += 1

        if not initial_states:
             messagebox.showinfo("Replace All", "No occurrences found needing replacement in the current results.", parent=self.root)
             self._clear_search(); return

        self.status_label.config(text=f"Status: Performing Replace All on {len(initial_states)} items...")
        self.root.update_idletasks()

        restored_states_for_undo = {}
        for iid, new_text_escaped in final_states.items():
            original_text_escaped = initial_states.get(iid)
            if original_text_escaped is None: continue
            restored_states_for_undo[iid] = original_text_escaped
            if self._update_tree_and_data(iid, new_text_escaped, is_undo_redo=True): # Pass editor-escaped
                 count += 1
            else:
                 errors += 1
        
        if count > 0:
            self.undo_stack.append({'type': 'replace_all', 'initial_states': restored_states_for_undo, 'final_states': final_states})
            self.redo_stack.clear(); self._update_undo_redo_state()

        self._clear_search()
        status_msg = f"Status: Replace All finished. Replaced in {count} item(s)."
        info_msg = f"Replace All complete.\n\nReplaced text in {count} item(s)."
        if errors > 0:
             status_msg += f" Encountered {errors} error(s)."
             info_msg += f"\nEncountered {errors} error(s) during update (check console)."
             messagebox.showwarning("Replace All Complete with Issues", info_msg, parent=self.root)
        elif count > 0 :
             messagebox.showinfo("Replace All Complete", info_msg, parent=self.root)
        elif initial_states and count == 0:
             status_msg = f"Status: Replace All failed. Encountered {errors} error(s). No changes made."
             info_msg = f"Replace All failed.\n\nEncountered {errors} error(s). No changes were successfully made."
             messagebox.showerror("Replace All Failed", info_msg, parent=self.root)
        self.status_label.config(text=status_msg)


    # --- Undo/Redo Logic ---
    def _update_undo_redo_state(self):
        """Updates the state of Undo/Redo menu items and context menu items."""
        undo_state = tk.NORMAL if self.undo_stack else tk.DISABLED
        redo_state = tk.NORMAL if self.redo_stack else tk.DISABLED
        try:
            # Main Edit Menu
            if hasattr(self, 'edit_menu'):
                undo_menu_index = self.edit_menu.index("Undo")
                if undo_menu_index is not None and undo_menu_index != tk.NONE: self.edit_menu.entryconfigure(undo_menu_index, state=undo_state)
                redo_menu_index = self.edit_menu.index("Redo")
                if redo_menu_index is not None and redo_menu_index != tk.NONE: self.edit_menu.entryconfigure(redo_menu_index, state=redo_state)

            # Entry Context Menu
            if hasattr(self, 'entry_context_menu'):
                self.entry_context_menu.entryconfig("Undo", state=undo_state)
                self.entry_context_menu.entryconfig("Redo", state=redo_state)
        except (tk.TclError, AttributeError):
             pass # Ignore if menus aren't fully ready

    def _clear_undo_redo(self):
        """Clears the undo and redo stacks and updates menu states."""
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._update_undo_redo_state()

    def _undo_action(self, event=None):
        """Performs the Undo action."""
        if not self.undo_stack: return "break" if event else None
        self._destroy_edit_entry() # Ensure edit isn't active
        action = self.undo_stack.pop()
        action_type = action.get('type', 'single') # Default to single item edit
        success = True
        first_iid = None # To focus after undo/redo

        try:
            if action_type in ['replace_all', 'import_text']:
                # Compound action: Restore multiple initial states
                initial_states = action.get('initial_states', {}) # State BEFORE the original action (editor-escaped)
                final_states = action.get('final_states', {})     # State AFTER the original action (editor-escaped)
                if not initial_states: success = False; print("Error: Undo data missing initial states.")
                else:
                    affected_iids = list(initial_states.keys())
                    if affected_iids: first_iid = affected_iids[0]
                    restored_states_for_redo = {} # Track what we actually put back for redo
                    failed_iids = []
                    for iid, old_value_escaped in initial_states.items():
                        current_value_before_undo_escaped = final_states.get(iid, None)
                        if current_value_before_undo_escaped is None: print(f"Warning: Missing final state for {iid} in undo action.")
                        restored_states_for_redo[iid] = current_value_before_undo_escaped
                        if not self._update_tree_and_data(iid, old_value_escaped, is_undo_redo=True): # Pass editor-escaped
                            success = False; failed_iids.append(iid)
                    if initial_states:
                         self.redo_stack.append({'type': action_type, 'initial_states': initial_states, 'final_states': restored_states_for_redo})
                    if failed_iids: messagebox.showerror("Undo Error", f"Errors undoing {action_type} for: {', '.join(failed_iids)}.", parent=self.root)


            elif action_type == 'single' and 'iid' in action:
                # Single item edit
                iid = action['iid']; old_value_escaped = action['old_value']; new_value_escaped = action['new_value']
                first_iid = iid
                if self._update_tree_and_data(iid, old_value_escaped, is_undo_redo=True): # Pass editor-escaped
                    self.redo_stack.append({'type': 'single', 'iid': iid, 'old_value': old_value_escaped, 'new_value': new_value_escaped})
                else:
                    success = False
                    messagebox.showerror("Undo Error", f"Could not undo change for item {iid}.", parent=self.root)
            else:
                print(f"Error: Unknown or invalid undo action type: {action}")
                success = False

        except Exception as e:
            print(f"Unexpected error during Undo: {e}"); traceback.print_exc()
            success = False
            self.redo_stack.clear() # Clear redo if unexpected error occurs

        self._update_undo_redo_state()
        if first_iid and self.tree.winfo_exists() and self.tree.exists(first_iid):
             try: self.tree.see(first_iid); self.tree.selection_set(first_iid)
             except tk.TclError: pass
        return "break" if event else None

    def _redo_action(self, event=None):
        """Performs the Redo action."""
        if not self.redo_stack: return "break" if event else None
        self._destroy_edit_entry()
        action = self.redo_stack.pop()
        action_type = action.get('type', 'single')
        success = True
        first_iid = None

        try:
            if action_type in ['replace_all', 'import_text']:
                initial_states_escaped = action.get('initial_states', {}) # State BEFORE original action (editor-escaped)
                final_states_escaped = action.get('final_states', {})     # State AFTER original action (editor-escaped)
                if not final_states_escaped: success = False; print("Error: Redo data missing final states.")
                else:
                    affected_iids = list(final_states_escaped.keys())
                    if affected_iids: first_iid = affected_iids[0]
                    restored_states_for_undo = {}
                    failed_iids = []
                    for iid, new_value_escaped in final_states_escaped.items():
                         current_value_before_redo_escaped = initial_states_escaped.get(iid, None)
                         if current_value_before_redo_escaped is None: print(f"Warning: Missing initial state for {iid} in redo action.")
                         restored_states_for_undo[iid] = current_value_before_redo_escaped
                         if not self._update_tree_and_data(iid, new_value_escaped, is_undo_redo=True): # Pass editor-escaped
                             success = False; failed_iids.append(iid)
                    if final_states_escaped:
                         self.undo_stack.append({'type': action_type, 'initial_states': restored_states_for_undo, 'final_states': final_states_escaped})
                    if failed_iids: messagebox.showerror("Redo Error", f"Errors redoing {action_type} for: {', '.join(failed_iids)}.", parent=self.root)

            elif action_type == 'single' and 'iid' in action:
                iid = action['iid']; old_value_escaped = action['old_value']; new_value_escaped = action['new_value']
                first_iid = iid
                if self._update_tree_and_data(iid, new_value_escaped, is_undo_redo=True): # Pass editor-escaped
                    self.undo_stack.append({'type': 'single', 'iid': iid, 'old_value': old_value_escaped, 'new_value': new_value_escaped})
                else:
                    success = False
                    messagebox.showerror("Redo Error", f"Could not redo change for item {iid}.", parent=self.root)
            else:
                print(f"Error: Unknown or invalid redo action type: {action}")
                success = False

        except Exception as e:
            print(f"Unexpected error during Redo: {e}"); traceback.print_exc()
            success = False
            self.undo_stack.clear()

        self._update_undo_redo_state()
        if first_iid and self.tree.winfo_exists() and self.tree.exists(first_iid):
             try: self.tree.see(first_iid); self.tree.selection_set(first_iid)
             except tk.TclError: pass
        return "break" if event else None


    # --- Entry Context Menu ---
    def _show_entry_context_menu(self, event):
        """Displays the context menu for Entry widgets (Search, Replace, Tree Edit)."""
        widget = event.widget
        if not isinstance(widget, (ttk.Entry, tk.Entry)): return # Handle both tk and ttk Entry

        # Apply theme colors
        colors = THEMES.get(self.current_theme.get(), THEMES["Red/Dark"])
        bg = colors.get("entry_context_bg", colors["menu_bg"])
        fg = colors.get("entry_context_fg", colors["menu_fg"])
        active_bg = colors.get("entry_context_active_bg", colors["menu_active_bg"])
        active_fg = colors.get("entry_context_active_fg", colors["menu_active_fg"])
        try: self.entry_context_menu.config(bg=bg, fg=fg, activebackground=active_bg, activeforeground=active_fg)
        except tk.TclError as e: print(f"Warning: Could not apply theme to entry context menu: {e}")

        # Enable/Disable based on selection/clipboard/undo state
        can_cut_copy = False
        try:
            if widget.selection_present(): can_cut_copy = True
        except tk.TclError: pass # Widget might not support selection_present

        can_paste = False
        try:
            clipboard_content = self.root.clipboard_get()
            if isinstance(clipboard_content, str) and clipboard_content: can_paste = True
        except tk.TclError: can_paste = False # Clipboard empty or inaccessible

        # Check if the widget supports standard events (most do)
        is_editable = widget.cget("state") != tk.DISABLED and widget.cget("state") != 'readonly'

        # Use general undo/redo state, not widget-specific
        undo_state = tk.NORMAL if self.undo_stack else tk.DISABLED
        redo_state = tk.NORMAL if self.redo_stack else tk.DISABLED

        self.entry_context_menu.entryconfig("Undo", state=undo_state)
        self.entry_context_menu.entryconfig("Redo", state=redo_state)
        self.entry_context_menu.entryconfig("Cut", state=tk.NORMAL if can_cut_copy and is_editable else tk.DISABLED)
        self.entry_context_menu.entryconfig("Copy", state=tk.NORMAL if can_cut_copy else tk.DISABLED)
        self.entry_context_menu.entryconfig("Paste", state=tk.NORMAL if can_paste and is_editable else tk.DISABLED)

        # Popup the menu
        self.entry_context_menu.tk_popup(event.x_root, event.y_root)

    def _entry_action(self, widget, action):
        """Performs standard clipboard actions (Cut, Copy, Paste) on the given widget."""
        if widget and isinstance(widget, (ttk.Entry, tk.Entry)):
            try:
                # Generate standard Tk events
                widget.event_generate(f'<<{action}>>')
            except tk.TclError as e:
                print(f"Error performing entry action '{action}': {e}")

    # --- Treeview Context Menu & Copy/Cut/Paste Logic ---
    def _show_tree_context_menu(self, event):
        """Shows the context menu for the Treeview."""
        iid_under_cursor = self.tree.identify_row(event.y)

        # If editing, save edit before showing menu if cursor moved off edited item
        if self.edit_entry and iid_under_cursor != self.edit_item_id:
             if self.edit_item_id and self.tree.exists(self.edit_item_id):
                 self._save_edit(self.edit_item_id, DIALOGUE_COLUMN_ID)
             else:
                 self._destroy_edit_entry()

        if not iid_under_cursor: return # Clicked outside rows

        # Select the row under the cursor for context
        if self.tree.winfo_exists(): self.tree.selection_set(iid_under_cursor)

        # Check if it's an actual data row (vs header/separator)
        is_data_row = iid_under_cursor in self.item_id_map

        # Check if paste is possible
        can_paste = False
        if is_data_row:
            try:
                clipboard_content = self.root.clipboard_get()
                if isinstance(clipboard_content, str): can_paste = True # Text in clipboard allows paste
            except tk.TclError: can_paste = False # Clipboard empty or invalid

        # Apply theme colors
        colors = THEMES.get(self.current_theme.get(), THEMES["Red/Dark"])
        try: self.tree_context_menu.config(bg=colors["menu_bg"], fg=colors["menu_fg"], activebackground=colors["menu_active_bg"], activeforeground=colors["menu_active_fg"])
        except tk.TclError as e: print(f"Warning: Could not apply theme to tree context menu: {e}")

        # Enable/Disable menu items
        self.tree_context_menu.entryconfig("Copy", state=tk.NORMAL if is_data_row else tk.DISABLED)
        self.tree_context_menu.entryconfig("Cut", state=tk.NORMAL if is_data_row else tk.DISABLED)
        self.tree_context_menu.entryconfig("Paste", state=tk.NORMAL if can_paste else tk.DISABLED) # Paste enabled only if data row & clipboard has text

        # Show the menu
        self.tree_context_menu.post(event.x_root, event.y_root)

    def _copy_selection(self, event=None):
        """Copies the text from the selected Treeview row(s)."""
        if not self.tree.winfo_exists(): return "break" if event else None
        selected_items = self.tree.selection()
        if not selected_items: return "break" if event else None
        iid = selected_items[0] # Copy first selected item only

        if iid in self.item_id_map: # Check if it's a data row
            try:
                if self.tree.exists(iid):
                    dialogue_text_escaped = self.tree.set(iid, DIALOGUE_COLUMN_ID) # editor-escaped
                    self.root.clipboard_clear()
                    self.root.clipboard_append(dialogue_text_escaped) # Copy editor-escaped version
                else: print(f"Warning: Could not copy from non-existent item {iid}.")
            except tk.TclError as e: print(f"Warning: TclError during copy for item {iid}: {e}")
            except Exception as e: print(f"Error during copy for {iid}: {e}"); messagebox.showerror("Copy Error", f"Could not copy text:\n{e}", parent=self.root)
        else:
            print(f"Info: Cannot copy from non-data row {iid}")
        return "break" if event else None # Prevent default binding if applicable

    def _cut_selection(self, event=None):
        """Copies the text from the selected row and clears it."""
        if not self.tree.winfo_exists(): return "break" if event else None
        selected_items = self.tree.selection()
        if not selected_items: return "break" if event else None
        iid = selected_items[0] # Cut first selected item only

        if iid in self.item_id_map: # Check if it's a data row
            try:
                if not self.tree.exists(iid): return "break" if event else None
                dialogue_text_escaped = self.tree.set(iid, DIALOGUE_COLUMN_ID) # editor-escaped
                # Copy to clipboard first
                self.root.clipboard_clear()
                self.root.clipboard_append(dialogue_text_escaped) # Copy editor-escaped version
                # Then clear the text in the tree/data (logs undo)
                if not self._update_tree_and_data(iid, ""): # "" is valid editor-escaped empty string
                     print(f"Warning: Cut failed for {iid} because update failed. Clearing clipboard.")
                     self.root.clipboard_clear() # Clear clipboard if update failed
            except tk.TclError as e: print(f"Warning: TclError during cut for item {iid}: {e}"); self.root.clipboard_clear()
            except Exception as e: print(f"Error during cut for {iid}: {e}"); messagebox.showerror("Cut Error", f"Could not cut text:\n{e}", parent=self.root); self.root.clipboard_clear()
        else:
            print(f"Info: Cannot cut non-data row {iid}")
        return "break" if event else None # Prevent default binding if applicable

    def _paste_selection(self, event=None):
        """Pastes text from the clipboard into the selected Treeview dialogue cell."""
        if not self.tree.winfo_exists(): return "break" if event else None
        selected_items = self.tree.selection()
        if not selected_items: return "break" if event else None
        iid = selected_items[0] # Paste into first selected item only

        if iid in self.item_id_map: # Check if it's a data row
            try:
                clipboard_text_escaped = self.root.clipboard_get() # Assume clipboard has editor-escaped text
                if not isinstance(clipboard_text_escaped, str):
                    raise TypeError("Clipboard does not contain text.")
                if not self.tree.exists(iid):
                    print(f"Warning: Cannot paste into non-existent item {iid}")
                    return "break" if event else None
                # Update the tree/data with clipboard content (assumed editor-escaped)
                self._update_tree_and_data(iid, clipboard_text_escaped)
            except tk.TclError:
                messagebox.showwarning("Paste Error", "Clipboard is empty or cannot be accessed.", parent=self.root)
            except TypeError as e:
                messagebox.showwarning("Paste Error", str(e), parent=self.root)
            except Exception as e:
                print(f"Error during paste for {iid}: {e}"); traceback.print_exc()
                messagebox.showerror("Paste Error", f"Could not paste text:\n{e}", parent=self.root)
        else:
            print(f"Info: Cannot paste into non-data row {iid}")
        return "break" if event else None # Prevent default binding if applicable


    # --- Saving Logic ---
    def save_all_files(self):
        """Saves ALL successfully processed files to the output folder."""
        output_dir = self.output_folder.get()
        input_dir = self.input_folder.get()

        if not output_dir or not input_dir:
            messagebox.showerror("Save Error", "Input and Output folders must be selected.", parent=self.root)
            return
        if not self.file_data:
             messagebox.showinfo("Save", "No data loaded to save.", parent=self.root)
             return

        p_output_dir = pathlib.Path(output_dir)
        try:
            p_output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Save Error", f"Output folder path is invalid or could not be created:\n{p_output_dir}\nError: {e}", parent=self.root)
            return

        if self.edit_entry:
            if self.edit_item_id and self.tree.exists(self.edit_item_id):
                self._save_edit(self.edit_item_id, DIALOGUE_COLUMN_ID)
            else:
                self._destroy_edit_entry()

        self.status_label.config(text="Status: Preparing to save...")
        self.root.update_idletasks()

        saved_count = 0; error_files = set(); something_saved_successfully = False
        files_to_process = len(self.file_data)

        try:
            for file_index, entry in enumerate(self.file_data):
                current_file_path = entry.get('path')
                file_format = entry.get('format')
                original_json_content = entry.get("json_content")

                if not current_file_path or file_format == FORMAT_UNKNOWN or not isinstance(original_json_content, list):
                     print(f"Error: Invalid data for file index {file_index} (Path: {current_file_path}, Format: {file_format}, ContentType: {type(original_json_content)}). Skipping save.")
                     error_files.add(f"File Index {file_index} (Invalid Data)"); continue

                current_file_path_name = current_file_path.name
                self.status_label.config(text=f"Status: Processing {file_index+1}/{files_to_process}: {current_file_path_name}")
                self.root.update_idletasks()

                try:
                    json_content_to_save = [item.copy() if isinstance(item, (dict, list)) else item for item in original_json_content]
                except Exception as copy_e:
                    print(f"Error: Failed to copy content for {current_file_path_name}: {copy_e}. Skipping save.")
                    error_files.add(f"{current_file_path_name} (Copy Error)"); continue

                for string_info in entry.get("en_strings", []):
                    pending_save_string_raw = None # This will store the raw string for JSON

                    if file_format == FORMAT_DLGE:
                        original_item_index = string_info.get("original_item_index")
                        segments = string_info.get("segments", [])
                        if not (isinstance(original_item_index, int) and 0 <= original_item_index < len(json_content_to_save)):
                            print(f"Error: Invalid original item index {original_item_index} for DLGE {current_file_path_name}.")
                            error_files.add(f"{current_file_path_name} (DLGE Bad Index)"); continue
                        target_item = json_content_to_save[original_item_index]
                        if not isinstance(target_item, dict) or "String" not in target_item:
                            print(f"Warning: Structure mismatch at DLGE index {original_item_index} in {current_file_path_name}. Skipping item.")
                            error_files.add(f"{current_file_path_name} (DLGE Struct Mismatch)"); continue

                        reconstructed_parts_raw = []
                        valid_segments = True
                        for segment in segments:
                            if not isinstance(segment, dict) or "text" not in segment:
                                print(f"Error: Invalid segment format DLGE index {original_item_index} in {current_file_path_name}."); error_files.add(f"{current_file_path_name} (Bad Segment)"); valid_segments = False; break
                            prefix = segment.get("original_prefix", "") or ""
                            editor_segment_text = segment["text"] # This is editor-escaped
                            raw_segment_text_for_json = custom_unescape_from_editor(editor_segment_text)
                            reconstructed_parts_raw.append(prefix + raw_segment_text_for_json)
                        if not valid_segments: continue
                        
                        final_reconstructed_string_raw = "".join(reconstructed_parts_raw)
                        target_item["String"] = final_reconstructed_string_raw
                        pending_save_string_raw = final_reconstructed_string_raw

                    elif file_format == FORMAT_LOCR:
                        lang_block_idx = string_info.get("original_lang_block_index")
                        string_item_list_idx = string_info.get("original_string_item_index")
                        string_hash = string_info.get("string_hash")
                        editor_text = string_info.get("text") # This is editor-escaped

                        if not (isinstance(lang_block_idx, int) and 0 <= lang_block_idx < len(json_content_to_save) and
                                isinstance(json_content_to_save[lang_block_idx], list) and
                                isinstance(string_item_list_idx, int) and 0 <= string_item_list_idx < len(json_content_to_save[lang_block_idx])):
                            print(f"Error: Invalid indices ({lang_block_idx}, {string_item_list_idx}) for LOCR {current_file_path_name}.")
                            error_files.add(f"{current_file_path_name} (LOCR Bad Index)"); continue

                        target_dict = json_content_to_save[lang_block_idx][string_item_list_idx]
                        if not (isinstance(target_dict, dict) and "String" in target_dict and target_dict.get("StringHash") == string_hash):
                            print(f"Warning: Structure or hash mismatch at LOCR index [{lang_block_idx}][{string_item_list_idx}] in {current_file_path_name}.")
                            error_files.add(f"{current_file_path_name} (LOCR Mismatch)"); continue
                        
                        raw_text_for_json = custom_unescape_from_editor(editor_text)
                        target_dict["String"] = raw_text_for_json
                        pending_save_string_raw = raw_text_for_json
                    
                    if pending_save_string_raw is not None:
                         string_info["_pending_save_value_raw"] = pending_save_string_raw # Store raw for baseline

                output_path = p_output_dir / current_file_path_name
                try:
                    with open(output_path, 'w', encoding='utf-8') as f:
                         json.dump(json_content_to_save, f, indent=4, ensure_ascii=False)
                    saved_count += 1
                    something_saved_successfully = True

                    for string_info in entry.get("en_strings", []):
                        if "_pending_save_value_raw" in string_info:
                            raw_saved_value = string_info["_pending_save_value_raw"]
                            if file_format == FORMAT_DLGE:
                                string_info["original_string"] = raw_saved_value # Update baseline with raw
                            elif file_format == FORMAT_LOCR:
                                string_info["original_text"] = raw_saved_value # Update baseline with raw
                            del string_info["_pending_save_value_raw"]

                except (IOError, TypeError) as e:
                    print(f"Error writing file {output_path}: {e}")
                    messagebox.showerror("Save Error", f"Failed to save {output_path.name}:\n{e}", parent=self.root)
                    error_files.add(f"{current_file_path_name} (Write Error)")
                    for string_info in entry.get("en_strings", []):
                        if "_pending_save_value_raw" in string_info: del string_info["_pending_save_value_raw"]
                except Exception as e:
                    print(f"Unexpected error writing file {output_path}: {e}")
                    traceback.print_exc()
                    messagebox.showerror("Save Error", f"Unexpected error saving {output_path.name}:\n{e}", parent=self.root)
                    error_files.add(f"{current_file_path_name} (Unexpected Write Error)")
                    for string_info in entry.get("en_strings", []):
                        if "_pending_save_value_raw" in string_info: del string_info["_pending_save_value_raw"]

            final_status_text = f"Status: Save complete. Saved: {saved_count}/{files_to_process}, Errors: {len(error_files)}."
            self.status_label.config(text=final_status_text)
            result_message = f"Processed {files_to_process} file(s).\nSaved {saved_count} file(s) to:\n{output_dir}"
            if error_files:
                error_list_str = "\n - ".join(sorted(list(error_files)))
                messagebox.showwarning("Save Complete with Issues", f"{result_message}\n\nEncountered issues saving or processing {len(error_files)} file(s):\n - {error_list_str}\n(Check console log)", parent=self.root)
            else:
                 messagebox.showinfo("Save Successful", result_message, parent=self.root)

            if something_saved_successfully:
                self._clear_undo_redo()
                print("Undo/Redo history cleared after successful save.")

        except Exception as e:
            messagebox.showerror("Critical Save Error", f"A critical error occurred during the saving process: {e}", parent=self.root)
            self.status_label.config(text=f"Status: Critical error during save - {e}")
            print(f"Saving Process Error: {e}"); traceback.print_exc()


    # --- Text Export/Import ---
    def _export_dialogue(self):
        """Exports text from the treeview to a TSV file. Text is editor-escaped."""
        if not self.file_data or not self.item_id_map:
             messagebox.showwarning("Export Error", "No data loaded to export.", parent=self.root)
             return

        input_path = pathlib.Path(self.input_folder.get())
        default_filename = f"{input_path.name}_export.tsv" if input_path.name else "dialogue_export.tsv"
        initial_dir = self.output_folder.get() or self.input_folder.get() or str(pathlib.Path.home())
        export_path = filedialog.asksaveasfilename(
            title="Export Text As", initialdir=initial_dir, initialfile=default_filename,
            defaultextension=".tsv", filetypes=[("Tab Separated Values", "*.tsv"), ("All Files", "*.*")],
            parent=self.root
        )
        if not export_path: return

        exported_count = 0; errors = 0
        try:
            with open(export_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
                writer.writerow(['# TreeItemID', 'DialogueText'])
                f.write(f'# ExportedFromAppVersion: {APP_VERSION}\n')
                f.write(f'# SourceInputFolder: {self.input_folder.get()}\n')
                f.write(f'# Note: DialogueText is in editor-escaped format (e.g., \\n for newline).\n')


                all_iids_in_order = []
                if self.tree.winfo_exists(): all_iids_in_order = self.tree.get_children('')
                editable_iids = [iid for iid in all_iids_in_order if iid in self.item_id_map]

                for iid in editable_iids:
                    try:
                        if self.tree.exists(iid):
                            dialogue_text_escaped = self.tree.set(iid, DIALOGUE_COLUMN_ID) # editor-escaped
                            writer.writerow([iid, dialogue_text_escaped])
                            exported_count += 1
                        else: print(f"Warning: Skipping missing item {iid} during export."); errors += 1
                    except tk.TclError: print(f"Warning: TclError accessing item {iid} during export."); errors += 1
                    except Exception as item_e: print(f"Error exporting item {iid}: {item_e}"); errors += 1

            msg = f"Exported {exported_count} dialogue lines to:\n{export_path}"
            status = f"Status: Exported {exported_count} lines."
            if errors > 0:
                 msg += f"\n\nEncountered {errors} errors (see console)."
                 status += f" ({errors} errors)."
                 messagebox.showwarning("Export Complete with Issues", msg, parent=self.root)
            else:
                 messagebox.showinfo("Export Successful", msg, parent=self.root)
            self.status_label.config(text=status)

        except (IOError, csv.Error) as e:
             messagebox.showerror("Export Error", f"Failed to write or format file:\n{export_path}\nError: {e}", parent=self.root)
             self.status_label.config(text="Status: Export failed.")
        except Exception as e:
             messagebox.showerror("Export Error", f"An unexpected error during export:\n{e}", parent=self.root)
             print(f"Export Error: {e}"); traceback.print_exc()
             self.status_label.config(text="Status: Export failed.")

    def _import_dialogue(self):
        """Imports text from a TSV file into the treeview. Expects editor-escaped text."""
        if not self.file_data or not self.item_id_map:
             messagebox.showwarning("Import Error", "Load data first before importing.", parent=self.root)
             return

        initial_dir = self.output_folder.get() or self.input_folder.get() or str(pathlib.Path.home())
        import_path = filedialog.askopenfilename(
            title="Import Text From", initialdir=initial_dir,
            filetypes=[("Tab Separated Values", "*.tsv"), ("Text Files", "*.txt"), ("All Files", "*.*")],
            parent=self.root
        )
        if not import_path: return

        imported_lines = []
        source_folder_in_file = None
        app_version_in_file = None
        status_final = "Status: Import finished or cancelled."

        try:
            with open(import_path, 'r', newline='', encoding='utf-8') as f:
                lines_to_parse = []
                for line in f:
                    stripped_line = line.strip()
                    if stripped_line.startswith('# SourceInputFolder:'): source_folder_in_file = stripped_line.split(':', 1)[1].strip()
                    elif stripped_line.startswith('# ExportedFromAppVersion:'): app_version_in_file = stripped_line.split(':', 1)[1].strip()
                    elif stripped_line.startswith('#'): continue
                    elif stripped_line: lines_to_parse.append(line)

                if not lines_to_parse:
                    messagebox.showwarning("Import Warning", "No data lines found in file (excluding comments and blank lines).", parent=self.root)
                    return

                reader = csv.reader(lines_to_parse, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
                invalid_rows = 0

                for i, row in enumerate(reader):
                    if i == 0 and len(row) >= 2 and row[0].strip().lower() == '#treeitemid' and row[1].strip().lower() == 'dialoguetext':
                        continue 

                    if len(row) >= 2:
                        iid = row[0].strip()
                        text_escaped = row[1] # Assumed to be editor-escaped
                        if iid:
                            imported_lines.append({'iid': iid, 'text': text_escaped})
                        else:
                            print(f"Warning: Skipping row {i+1} (after comments) due to missing IID: {row}")
                            invalid_rows += 1
                    else:
                        print(f"Warning: Skipping invalid data row {i+1} (after comments): {row}")
                        invalid_rows += 1

            if not imported_lines:
                msg = "No valid data rows parsed."
                if invalid_rows > 0: msg += f" Skipped {invalid_rows} invalid row(s)."
                messagebox.showwarning("Import Warning", msg, parent=self.root)
                return

            confirm_msg_parts = [f"Found {len(imported_lines)} lines with valid IIDs to import from:\n{pathlib.Path(import_path).name}"]
            if invalid_rows > 0: confirm_msg_parts.append(f"(Skipped {invalid_rows} invalid rows)")
            if app_version_in_file and app_version_in_file != APP_VERSION:
                confirm_msg_parts.append(f"\nWARNING: File exported from v{app_version_in_file}, current is v{APP_VERSION}.")
            if source_folder_in_file:
                 current_input = self.input_folder.get()
                 try:
                    norm_file_source = str(pathlib.Path(source_folder_in_file).resolve())
                    norm_current_input = str(pathlib.Path(current_input).resolve()) if current_input else ""
                    is_win = platform.system() == "Windows"
                    if norm_current_input and (norm_file_source.lower() != norm_current_input.lower() if is_win else norm_file_source != norm_current_input):
                         confirm_msg_parts.append(f"\n\nWARNING: File's source folder mismatches current input folder!")
                         confirm_msg_parts.append(f"  File: {source_folder_in_file}")
                         confirm_msg_parts.append(f"  Current: {current_input}")
                 except Exception as path_e: print(f"Warning: Could not compare source folders: {path_e}")
            confirm_msg_parts.append(f"\n\nNote: Text from file is assumed to be in editor-escaped format (e.g., \\\\n for newline).")
            confirm_msg_parts.append(f"Overwrite current text in matching rows?\n(Can be undone as a single step)")
            confirm_msg = "\n".join(confirm_msg_parts)

            if not messagebox.askyesno("Confirm Import", confirm_msg, parent=self.root): return

            self.status_label.config(text="Status: Importing..."); self.root.update_idletasks()
            updated_count, skipped_count, error_count = 0, 0, 0
            initial_states, final_states = {}, {}
            valid_iids_in_tree = set(self.item_id_map.keys())

            for item in imported_lines:
                iid = item['iid']; new_text_escaped = item['text'] # editor-escaped from file
                if iid in valid_iids_in_tree:
                    try:
                        if not self.tree.exists(iid): skipped_count += 1; continue
                        current_text_escaped = self.tree.set(iid, DIALOGUE_COLUMN_ID) # editor-escaped
                        if current_text_escaped != new_text_escaped:
                            initial_states[iid] = current_text_escaped
                            final_states[iid] = new_text_escaped
                        else:
                            skipped_count += 1
                    except tk.TclError: print(f"Warning: TclError getting initial state for {iid}."); skipped_count += 1; error_count += 1
                    except Exception as e: print(f"Error getting initial state for {iid}: {e}"); skipped_count += 1; error_count += 1
                else:
                    skipped_count += 1

            if not final_states:
                 messagebox.showinfo("Import Info", f"No matching items found needing updates.\nSkipped/Not Found: {skipped_count}", parent=self.root)
                 status_final = f"Status: Import complete. No changes. Skipped: {skipped_count}";
                 self.status_label.config(text=status_final); return

            self.status_label.config(text=f"Status: Applying {len(final_states)} updates..."); self.root.update_idletasks()
            restored_states_for_undo = {}
            for iid, text_to_import_escaped in final_states.items():
                 current_text_before_update_escaped = initial_states.get(iid, "[ERROR: Unknown initial state]")
                 restored_states_for_undo[iid] = current_text_before_update_escaped
                 if self._update_tree_and_data(iid, text_to_import_escaped, is_undo_redo=True): # Pass editor-escaped
                     updated_count += 1
                 else:
                     error_count += 1; print(f"Error importing data for item {iid}.")
            
            if updated_count > 0:
                self.undo_stack.append({'type': 'import_text', 'initial_states': restored_states_for_undo, 'final_states': final_states})
                self.redo_stack.clear(); self._update_undo_redo_state()

            result_msg = f"Import Complete.\n\nUpdated: {updated_count}\nSkipped/Not Found: {skipped_count}\nErrors: {error_count}"
            status_final = f"Status: Import complete. Updated: {updated_count}, Skipped: {skipped_count}, Errors: {error_count}"
            if error_count > 0:
                 messagebox.showwarning("Import Complete with Errors", result_msg + "\nCheck console.", parent=self.root)
            else:
                 messagebox.showinfo("Import Complete", result_msg, parent=self.root)

        except FileNotFoundError:
            messagebox.showerror("Import Error", f"File not found:\n{import_path}", parent=self.root)
            status_final = "Status: Import failed (File not found)."
        except (IOError, csv.Error) as e:
            messagebox.showerror("Import Error", f"Failed to read or parse TSV file:\n{import_path}\nError: {e}", parent=self.root)
            status_final = "Status: Import failed (Read/Parse Error)."
        except Exception as e:
            messagebox.showerror("Import Error", f"An unexpected error occurred during import:\n{e}", parent=self.root)
            print(f"Import Error: {e}"); traceback.print_exc()
            status_final = "Status: Import failed (Unexpected Error)."
        finally:
            self.status_label.config(text=status_final); self.root.update_idletasks()

    # --- Help / About Dialogs ---
    def _show_about(self):
        """Displays the About dialog."""
        messagebox.showinfo("About HITMAN JSON Editor",
                            f"HITMAN JSON Editor v{APP_VERSION}\n\n"
                            "Tool for viewing, editing, and saving text within "
                            "HITMAN JSON language files (DLGE and LOCR formats).\n\n"
                            "Features:\n"
                            "- Loads 'en' strings from DLGE (with segments) and LOCR.\n"
                            "- Direct text editing, Search/Replace (Case-Insensitive).\n"
                            "- Multi-level Undo/Redo.\n"
                            "- Export/Import text via TSV (preserves mapping).\n"
                            "- Copy/Cut/Paste.\n"
                            "- Open original file / folders.\n"
                            "- Selectable Themes (Light/Dark/Red-Dark).\n"
                            "- Remembers state (folders, theme, search, window size).\n"
                            "- Displays newlines (\\n), tabs (\\t) etc. as literals in editor.\n\n" # Added note
                            "Developed by: MrGamesKingPro\n"
                            "GitHub: https://github.com/MrGamesKingPro\n",
                            parent=self.root)

    def _show_help(self):
         """Displays the Help/Instructions dialog."""
         messagebox.showinfo("Help / Instructions",
                            "Basic Usage:\n\n"
                            "1. Folders:\n"
                            "   - Select Input: Folder containing original JSON files (.DLGE, .LOCR).\n"
                            "   - Select Output: Folder where modified files will be saved.\n"
                            "   - Input/Output cannot be the same folder.\n"
                            "   - Use 'Open' buttons to view selected folders.\n\n"
                            "2. Loading:\n"
                            "   - Files load automatically when Input Folder is selected.\n"
                            "   - Only 'en' language strings are loaded for editing.\n"
                            "   - Files with unrecognized formats are skipped.\n\n"
                            "3. Viewing Data:\n"
                            "   - Treeview shows items grouped by file.\n"
                            "   - Columns: Line/ID, Timecode/Hash, Text (Editable).\n"
                            "   - Double-click grey file header to open the original file.\n"
                            "   - Note: Special characters like newlines (\\n), tabs (\\t), and literal backslashes (\\\\) are shown as these visible codes in the Text column.\n\n" # Added note
                            "4. Editing:\n"
                            "   - Double-click a cell in the 'Text' column.\n"
                            "   - Edit the text, using \\n for newlines, \\t for tabs, \\\\ for a literal backslash, etc.\n"
                            "   - Press Enter/Return to save the edit.\n"
                            "   - Press Escape to cancel the edit.\n"
                            "   - Clicking outside the edit box also saves (unless Escape was pressed).\n\n"
                            "5. Search & Replace:\n"
                            "   - Enter text in 'Search Text' field. To search for a newline, type \\n. For a literal backslash, type \\\\.\n"
                            "   - Find: Jumps to the next match sequentially.\n"
                            "   - Find All: Highlights all matches.\n"
                            "   - Next/Previous: Navigate between matches.\n"
                            "   - Replace: Replaces the currently selected match.\n"
                            "   - Replace All: Replaces all currently found matches (confirm first).\n"
                            "   - Search is case-insensitive.\n\n"
                            "6. Clipboard:\n"
                            "   - Use Edit menu, context menu (right-click), or shortcuts:\n"
                            "     - " + self._get_accelerator("C") + " (Copy)\n"
                            "     - " + self._get_accelerator("X") + " (Cut)\n"
                            "     - " + self._get_accelerator("V") + " (Paste)\n"
                            "   - Works on selected 'Text' cell in the tree or within text entry fields. Copied/pasted text is in the editor-escaped format.\n\n"
                            "7. Undo/Redo:\n"
                            "   - Use Edit menu, context menu, or shortcuts:\n"
                            "     - " + self._get_accelerator("Z") + " (Undo)\n"
                            "     - " + self._get_redo_accelerator() + " (Redo)\n"
                            "   - Applies to edits, cut, paste, replace, replace all, import.\n\n"
                            "8. Export/Import (File Menu):\n"
                            "   - Export: Saves current text to a TSV file. Text is in editor-escaped format.\n"
                            "   - Import: Loads text from a TSV file, matching based on internal ID. Expects editor-escaped text.\n"
                            "   - Useful for external editing (e.g., spreadsheets).\n\n"
                            "9. Save All Changes:\n"
                            "   - Use File menu, button, or shortcut (" + self._get_accelerator("S") + ").\n"
                            "   - Saves all files to the Output folder, converting editor-escaped text back to JSON standard strings.\n"
                            "   - Updates the internal 'baseline' for comparison.\n"
                            "   - Clears Undo/Redo history after successful save.\n\n"
                            "10. Theme: Change via View > Theme menu.\n\n"
                            "11. State Saving: Folders, theme, search terms, window size/position are saved automatically on exit.",
                            parent=self.root
                           )

    def _get_version(self):
        """Extracts version from the APP_VERSION constant."""
        return APP_VERSION


if __name__ == "__main__":
    root = tk.Tk()
    app = JsonEditorApp(root)
    root.mainloop()
