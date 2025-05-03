
#  Requirements
[Download RPKG-Tool](https://github.com/glacier-modding/RPKG-Tool)

- Extract JSON files folder
- example folder chunk0.rpkg
- Inside the folder example :
- 000AB9F9BA9C7D46.DLGE
- 000AB9F9BA9C7D46.DLGE.JSON
- 000AB9F9BA9C7D46.DLGE_00D3FBEF465BE5FB
- 000ADEB2F0B41883.DLGE
- 000ADEB2F0B41883.DLGE.JSON
- 000ADEB2F0B41883.DLGE_003D26D42DCBF167
- 000AF9BA9013F87F.DLGE


[Download HITMAN-III-JSON-Editor](https://github.com/MrGamesKingPro/HITMAN-III-JSON-Editor/releases/tag/HITMAN-III-JSON-Editor)

Or use a version Python

# HITMAN-III-JSON-Editor

**Purpose:**

This program is designed to help you view, search, and edit specific text content within JSON files, particularly those structured like dialogue or subtitle files used in games (like Hitman). It focuses on finding JSON objects with `"Language": "en"` and then allows editing the text associated with the `"String"` key, especially handling text split into segments marked by timecodes like `//(start,end)\\`.

**How to Use:**

1.  **Launch the Application:** Run the Python script. The main window will appear.

2.  **Select Folders (Crucial First Step):**
    *   **Input Folder:** Click the `Select Input Folder` button. Browse to and select the directory containing the `.json` files you want to examine or edit. The program will automatically scan this folder for compatible files once selected.
    *   **Output Folder:** Click the `Select Output Folder` button. Browse to and select a **different** folder where any modified files will be saved. **Important:** The output folder *must not* be the same as the input folder to prevent accidentally overwriting your original files.

3.  **Loading Data:**
    *   Once you select an input folder, the program automatically reads the `.json` files inside it (ignoring `.json.meta` files).
    *   It looks for JSON objects that contain `"Language": "en"`.
    *   For each found object, it takes the value associated with the `"String"` key.
    *   It uses a regular expression (`//(start,end)\\text`) to split the "String" value into segments based on timecode-like prefixes. If no such prefixes are found, the entire string is treated as one segment.
    *   The program populates the central table (Treeview) with this data.

4.  **Navigating the Data Table:**
    *   The main table displays the loaded data:
        *   **Line #:** Shows the approximate line number in the *original* JSON file where the `"String":` key was found for the corresponding English entry. This helps locate the original data if needed. (`??` means the line number couldn't be determined reliably).
        *   **Timecode:** Shows the `//(start,end)\\` prefix found before the text segment. This column will be empty if the string wasn't segmented this way.
        *   **Text:** Shows the actual text segment that you can edit.
    *   **File Headers:** Grey rows starting with `--- File:` act as separators between data from different files. Double-clicking a file header row will attempt to open the original `.json` file using your system's default application for JSON files.
    *   Use the vertical and horizontal scrollbars to view all the data if it doesn't fit in the window.

5.  **Editing Text:**
    *   Find the row containing the text segment you want to change.
    *   **Double-click** directly on the cell in the **Text** column for that row.
    *   An edit box will appear directly over the cell, containing the current text.
    *   Type your desired changes.
    *   Press **Enter** or **Return** on your keyboard to confirm and save the change (within the program's memory for now).
    *   Press the **Escape** key to cancel the edit and revert to the previous text.
    *   Clicking outside the edit box will also typically confirm the change (unless you pressed Escape just before).

6.  **Searching:**
    *   Type the text you want to find into the **Search Text** box at the top.
    *   Press **Enter** or click the `Find` button.
    *   The program searches (case-insensitively) within the **Text** column of all loaded segments.
    *   Matching rows will be highlighted (typically in yellow or another theme-appropriate color).
    *   The first match will be selected and scrolled into view.
    *   Use the `Next` and `Previous` buttons to jump between the highlighted matches.
    *   The status bar at the bottom will show how many matches were found.
    *   Clearing the search box (and pressing Enter or moving focus away) will remove the highlights and clear the search results. Shortcut: `Ctrl+F` (or `Cmd+F` on Mac) focuses the search box.

7.  **Copy / Cut / Paste:**
    *   These standard editing operations work on the **Text** column data.
    *   **Select a row** containing data (not a file header or separator).
    *   **Right-click** on the selected row to open the context menu and choose `Copy`, `Cut`, or `Paste`.
    *   Alternatively, use the **Edit** menu in the menu bar.
    *   Standard keyboard shortcuts also work:
        *   `Ctrl+C` (or `Cmd+C` on Mac) to Copy
        *   `Ctrl+X` (or `Cmd+X` on Mac) to Cut (copies the text and clears the cell)
        *   `Ctrl+V` (or `Cmd+V` on Mac) to Paste (replaces the selected cell's text with clipboard content)
    *   Paste is only enabled if the clipboard contains text and you have selected an editable data row.

8.  **Saving Changes:**
    *   After making edits, you need to save them to files.
    *   Click the `Save All Changes` button in the bottom-right corner, or go to `File` -> `Save All Changes` in the menu bar. The shortcut `Ctrl+S` (or `Cmd+S` on Mac) also works.
    *   **Important:** This action checks *all* the loaded data against the original files. For *each file where you made at least one edit*, it reconstructs the full JSON content with your changes and writes a *new* file with the *same name* into the **Output Folder** you selected earlier.
    *   Files that were not edited will *not* be copied or saved to the output folder.
    *   A message will confirm how many files were processed and saved. If errors occur during saving, they will usually be mentioned in a message box and/or printed to the console if you ran the script from one.
    *   The "Save" button and menu item are only enabled when both Input and Output folders are selected and data has been loaded.

9.  **Changing Themes:**
    *   Go to the `View` -> `Theme` menu.
    *   Select `Light`, `Dark`, or `Red/Dark` to change the application's color scheme.

10. **Help and About:**
    *   Use the `Help` menu for `Instructions` (a summary similar to this explanation) or `About` (version and credit information).

11. **Exiting:**
    *   Close the window or select `File` -> `Exit`.

This covers the main functionality. The core workflow is: select folders -> browse/search -> double-click to edit -> save all changes.
