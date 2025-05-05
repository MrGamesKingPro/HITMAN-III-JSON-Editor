
#  Requirements
[Download RPKG-Tool](https://github.com/glacier-modding/RPKG-Tool)

- Extract JSON files folder
- example folder chunk0.rpkg
- Inside the folder example :
- 000AB9F9BA9C7D46.DLGE.JSON
or
- 0000DB5028ADFA16.LOCR.JSON
or
- 0099F3A8C676439A.RTLV.JSON




[Download HITMAN-III-JSON-Editor](https://github.com/MrGamesKingPro/HITMAN-III-JSON-Editor/releases/tag/HITMAN-III-JSON-Editor)

Or use a version Python

# HITMAN-III-JSON-Editor

![h3](https://github.com/user-attachments/assets/08447e1a-764e-4d59-a482-89a656c5aa8b)


**Purpose:**

This program is designed to help you view, search, and edit specific text content within JSON files, particularly those structured like dialogue or subtitle files used in games (like Hitman). It focuses on finding JSON objects with `"Language": "en"` and then allows editing the text associated with the `"String"` key, especially handling text split into segments marked by timecodes like `//(start,end)\\`.

**How to Use:**

1.  **Launch the Application:** Run the Python script. The main window will appear.

2.  **Select Folders (Crucial First Step):**
    *   **Input Folder:** Click "Select Input Folder" (or go to `File -> Select Input Folder...`). Choose the directory that contains the original `.DLGE` or `.LOCR` JSON files you want to edit. The program will automatically scan this folder for compatible files and load the 'en' (English) text from them.
    *   **Output Folder:** Click "Select Output Folder" (or go to `File -> Select Output Folder...`). Choose the directory where the modified JSON files will be saved. **This folder MUST be different from the Input Folder.**

3.  **Viewing Data:**
    *   Once the input folder is selected, the treeview in the main part of the window will populate.
    *   Files are separated by headers (grey rows). You can double-click a file header row to attempt to open the original JSON file in your default system editor/viewer.
    *   Each editable text line is shown with:
        *   `Line / ID`: Original line number in the JSON (if detectable) or a unique ID like the hash for LOCR files.
        *   `Timecode / Hash`: The segment prefix (e.g., `//(start,end)\\`) for DLGE or the `StringHash` for LOCR.
        *   `Text`: The actual dialogue or string content (this is the column you edit).

4.  **Editing Text:**
    *   **Double-click** on a cell in the "Text" column for the line you want to change.
    *   An edit box will appear over the cell. Type your changes.
    *   Press **Enter/Return** to confirm the change.
    *   Press **Escape** to cancel the change.
    *   Clicking outside the edit box will also confirm the change (unless you pressed Escape).

5.  **Search and Replace:**
    *   Use the fields and buttons at the top:
        *   Enter your search term in "Search Text".
        *   Enter the replacement text in "Replace with".
        *   **Find:** Highlights the next occurrence sequentially.
        *   **Find All:** Highlights *all* occurrences in the loaded data.
        *   **Next/Previous:** Navigate between found matches when using "Find" or after "Find All".
        *   **Replace:** Replaces the currently highlighted match and moves to the next.
        *   **Replace All:** Replaces *all* currently found/highlighted matches (will ask for confirmation). Search is case-insensitive.

6.  **Undo/Redo:**
    *   Use the `Edit` menu or standard keyboard shortcuts (`Ctrl+Z`/`Cmd+Z` for Undo, `Ctrl+Y`/`Shift+Cmd+Z` for Redo) to undo or redo edits, cuts, pastes, replaces, and imports.

7.  **Export/Import Text (File Menu):**
    *   **Export Text...:** Saves the *currently displayed text* along with its internal identifier to a `.tsv` (Tab Separated Values) file. This is useful for bulk editing in spreadsheet software.
    *   **Import Text...:** Loads text from a previously exported `.tsv` file. It matches lines based on the identifier in the first column of the TSV and updates the text in the editor. It will warn you if the source folder mentioned in the file doesn't match the currently loaded folder.

8.  **Save All Changes (Crucial Last Step):**
    *   Click the "Save All Changes" button (bottom right), use the `File` menu, or press `Ctrl+S`/`Cmd+S`.
    *   This will write **all** the files that were loaded (incorporating any edits you made) to the **Output Folder** you selected earlier.
    *   It uses the original filenames. Any existing files in the output folder with the same names will be overwritten.
    *   **Important:** Saving successfully clears the Undo/Redo history.

9. **Other Features:**
    *   **Themes:** Change the look via `View -> Theme`. The selected theme is saved.
    *   **Open Folders:** Use the "Open" buttons next to the input/output paths to open them in your system's file explorer.
    *   **Configuration:** The application automatically saves your selected folders, theme, last search/replace terms, and window size/position to a file named `H-III-Config.ini` in the same directory where you run the script. It loads these settings on the next startup.
    *   **Help/About:** Provides basic instructions and version info (`Help` menu).

That covers the setup and main usage workflow! Remember to always select input and output folders first, and save your changes when done.

