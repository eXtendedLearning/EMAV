# EMAV - Experimental Modal Analysis Viewer
# Version: 0.2.1 (with UNV temp file fix)
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import scipy.io as sio
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pyuff
import traceback # Import for detailed error logging
import io
import tempfile
import os

class EMAVApp:
    """
    A GUI application for viewing, comparing, and analyzing data from .mat or .unv files
    containing experimental modal analysis records.
    """
    def __init__(self, root):
        """
        Initializes the main application window and its widgets.
        """
        self.root = root
        self.root.title("EMAV - v0.2.1")
        self.root.geometry("1200x800")

        # --- Member variables ---
        self.testlab_data = None
        self.reconstructed_data = None
        self.record_map = {}
        self.selected_record_iid = None
        self.current_testlab_filepath = ""
        self.file_type = None
        
        self.recon_x_data = None
        self.recon_y_data = None

        # --- Main layout ---
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(expand=True, fill=tk.BOTH)

        # Top frame for buttons and version
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        self.open_testlab_button = ttk.Button(top_frame, text="Load Testlab File (.unv, .mat)", command=self.load_testlab_file)
        self.open_testlab_button.pack(side=tk.LEFT, padx=(0,10))

        self.open_recon_button = ttk.Button(top_frame, text="Load Reconstructed FRF (.unv)", command=self.load_reconstructed_file)
        self.open_recon_button.pack(side=tk.LEFT)

        self.file_label = ttk.Label(top_frame, text="No file loaded.")
        self.file_label.pack(side=tk.LEFT, padx=10)

        self.version_label = ttk.Label(top_frame, text="v0.2.1")
        self.version_label.pack(side=tk.RIGHT)

        # Paned window for resizable left/right panes
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(expand=True, fill=tk.BOTH)

        # --- Left Pane: Treeview for records ---
        left_pane = ttk.Frame(paned_window, padding="5")
        paned_window.add(left_pane, weight=2) 

        tree_frame = ttk.Frame(left_pane)
        tree_frame.pack(expand=True, fill=tk.BOTH)

        self.tree = ttk.Treeview(tree_frame, columns=("info",), show="tree headings")
        self.tree.heading("#0", text="File / Record")
        self.tree.column("#0", width=200)
        self.tree.heading("info", text="Information")
        self.tree.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

        tree_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # --- Right Pane: Plots and controls ---
        right_pane = ttk.Frame(paned_window, padding="5")
        paned_window.add(right_pane, weight=5)
        right_pane.grid_rowconfigure(0, weight=4) # Reconstructed plot area
        right_pane.grid_rowconfigure(1, weight=0) # Reconstructed controls
        right_pane.grid_rowconfigure(2, weight=5) # Testlab plot area
        right_pane.grid_rowconfigure(3, weight=0) # Testlab controls
        right_pane.grid_columnconfigure(0, weight=1)

        # Reconstructed FRF Plot
        self.fig_recon = Figure(figsize=(7, 3), dpi=100)
        self.ax_recon = self.fig_recon.add_subplot(111)
        self.ax_recon.set_title("Reconstructed FRF (Linear Scale)")
        self.canvas_recon = FigureCanvasTkAgg(self.fig_recon, master=right_pane)
        self.canvas_recon_widget = self.canvas_recon.get_tk_widget()
        self.canvas_recon_widget.grid(row=0, column=0, sticky="nsew", pady=(0, 5))
        
        # --- Reconstructed Plot Controls ---
        recon_controls_frame = ttk.Frame(right_pane)
        recon_controls_frame.grid(row=1, column=0, sticky="ew", pady=5)
        
        self.recon_xmin_var = tk.StringVar()
        self.recon_xmax_var = tk.StringVar()
        self.recon_ymin_var = tk.StringVar()
        self.recon_ymax_var = tk.StringVar()

        ttk.Label(recon_controls_frame, text="X Min:").pack(side=tk.LEFT, padx=(0,2))
        self.recon_xmin_entry = ttk.Entry(recon_controls_frame, textvariable=self.recon_xmin_var, width=8, state=tk.DISABLED)
        self.recon_xmin_entry.pack(side=tk.LEFT)
        ttk.Label(recon_controls_frame, text="X Max:").pack(side=tk.LEFT, padx=(5,2))
        self.recon_xmax_entry = ttk.Entry(recon_controls_frame, textvariable=self.recon_xmax_var, width=8, state=tk.DISABLED)
        self.recon_xmax_entry.pack(side=tk.LEFT)
        
        ttk.Label(recon_controls_frame, text="Y Min:").pack(side=tk.LEFT, padx=(15,2))
        self.recon_ymin_entry = ttk.Entry(recon_controls_frame, textvariable=self.recon_ymin_var, width=8, state=tk.DISABLED)
        self.recon_ymin_entry.pack(side=tk.LEFT)
        ttk.Label(recon_controls_frame, text="Y Max:").pack(side=tk.LEFT, padx=(5,2))
        self.recon_ymax_entry = ttk.Entry(recon_controls_frame, textvariable=self.recon_ymax_var, width=8, state=tk.DISABLED)
        self.recon_ymax_entry.pack(side=tk.LEFT)
        
        self.apply_scale_button = ttk.Button(recon_controls_frame, text="Apply Scale", command=self.apply_recon_scale, state=tk.DISABLED)
        self.apply_scale_button.pack(side=tk.LEFT, padx=10)
        self.reset_scale_button = ttk.Button(recon_controls_frame, text="Reset Scale", command=self.reset_recon_scale, state=tk.DISABLED)
        self.reset_scale_button.pack(side=tk.LEFT)


        # Testlab FRF Plot
        self.fig_testlab = Figure(figsize=(7, 4), dpi=100)
        self.axes_testlab = self.fig_testlab.subplots(2, 1, sharex=True)
        self.fig_testlab.tight_layout(pad=3.0)
        self.canvas_testlab = FigureCanvasTkAgg(self.fig_testlab, master=right_pane)
        self.canvas_testlab_widget = self.canvas_testlab.get_tk_widget()
        self.canvas_testlab_widget.grid(row=2, column=0, sticky="nsew", pady=(10, 5))
        
        # Controls for Testlab plot
        controls_frame_testlab = ttk.Frame(right_pane)
        controls_frame_testlab.grid(row=3, column=0, sticky="ew", pady=(5,0))
        
        self.log_scale_var = tk.BooleanVar(value=True)
        self.log_scale_check = ttk.Checkbutton(controls_frame_testlab, text="Log Scale", variable=self.log_scale_var, command=self.update_testlab_plots)
        self.log_scale_check.pack(side=tk.LEFT)

        self.save_button = ttk.Button(controls_frame_testlab, text="Save Selected Testlab Record (as Linear UNV)", command=self.save_selected_record, state=tk.DISABLED)
        self.save_button.pack(side=tk.RIGHT)

    def reset_ui_testlab(self):
        """Clears the tree, testlab plot, and resets state variables."""
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.record_map.clear()
        for ax in self.axes_testlab:
            ax.clear()
        self.axes_testlab[0].set_title("Select a Testlab record to display")
        self.canvas_testlab.draw()
        self.save_button.config(state=tk.DISABLED)
        self.selected_record_iid = None
        self.file_type = None

    def load_testlab_file(self):
        """Opens a file dialog to select a .mat or .unv file and loads its contents into the tree."""
        filepath = filedialog.askopenfilename(
            title="Select Testlab data file",
            filetypes=(("Supported Files", "*.mat *.unv"), ("All files", "*.*"))
        )
        if not filepath: return

        self.reset_ui_testlab()
        self.current_testlab_filepath = filepath
        filename = filepath.split('/')[-1]
        self.file_label.config(text=f"Loading: {filename}...")
        self.root.update_idletasks() 

        try:
            print(f"--- Loading Testlab File: {filepath} ---")
            if filepath.lower().endswith('.mat'):
                self.file_type = 'mat'
                print("File type detected: .mat")
                self.testlab_data = sio.loadmat(filepath, struct_as_record=False, squeeze_me=True)
                print("Raw .mat data loaded.")
                self.populate_tree_mat()
            elif filepath.lower().endswith('.unv'):
                self.file_type = 'unv'
                print("File type detected: .unv")
                uff_file = pyuff.UFF(filepath)
                self.testlab_data = uff_file.read_sets()
                print(f"pyuff read_sets result type: {type(self.testlab_data)}")
                self.populate_tree_unv()
            else:
                raise ValueError("Unsupported file type.")
            
            self.file_label.config(text=f"Loaded: {filename}")
            print("--- File loading successful ---")

        except Exception as e:
            print("--- ERROR DETAILS (Testlab File) ---")
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Message: {e}")
            traceback.print_exc()
            print("---------------------------------")
            messagebox.showerror("Error", f"Failed to load Testlab file. See console for details.\n{e}")
            self.reset_ui_testlab()
            self.file_label.config(text="File loading failed.")
        
        self.canvas_testlab.draw()

    def load_reconstructed_file(self):
        """Loads a single reconstructed FRF .unv file into the top plot."""
        filepath = filedialog.askopenfilename(
            title="Select Reconstructed FRF file",
            filetypes=(("Universal files", "*.unv"), ("All files", "*.*"))
        )
        if not filepath: return
        
        temp_filepath = None
        try:
            print(f"--- Loading Reconstructed File: {filepath} ---")
            
            print("Pre-processing .unv file to remove dataset 151...")
            with open(filepath, 'r') as f:
                lines = f.readlines()
            
            output_lines = []
            i = 0
            in_151 = False
            while i < len(lines):
                line = lines[i].strip()
                if line == '151' and i > 0 and lines[i-1].strip() == '-1':
                    in_151 = True
                    print(f"Found and skipping dataset 151 starting at line {i+1}.")
                    i += 1 # Skip the 151 line
                    while i < len(lines):
                        if lines[i].strip() == '-1':
                            break
                        i += 1
                else:
                    output_lines.append(lines[i])
                i += 1

            filtered_content = "".join(output_lines)
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.unv', encoding='utf-8') as temp_f:
                temp_f.write(filtered_content)
                temp_filepath = temp_f.name
            print(f"Pre-processing complete. Wrote cleaned data to temp file: {temp_filepath}")

            uff_file = pyuff.UFF(temp_filepath)
            data = uff_file.read_sets()
            
            print(f"pyuff read_sets result type: {type(data)}")
            if isinstance(data, dict):
                print("Single dataset found, wrapping it in a list.")
                data = [data]
            
            if not data or not isinstance(data, list) or len(data) == 0:
                 raise ValueError("No valid data sets found in the file.")

            print("File contains one or more datasets. Processing the first one.")
            self.reconstructed_data = data[0]
            print("Successfully extracted first dataset.")
            
            self.recon_x_data = self.reconstructed_data['x']
            y_data_raw = self.reconstructed_data['data']
            print(f"Reconstructed Y-data shape: {y_data_raw.shape}")

            if y_data_raw.ndim == 2:
                print("Y-data is 2D, taking first column for amplitude.")
                self.recon_y_data = y_data_raw[:, 0]
            else:
                print("Y-data is 1D, using as is.")
                self.recon_y_data = y_data_raw

            self.plot_reconstructed(f"Reconstructed: {filepath.split('/')[-1]}")
            
            xmin, xmax = self.ax_recon.get_xlim()
            ymin, ymax = self.ax_recon.get_ylim()
            self.recon_xmin_var.set(f"{xmin:.2f}")
            self.recon_xmax_var.set(f"{xmax:.2f}")
            self.recon_ymin_var.set(f"{ymin:.2f}")
            self.recon_ymax_var.set(f"{ymax:.2f}")

            for widget in [self.recon_xmin_entry, self.recon_xmax_entry, self.recon_ymin_entry, self.recon_ymax_entry, self.apply_scale_button, self.reset_scale_button]:
                widget.config(state=tk.NORMAL)
                
            print("--- Reconstructed file loaded and plotted successfully ---")

        except Exception as e:
            print("--- ERROR DETAILS (Reconstructed File) ---")
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Message: {e}")
            traceback.print_exc()
            print("---------------------------------")
            messagebox.showerror("Error", f"Failed to load Reconstructed FRF file. See console for details.\n{e}")
        finally:
            if temp_filepath and os.path.exists(temp_filepath):
                print(f"Deleting temporary file: {temp_filepath}")
                os.remove(temp_filepath)


    def plot_reconstructed(self, title):
        """Helper to plot or re-plot the reconstructed data."""
        if self.recon_x_data is None or self.recon_y_data is None:
            return
            
        self.ax_recon.clear()
        self.ax_recon.plot(self.recon_x_data, self.recon_y_data)
        self.ax_recon.set_title(title)
        self.ax_recon.set_xlabel("Frequency (Hz)")
        self.ax_recon.set_ylabel("Amplitude")
        self.ax_recon.grid(True, linestyle='--')
        self.fig_recon.tight_layout()
        self.canvas_recon.draw()

    def apply_recon_scale(self):
        """Applies the manual axis limits from the entry boxes to the reconstructed plot."""
        try:
            xmin = float(self.recon_xmin_var.get())
            xmax = float(self.recon_xmax_var.get())
            ymin = float(self.recon_ymin_var.get())
            ymax = float(self.recon_ymax_var.get())
            
            self.ax_recon.set_xlim(xmin, xmax)
            self.ax_recon.set_ylim(ymin, ymax)
            self.canvas_recon.draw()
        except (ValueError, TypeError):
            messagebox.showerror("Input Error", "Please enter valid numbers for all axis limits.")

    def reset_recon_scale(self):
        """Resets the reconstructed plot to its default auto-scale."""
        if self.reconstructed_data:
            self.plot_reconstructed(self.ax_recon.get_title()) # Re-plot to auto-scale
            xmin, xmax = self.ax_recon.get_xlim()
            ymin, ymax = self.ax_recon.get_ylim()
            self.recon_xmin_var.set(f"{xmin:.2f}")
            self.recon_xmax_var.set(f"{xmax:.2f}")
            self.recon_ymin_var.set(f"{ymin:.2f}")
            self.recon_ymax_var.set(f"{ymax:.2f}")

    def populate_tree_mat(self):
        filename = self.current_testlab_filepath.split('/')[-1]
        file_node = self.tree.insert("", "end", text=filename, open=True)
        if not self.testlab_data: return
        for key, value in self.testlab_data.items():
            if key.startswith('__'): continue
            def process_record(record, iid, parent):
                if hasattr(record, 'Name') and hasattr(record, 'X_Data') and hasattr(record, 'Y_Data'):
                    record_name = getattr(record, 'Name', f'Record {iid}')
                    self.record_map[iid] = record
                    self.tree.insert(parent, "end", text=record_name, iid=iid)
                    return True
                return False
            if isinstance(value, np.ndarray) and value.dtype.kind == 'O':
                parent_node = self.tree.insert(file_node, "end", text=key, open=True)
                for i, record in enumerate(value):
                    process_record(record, f"{key}_{i}", parent_node)
            elif hasattr(value, '_fieldnames'):
                parent_node = file_node
                process_record(value, key, parent_node)

    def populate_tree_unv(self):
        filename = self.current_testlab_filepath.split('/')[-1]
        file_node = self.tree.insert("", "end", text=filename, open=True)
        type_nodes = {}
        
        data_to_process = self.testlab_data
        if isinstance(data_to_process, dict):
            data_to_process = [data_to_process]
            
        for i, dataset in enumerate(data_to_process):
            if dataset.get('type') == 58:
                node_key = 58
                node_text = "Functions (Type 58)"
                try:
                    record_name = f"Resp:{dataset.get('rsp_node',0)}:{dataset.get('rsp_dir',0)}/Ref:{dataset.get('ref_node',0)}:{dataset.get('ref_dir',0)}"
                except:
                    record_name = f"Record {i+1}"
                if node_key not in type_nodes:
                    type_nodes[node_key] = self.tree.insert(file_node, "end", text=node_text, open=True)
                iid = str(i)
                self.record_map[iid] = dataset
                self.tree.insert(type_nodes[node_key], "end", text=record_name, iid=iid)

    def on_tree_select(self, event=None):
        selected_iid = self.tree.focus()
        if not selected_iid or selected_iid not in self.record_map:
            self.save_button.config(state=tk.DISABLED)
            self.selected_record_iid = None
            return
        self.selected_record_iid = selected_iid
        self.update_testlab_plots()
        self.save_button.config(state=tk.NORMAL)
    
    def update_testlab_plots(self):
        if not self.selected_record_iid: return
            
        record = self.record_map[self.selected_record_iid]
        name = self.tree.item(self.selected_record_iid, 'text')
        
        for ax in self.axes_testlab: ax.clear()

        try:
            raw_y_data = None
            if self.file_type == 'mat':
                x_data = record.X_Data
                raw_y_data = record.Y_Data
                x_label = f"{getattr(record, 'X_Label', 'Freq')} ({getattr(record, 'X_Units', 'Hz')})"
            elif self.file_type == 'unv':
                x_data = record['x']
                raw_y_data = record['data']
                x_label = f"{record.get('xlabel', 'Abscissa')} ({record.get('xunits_description', '')})"

            is_complex = np.iscomplexobj(raw_y_data)
            is_unv_frf = (self.file_type == 'unv' and raw_y_data.ndim == 2 and raw_y_data.shape[1] >= 2)

            if is_complex or is_unv_frf:
                if is_unv_frf:
                    complex_y_data = raw_y_data[:, 0] + 1j * raw_y_data[:, 1]
                else:
                    complex_y_data = raw_y_data
                
                mag = np.abs(complex_y_data)
                phase = np.angle(complex_y_data, deg=True)
                self.plot_frf(x_data, mag, phase, name, x_label)
            else:
                self.plot_real(x_data, raw_y_data, name, x_label)

        except Exception as e:
            messagebox.showwarning("Plot Error", f"Could not plot selected record.\nDetails: {e}")
            for ax in self.axes_testlab: ax.clear()
            self.axes_testlab[0].set_title(f"Could not plot record: {name}")
            self.canvas_testlab.draw()
            self.save_button.config(state=tk.DISABLED)

    def plot_frf(self, x, mag, phase, name, xlabel):
        self.axes_testlab[0].set_visible(True)
        self.axes_testlab[1].set_visible(True)

        self.axes_testlab[0].plot(x, mag)
        self.axes_testlab[0].set_title(f"Testlab: {name}")
        self.axes_testlab[0].set_ylabel("Amplitude")
        
        if self.log_scale_var.get():
            self.axes_testlab[0].set_yscale('log')
            self.axes_testlab[0].set_ylim(1e-3, 1e2)
            self.axes_testlab[0].grid(True, which='both', linestyle='--')
        else:
            self.axes_testlab[0].set_yscale('linear')
            self.axes_testlab[0].grid(True, linestyle='--')

        self.axes_testlab[1].plot(x, phase)
        self.axes_testlab[1].set_ylabel("Phase (deg)")
        self.axes_testlab[1].set_xlabel(xlabel)
        self.axes_testlab[1].grid(True, linestyle='--')
        
        self.fig_testlab.tight_layout(h_pad=0.5)
        self.canvas_testlab.draw()

    def plot_real(self, x, y, name, xlabel):
        self.axes_testlab[0].set_visible(True)
        self.axes_testlab[1].set_visible(False)
        
        self.axes_testlab[0].plot(x, y)
        self.axes_testlab[0].set_title(f"Testlab: {name}")
        self.axes_testlab[0].set_ylabel("Value")
        self.axes_testlab[0].set_xlabel(xlabel)
        self.axes_testlab[0].set_yscale('linear')
        self.axes_testlab[0].grid(True, linestyle='--')
        
        self.fig_testlab.tight_layout()
        self.canvas_testlab.draw()

    def save_selected_record(self):
        if not self.selected_record_iid:
            messagebox.showwarning("Save Error", "No record selected.")
            return

        original_record = self.record_map.get(self.selected_record_iid)
        
        initial_filename = self.tree.item(self.selected_record_iid, 'text').replace(":","_").replace("/","-").strip()
        save_path = filedialog.asksaveasfilename(
            title="Save Transformed Record as .unv",
            defaultextension=".unv", filetypes=(("Universal files", "*.unv"),),
            initialfile=f"Linear_{initial_filename}.unv"
        )
        if not save_path: return

        try:
            if self.file_type == 'unv' and original_record.get('type') == 58:
                y_data_raw = original_record['data']
                
                # Ensure we have complex data to transform
                if y_data_raw.ndim == 2 and y_data_raw.shape[1] >= 2:
                    complex_y = y_data_raw[:, 0] + 1j * y_data_raw[:, 1]
                    linear_magnitude = np.abs(complex_y)

                    # Create a new dataset dictionary for saving
                    new_record = original_record.copy()
                    
                    # Reshape for saving as a 2-column array (value, 0)
                    save_data = np.zeros((len(linear_magnitude), 2))
                    save_data[:, 0] = linear_magnitude

                    new_record['data'] = save_data
                    new_record['data_type'] = 2  # Set to Real
                    new_record['z_def_type'] = 0 # No longer complex
                    new_record['num_values_per_point'] = 2
                    new_record['ylabel'] = 'AMPLITUDE' # Match reconstructed format
                    
                    uff_out = pyuff.UFF(save_path, 'w')
                    uff_out.write_sets(new_record)
                    messagebox.showinfo("Success", f"Successfully saved transformed record to:\n{save_path}")

                else: # Handle cases like PSD or Coherence
                     uff_out = pyuff.UFF(save_path, 'w')
                     uff_out.write_sets(original_record)
                     messagebox.showinfo("Success", f"Record was not a complex FRF. Saved original data to:\n{save_path}")

            elif self.file_type == 'mat':
                messagebox.showwarning("Not Implemented", "Saving transformed FRF from .mat is not yet supported. Please use .unv files for this feature.")

        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save to .unv file.\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = EMAVApp(root)
    root.mainloop()

