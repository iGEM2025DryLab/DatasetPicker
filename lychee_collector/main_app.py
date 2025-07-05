"""
Main Application Module
Coordinates all components and provides the main GUI
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import cv2
import os
from datetime import datetime
from typing import Optional

from .core.camera_manager import CameraManager
from .core.data_manager import DataManager, SampleData
from .gui.camera_panel import CameraPanel
from .gui.data_entry_panel import DataEntryPanel


class LycheeDataCollectorApp:
    """Main application class"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Lychee Data Collection Interface")
        self.root.geometry("1600x1000")
        
        # Core managers
        self.camera_manager = CameraManager()
        self.data_manager = DataManager()
        
        # GUI components
        self.camera_panel = None
        self.data_panel = None
        
        # Current sample data
        self.current_sample = SampleData()
        self.rgb_image_data = None
        self.nir_image_data = None
        self.rgb_processing_settings = None
        self.nir_processing_settings = None
        
        # Status
        self.status_var = tk.StringVar()
        
        # Initialize
        self.setup_ui()
        self.setup_callbacks()
        self.new_sample()
    
    def setup_ui(self):
        """Setup the main user interface"""
        # Configure root grid
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # Left panel - Camera feeds
        self.camera_panel = CameraPanel(main_frame, self.camera_manager)
        self.camera_panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # Right panel - Data entry
        self.data_panel = DataEntryPanel(main_frame, self.data_manager.get_next_sample_id())
        self.data_panel.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Bottom panel - Controls
        self.create_control_panel(main_frame)
        
        # Status bar
        self.create_status_bar()
    
    def create_control_panel(self, parent):
        """Create control buttons panel"""
        control_frame = ttk.Frame(parent)
        control_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Control buttons
        ttk.Button(control_frame, text="Capture All", 
                  command=self.capture_all_images).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(control_frame, text="Save Sample", 
                  command=self.save_sample).grid(row=1, column=0, padx=(0, 5))
        ttk.Button(control_frame, text="New Sample", 
                  command=self.new_sample).grid(row=1, column=1, padx=5)
        ttk.Button(control_frame, text="Load Sample", 
                  command=self.load_sample).grid(row=1, column=2, padx=5)
        ttk.Button(control_frame, text="Delete Sample", 
                  command=self.delete_sample).grid(row=1, column=3, padx=5)
        ttk.Button(control_frame, text="Export Data", 
                  command=self.export_data).grid(row=1, column=4, padx=5)
        ttk.Button(control_frame, text="Statistics", 
                  command=self.show_statistics).grid(row=1, column=5, padx=5)
        
        # Camera detection refresh
        ttk.Button(control_frame, text="Refresh Cameras", 
                  command=self.refresh_cameras).grid(row=1, column=6, padx=(20, 0))
    
    def create_status_bar(self):
        """Create status bar"""
        status_frame = ttk.Frame(self.root)
        status_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        # Status label
        available_cameras = self.camera_manager.available_cameras
        initial_status = f"Ready - Available cameras: {available_cameras}"
        self.status_var.set(initial_status)
        
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        
        # Current sample indicator
        self.sample_indicator_var = tk.StringVar()
        sample_label = ttk.Label(status_frame, textvariable=self.sample_indicator_var, foreground='blue')
        sample_label.grid(row=0, column=1, sticky=tk.E, padx=10, pady=5)
        
        status_frame.columnconfigure(0, weight=1)
    
    def setup_callbacks(self):
        """Setup callbacks between components"""
        # Camera capture callbacks
        self.camera_panel.set_rgb_captured_callback(self.on_rgb_captured)
        self.camera_panel.set_nir_captured_callback(self.on_nir_captured)
        
        # Data change callback
        self.data_panel.set_data_changed_callback(self.on_data_changed)
    
    def on_rgb_captured(self, frame, processing_settings):
        """Handle RGB image capture"""
        self.rgb_image_data = frame.copy()
        self.rgb_processing_settings = processing_settings
        self.data_panel.update_image_status('rgb_image', True)
        self.status_var.set("RGB image captured")
        
        # Auto-save image
        self.save_rgb_image()
    
    def on_nir_captured(self, frame, processing_settings):
        """Handle NIR image capture"""
        self.nir_image_data = frame.copy()
        self.nir_processing_settings = processing_settings
        self.data_panel.update_image_status('nir_image', True)
        self.status_var.set("NIR image captured")
        
        # Auto-save image
        self.save_nir_image()
    
    def on_data_changed(self, sample_data: SampleData):
        """Handle data entry changes"""
        self.current_sample = sample_data
    
    def capture_all_images(self):
        """Capture both RGB and NIR images simultaneously"""
        # Check if cameras are connected
        rgb_connected = (self.camera_panel.rgb_panel and 
                        self.camera_panel.rgb_panel.camera_feed.is_connected)
        nir_connected = (self.camera_panel.nir_panel and 
                        self.camera_panel.nir_panel.camera_feed.is_connected)
        
        if not rgb_connected and not nir_connected:
            messagebox.showwarning("Warning", "No cameras are connected. Please connect at least one camera first.")
            return
        
        # Check if we have a valid sample ID
        if not self.current_sample.sample_id:
            messagebox.showwarning("Warning", "Please create a new sample first before capturing images.")
            return
        
        # Capture RGB image if connected
        if rgb_connected:
            self.camera_panel.rgb_panel.capture_image()
        
        # Capture NIR image if connected
        if nir_connected:
            self.camera_panel.nir_panel.capture_image()
        
        # Update status
        captured_images = []
        if rgb_connected:
            captured_images.append("RGB")
        if nir_connected:
            captured_images.append("NIR")
        
        images_str = " and ".join(captured_images)
        self.status_var.set(f"{images_str} images captured")
        
        # Show success message
        # messagebox.showinfo("Capture Complete", f"Successfully captured {images_str.lower()} images for sample {self.current_sample.sample_id}")
    
    def save_rgb_image(self):
        """Save RGB image to disk"""
        if self.rgb_image_data is not None and self.current_sample.sample_id:
            rgb_dir = self.data_manager.rgb_image_dir
            filename = f"{self.current_sample.sample_id}_rgb.jpg"
            filepath = os.path.join(rgb_dir, filename)
            
            cv2.imwrite(filepath, self.rgb_image_data)
            self.current_sample.rgb_image = filename
    
    def save_nir_image(self):
        """Save NIR image to disk"""
        if self.nir_image_data is not None and self.current_sample.sample_id:
            nir_dir = self.data_manager.nir_image_dir
            filename = f"{self.current_sample.sample_id}_nir.jpg"
            filepath = os.path.join(nir_dir, filename)
            
            cv2.imwrite(filepath, self.nir_image_data)
            self.current_sample.nir_image = filename
    
    def save_sample(self):
        """Save current sample"""
        # Validate form
        errors = self.data_panel.get_validation_errors()
        if errors:
            error_msg = "Please fix the following errors:\n\n" + "\n".join(f"• {error}" for error in errors)
            messagebox.showerror("Validation Error", error_msg)
            return
        
        # Check for missing images and warn user
        missing_images = []
        if self.rgb_image_data is None:
            missing_images.append("RGB image")
        if self.nir_image_data is None:
            missing_images.append("NIR image")
        
        if missing_images:
            missing_str = " and ".join(missing_images)
            result = messagebox.askyesno(
                "Missing Images", 
                f"Warning: {missing_str} not captured yet.\n\n"
                f"Do you want to save the sample without the {missing_str}?\n\n"
                f"You can capture the {missing_str} later and save again to update the sample.",
                icon='warning'
            )
            if not result:
                return
        
        # Get current sample data
        sample = self.data_panel.get_sample_data()
        
        # Add processing settings
        sample.rgb_processing_settings = self.rgb_processing_settings
        sample.nir_processing_settings = self.nir_processing_settings
        
        # Add image filenames
        if self.rgb_image_data is not None:
            sample.rgb_image = f"{sample.sample_id}_rgb.jpg"
        if self.nir_image_data is not None:
            sample.nir_image = f"{sample.sample_id}_nir.jpg"
        
        # Save images if not already saved
        if self.rgb_image_data is not None:
            self.save_rgb_image()
        if self.nir_image_data is not None:
            self.save_nir_image()
        
        # Save to database
        if self.data_manager.save_sample(sample):
            success_msg = f"Sample {sample.sample_id} saved successfully"
            if missing_images:
                success_msg += f"\n\nNote: Remember to capture the {' and '.join(missing_images)} later."
            self.status_var.set(f"Sample {sample.sample_id} saved successfully")
            # messagebox.showinfo("Success", success_msg)
        else:
            messagebox.showerror("Error", "Failed to save sample")
    
    def new_sample(self):
        """Start a new sample"""
        # Get next sample ID
        next_id = self.data_manager.get_next_sample_id()
        
        # Clear form
        self.data_panel.clear_form()
        self.data_panel.set_sample_id(next_id)
        
        # Reset sample data
        self.current_sample = SampleData(next_id)
        self.rgb_image_data = None
        self.nir_image_data = None
        self.rgb_processing_settings = None
        self.nir_processing_settings = None
        
        # Update indicators
        self.sample_indicator_var.set(f"Current: {next_id}")
        self.status_var.set("New sample ready")
    
    def load_sample(self):
        """Load an existing sample"""
        # Get all sample IDs
        sample_ids = self.data_manager.get_all_sample_ids()
        
        if not sample_ids:
            messagebox.showinfo("Info", "No samples found")
            return
        
        # Create selection dialog
        dialog = SampleSelectionDialog(self.root, sample_ids)
        selected_id = dialog.result
        
        if selected_id:
            sample = self.data_manager.load_sample(selected_id)
            if sample:
                self.data_panel.set_sample_data(sample)
                self.current_sample = sample
                
                # Load images if they exist
                self.load_sample_images(sample)
                
                self.sample_indicator_var.set(f"Current: {selected_id}")
                self.status_var.set(f"Sample {selected_id} loaded")
            else:
                messagebox.showerror("Error", f"Could not load sample {selected_id}")
    
    def load_sample_images(self, sample: SampleData):
        """Load sample images if they exist"""
        # Load RGB image
        if sample.rgb_image:
            rgb_path = os.path.join(self.data_manager.rgb_image_dir, sample.rgb_image)
            if os.path.exists(rgb_path):
                self.rgb_image_data = cv2.imread(rgb_path)
                self.data_panel.update_image_status('rgb_image', True)
        
        # Load NIR image
        if sample.nir_image:
            nir_path = os.path.join(self.data_manager.nir_image_dir, sample.nir_image)
            if os.path.exists(nir_path):
                self.nir_image_data = cv2.imread(nir_path)
                self.data_panel.update_image_status('nir_image', True)
        
        # Load processing settings
        self.rgb_processing_settings = sample.rgb_processing_settings
        self.nir_processing_settings = sample.nir_processing_settings
    
    def delete_sample(self):
        """Delete current sample"""
        if not self.current_sample.sample_id:
            messagebox.showwarning("Warning", "No sample selected")
            return
        
        # Confirm deletion
        result = messagebox.askyesno("Confirm Delete", 
                                   f"Are you sure you want to delete sample {self.current_sample.sample_id}?\n\n"
                                   "This will permanently delete the sample data and images.")
        
        if result:
            if self.data_manager.delete_sample(self.current_sample.sample_id):
                self.status_var.set(f"Sample {self.current_sample.sample_id} deleted")
                self.new_sample()  # Start fresh
            else:
                messagebox.showerror("Error", "Failed to delete sample")
    
    def export_data(self):
        """Export data to CSV"""
        export_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Data",
            initialvalue=f"lychee_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        if export_path:
            if self.data_manager.export_csv(export_path):
                messagebox.showinfo("Success", f"Data exported to {export_path}")
            else:
                messagebox.showerror("Error", "Failed to export data")
    
    def show_statistics(self):
        """Show dataset statistics"""
        stats = self.data_manager.get_statistics()
        
        if not stats:
            messagebox.showinfo("Statistics", "No data available")
            return
        
        # Create statistics dialog
        StatisticsDialog(self.root, stats)
    
    def refresh_cameras(self):
        """Refresh camera detection"""
        self.camera_manager.detect_cameras()
        available = self.camera_manager.available_cameras
        self.status_var.set(f"Cameras refreshed - Available: {available}")
    
    def on_closing(self):
        """Handle application closing"""
        # Cleanup cameras
        self.camera_panel.cleanup()
        
        # Close window
        self.root.destroy()


class SampleSelectionDialog:
    """Dialog for selecting a sample to load"""
    
    def __init__(self, parent, sample_ids):
        self.result = None
        
        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Select Sample")
        self.dialog.geometry("400x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Create widgets
        ttk.Label(self.dialog, text="Select a sample to load:").pack(pady=10)
        
        # Listbox with samples
        list_frame = ttk.Frame(self.dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.listbox = tk.Listbox(list_frame)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add samples to listbox
        for sample_id in reversed(sample_ids):  # Most recent first
            self.listbox.insert(0, sample_id)
        
        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Load", command=self.load_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.LEFT, padx=5)
        
        # Bind double-click
        self.listbox.bind('<Double-Button-1>', lambda e: self.load_selected())
        
        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        # Wait for result
        self.dialog.wait_window()
    
    def load_selected(self):
        """Load selected sample"""
        selection = self.listbox.curselection()
        if selection:
            self.result = self.listbox.get(selection[0])
            self.dialog.destroy()
    
    def cancel(self):
        """Cancel selection"""
        self.dialog.destroy()


class StatisticsDialog:
    """Dialog for displaying dataset statistics"""
    
    def __init__(self, parent, stats):
        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Dataset Statistics")
        self.dialog.geometry("500x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Create widgets
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Statistics text
        text_widget = tk.Text(main_frame, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Format and insert statistics
        stats_text = self.format_statistics(stats)
        text_widget.insert(tk.END, stats_text)
        text_widget.config(state=tk.DISABLED)
        
        # Close button
        ttk.Button(self.dialog, text="Close", command=self.dialog.destroy).pack(pady=10)
        
        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
    
    def format_statistics(self, stats):
        """Format statistics for display"""
        text = "LYCHEE DATASET STATISTICS\n"
        text += "=" * 50 + "\n\n"
        
        text += f"Total Samples: {stats.get('total_samples', 0)}\n"
        text += f"Complete Samples: {stats.get('complete_samples', 0)}\n\n"
        
        # Variations
        text += "Lychee Variations:\n"
        text += "-" * 20 + "\n"
        for variation, count in stats.get('variations', {}).items():
            text += f"  {variation}: {count} samples\n"
        text += "\n"
        
        # Days distribution
        text += "Days After Harvest Distribution:\n"
        text += "-" * 35 + "\n"
        for day, count in sorted(stats.get('days_distribution', {}).items()):
            text += f"  {day.replace('_', ' ').title()}: {count} samples\n"
        text += "\n"
        
        # Missing data
        text += "Missing Data Summary:\n"
        text += "-" * 25 + "\n"
        for field, missing_count in stats.get('missing_data', {}).items():
            total = stats.get('total_samples', 0)
            percentage = (missing_count / total * 100) if total > 0 else 0
            text += f"  {field.replace('_', ' ').title()}: {missing_count}/{total} ({percentage:.1f}%)\n"
        
        return text


def main():
    """Main application entry point"""
    root = tk.Tk()
    app = LycheeDataCollectorApp(root)
    
    # Handle window closing
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # Start application
    root.mainloop()


if __name__ == "__main__":
    main()