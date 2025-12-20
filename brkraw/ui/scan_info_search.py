import tkinter as tk
from tkinter import messagebox
# Assuming 'font' is defined in .config and brkraw is available
from .config import font 
import re 

class ScanInfoSearch(tk.Frame):
    
    def __init__(self, *args, **kwargs):
        super(ScanInfoSearch, self).__init__(*args, **kwargs)
        
        # --- Internal Data Storage ---
        self._raw = None        # The brkraw object
        self._scan_id = None    # The selected Scan ID
        self._reco_id = None    # The selected Reco ID
        self._parameter_cache = None
        
        # Dictionary to map displayed keys to their actual values/full key names
        self._displayed_keys_map = {} 
        
        # --- Layout ---
        self.title = tk.Label(self, text='Scan Info Keyword Search', font=font) 
        self.title.pack(side=tk.TOP, fill=tk.X)
        
        # Frame for Search Input
        search_frame = tk.Frame(self)
        search_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=(5, 0))
        
        tk.Label(search_frame, text="Keyword:", font=font).pack(side=tk.LEFT)
        self._keyword_var = tk.StringVar(self)
        self._keyword_var.trace_add("write", self._perform_search)
        
        self._keyword_entry = tk.Entry(search_frame, textvariable=self._keyword_var, font=font)
        self._keyword_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self._keyword_entry.bind('<Return>', self._perform_search)
        
        self._search_button = tk.Button(search_frame, text="Search", command=self._perform_search, font=font)
        self._search_button.pack(side=tk.RIGHT)
        
        # --- Exclusion Input Frame ---
        exclude_frame = tk.Frame(self)
        exclude_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=(0, 5))
        
        tk.Label(exclude_frame, text="Drop Entries Containing Chars:", font=font).pack(side=tk.LEFT)
        
        self._exclude_var = tk.StringVar(self, value='$') 
        self._exclude_var.trace_add("write", self._perform_search)
        
        self._exclude_entry = tk.Entry(exclude_frame, textvariable=self._exclude_var, font=font)
        self._exclude_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # --- Frame for Listbox and Scrollbar ---
        list_frame = tk.Frame(self)
        list_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Listbox for suggested KEY NAMES
        self._key_listbox = tk.Listbox(list_frame, height=10, font=font)
        self._key_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar for Listbox
        list_scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self._key_listbox.yview)
        list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._key_listbox.config(yscrollcommand=list_scrollbar.set)
        
        # Bind the selection event to the handler
        self._key_listbox.bind('<<ListboxSelect>>', self._on_key_select)
        
        # --- Textbox for displaying the VALUE (below the Listbox) ---
        tk.Label(self, text="Value:", font=font).pack(side=tk.TOP, fill=tk.X, padx=5, pady=(0, 2))
        self.value_textbox = tk.Text(self, width=30, height=5)
        self.value_textbox.pack(side=tk.TOP, fill=tk.X, padx=5, pady=(0, 5))
        self.value_textbox.configure(font=font)
        self.value_textbox.config(state=tk.DISABLED)
        
        self._initial_message()

    def _initial_message(self):
        """Helper to set the initial message."""
        self._key_listbox.insert(tk.END, "Enter a keyword to search for parameters.")
        self._key_listbox.insert(tk.END, "Then click a parameter name to view its value below.")


    # --- Public Data Loading Method ---
    def load_data(self, brkraw_obj, scan_id, reco_id):
        """
        Receives the full brkraw object and the currently selected IDs.
        """
        self._raw = brkraw_obj
        self._scan_id = scan_id
        self._reco_id = reco_id
        
        # Invalidate the old parameter cache, forcing a reload on the next search
        self._parameter_cache = None
        
        # Update status message
        self._key_listbox.delete(0, tk.END)
        self.value_textbox.config(state=tk.NORMAL)
        self.value_textbox.delete('1.0', tk.END)
        
        scan_num = self._scan_id if self._scan_id is not None else '?'
        self._key_listbox.insert(tk.END, f"Parameters loaded for scan **{scan_num}**.")
        
        self.value_textbox.insert(tk.END, "Start typing a keyword to search.")
        self.value_textbox.config(state=tk.DISABLED)

        # Automatically re-run the search on the new parameter set if a keyword is already entered
        if self._keyword_var.get().strip():
            self._perform_search()

    # --- Internal Data Access Method ---
    def _get_current_parameters(self):
        """
        Retrieves the full parameter dictionary using the brkraw object and IDs, 
        using a simple caching mechanism.
        """
        if self._parameter_cache is not None:
            return self._parameter_cache
        
        if self._raw and self._scan_id is not None:
            try:
                # Access the data via the brkraw object
                visu_parameters = self._raw._get_visu_pars(self._scan_id, self._reco_id)._parameters
                reco_parameters = self._raw._get_reco_pars(self._scan_id, self._reco_id)._parameters
                acqp_parameters = self._raw.get_acqp(self._scan_id)._parameters
                method_parameters = self._raw.get_method(self._scan_id)._parameters

                # Merge all dictionaries
                parameters = visu_parameters | acqp_parameters | method_parameters |reco_parameters
                
                # Cache the results
                if isinstance(parameters, dict):
                    self._parameter_cache = parameters
                    return self._parameter_cache
                
            except Exception as e:
                print(f"Failed to retrieve parameters from brkraw object: {e}")
                messagebox.showerror("Data Error", "Failed to retrieve scan parameters.")
                
        return None
    
    # --- Handler for Listbox Key Selection ---
    def _on_key_select(self, event):
        """Displays the full value of the selected key in the value_textbox."""
        try:
            selection_index = self._key_listbox.curselection()
            if not selection_index:
                return
            
            selected_key = self._key_listbox.get(selection_index[0])
            value_to_display = self._displayed_keys_map.get(selected_key, "Value not found.")
            
            # Update the value textbox
            self.value_textbox.config(state=tk.NORMAL)
            self.value_textbox.delete('1.0', tk.END)
            self.value_textbox.insert(tk.END, str(value_to_display))
            self.value_textbox.config(state=tk.DISABLED)
            
        except Exception as e:
            print(f"Error during key selection: {e}")
            self.value_textbox.config(state=tk.NORMAL)
            self.value_textbox.delete('1.0', tk.END)
            self.value_textbox.insert(tk.END, "Error retrieving value.")
            self.value_textbox.config(state=tk.DISABLED)

    # --- Helper function for checking exclusion ---
    def _contains_excluded_char(self, text, exclude_chars):
        """Returns True if the text contains any of the characters in exclude_chars."""
        if not exclude_chars:
            return False
        # Create a regex pattern to match ANY of the characters
        pattern = '[' + re.escape(exclude_chars) + ']'
        return re.search(pattern, text) is not None

    # --- Search Logic ---
    def _perform_search(self, *args):
        """
        Performs the search whenever the keyword entry changes or the search button is pressed.
        """
        keyword = self._keyword_var.get().strip()
        exclude_chars = self._exclude_var.get()
        
        # Reset the Listbox and Value Textbox
        self._key_listbox.delete(0, tk.END)
        self.value_textbox.config(state=tk.NORMAL)
        self.value_textbox.delete('1.0', tk.END)
        self.value_textbox.config(state=tk.DISABLED)
        self._displayed_keys_map = {} # Reset the map for the new search results

        parameter_dict = self._get_current_parameters()
        
        if parameter_dict is None or not isinstance(parameter_dict, dict):
            self._key_listbox.insert(tk.END, "Error: Scan parameters are not loaded. Select a valid scan.")
            return

        all_keys = sorted(parameter_dict.keys())
        found_count = 0
        search_lower = keyword.lower()
        
        # --- Combined search and filtering logic ---
        for key in all_keys:
            value = parameter_dict[key]
            
            # 1. EXCLUSION CHECK (Drop keywords/values containing excluded chars)
            
            # Check key exclusion
            if self._contains_excluded_char(key, exclude_chars):
                continue

            # Check value exclusion
            is_value_excluded = False
            if isinstance(value, (str, int, float, list, tuple)):
                try:
                    value_str = str(value)
                    if self._contains_excluded_char(value_str, exclude_chars):
                        is_value_excluded = True
                except Exception:
                    pass
            
            if is_value_excluded:
                continue

            # 2. KEYWORD MATCH CHECK
            
            key_lower = key.lower()
            match_found = False

            # Match in Key
            if search_lower in key_lower:
                match_found = True
            
            # Match in Value (if keyword is not empty)
            elif keyword and isinstance(value, (str, int, float, list, tuple)):
                try:
                    value_str = str(value).lower()
                    if search_lower in value_str:
                        match_found = True
                except Exception:
                    pass
            
            # 3. If a match is found (or keyword is empty for full list)
            if match_found or not keyword:
                
                display_key = key
                
                # Store the key-value pair in the map
                self._displayed_keys_map[display_key] = value
                
                # Insert only the KEY name into the Listbox
                self._key_listbox.insert(tk.END, display_key)
                found_count += 1
        
        # --- Final Message ---
        self.value_textbox.config(state=tk.NORMAL)

        if not keyword:
             # Full list mode
            self.value_textbox.insert(tk.END, f"Found {found_count} parameters ({len(all_keys) - found_count} excluded). Select a key above to view its value.")
            
        elif found_count > 0:
            # Search results mode
            self.value_textbox.insert(tk.END, f"Found {found_count} match(es). Click a key above to view its value.")
        else:
            # No matches found
            self.value_textbox.insert(tk.END, f"No parameters or values found matching '{keyword}' after dropping entries containing '{exclude_chars}'.")

        self.value_textbox.config(state=tk.DISABLED)