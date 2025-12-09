import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from brkraw import __version__, load
from .scan_list import ScanList
from .scan_info import ScanInfo
from .subj_info import SubjInfo
from .scan_info_search import ScanInfoSearch
from .previewer import Previewer
from .config import win_pre_width as _width, win_pre_height as _height
from .config import win_pst_width, win_pst_height
from .config import window_posx, window_posy

class MainWindow(tk.Tk):
  

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self._raw = None
        self._ignore_slope = False
        self._ignore_offset = False
        self._scan_id = None
        self._reco_id = None
        self._output = None
        self._path = '' # Added for robust initial state
        self.title('BrkRaw GUI - v{}'.format(__version__))

        # --- Instance variables for ScanInfo widgets ---
        # Tab 1: Summary of the currently selected scan
        self._scan_info_summary = None 
        # Tab 2: The new keyword search widget
        self._scan_info_search = None 
        # ---------------------------------------------
        
        # --- Dataset Selector Dropdown Variables ---
        self._dataset_var = tk.StringVar(self)
        self._available_datasets = []
        self._dataset_selector = None # To hold the OptionMenu widget
        self._dataset_label = None # To hold the Label widget
        # ----------------------------------------

        # initiated windows size and location
        self.geometry('{}x{}+{}+{}'.format(_width, _height,
                                             window_posx, window_posy))
        # minimal size
        self.minsize(_width, _height)

        self._init_layout()


    def open_filediag(self):
        self._path = filedialog.askopenfilename(
            initialdir = ".",
            title = "Select file",
            filetypes = (("Zip compressed", "*.zip"),
                         ("Paravision 6 format", "*.PVdatasets"),
                         ))
        self._extend_layout()
        self._load_dataset()



    def open_dirdiag(self):
        # Open directory dialog (User selects the root folder, e.g., 'C:/Data')
        self._path = filedialog.askdirectory(
            initialdir = ".",
            title = "Select Root Directory")
            
        # If a path is selected, find the available dataset folders and show the dropdown
        if self._path:
            self._update_dataset_dropdown()
    
    
    def _update_dataset_dropdown(self):
        import os
        
        # 1. Clean up
        self._close() 
        if self._dataset_selector:
            self._dataset_selector.destroy()
            self._dataset_selector = None
        if self._dataset_label:
            self._dataset_label.destroy()
            self._dataset_label = None

        # Reset the lists/mappings
        self._available_datasets = []
        self._dataset_paths = {} # Stores {folder_name: full_path} mapping
        
        # 2. Traverse subfolders and find valid datasets
        try:
            # os.walk is necessary to look inside subdirectories recursively
            for dirpath, dirnames, filenames in os.walk(self._path):
                # Check if the 'subject' file exists in the current directory
                if "subject" in filenames:
                    dataset_path = dirpath
                    folder_name = os.path.basename(dirpath) # The name of the dataset folder itself
                    
                    # Store the folder name for the dropdown and map it to its full path
                    self._available_datasets.append(folder_name)
                    self._dataset_paths[folder_name] = dataset_path
                    print(f"Found dataset: '{folder_name}' at {dataset_path}")

            # Sort the dataset names for the dropdown
            self._available_datasets.sort()

        except Exception as e:
            print(f"ERROR: Could not traverse {self._path}: {e}")
            self._available_datasets = []
            self._dataset_paths = {}

        # 3. Create the dropdown if datasets are found
        if self._available_datasets:
            
            self._dataset_label = tk.Label(self, text="Select Dataset ({})".format(len(self._available_datasets))) 
            self._dataset_label.pack(
                side=tk.TOP, padx=20, pady=(10, 0))

            self._dataset_var.set(self._available_datasets[0]) # Set first dataset as default
            
            # Create the OptionMenu widget
            self._dataset_selector = tk.OptionMenu(
                self, 
                self._dataset_var, 
                *self._available_datasets,
                command=self._load_selected_dataset
            )
            self._dataset_selector.pack(
                side=tk.TOP, 
                fill=tk.X, 
                padx=20, 
                pady=(0, 10)
            )

            # Automatically load the first dataset found
            self._load_selected_dataset(self._available_datasets[0])
        else:
            print("INFO: No dataset folders containing a 'subject' file found.")
    


    def _load_selected_dataset(self, dataset_name):
        """
        Callback from the OptionMenu to load the dataset for the selected folder name.
        """
        full_path_to_dataset = self._dataset_paths.get(dataset_name)
        
        if not full_path_to_dataset:
            print(f"Error: Path for dataset '{dataset_name}' not found.")
            return

        # 1. Store the full dataset folder path
        self._path = full_path_to_dataset 

        # 2. Reset existing data widgets and data object without changing window geometry.
        self._reset_dynamic_widgets()
        
        # 3. Extend the layout (will expand the window only if it's still in the initial size)
        self._extend_layout()
        
        # 4. Load the dataset
        self._load_dataset()


    def _init_layout(self):
        # level 1
        self._subj_info   = SubjInfo(self)
        self._subj_info.pack(
            side=tk.TOP,    fill=tk.X, anchor=tk.CENTER)

        # Button binding
        self._subj_info._loadfile.config(command=self.open_filediag)
        self._subj_info._loaddir.config(command=self.open_dirdiag)



    def _close(self):
        """
        Closes the currently loaded dataset, destroys all dynamic widgets,
        and reverts the window size to the initial small dimensions.
        """
        if self._raw is not None:
            # 1. Restore initial window geometry (small size)
            self.geometry('{}x{}+{}+{}'.format(_width, _height,
                                                window_posx, window_posy))
            self.minsize(_width, _height)

            # 2. Destroy dynamic widgets and data object
            self._reset_dynamic_widgets()
    

   

    

    def _extend_layout(self):
        # Get the current geometry size (e.g., '300x200') by splitting off the position ('+x+y')
        current_geom_size = self.geometry().split('+')[0]
        # Define the expected initial small size
        initial_geom_size = '{}x{}'.format(_width, _height) # _width and _height are pre-load values

        if len(self._path) != 0:
            
            # --- IMPORTANT: Only expand/set minsize once on the FIRST load ---
            if current_geom_size == initial_geom_size:
                # 1. Expand the window geometry
                self.geometry('{}x{}+{}+{}'.format(win_pst_width, win_pst_height,
                                                     window_posx, window_posy))
                # 2. Set the expanded size as the new permanent MINIMUM size
                self.minsize(win_pst_width, win_pst_height)
            # -----------------------------------------------------------------
            
            # extend level 1 (Re-create extended widgets in SubjInfo)
            self._subj_info._extend_layout()
            self._subj_info._refresh.config(command=self._refresh)

            # Re-create main frame
            self._main_frame = tk.Frame(self)
            self._main_frame.pack(
                side=tk.BOTTOM, fill=tk.BOTH, expand=True)

            # level 2
            self._scan_list = ScanList(self._main_frame)
            view_frame = tk.Frame(self._main_frame)
            self._scan_list.pack(
                side=tk.LEFT, fill=tk.BOTH)
            view_frame.pack(
                side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            # Pack the Previewer next to the Notebook
            self._preview = Previewer(view_frame)
            self._preview.pack(
                side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            # level 3 - USE NOTEBOOK FOR TABBED LAYOUT
            
            # 1. Create the Notebook (Tabbed Container)
            info_notebook = ttk.Notebook(view_frame)
            info_notebook.pack(
                side=tk.LEFT, fill=tk.BOTH, padx=10, pady=10) # pack the notebook

            # --- TAB 1: Selected Scan Info (Summary) ---
            scan_info_summary_frame = tk.Frame(info_notebook)
            scan_info_summary_frame.pack(fill='both', expand=True)
            
            # Use ScanInfo for the Summary (renamed from self._scan_info)
            self._scan_info_summary = ScanInfo(scan_info_summary_frame)
            self._scan_info_summary.pack(fill=tk.BOTH, expand=True) 

            info_notebook.add(scan_info_summary_frame, text="Selected Scan Info")
            
            # --- TAB 2: Scan Info Search (Keywords Only) ---
            scan_info_search_frame = tk.Frame(info_notebook)
            scan_info_search_frame.pack(fill='both', expand=True)
            
            # Create the ScanInfoSearch widget
            # NOTE: You must uncomment 'from .scan_info_search import ScanInfoSearch' at the top.
            self._scan_info_search = ScanInfoSearch(scan_info_search_frame)
            self._scan_info_search.pack(fill=tk.BOTH, expand=True) 
            
            info_notebook.add(scan_info_search_frame, text="Scan Info Search")
            
            self._bind_scanlist()
            self._set_convert_button()
    
    def _refresh(self):
        self._reset_dynamic_widgets()
        self._extend_layout()
        self._load_dataset()

    
    def _load_dataset(self):
        # Use the path to the SPECIFIC dataset folder, which is set in _load_selected_dataset
        path_to_load = self._path
        
        # Check the length of the *full* path
        if len(path_to_load) != 0:
            # Assuming 'brkraw.load' can handle the directory path
            self._raw = load(path_to_load)
            self._init_update()


    def _reset_dynamic_widgets(self):
        """
        Clears and destroys the data-dependent widgets (scan lists, preview, etc.)
        that need to be rebuilt when a new dataset is loaded. Does NOT touch
        the window size or position.
        """
        if self._raw is not None:
            # 1. Clean up Subject Info's extended widgets
            # Wrap in try/except or check if attribute exists as they might not be created yet
            try:
                self._subj_info._clean_path()
                self._subj_info._main_frame.destroy()
                self._subj_info._path.destroy()
                self._subj_info._path_label.destroy()
                self._subj_info._refresh.destroy()
            except AttributeError:
                 # Widgets may not have been created yet, which is fine
                pass
            
            # 2. Clean up the main data display frame
            # This destroys ScanList, ScanInfo, and Previewer, as they are children of _main_frame.
            try:
                self._main_frame.destroy()
            except AttributeError:
                pass

            # 3. Clean up the underlying data object
            self._raw.close()
            self._raw = None
            
            # 4. Reset internal tracking variables
            self._scan_id = None
            self._reco_id = None
            self._output = None



    def _init_update(self):
        # take first image from dataset
        self._scan_id, recos = [v for i, v in enumerate(self._raw._avail.items()) if i == 0][0]

        self._reco_id = recos[0]
        # update subject info
        self._subj_info.load_data(self._raw)

        # update scan and reco listbox
        self._scan_list.load_data(self._raw)
        self._scan_list._update_recos(self._raw, self._scan_id)

        # Update Scan Info Summary (Tab 1) with the first image data
        self._scan_info_summary.load_data(self._raw, self._scan_id, self._reco_id)
        
        # FIX: Pass all required arguments (brkraw_obj, scan_id, reco_id)
        self._scan_info_search.load_data(self._raw, self._scan_id, self._reco_id)

        # update preview of first image (CRITICAL for initial image loading)
        self._preview.load_data(self._raw, self._scan_id, self._reco_id)


    def _bind_scanlist(self):
        self._scan_list._scanlist.bind('<<ListboxSelect>>', self._update_scanid)
        self._scan_list._recolist.bind('<<ListboxSelect>>', self._update_recoid)

    def _update_scanid(self, event):
        w = event.widget
        index = int(w.curselection()[0])
        self._scan_id = self._raw._pvobj.avail_scan_id[index]
        self._reco_id = self._raw._avail[self._scan_id][0]
        self._scan_list._update_recos(self._raw, self._scan_id)
        self._update_data()

    def _update_recoid(self, event):
        w = event.widget
        index = int(w.curselection()[0])
        self._reco_id = self._raw._avail[self._scan_id][index]
        self._update_data()



    def _update_data(self):

        # --------------------------------------------------------------------------
        
        # 2. Update scan info summary (Tab 1) - uses the object directly
        # The ScanInfo widget (Summary) can still use the Parameter object directly:
        self._scan_info_summary.load_data(self._raw, self._scan_id, self._reco_id)
        
        # 3. Update Scan Info Search (Tab 2) with the new scan/reco IDs
        self._scan_info_search.load_data(self._raw, self._scan_id, self._reco_id)
        
        # 4. update preview of selected image
        self._preview.load_data(self._raw, self._scan_id, self._reco_id)

    def _set_convert_button(self):
        self._scan_list._updt_bt.config(state=tk.NORMAL)
        self._scan_list._conv_bt.config(state=tk.NORMAL)
        self._scan_list._updt_bt.config(command=self._set_output)
        self._scan_list._conv_bt.config(command=self._save_as)

    def _set_output(self):
        self._output = filedialog.askdirectory(initialdir=self._output,
                                               title="Select Output Directory")

    def _save_as(self):
        try:
            date = self._raw.get_scan_time()['date'].strftime("%y%m%d")
        except Exception:
            date = ''
        pvobj = self._raw._pvobj
        acqp  = self._raw.get_acqp
        this_acqp = acqp(self._scan_id)
        scan_name = this_acqp.parameters['ACQ_scan_name']
        scan_name = scan_name.replace(' ','-')
        filename = '{}_{}_{}_{}_{}_{}_{}'.format(date,
                                              pvobj.subj_id,
                                              pvobj.session_id,
                                              pvobj.study_id,
                                              self._scan_id,
                                              self._reco_id,
                                              scan_name)
        if self._ignore_slope:
            slope = None
        else:
            slope = False
        if self._ignore_offset:
            offset = None
        else:
            offset = False
        self._raw.save_as(self._scan_id, self._reco_id, filename,
                          dir=self._output, slope=slope, offset=offset)
        method = self._raw._pvobj._method[self._scan_id].parameters['Method']
        import re
        if re.search('dti', method, re.IGNORECASE):
            self._raw.save_bdata(self._scan_id, filename)
        from tkinter import messagebox
        messagebox.showinfo(title='File conversion',
                            message='{}/{}.nii.gz has been converted'.format(self._output,
                                                                       filename))


if __name__ == '__main__':
    root = MainWindow()
    root.mainloop()
