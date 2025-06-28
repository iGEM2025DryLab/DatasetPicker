"""
Camera Panel GUI Module
Handles camera feed display and live editing controls
"""

import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk
from typing import Optional, Callable, Dict, List, Tuple

from ..core.camera_manager import CameraFeed, ImageProcessor


class CameraControlPanel:
    """Control panel for a single camera with live editing"""
    
    def __init__(self, parent_frame, camera_feed: CameraFeed, camera_options: List[Tuple[int, str]], 
                 title: str = "Camera"):
        self.parent_frame = parent_frame
        self.camera_feed = camera_feed
        self.camera_options = camera_options
        self.title = title
        
        # UI elements
        self.frame = None
        self.canvas = None
        self.camera_var = None
        self.connect_btn = None
        self.capture_btn = None
        self.status_label = None
        
        # Settings panels
        self.settings_frame = None
        self.rotation_var = None
        self.flip_h_var = None
        self.flip_v_var = None
        
        # Crop variables
        self.crop_start = None
        self.crop_end = None
        self.cropping = False
        self.crop_rect_id = None
        
        # Canvas dimensions
        self.canvas_width = 400
        self.canvas_height = 300
        
        # Callbacks
        self.on_image_captured = None  # Callback when image is captured
        
        self.create_widgets()
        self.setup_callbacks()
    
    def create_widgets(self):
        """Create all widgets for this camera panel"""
        # Main frame
        self.frame = ttk.LabelFrame(self.parent_frame, text=self.title, padding="10")
        
        # Camera selection
        selection_frame = ttk.Frame(self.frame)
        selection_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        selection_frame.columnconfigure(1, weight=1)
        
        ttk.Label(selection_frame, text="Camera:").grid(row=0, column=0, sticky=tk.W)
        
        self.camera_var = tk.StringVar(value=str(self.camera_feed.camera_index))
        camera_combo = ttk.Combobox(selection_frame, textvariable=self.camera_var, width=20)
        camera_combo['values'] = [f"{idx}: {name}" for idx, name in self.camera_options]
        camera_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0))
        camera_combo.bind('<<ComboboxSelected>>', self.on_camera_change)
        
        # Canvas for video feed
        self.canvas = tk.Canvas(self.frame, width=self.canvas_width, height=self.canvas_height, bg='black')
        self.canvas.grid(row=1, column=0, pady=(5, 10))
        
        # Bind canvas events for cropping
        self.canvas.bind("<Button-1>", self.start_crop)
        self.canvas.bind("<B1-Motion>", self.update_crop)
        self.canvas.bind("<ButtonRelease-1>", self.end_crop)
        
        # Control buttons
        control_frame = ttk.Frame(self.frame)
        control_frame.grid(row=2, column=0, pady=(0, 10))
        
        self.connect_btn = ttk.Button(control_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=0, padx=(0, 5))
        
        self.capture_btn = ttk.Button(control_frame, text="Capture", command=self.capture_image, state='disabled')
        self.capture_btn.grid(row=0, column=1, padx=(0, 5))
        
        # Live editing controls
        self.create_settings_panel()
        
        # Status label
        self.status_label = ttk.Label(self.frame, text="Disconnected", foreground='red')
        self.status_label.grid(row=4, column=0, pady=(10, 0))
    
    def create_settings_panel(self):
        """Create live editing settings panel"""
        self.settings_frame = ttk.LabelFrame(self.frame, text="Live Editing", padding="5")
        self.settings_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # Rotation controls
        rotation_frame = ttk.Frame(self.settings_frame)
        rotation_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Label(rotation_frame, text="Rotation:").grid(row=0, column=0, sticky=tk.W)
        
        ttk.Button(rotation_frame, text="↶ 90°", width=6, 
                  command=self.rotate_ccw).grid(row=0, column=1, padx=(10, 2))
        ttk.Button(rotation_frame, text="↷ 90°", width=6, 
                  command=self.rotate_cw).grid(row=0, column=2, padx=2)
        
        # Flip controls
        flip_frame = ttk.Frame(self.settings_frame)
        flip_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.flip_h_var = tk.BooleanVar()
        self.flip_v_var = tk.BooleanVar()
        
        ttk.Checkbutton(flip_frame, text="Flip Horizontal", variable=self.flip_h_var,
                       command=self.toggle_flip_horizontal).grid(row=0, column=0, sticky=tk.W)
        ttk.Checkbutton(flip_frame, text="Flip Vertical", variable=self.flip_v_var,
                       command=self.toggle_flip_vertical).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        # Crop controls
        crop_frame = ttk.Frame(self.settings_frame)
        crop_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Label(crop_frame, text="Crop:").grid(row=0, column=0, sticky=tk.W)
        
        self.crop_btn = ttk.Button(crop_frame, text="Draw Crop", command=self.toggle_crop)
        self.crop_btn.grid(row=0, column=1, padx=(10, 5))
        
        ttk.Button(crop_frame, text="Clear", command=self.clear_crop).grid(row=0, column=2)
        
        # Crop status label
        self.crop_status = ttk.Label(crop_frame, text="No crop", foreground='gray')
        self.crop_status.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(2, 0))
        
        # Reset button
        ttk.Button(self.settings_frame, text="Reset All", command=self.reset_settings).grid(row=3, column=0, pady=(5, 0))
    
    def setup_callbacks(self):
        """Setup camera feed callbacks"""
        if self.camera_feed:
            self.camera_feed.add_frame_callback(self.update_display)
    
    def grid(self, **kwargs):
        """Grid the main frame"""
        self.frame.grid(**kwargs)
    
    def on_camera_change(self, event=None):
        """Handle camera selection change"""
        selected = self.camera_var.get()
        if ':' in selected:
            camera_index = int(selected.split(':')[0])
            
            # Disconnect current camera
            if self.camera_feed.is_active:
                self.toggle_connection()
            
            # Update camera index
            self.camera_feed.camera_index = camera_index
            self.camera_feed.name = f"Camera {camera_index}"
    
    def toggle_connection(self):
        """Toggle camera connection"""
        if self.camera_feed.is_connected:
            # Disconnect
            self.camera_feed.disconnect()
            self.connect_btn.config(text="Connect")
            self.capture_btn.config(state='disabled')
            self.status_label.config(text="Disconnected", foreground='red')
            self.canvas.delete("all")
        else:
            # Connect
            if self.camera_feed.start_feed():
                self.connect_btn.config(text="Disconnect")
                self.capture_btn.config(state='normal')
                self.status_label.config(text="Connected", foreground='green')
            else:
                messagebox.showerror("Error", f"Could not connect to camera {self.camera_feed.camera_index}")
    
    def capture_image(self):
        """Capture current frame"""
        if self.camera_feed.is_active:
            frame = self.camera_feed.capture_frame(processed=True)
            if frame is not None and self.on_image_captured:
                # Also capture processing settings
                settings = self.camera_feed.processor.get_settings_dict()
                self.on_image_captured(frame, settings)
    
    def update_display(self, frame):
        """Update canvas display with new frame"""
        if frame is None or self.canvas is None:
            return
        
        try:
            # Fit frame to canvas while maintaining aspect ratio
            fitted_frame, display_width, display_height = self.fit_frame_to_canvas(frame)
            
            # Convert to RGB for display
            if len(fitted_frame.shape) == 3:
                frame_rgb = cv2.cvtColor(fitted_frame, cv2.COLOR_BGR2RGB)
            else:
                frame_rgb = fitted_frame
            
            # Convert to PIL and then to PhotoImage
            image = Image.fromarray(frame_rgb)
            photo = ImageTk.PhotoImage(image)
            
            # Update canvas
            self.canvas.delete("all")
            x_offset = (self.canvas_width - display_width) // 2
            y_offset = (self.canvas_height - display_height) // 2
            self.canvas.create_image(x_offset + display_width//2, y_offset + display_height//2,
                                   image=photo, anchor=tk.CENTER)
            self.canvas.image = photo  # Keep reference
            
            # Store display info for cropping
            self.display_width = display_width
            self.display_height = display_height
            self.display_x_offset = x_offset
            self.display_y_offset = y_offset
            
        except Exception as e:
            print(f"Error updating display: {e}")
    
    def fit_frame_to_canvas(self, frame):
        """Fit frame to canvas maintaining aspect ratio"""
        if len(frame.shape) == 3:
            height, width = frame.shape[:2]
        else:
            height, width = frame.shape
        
        # Calculate scaling
        scale_w = self.canvas_width / width
        scale_h = self.canvas_height / height
        scale = min(scale_w, scale_h)
        
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        resized_frame = cv2.resize(frame, (new_width, new_height))
        return resized_frame, new_width, new_height
    
    # Live editing controls
    def rotate_cw(self):
        """Rotate clockwise"""
        self.camera_feed.processor.rotate_clockwise()
    
    def rotate_ccw(self):
        """Rotate counterclockwise"""
        self.camera_feed.processor.rotate_counterclockwise()
    
    def toggle_flip_horizontal(self):
        """Toggle horizontal flip"""
        self.camera_feed.processor.flip_horizontal = self.flip_h_var.get()
    
    def toggle_flip_vertical(self):
        """Toggle vertical flip"""
        self.camera_feed.processor.flip_vertical = self.flip_v_var.get()
    
    def toggle_crop(self):
        """Toggle crop mode"""
        if not self.cropping:
            self.cropping = True
            self.crop_btn.config(text="Cancel Crop")
            self.canvas.config(cursor="cross")
            self.crop_status.config(text="Click and drag to select crop area", foreground='blue')
        else:
            self.cropping = False
            self.crop_btn.config(text="Draw Crop")
            self.canvas.config(cursor="")
            self.canvas.delete("crop_rect")
            self.update_crop_status()
    
    def clear_crop(self):
        """Clear crop region"""
        self.camera_feed.processor.clear_crop()
        self.canvas.delete("crop_rect")
        self.cropping = False
        self.crop_btn.config(text="Draw Crop")
        self.canvas.config(cursor="")
        self.update_crop_status()
    
    def reset_settings(self):
        """Reset all processing settings"""
        self.camera_feed.processor.reset()
        self.flip_h_var.set(False)
        self.flip_v_var.set(False)
        self.clear_crop()
        self.update_crop_status()
    
    # Crop interaction
    def start_crop(self, event):
        """Start crop selection"""
        if self.cropping:
            self.crop_start = (event.x, event.y)
            self.canvas.delete("crop_rect")
    
    def update_crop(self, event):
        """Update crop rectangle"""
        if self.cropping and self.crop_start:
            self.canvas.delete("crop_rect")
            self.crop_rect_id = self.canvas.create_rectangle(
                self.crop_start[0], self.crop_start[1], event.x, event.y,
                outline="red", width=2, tags="crop_rect"
            )
    
    def end_crop(self, event):
        """End crop selection and apply"""
        if self.cropping and self.crop_start:
            self.crop_end = (event.x, event.y)
            self.apply_crop()
    
    def apply_crop(self):
        """Apply crop to processor"""
        if not self.crop_start or not self.crop_end:
            return
        
        # Convert canvas coordinates to image coordinates
        x1 = min(self.crop_start[0], self.crop_end[0]) - self.display_x_offset
        y1 = min(self.crop_start[1], self.crop_end[1]) - self.display_y_offset
        x2 = max(self.crop_start[0], self.crop_end[0]) - self.display_x_offset
        y2 = max(self.crop_start[1], self.crop_end[1]) - self.display_y_offset
        
        # Ensure coordinates are within display bounds
        x1 = max(0, min(x1, self.display_width))
        y1 = max(0, min(y1, self.display_height))
        x2 = max(0, min(x2, self.display_width))
        y2 = max(0, min(y2, self.display_height))
        
        # Get current processed frame to determine actual rotated size
        processed_frame = self.camera_feed.get_current_frame(processed=True)
        if processed_frame is not None:
            if len(processed_frame.shape) == 3:
                actual_height, actual_width = processed_frame.shape[:2]
            else:
                actual_height, actual_width = processed_frame.shape
            
            # Scale coordinates to actual processed image size
            scale_x = actual_width / self.display_width
            scale_y = actual_height / self.display_height
            
            actual_x = int(x1 * scale_x)
            actual_y = int(y1 * scale_y)
            actual_w = int((x2 - x1) * scale_x)
            actual_h = int((y2 - y1) * scale_y)
            
            # Apply crop if region is large enough
            if actual_w > 10 and actual_h > 10:
                self.camera_feed.processor.set_crop_region(actual_x, actual_y, actual_w, actual_h)
                self.update_crop_status()
            else:
                self.crop_status.config(text="Crop area too small", foreground='red')
        
        # Reset crop UI
        self.crop_start = None
        self.crop_end = None
        self.cropping = False
        self.crop_btn.config(text="Draw Crop")
        self.canvas.config(cursor="")
    
    def update_crop_status(self):
        """Update crop status display"""
        crop_region = self.camera_feed.processor.crop_region
        if crop_region:
            x, y, w, h = crop_region
            self.crop_status.config(text=f"Crop: {w}x{h} at ({x},{y})", foreground='green')
        else:
            self.crop_status.config(text="No crop", foreground='gray')
    
    def set_image_captured_callback(self, callback: Callable):
        """Set callback for when image is captured"""
        self.on_image_captured = callback
    
    def cleanup(self):
        """Cleanup resources"""
        if self.camera_feed:
            self.camera_feed.disconnect()


class CameraPanel:
    """Main camera panel containing RGB and NIR camera controls"""
    
    def __init__(self, parent_frame, camera_manager):
        self.parent_frame = parent_frame
        self.camera_manager = camera_manager
        
        # Camera feeds
        self.rgb_feed = None
        self.nir_feed = None
        
        # Camera panels
        self.rgb_panel = None
        self.nir_panel = None
        
        # Callbacks
        self.on_rgb_captured = None
        self.on_nir_captured = None
        
        self.create_widgets()
    
    def create_widgets(self):
        """Create camera panel widgets"""
        # Main frame
        self.main_frame = ttk.LabelFrame(self.parent_frame, text="Camera Feeds & Live Editing", padding="10")
        
        # Get camera options
        camera_options = self.camera_manager.get_available_camera_options()
        
        # Create camera feeds
        self.rgb_feed = self.camera_manager.create_camera_feed(
            camera_options[0][0] if camera_options else 0, "rgb_feed"
        )
        self.nir_feed = self.camera_manager.create_camera_feed(
            camera_options[1][0] if len(camera_options) > 1 else 1, "nir_feed"
        )
        
        # Create RGB camera panel
        if self.rgb_feed:
            self.rgb_panel = CameraControlPanel(
                self.main_frame, self.rgb_feed, camera_options, "RGB Camera"
            )
            self.rgb_panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
            self.rgb_panel.set_image_captured_callback(self._on_rgb_captured)
        
        # Create NIR camera panel
        if self.nir_feed:
            self.nir_panel = CameraControlPanel(
                self.main_frame, self.nir_feed, camera_options, "NIR Camera"
            )
            self.nir_panel.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
            self.nir_panel.set_image_captured_callback(self._on_nir_captured)
        
        # Configure grid weights
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(0, weight=1)
    
    def grid(self, **kwargs):
        """Grid the main frame"""
        self.main_frame.grid(**kwargs)
    
    def _on_rgb_captured(self, frame, settings):
        """Handle RGB image capture"""
        if self.on_rgb_captured:
            self.on_rgb_captured(frame, settings)
    
    def _on_nir_captured(self, frame, settings):
        """Handle NIR image capture"""
        if self.on_nir_captured:
            self.on_nir_captured(frame, settings)
    
    def set_rgb_captured_callback(self, callback: Callable):
        """Set callback for RGB image capture"""
        self.on_rgb_captured = callback
    
    def set_nir_captured_callback(self, callback: Callable):
        """Set callback for NIR image capture"""
        self.on_nir_captured = callback
    
    def cleanup(self):
        """Cleanup resources"""
        if self.rgb_panel:
            self.rgb_panel.cleanup()
        if self.nir_panel:
            self.nir_panel.cleanup()
        
        self.camera_manager.cleanup()