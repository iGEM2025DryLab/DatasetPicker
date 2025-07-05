"""
Data Entry Panel GUI Module
Handles sample data entry form and validation
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, Any, Optional

from ..core.data_manager import SampleData


class DataEntryPanel:
    """Panel for entering lychee sample data"""
    
    def __init__(self, parent_frame, initial_sample_id: str = "sample_001"):
        self.parent_frame = parent_frame
        self.initial_sample_id = initial_sample_id
        
        # Variables for form fields
        self.sample_id_var = tk.StringVar(value=initial_sample_id)
        self.variation_var = tk.StringVar()
        self.days_var = tk.StringVar()
        self.sugar_var = tk.StringVar()
        self.acid_var = tk.StringVar()
        self.ph_var = tk.StringVar()
        self.ratio_var = tk.StringVar(value="N/A")
        
        # Status tracking
        self.status_labels = {}
        
        # Callbacks
        self.on_data_changed = None
        
        self.create_widgets()
        self.setup_bindings()
    
    def create_widgets(self):
        """Create data entry form widgets"""
        # Main frame
        self.main_frame = ttk.LabelFrame(self.parent_frame, text="Sample Data Entry", padding="10")
        self.main_frame.columnconfigure(1, weight=1)
        
        row = 0
        
        # Sample ID
        ttk.Label(self.main_frame, text="Sample ID:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.sample_id_entry = ttk.Entry(self.main_frame, textvariable=self.sample_id_var, state='readonly')
        self.sample_id_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        row += 1
        
        # Lychee Variation
        ttk.Label(self.main_frame, text="Lychee Variation:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.variation_combo = ttk.Combobox(self.main_frame, textvariable=self.variation_var, 
                                          values=['NMZ', 'GW', 'FZX', 'HS', 'HZ', 'BTY', 'JZ'])
        self.variation_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        row += 1
        
        # Days After Picked
        ttk.Label(self.main_frame, text="Days After Picked:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.days_spinbox = ttk.Spinbox(self.main_frame, from_=0, to=30, textvariable=self.days_var)
        self.days_spinbox.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        row += 1
        
        # Sugar Content
        ttk.Label(self.main_frame, text="Sugar Content (Brix):").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.sugar_entry = ttk.Entry(self.main_frame, textvariable=self.sugar_var)
        self.sugar_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        row += 1
        
        # Acid Content
        ttk.Label(self.main_frame, text="Acid Content (%):").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.acid_entry = ttk.Entry(self.main_frame, textvariable=self.acid_var)
        self.acid_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        row += 1
        
        # pH
        ttk.Label(self.main_frame, text="pH:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.ph_entry = ttk.Entry(self.main_frame, textvariable=self.ph_var)
        self.ph_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        row += 1
        
        # Sugar/Acid Ratio (calculated)
        ttk.Label(self.main_frame, text="Sugar/Acid Ratio:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.ratio_label = ttk.Label(self.main_frame, textvariable=self.ratio_var, 
                                    background='lightgray', relief='sunken')
        self.ratio_label.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        row += 1
        
        # Notes
        ttk.Label(self.main_frame, text="Notes:").grid(row=row, column=0, sticky=(tk.W, tk.N), pady=2)
        self.notes_text = tk.Text(self.main_frame, height=4, width=30)
        self.notes_text.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        
        # Scrollbar for notes
        notes_scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.notes_text.yview)
        notes_scrollbar.grid(row=row, column=2, sticky=(tk.N, tk.S), padx=(2, 0), pady=2)
        self.notes_text.configure(yscrollcommand=notes_scrollbar.set)
        row += 1
        
        # Status indicators
        self.create_status_panel(row)
    
    def create_status_panel(self, row):
        """Create status indicator panel"""
        status_frame = ttk.LabelFrame(self.main_frame, text="Data Status", padding="5")
        status_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        status_frame.columnconfigure(1, weight=1)
        
        # Status indicators for each field
        fields = [
            ('Variation', 'variation'),
            ('Days After Picked', 'days'),
            ('Sugar Content', 'sugar'),
            ('Acid Content', 'acid'),
            ('pH', 'ph'),
            ('RGB Image', 'rgb_image'),
            ('NIR Image', 'nir_image')
        ]
        
        for i, (label_text, field_key) in enumerate(fields):
            ttk.Label(status_frame, text=f"{label_text}:").grid(row=i, column=0, sticky=tk.W, pady=1)
            status_label = ttk.Label(status_frame, text="Missing", foreground='red')
            status_label.grid(row=i, column=1, sticky=tk.W, padx=(10, 0), pady=1)
            self.status_labels[field_key] = status_label
    
    def setup_bindings(self):
        """Setup event bindings for automatic updates"""
        # Bind calculation events
        self.sugar_var.trace('w', self.calculate_ratio)
        self.acid_var.trace('w', self.calculate_ratio)
        
        # Bind status update events
        self.variation_var.trace('w', lambda *args: self.update_field_status('variation'))
        self.days_var.trace('w', lambda *args: self.update_field_status('days'))
        self.sugar_var.trace('w', lambda *args: self.update_field_status('sugar'))
        self.acid_var.trace('w', lambda *args: self.update_field_status('acid'))
        self.ph_var.trace('w', lambda *args: self.update_field_status('ph'))
        
        # Bind text widget for notes
        self.notes_text.bind('<KeyRelease>', self.on_data_change)
        
        # Bind other fields
        for widget in [self.variation_combo, self.days_spinbox, self.sugar_entry, 
                      self.acid_entry, self.ph_entry]:
            widget.bind('<KeyRelease>', self.on_data_change)
            widget.bind('<<ComboboxSelected>>', self.on_data_change)
    
    def grid(self, **kwargs):
        """Grid the main frame"""
        self.main_frame.grid(**kwargs)
    
    def calculate_ratio(self, *args):
        """Calculate sugar/acid ratio automatically"""
        try:
            sugar_text = self.sugar_var.get().strip()
            acid_text = self.acid_var.get().strip()
            
            if sugar_text and acid_text:
                sugar = float(sugar_text)
                acid = float(acid_text)
                
                if acid > 0:
                    ratio = sugar / acid
                    self.ratio_var.set(f"{ratio:.2f}")
                else:
                    self.ratio_var.set("∞")
            else:
                self.ratio_var.set("N/A")
                
        except ValueError:
            self.ratio_var.set("Invalid")
        
        self.on_data_change()
    
    def update_field_status(self, field_key):
        """Update status indicator for a specific field"""
        if field_key not in self.status_labels:
            return
        
        value = ""
        if field_key == 'variation':
            value = self.variation_var.get().strip()
        elif field_key == 'days':
            value = self.days_var.get().strip()
        elif field_key == 'sugar':
            value = self.sugar_var.get().strip()
        elif field_key == 'acid':
            value = self.acid_var.get().strip()
        elif field_key == 'ph':
            value = self.ph_var.get().strip()
        
        if value:
            self.status_labels[field_key].config(text="Entered", foreground='green')
        else:
            self.status_labels[field_key].config(text="Missing", foreground='red')
        
        self.on_data_change()
    
    def update_image_status(self, image_type: str, captured: bool):
        """Update image capture status"""
        if image_type in self.status_labels:
            if captured:
                self.status_labels[image_type].config(text="Captured", foreground='green')
            else:
                self.status_labels[image_type].config(text="Missing", foreground='red')
    
    def on_data_change(self, event=None):
        """Handle data change events"""
        if self.on_data_changed:
            self.on_data_changed(self.get_sample_data())
    
    def get_sample_data(self) -> SampleData:
        """Get current sample data"""
        sample = SampleData(self.sample_id_var.get())
        sample.lychee_variation = self.variation_var.get().strip()
        sample.days_after_picked = self.days_var.get().strip() or None
        sample.sugar_content = self.sugar_var.get().strip() or None
        sample.acid_content = self.acid_var.get().strip() or None
        sample.ph = self.ph_var.get().strip() or None
        sample.notes = self.notes_text.get(1.0, tk.END).strip()
        
        # Calculate ratio
        ratio_text = self.ratio_var.get()
        if ratio_text not in ["N/A", "Invalid", "∞"]:
            try:
                sample.sugar_acid_ratio = float(ratio_text)
            except ValueError:
                sample.sugar_acid_ratio = None
        
        return sample
    
    def set_sample_data(self, sample: SampleData):
        """Load sample data into the form"""
        self.sample_id_var.set(sample.sample_id or "")
        self.variation_var.set(sample.lychee_variation or "")
        self.days_var.set(str(sample.days_after_picked) if sample.days_after_picked else "")
        self.sugar_var.set(str(sample.sugar_content) if sample.sugar_content else "")
        self.acid_var.set(str(sample.acid_content) if sample.acid_content else "")
        self.ph_var.set(str(sample.ph) if sample.ph else "")
        
        # Set notes
        self.notes_text.delete(1.0, tk.END)
        if sample.notes:
            self.notes_text.insert(1.0, sample.notes)
        
        # Update ratio
        if sample.sugar_acid_ratio:
            self.ratio_var.set(str(sample.sugar_acid_ratio))
        else:
            self.calculate_ratio()
        
        # Update status indicators
        self.update_all_status()
    
    def clear_form(self):
        """Clear all form fields"""
        # self.variation_var.set("")
        # self.days_var.set("")
        self.sugar_var.set("")
        self.acid_var.set("")
        self.ph_var.set("")
        self.ratio_var.set("N/A")
        self.notes_text.delete(1.0, tk.END)
        
        # Reset image status
        self.update_image_status('rgb_image', False)
        self.update_image_status('nir_image', False)
        
        # Update field status
        self.update_all_status()
    
    def update_all_status(self):
        """Update all status indicators"""
        for field in ['variation', 'days', 'sugar', 'acid', 'ph']:
            self.update_field_status(field)
    
    def set_sample_id(self, sample_id: str):
        """Set the sample ID"""
        self.sample_id_var.set(sample_id)
    
    def get_validation_errors(self) -> list:
        """Get list of validation errors"""
        errors = []
        
        if not self.variation_var.get().strip():
            errors.append("Lychee variation is required")
        
        if not self.days_var.get().strip():
            errors.append("Days after picked is required")
        
        # Validate numeric fields
        for field_name, var in [("Sugar content", self.sugar_var), 
                               ("Acid content", self.acid_var), 
                               ("pH", self.ph_var)]:
            value = var.get().strip()
            if value:
                try:
                    float(value)
                except ValueError:
                    errors.append(f"{field_name} must be a valid number")
        
        return errors
    
    def is_valid(self) -> bool:
        """Check if form data is valid"""
        return len(self.get_validation_errors()) == 0
    
    def set_data_changed_callback(self, callback: Callable):
        """Set callback for when data changes"""
        self.on_data_changed = callback