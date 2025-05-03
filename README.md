
#  Requirements
[Download RPKG-Tool](https://github.com/glacier-modding/RPKG-Tool)

- Extract JSON files folder
- example folder chunk0.rpkg
- Inside the folder example :
-- 000AB9F9BA9C7D46.DLGE
-- 000AB9F9BA9C7D46.DLGE.JSON
-- 000AB9F9BA9C7D46.DLGE_00D3FBEF465BE5FB
-- 000ADEB2F0B41883.DLGE
-- 000ADEB2F0B41883.DLGE.JSON
-- 000ADEB2F0B41883.DLGE_003D26D42DCBF167
-- 000AF9BA9013F87F.DLGE


# HITMAN-III-JSON-Editor
This program is designed to help you view, search, and edit specific text content within a collection of JSON files, particularly those used in games like HITMAN III that follow a certain structure. It focuses on finding JSON objects containing "Language": "en" and allows editing the associated "String" value, especially when that string contains timecoded segments like //(start,end)\\text.

Download HITMAN-III-JSON-Editor

Or use a version Python

Install Libraries

pip install ttkbootstrap

# How to Use:


    Launch the Application: Run the Python script. A window titled "HITMAN III JSON Editor" will appear.

    Select Folders (Crucial First Step):

        Input Folder: Click the "Select Input Folder" button. Navigate to and choose the folder containing the .json files you want to examine or edit. The path will appear in the read-only box next to the button.

        Output Folder: Click the "Select Output Folder" button. Navigate to and choose a DIFFERENT folder where any modified files will be saved. Do not select the same folder as the input folder. This prevents accidentally overwriting your original files. The chosen path will appear in its box.

    Loading Data:

        Once you select a valid input folder, the application automatically scans it for .json files (ignoring .json.meta files).

        It reads each JSON file and looks for objects that have the key-value pair "Language": "en".

        For each "en" string found, it checks if the text contains segments marked like //(some_timecode)\\Actual Text.

        The data is then displayed in the main table (Treeview):

            Line #: Shows the approximate line number in the original source file where the "String": key was found for this entry (useful for reference, but might be inaccurate if the file structure is complex or comments interfere). It shows '??' if the line number couldn't be reliably determined.

            Timecode: Displays the //(timecode)\\ part if the string was segmented. If the string wasn't segmented, this column is empty.

            Text: Shows the actual text content following the timecode (or the entire string if no timecode segment was found). This is the column you can edit.

        File Headers: Each file containing editable "en" strings is separated by a grey header row (e.g., --- File: your_file_name.json (Double-click to open) ---). Double-clicking this header row will attempt to open the original .json file in your system's default text/JSON editor.

        Separators: Light grey lines separate the content of different files visually.

        Status Bar: The bottom bar provides feedback (e.g., "Status: Loading...", "Status: Loaded X files...", "Status: Saving...").

    Browsing and Editing:

        Scroll through the table to view the extracted text segments.

        To edit text: Double-click directly on a cell in the Text column. An editing box will appear over the cell.

        Type your changes in the box.

        Press Enter or Return to confirm and save the change within the application's memory (it's not saved to a file yet).

        Press Escape to cancel the edit without saving changes to that cell.

        Clicking outside the edit box will also attempt to save the change.

    Searching:

        Type the text you want to find into the "Search Text:" box at the top.

        Press Enter or click the Find button.

        Matching text segments will be highlighted (typically yellow or gold, depending on the theme).

        The status bar will indicate how many matches were found.

        Use the Next and Previous buttons to jump between highlighted matches.

        Clearing the search box (and pressing Enter or losing focus) or modifying the text will clear the highlights and search results. You can also press Ctrl+F (or Cmd+F on Mac) to focus the search box.

    Copy / Cut / Paste:

        You can copy, cut, or paste text from/to the editable "Text" cells:

            Right-Click: Right-click on a text cell (not a header or separator) to open a context menu with Copy, Cut, and Paste options. Paste is only enabled if the clipboard contains text.

            Edit Menu: Use the "Edit" menu in the main menu bar.

            Keyboard Shortcuts: Use standard shortcuts (Ctrl+C, Ctrl+X, Ctrl+V on Windows/Linux; Cmd+C, Cmd+X, Cmd+V on macOS).

    Saving Changes to Files:

        When you are ready to save your edits:

            Click the Save All Changes button in the bottom-right corner.

            Or, go to the File menu and select Save All Changes.

            Or, use the keyboard shortcut (Ctrl+S on Windows/Linux; Cmd+S on macOS).

        The application will:

            Go through all the files it originally loaded.

            For each file where you made at least one edit, it reconstructs the modified "String" values (rejoining prefixes and edited text).

            It saves a new version of the modified JSON file into your selected Output Folder.

            Files that were not edited will not be saved to the output folder.

        A message box will confirm success or report any errors encountered during saving. Check the console/terminal output for more detailed error messages if needed.

    Changing Themes:

        Go to the View menu -> Theme.

        Select "Light", "Dark", or "Red/Dark" to change the application's color scheme.

    Help and About:

        Use the Help menu for basic instructions ("Help" > "Instructions") or information about the application ("Help" > "About").

    Exiting:

        Close the window or use File > Exit. You will not be prompted to save unsaved changes automatically, so make sure to use "Save All Changes" before exiting if you want to keep your edits.
