import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import os
import json
from datetime import datetime
from PIL import Image, ImageTk
import numpy as np
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder, MJPEGEncoder, Quality
from picamera2.outputs import FileOutput

class CameraInfoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Picamera2 Interface")
        # Set appropriate size for 7" touchscreen
        self.root.geometry("800x480")
        
        # Define default directories
        self.video_dir = os.path.expanduser("~/Videos")
        self.photo_dir = os.path.expanduser("~/Pictures")
        
        # Create directories if they don't exist
        os.makedirs(self.video_dir, exist_ok=True)
        os.makedirs(self.photo_dir, exist_ok=True)
        
        # Configuration file path
        self.config_dir = os.path.expanduser("~/.camera_app")
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Store camera information
        self.all_camera_info = []
        self.selected_camera_index = tk.StringVar()
        self.selected_camera_id = None
        self.camera_config = {}
        
        # Preview variables
        self.preview_active = False
        self.preview_thread = None
        self.stop_preview_event = threading.Event()
        
        # Video variables
        self.video_resolution = tk.StringVar(value="1280x720")
        self.video_custom_width = tk.StringVar(value="1280")
        self.video_custom_height = tk.StringVar(value="720")
        self.video_framerate = tk.StringVar(value="30")
        self.video_encoder = tk.StringVar(value="H264Encoder")
        self.video_format = tk.StringVar(value=".mp4")
        
        # Still variables
        self.still_resolution = tk.StringVar(value="3280x2464")
        self.still_custom_width = tk.StringVar(value="3280")
        self.still_custom_height = tk.StringVar(value="2464")
        
        # Use a more compact style for small screens
        self.style = ttk.Style()
        self.style.configure('TButton', padding=2)
        self.style.configure('TLabel', padding=1)
        self.style.configure('TFrame', padding=2)
        self.style.configure('TLabelframe', padding=2)
        self.style.configure('TNotebook.Tab', padding=(5, 2))
        
        # Create main UI structure
        self.create_ui()
        
        # Initialize camera
        self.picam2 = None
        self.initialize_camera()
        
        # Load camera info when app starts
        self.load_camera_info()
    
    def create_ui(self):
        # Main frame
        self.main_frame = ttk.Frame(self.root, padding=2)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create header with camera selector (simplified)
        self.create_header()
        
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=2)
        
        # Create tabs
        self.camera_info_tab = ttk.Frame(self.notebook)
        self.still_tab = ttk.Frame(self.notebook)
        self.video_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.camera_info_tab, text="Info")
        self.notebook.add(self.still_tab, text="Photo")
        self.notebook.add(self.video_tab, text="Video")
        
        # Setup tabs
        self.setup_camera_info_tab()
        self.setup_still_tab()
        self.setup_video_tab()
        
        # Setup preview frame
        self.preview_frame = ttk.LabelFrame(self.main_frame, text="Preview")
        self.preview_frame.pack(fill=tk.BOTH, expand=True, pady=2)
        
        # Preview canvas (make it short to accommodate other controls)
        self.preview_canvas = tk.Canvas(self.preview_frame, bg="black", height=180)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Close preview button (initially hidden)
        self.close_preview_btn = ttk.Button(
            self.preview_frame, 
            text="Close Preview", 
            command=self.stop_preview
        )
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def create_header(self):
        # Simplified header
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(fill=tk.X, pady=2)
        
        # Left side: Camera selector
        camera_label = ttk.Label(header_frame, text="Camera:")
        camera_label.pack(side=tk.LEFT, padx=2)
        
        self.camera_dropdown = ttk.Combobox(
            header_frame, 
            textvariable=self.selected_camera_index, 
            state="readonly",
            width=20  # Shorter width
        )
        self.camera_dropdown.pack(side=tk.LEFT, padx=2)
        self.camera_dropdown.bind("<<ComboboxSelected>>", self.on_camera_selected)
        
        # Right side: Refresh button
        refresh_btn = ttk.Button(
            header_frame, 
            text="↻", 
            command=self.refresh_camera_info,
            width=3  # Smaller button
        )
        refresh_btn.pack(side=tk.RIGHT, padx=2)
    
    def setup_camera_info_tab(self):
        # Use a paned window for better space management
        paned = ttk.PanedWindow(self.camera_info_tab, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Camera details frame
        camera_details_frame = ttk.LabelFrame(paned, text="Camera Details")
        
        # Create scrollbar and text widget for camera details
        camera_details_scroll = ttk.Scrollbar(camera_details_frame)
        camera_details_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.camera_details_text = tk.Text(camera_details_frame, wrap=tk.WORD, height=10)
        self.camera_details_text.pack(fill=tk.BOTH, expand=True)
        
        camera_details_scroll.config(command=self.camera_details_text.yview)
        self.camera_details_text.config(yscrollcommand=camera_details_scroll.set)
        
        # Sensor modes frame
        sensor_modes_frame = ttk.LabelFrame(paned, text="Sensor Modes")
        
        # Create scrollbar and text widget for sensor modes
        sensor_modes_scroll = ttk.Scrollbar(sensor_modes_frame)
        sensor_modes_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.sensor_modes_text = tk.Text(sensor_modes_frame, wrap=tk.WORD, height=10)
        self.sensor_modes_text.pack(fill=tk.BOTH, expand=True)
        
        sensor_modes_scroll.config(command=self.sensor_modes_text.yview)
        self.sensor_modes_text.config(yscrollcommand=sensor_modes_scroll.set)
        
        # Add frames to paned window
        paned.add(camera_details_frame, weight=1)
        paned.add(sensor_modes_frame, weight=1)
    
    def setup_still_tab(self):
        # Use a notebook inside the tab for better space organization
        inner_notebook = ttk.Notebook(self.still_tab)
        inner_notebook.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Create sub-tabs
        settings_tab = ttk.Frame(inner_notebook)
        output_tab = ttk.Frame(inner_notebook)
        
        inner_notebook.add(settings_tab, text="Settings")
        inner_notebook.add(output_tab, text="Output")
        
        # Settings tab
        # Resolution section
        res_frame = ttk.LabelFrame(settings_tab, text="Resolution")
        res_frame.pack(fill=tk.X, expand=False, pady=2, padx=2)
        
        # Grid layout for compactness
        ttk.Label(res_frame, text="Resolution:").grid(row=0, column=0, sticky=tk.W, padx=2, pady=2)
        self.still_res_dropdown = ttk.Combobox(res_frame, textvariable=self.still_resolution, state="readonly", width=15)
        self.still_res_dropdown.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=2, pady=2)
        self.still_res_dropdown.bind("<<ComboboxSelected>>", self.on_still_resolution_changed)
        
        # Custom resolution
        ttk.Label(res_frame, text="Custom:").grid(row=1, column=0, sticky=tk.W, padx=2, pady=2)
        
        custom_frame = ttk.Frame(res_frame)
        custom_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=2, pady=2)
        
        ttk.Label(custom_frame, text="W:").pack(side=tk.LEFT)
        width_entry = ttk.Entry(custom_frame, textvariable=self.still_custom_width, width=5)
        width_entry.pack(side=tk.LEFT, padx=(0, 2))
        
        ttk.Label(custom_frame, text="H:").pack(side=tk.LEFT)
        height_entry = ttk.Entry(custom_frame, textvariable=self.still_custom_height, width=5)
        height_entry.pack(side=tk.LEFT)
        
        # Apply custom button
        apply_custom_btn = ttk.Button(res_frame, text="Apply", command=self.apply_custom_still_resolution, width=6)
        apply_custom_btn.grid(row=1, column=2, padx=2, pady=2)
        
        # Format selection
        ttk.Label(res_frame, text="Format:").grid(row=2, column=0, sticky=tk.W, padx=2, pady=2)
        self.still_format_var = tk.StringVar(value=".jpg")
        format_combo = ttk.Combobox(res_frame, textvariable=self.still_format_var, values=[".jpg", ".png"], state="readonly", width=5)
        format_combo.grid(row=2, column=1, sticky=tk.W, padx=2, pady=2)
        
        # Actions section
        actions_frame = ttk.LabelFrame(settings_tab, text="Actions")
        actions_frame.pack(fill=tk.X, expand=False, pady=2, padx=2)
        
        # Use grid for buttons to place them horizontally
        preview_btn = ttk.Button(actions_frame, text="Preview (10s)", command=lambda: self.start_preview("still"))
        preview_btn.grid(row=0, column=0, padx=2, pady=2, sticky=(tk.W, tk.E))
        
        capture_btn = ttk.Button(actions_frame, text="Capture Photo", command=self.capture_photo)
        capture_btn.grid(row=0, column=1, padx=2, pady=2, sticky=(tk.W, tk.E))
        
        # Configure grid weights
        actions_frame.columnconfigure(0, weight=1)
        actions_frame.columnconfigure(1, weight=1)
        
        # Output tab
        # Output settings
        output_frame = ttk.LabelFrame(output_tab, text="Output Settings")
        output_frame.pack(fill=tk.X, expand=False, pady=2, padx=2)
        
        # Save folder
        ttk.Label(output_frame, text="Save folder:").grid(row=0, column=0, sticky=tk.W, padx=2, pady=2)
        self.still_dir_var = tk.StringVar(value=self.photo_dir)
        dir_entry = ttk.Entry(output_frame, textvariable=self.still_dir_var)
        dir_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=2, pady=2)
        
        browse_btn = ttk.Button(output_frame, text="...", command=lambda: self.browse_directory("still"), width=3)
        browse_btn.grid(row=0, column=2, padx=2, pady=2)
        
        # Filename prefix
        ttk.Label(output_frame, text="Prefix:").grid(row=1, column=0, sticky=tk.W, padx=2, pady=2)
        self.still_prefix_var = tk.StringVar(value="photo_")
        prefix_entry = ttk.Entry(output_frame, textvariable=self.still_prefix_var)
        prefix_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=2, pady=2)
        
        # Configure column weights
        output_frame.columnconfigure(1, weight=1)
        
        # Image info
        info_frame = ttk.LabelFrame(output_tab, text="Image Information")
        info_frame.pack(fill=tk.BOTH, expand=True, pady=2, padx=2)
        
        self.still_info_text = tk.Text(info_frame, wrap=tk.WORD, height=6)
        self.still_info_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.still_info_text.insert(tk.END, "No images captured yet.")
    
    def setup_video_tab(self):
        # Use a notebook inside the tab for better space organization
        inner_notebook = ttk.Notebook(self.video_tab)
        inner_notebook.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Create sub-tabs
        settings_tab = ttk.Frame(inner_notebook)
        encoder_tab = ttk.Frame(inner_notebook)
        output_tab = ttk.Frame(inner_notebook)
        
        inner_notebook.add(settings_tab, text="Settings")
        inner_notebook.add(encoder_tab, text="Encoder")
        inner_notebook.add(output_tab, text="Output")
        
        # Settings tab
        # Resolution section
        res_frame = ttk.LabelFrame(settings_tab, text="Resolution")
        res_frame.pack(fill=tk.X, expand=False, pady=2, padx=2)
        
        # Grid layout for compactness
        ttk.Label(res_frame, text="Resolution:").grid(row=0, column=0, sticky=tk.W, padx=2, pady=2)
        self.video_res_dropdown = ttk.Combobox(res_frame, textvariable=self.video_resolution, state="readonly", width=15)
        self.video_res_dropdown.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=2, pady=2)
        self.video_res_dropdown.bind("<<ComboboxSelected>>", self.on_video_resolution_changed)
        
        # Framerate
        ttk.Label(res_frame, text="Framerate:").grid(row=1, column=0, sticky=tk.W, padx=2, pady=2)
        framerate_entry = ttk.Entry(res_frame, textvariable=self.video_framerate, width=5)
        framerate_entry.grid(row=1, column=1, sticky=tk.W, padx=2, pady=2)
        ttk.Label(res_frame, text="fps").grid(row=1, column=2, sticky=tk.W, padx=2, pady=2)
        
        # Custom resolution
        ttk.Label(res_frame, text="Custom:").grid(row=2, column=0, sticky=tk.W, padx=2, pady=2)
        
        custom_frame = ttk.Frame(res_frame)
        custom_frame.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=2, pady=2)
        
        ttk.Label(custom_frame, text="W:").pack(side=tk.LEFT)
        width_entry = ttk.Entry(custom_frame, textvariable=self.video_custom_width, width=5)
        width_entry.pack(side=tk.LEFT, padx=(0, 2))
        
        ttk.Label(custom_frame, text="H:").pack(side=tk.LEFT)
        height_entry = ttk.Entry(custom_frame, textvariable=self.video_custom_height, width=5)
        height_entry.pack(side=tk.LEFT)
        
        # Apply custom button
        apply_custom_btn = ttk.Button(res_frame, text="Apply", command=self.apply_custom_video_resolution, width=6)
        apply_custom_btn.grid(row=2, column=2, padx=2, pady=2)
        
        # Actions for video
        actions_frame = ttk.LabelFrame(settings_tab, text="Actions")
        actions_frame.pack(fill=tk.X, expand=False, pady=2, padx=2)
        
        # Use grid for buttons to place them horizontally
        preview_btn = ttk.Button(actions_frame, text="Preview (10s)", command=lambda: self.start_preview("video"))
        preview_btn.grid(row=0, column=0, padx=2, pady=2, sticky=(tk.W, tk.E))
        
        self.record_btn = ttk.Button(actions_frame, text="Record Video", command=self.record_video)
        self.record_btn.grid(row=0, column=1, padx=2, pady=2, sticky=(tk.W, tk.E))
        
        # Configure grid weights
        actions_frame.columnconfigure(0, weight=1)
        actions_frame.columnconfigure(1, weight=1)
        
        # Encoder tab
        # Encoder settings
        encoder_frame = ttk.LabelFrame(encoder_tab, text="Encoder Settings")
        encoder_frame.pack(fill=tk.X, expand=False, pady=2, padx=2)
        
        # Encoder selection
        ttk.Label(encoder_frame, text="Encoder:").grid(row=0, column=0, sticky=tk.W, padx=2, pady=2)
        encoder_combo = ttk.Combobox(encoder_frame, textvariable=self.video_encoder, 
                                    values=["H264Encoder", "MJPEGEncoder"], state="readonly", width=12)
        encoder_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=2, pady=2)
        
        # Format selection
        ttk.Label(encoder_frame, text="Format:").grid(row=1, column=0, sticky=tk.W, padx=2, pady=2)
        format_combo = ttk.Combobox(encoder_frame, textvariable=self.video_format, 
                                   values=[".mp4", ".h264", ".mjpg"], state="readonly", width=6)
        format_combo.grid(row=1, column=1, sticky=tk.W, padx=2, pady=2)
        
        # Quality selection
        ttk.Label(encoder_frame, text="Quality:").grid(row=2, column=0, sticky=tk.W, padx=2, pady=2)
        self.video_quality_var = tk.StringVar(value="High")
        quality_combo = ttk.Combobox(encoder_frame, textvariable=self.video_quality_var, 
                                    values=["Very Low", "Low", "Medium", "High", "Very High"], state="readonly", width=10)
        quality_combo.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=2, pady=2)
        
        # Recording duration
        ttk.Label(encoder_frame, text="Duration:").grid(row=3, column=0, sticky=tk.W, padx=2, pady=2)
        duration_frame = ttk.Frame(encoder_frame)
        duration_frame.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=2, pady=2)
        
        self.video_duration_var = tk.StringVar(value="10")
        duration_entry = ttk.Entry(duration_frame, textvariable=self.video_duration_var, width=5)
        duration_entry.pack(side=tk.LEFT)
        ttk.Label(duration_frame, text="sec").pack(side=tk.LEFT, padx=2)
        
        # Output tab
        # Output settings
        output_frame = ttk.LabelFrame(output_tab, text="Output Settings")
        output_frame.pack(fill=tk.X, expand=False, pady=2, padx=2)
        
        # Save folder
        ttk.Label(output_frame, text="Save folder:").grid(row=0, column=0, sticky=tk.W, padx=2, pady=2)
        self.video_dir_var = tk.StringVar(value=self.video_dir)
        dir_entry = ttk.Entry(output_frame, textvariable=self.video_dir_var)
        dir_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=2, pady=2)
        
        browse_btn = ttk.Button(output_frame, text="...", command=lambda: self.browse_directory("video"), width=3)
        browse_btn.grid(row=0, column=2, padx=2, pady=2)
        
        # Filename prefix
        ttk.Label(output_frame, text="Prefix:").grid(row=1, column=0, sticky=tk.W, padx=2, pady=2)
        self.video_prefix_var = tk.StringVar(value="video_")
        prefix_entry = ttk.Entry(output_frame, textvariable=self.video_prefix_var)
        prefix_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=2, pady=2)
        
        # Configure column weights
        output_frame.columnconfigure(1, weight=1)
        
        # Video info
        info_frame = ttk.LabelFrame(output_tab, text="Video Information")
        info_frame.pack(fill=tk.BOTH, expand=True, pady=2, padx=2)
        
        self.video_info_text = tk.Text(info_frame, wrap=tk.WORD, height=6)
        self.video_info_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.video_info_text.insert(tk.END, "No videos recorded yet.")
    
    # The rest of the methods remain the same as in the previous implementation
    
    def initialize_camera(self):
        try:
            if self.picam2 is not None:
                self.picam2.close()
            
            self.picam2 = Picamera2()
            self.status_var.set("Camera initialized")
        except Exception as e:
            self.status_var.set(f"Camera error: {str(e)}")
    
    def load_camera_info(self):
        self.status_var.set("Loading camera information...")
        threading.Thread(target=self.get_camera_info, daemon=True).start()
    
    def get_camera_info(self):
        try:
            # Get camera information
            self.all_camera_info = self.picam2.global_camera_info()
            
            # Update camera dropdown
            self.root.after(0, self.update_camera_dropdown)
            
            # Update status
            self.root.after(0, lambda: self.status_var.set("Camera information loaded"))
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.root.after(0, lambda: self.status_var.set(error_msg))
    
    def update_camera_dropdown(self):
        # Clear the dropdown
        self.camera_dropdown['values'] = []
        
        if not self.all_camera_info:
            self.camera_dropdown['values'] = ["No cameras"]
            self.camera_dropdown.current(0)
            return
        
        # Add camera entries to dropdown
        dropdown_values = []
        for i, cam in enumerate(self.all_camera_info):
            model = cam.get('Model', 'Unknown')
            dropdown_text = f"Camera #{i+1}: {model}"
            dropdown_values.append(dropdown_text)
        
        self.camera_dropdown['values'] = dropdown_values
        
        # Select the first camera by default if no previous selection
        if dropdown_values and self.selected_camera_id is None:
            self.camera_dropdown.current(0)
            self.on_camera_selected()
    
    def on_camera_selected(self, event=None):
        try:
            # Get the selected index
            selected_index = self.camera_dropdown.current()
            
            if selected_index >= 0 and selected_index < len(self.all_camera_info):
                # Get camera info
                camera_info = self.all_camera_info[selected_index]
                
                # Update selected camera ID
                self.selected_camera_id = camera_info.get('Id')
                
                # Re-initialize camera with selected camera
                self.initialize_camera()
                
                # Load camera configuration
                self.load_camera_configuration()
                
                # Display camera details
                self.update_camera_details(camera_info)
                
                # Update sensor modes
                self.update_sensor_modes()
                
                # Update resolution options in video and still tabs
                self.update_resolution_options()
                
                # Update status
                self.status_var.set(f"Camera '{camera_info.get('Model', 'Unknown')}' selected")
                
        except Exception as e:
            self.status_var.set(f"Error selecting camera: {str(e)}")
    
    def update_camera_details(self, camera_info):
        # Clear text widget
        self.camera_details_text.delete(1.0, tk.END)
        
        # Display camera details
        self.camera_details_text.insert(tk.END, "Camera Details:\n\n")
        
        for key, value in camera_info.items():
            self.camera_details_text.insert(tk.END, f"{key}: {value}\n")
    
    def update_sensor_modes(self):
        try:
            # Clear text widget
            self.sensor_modes_text.delete(1.0, tk.END)
            
            # Get sensor modes
            sensor_modes = self.picam2.sensor_modes
            
            # Display sensor modes
            self.sensor_modes_text.insert(tk.END, "Available Sensor Modes:\n\n")
            
            if not sensor_modes:
                self.sensor_modes_text.insert(tk.END, "No sensor modes available")
                return
            
            for i, mode in enumerate(sensor_modes):
                self.sensor_modes_text.insert(tk.END, f"Mode #{i+1}:\n")
                
                # Display resolution
                if 'size' in mode:
                    width, height = mode['size']
                    self.sensor_modes_text.insert(tk.END, f"  Resolution: {width}x{height}\n")
                
                # Display format
                if 'format' in mode:
                    self.sensor_modes_text.insert(tk.END, f"  Format: {mode['format']}\n")
                
                # Display other properties
                for key, value in mode.items():
                    if key not in ['size', 'format']:
                        self.sensor_modes_text.insert(tk.END, f"  {key}: {value}\n")
                
                self.sensor_modes_text.insert(tk.END, "\n")
        
        except Exception as e:
            self.sensor_modes_text.insert(tk.END, f"Error retrieving sensor modes: {str(e)}")
    
    def update_resolution_options(self):
        try:
            # Get sensor modes
            sensor_modes = self.picam2.sensor_modes
            
            if not sensor_modes:
                return
            
            # Extract resolutions
            resolutions = []
            for mode in sensor_modes:
                if 'size' in mode:
                    width, height = mode['size']
                    res_str = f"{width}x{height}"
                    if res_str not in resolutions:
                        resolutions.append(res_str)
            
            # Add common video resolutions if not in list
            video_res = ["640x480", "1280x720", "1920x1080"]
            for res in video_res:
                if res not in resolutions:
                    resolutions.append(res)
            
            # Sort resolutions by total pixels (ascending)
            resolutions.sort(key=lambda x: int(x.split('x')[0]) * int(x.split('x')[1]))
            
            # Add 'Custom' option
            resolutions.append("Custom")
            
            # Update video resolution dropdown
            self.video_res_dropdown['values'] = resolutions
            
            # Set current value or default to 1280x720 for video
            if self.video_resolution.get() not in resolutions:
                if "1280x720" in resolutions:
                    self.video_resolution.set("1280x720")
                else:
                    self.video_resolution.set(resolutions[0])
            
            # Update still resolution dropdown (use all resolutions)
            self.still_res_dropdown['values'] = resolutions
            
            # Set current value or default to highest resolution for stills
            if self.still_resolution.get() not in resolutions:
                self.still_resolution.set(resolutions[-2])  # Last one before 'Custom'
        
        except Exception as e:
            self.status_var.set(f"Error updating resolution options: {str(e)}")
    
    def on_video_resolution_changed(self, event=None):
        res = self.video_resolution.get()
        if res == "Custom":
            return  # Allow custom entries
        
        try:
            width, height = res.split("x")
            self.video_custom_width.set(width)
            self.video_custom_height.set(height)
        except:
            pass
    
    def on_still_resolution_changed(self, event=None):
        res = self.still_resolution.get()
        if res == "Custom":
            return  # Allow custom entries
        
        try:
            width, height = res.split("x")
            self.still_custom_width.set(width)
            self.still_custom_height.set(height)
        except:
            pass
    
    def apply_custom_video_resolution(self):
        try:
            width = int(self.video_custom_width.get())
            height = int(self.video_custom_height.get())
            
            # Basic validation
            if width <= 0 or height <= 0:
                messagebox.showerror("Invalid Resolution", "Width and height must be positive numbers")
                return
            
            # Check if framerate is too high for resolution
            try:
                framerate = int(self.video_framerate.get())
                if width * height > 1920 * 1080 and framerate > 30:
                    messagebox.showwarning("High Framerate", 
                                        f"Framerate of {framerate}fps may be too high for {width}x{height} resolution")
            except:
                pass
            
            # Set resolution to Custom
            self.video_resolution.set("Custom")
            
            # Update status
            self.status_var.set(f"Custom video resolution set to {width}x{height}")
            
            # Save configuration
            self.save_camera_configuration()
            
        except ValueError:
            messagebox.showerror("Invalid Input", "Width and height must be valid numbers")
    
    def apply_custom_still_resolution(self):
        try:
            width = int(self.still_custom_width.get())
            height = int(self.still_custom_height.get())
            
            # Basic validation
            if width <= 0 or height <= 0:
                messagebox.showerror("Invalid Resolution", "Width and height must be positive numbers")
                return
            
            # Set resolution to Custom
            self.still_resolution.set("Custom")
            
            # Update status
            self.status_var.set(f"Custom still resolution set to {width}x{height}")
            
            # Save configuration
            self.save_camera_configuration()
            
        except ValueError:
            messagebox.showerror("Invalid Input", "Width and height must be valid numbers")
    
    def browse_directory(self, mode):
        current_dir = self.video_dir_var.get() if mode == "video" else self.still_dir_var.get()
        dir_path = filedialog.askdirectory(initialdir=current_dir)
        
        if dir_path:
            if mode == "video":
                self.video_dir_var.set(dir_path)
            else:
                self.still_dir_var.set(dir_path)
            
            # Save configuration
            self.save_camera_configuration()
    
    def start_preview(self, mode):
        if self.preview_active:
            messagebox.showinfo("Preview Active", "A preview is already running. Please close it first.")
            return
        
        # Stop any active preview
        self.stop_preview_event.set()
        if self.preview_thread and self.preview_thread.is_alive():
            self.preview_thread.join(1.0)
        
        # Reset stop event
        self.stop_preview_event.clear()
        
        # Configure preview based on mode
        if mode == "video":
            # Get video resolution
            if self.video_resolution.get() == "Custom":
                try:
                    width = int(self.video_custom_width.get())
                    height = int(self.video_custom_height.get())
                except ValueError:
                    messagebox.showerror("Invalid Resolution", "Width and height must be valid numbers")
                    return
            else:
                try:
                    width, height = map(int, self.video_resolution.get().split("x"))
                except:
                    messagebox.showerror("Invalid Resolution", "Could not parse resolution")
                    return
            
            # Create video configuration
            self.preview_config = self.picam2.create_video_configuration(
                main={"size": (width, height), "format": "RGB888"},
                lores={"size": (640, 480), "format": "YUV420"},
                display="lores"
            )
            
        else:  # still mode
            # Get still resolution
            if self.still_resolution.get() == "Custom":
                try:
                    width = int(self.still_custom_width.get())
                    height = int(self.still_custom_height.get())
                except ValueError:
                    messagebox.showerror("Invalid Resolution", "Width and height must be valid numbers")
                    return
            else:
                try:
                    width, height = map(int, self.still_resolution.get().split("x"))
                except:
                    messagebox.showerror("Invalid Resolution", "Could not parse resolution")
                    return
            
            # Create still configuration
            self.preview_config = self.picam2.create_still_configuration(
                main={"size": (width, height), "format": "RGB888"},
                lores={"size": (640, 480), "format": "YUV420"},
                display="lores"
            )
        
        # Start preview thread
        self.preview_thread = threading.Thread(target=self.run_preview, args=(10,))
        self.preview_thread.daemon = True
        self.preview_thread.start()
        
        # Show close button
        self.close_preview_btn.pack(pady=5)
    
    def run_preview(self, duration):
        try:
            # Set status
            self.status_var.set("Starting preview...")
            self.preview_active = True
            
            # Configure and start camera
            self.picam2.configure(self.preview_config)
            self.picam2.start()
            
            # Update status
            self.root.after(0, lambda: self.status_var.set(f"Preview active ({duration}s)..."))
            
            # Get preview dimensions
            canvas_width = self.preview_canvas.winfo_width()
            canvas_height = self.preview_canvas.winfo_height()
            
            start_time = time.time()
            frame_count = 0
            
            # Run preview loop
            while not self.stop_preview_event.is_set() and time.time() - start_time < duration:
                # Capture frame
                frame = self.picam2.capture_array("lores")
                
                # Convert to RGB if needed (assuming YUV420)
                if len(frame.shape) == 3 and frame.shape[2] == 3:
                    # Already RGB
                    rgb_frame = frame
                else:
                    # Need to convert from YUV
                    height, width = frame.shape[0], frame.shape[1]
                    rgb_frame = np.zeros((height, width, 3), dtype=np.uint8)
                    # This is simplified; actual YUV420 to RGB conversion is more complex
                    rgb_frame[:, :, 0] = frame[:, :, 0]  # Just using Y channel for all RGB values
                    rgb_frame[:, :, 1] = frame[:, :, 0]
                    rgb_frame[:, :, 2] = frame[:, :, 0]
                
                # Convert to PIL Image
                img = Image.fromarray(rgb_frame)
                
                # Resize to fit canvas (maintaining aspect ratio)
                img_width, img_height = img.size
                scale = min(canvas_width/img_width, canvas_height/img_height)
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                img = img.resize((new_width, new_height), Image.LANCZOS)
                
                # Convert to Tkinter PhotoImage
                photo = ImageTk.PhotoImage(image=img)
                
                # Update canvas
                self.root.after(0, lambda p=photo: self.update_preview_canvas(p, new_width, new_height))
                
                # Increment frame count
                frame_count += 1
                
                # Sleep to limit CPU usage
                time.sleep(0.033)  # ~30fps
            
            # Calculate actual FPS
            elapsed = time.time() - start_time
            fps = frame_count / elapsed if elapsed > 0 else 0
            
            # Stop the camera
            self.picam2.stop()
            
            # Update status
            self.root.after(0, lambda: self.status_var.set(f"Preview ended. Average FPS: {fps:.1f}"))
            
        except Exception as e:
            self.root.after(0, lambda: self.status_var.set(f"Preview error: {str(e)}"))
        finally:
            self.preview_active = False
            self.root.after(0, lambda: self.close_preview_btn.pack_forget())
    
    def update_preview_canvas(self, photo, width, height):
        # Store reference to photo to prevent garbage collection
        self.preview_photo = photo
        
        # Get canvas dimensions
        canvas_width = self.preview_canvas.winfo_width()
        canvas_height = self.preview_canvas.winfo_height()
        
        # Calculate position to center the image
        x = (canvas_width - width) // 2
        y = (canvas_height - height) // 2
        
        # Clear previous image
        self.preview_canvas.delete("all")
        
        # Create new image
        self.preview_canvas.create_image(x, y, anchor=tk.NW, image=photo)
    
    def stop_preview(self):
        if self.preview_active:
            self.stop_preview_event.set()
            self.status_var.set("Stopping preview...")
    
    def capture_photo(self):
        try:
            # Get still resolution
            if self.still_resolution.get() == "Custom":
                try:
                    width = int(self.still_custom_width.get())
                    height = int(self.still_custom_height.get())
                except ValueError:
                    messagebox.showerror("Invalid Resolution", "Width and height must be valid numbers")
                    return
            else:
                try:
                    width, height = map(int, self.still_resolution.get().split("x"))
                except:
                    messagebox.showerror("Invalid Resolution", "Could not parse resolution")
                    return
            
            # Configure camera for still capture
            still_config = self.picam2.create_still_configuration(
                main={"size": (width, height)}
            )
            
            # Set status
            self.status_var.set("Configuring camera for still capture...")
            
            # Configure and start camera
            self.picam2.configure(still_config)
            self.picam2.start()
            
            # Give camera time to adjust
            time.sleep(0.5)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.still_prefix_var.get()}{timestamp}{self.still_format_var.get()}"
            filepath = os.path.join(self.still_dir_var.get(), filename)
            
            # Capture image
            self.status_var.set("Capturing photo...")
            self.picam2.capture_file(filepath)
            
            # Stop camera
            self.picam2.stop()
            
            # Update status
            self.status_var.set(f"Photo saved to: {filepath}")
            
            # Update info text
            self.still_info_text.delete(1.0, tk.END)
            self.still_info_text.insert(tk.END, f"Last Photo:\n")
            self.still_info_text.insert(tk.END, f"Filename: {filename}\n")
            self.still_info_text.insert(tk.END, f"Resolution: {width}x{height}\n")
            self.still_info_text.insert(tk.END, f"Format: {self.still_format_var.get()[1:]}\n")
            self.still_info_text.insert(tk.END, f"Saved to: {self.still_dir_var.get()}\n")
            self.still_info_text.insert(tk.END, f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            # Save configuration
            self.save_camera_configuration()
            
        except Exception as e:
            self.status_var.set(f"Error capturing photo: {str(e)}")
    
    def record_video(self):
        try:
            # Get video resolution
            if self.video_resolution.get() == "Custom":
                try:
                    width = int(self.video_custom_width.get())
                    height = int(self.video_custom_height.get())
                except ValueError:
                    messagebox.showerror("Invalid Resolution", "Width and height must be valid numbers")
                    return
            else:
                try:
                    width, height = map(int, self.video_resolution.get().split("x"))
                except:
                    messagebox.showerror("Invalid Resolution", "Could not parse resolution")
                    return
            
            # Get framerate
            try:
                framerate = int(self.video_framerate.get())
                if framerate <= 0:
                    messagebox.showerror("Invalid Framerate", "Framerate must be a positive number")
                    return
            except ValueError:
                messagebox.showerror("Invalid Framerate", "Framerate must be a valid number")
                return
            
            # Get duration
            try:
                duration = int(self.video_duration_var.get())
                if duration <= 0:
                    messagebox.showerror("Invalid Duration", "Duration must be a positive number")
                    return
            except ValueError:
                messagebox.showerror("Invalid Duration", "Duration must be a valid number")
                return
            
            # Configure camera for video recording
            video_config = self.picam2.create_video_configuration(
                main={"size": (width, height)}
            )
            
            # Set status
            self.status_var.set("Configuring camera for video recording...")
            
            # Configure and start camera
            self.picam2.configure(video_config)
            self.picam2.start()
            
            # Give camera time to adjust
            time.sleep(0.5)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.video_prefix_var.get()}{timestamp}{self.video_format.get()}"
            filepath = os.path.join(self.video_dir_var.get(), filename)
            
            # Create encoder
            if self.video_encoder.get() == "H264Encoder":
                encoder = H264Encoder(bitrate=self.get_bitrate_from_quality())
            else:
                encoder = MJPEGEncoder()
            
            # Set status
            self.status_var.set(f"Recording video for {duration} seconds...")
            
            # Disable record button during recording
            self.record_btn.config(state=tk.DISABLED)
            
            # Start recording
            self.picam2.start_recording(encoder, filepath)
            
            # Wait for specified duration
            time.sleep(duration)
            
            # Stop recording
            self.picam2.stop_recording()
            
            # Stop camera
            self.picam2.stop()
            
            # Re-enable record button
            self.record_btn.config(state=tk.NORMAL)
            
            # Update status
            self.status_var.set(f"Video saved to: {filepath}")
            
            # Update info text
            self.video_info_text.delete(1.0, tk.END)
            self.video_info_text.insert(tk.END, f"Last Video:\n")
            self.video_info_text.insert(tk.END, f"Filename: {filename}\n")
            self.video_info_text.insert(tk.END, f"Resolution: {width}x{height}\n")
            self.video_info_text.insert(tk.END, f"Framerate: {framerate}fps\n")
            self.video_info_text.insert(tk.END, f"Duration: {duration}s\n")
            self.video_info_text.insert(tk.END, f"Encoder: {self.video_encoder.get()}\n")
            self.video_info_text.insert(tk.END, f"Format: {self.video_format.get()[1:]}\n")
            self.video_info_text.insert(tk.END, f"Saved to: {self.video_dir_var.get()}\n")
            self.video_info_text.insert(tk.END, f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            # Save configuration
            self.save_camera_configuration()
            
        except Exception as e:
            self.status_var.set(f"Error recording video: {str(e)}")
            self.record_btn.config(state=tk.NORMAL)
    
    def get_bitrate_from_quality(self):
        # Map quality levels to bitrates (in bps)
        quality_map = {
            "Very Low": 1_000_000,    # 1 Mbps
            "Low": 2_000_000,         # 2 Mbps
            "Medium": 4_000_000,      # 4 Mbps
            "High": 8_000_000,        # 8 Mbps
            "Very High": 16_000_000   # 16 Mbps
        }
        
        quality = self.video_quality_var.get()
        return quality_map.get(quality, 4_000_000)  # Default to Medium if not found
    
    def get_config_filename(self):
        if not self.selected_camera_id:
            return None
        
        # Create a sanitized version of camera ID for filename
        safe_id = ''.join(c if c.isalnum() else '_' for c in self.selected_camera_id)
        return os.path.join(self.config_dir, f"camera_{safe_id}.json")
    
    def save_camera_configuration(self):
        config_file = self.get_config_filename()
        if not config_file:
            return
        
        # Create configuration data
        config = {
            "camera_id": self.selected_camera_id,
            "video": {
                "resolution": self.video_resolution.get(),
                "custom_width": self.video_custom_width.get(),
                "custom_height": self.video_custom_height.get(),
                "framerate": self.video_framerate.get(),
                "encoder": self.video_encoder.get(),
                "format": self.video_format.get(),
                "quality": self.video_quality_var.get(),
                "directory": self.video_dir_var.get(),
                "prefix": self.video_prefix_var.get(),
                "duration": self.video_duration_var.get()
            },
            "still": {
                "resolution": self.still_resolution.get(),
                "custom_width": self.still_custom_width.get(),
                "custom_height": self.still_custom_height.get(),
                "format": self.still_format_var.get(),
                "directory": self.still_dir_var.get(),
                "prefix": self.still_prefix_var.get()
            }
        }
        
        try:
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            self.status_var.set(f"Error saving configuration: {str(e)}")
    
    def load_camera_configuration(self):
        config_file = self.get_config_filename()
        if not config_file or not os.path.exists(config_file):
            return
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Load video settings
            if "video" in config:
                video_cfg = config["video"]
                if "resolution" in video_cfg:
                    self.video_resolution.set(video_cfg["resolution"])
                if "custom_width" in video_cfg:
                    self.video_custom_width.set(video_cfg["custom_width"])
                if "custom_height" in video_cfg:
                    self.video_custom_height.set(video_cfg["custom_height"])
                if "framerate" in video_cfg:
                    self.video_framerate.set(video_cfg["framerate"])
                if "encoder" in video_cfg:
                    self.video_encoder.set(video_cfg["encoder"])
                if "format" in video_cfg:
                    self.video_format.set(video_cfg["format"])
                if "quality" in video_cfg:
                    self.video_quality_var.set(video_cfg["quality"])
                if "directory" in video_cfg:
                    self.video_dir_var.set(video_cfg["directory"])
                if "prefix" in video_cfg:
                    self.video_prefix_var.set(video_cfg["prefix"])
                if "duration" in video_cfg:
                    self.video_duration_var.set(video_cfg["duration"])
            
            # Load still settings
            if "still" in config:
                still_cfg = config["still"]
                if "resolution" in still_cfg:
                    self.still_resolution.set(still_cfg["resolution"])
                if "custom_width" in still_cfg:
                    self.still_custom_width.set(still_cfg["custom_width"])
                if "custom_height" in still_cfg:
                    self.still_custom_height.set(still_cfg["custom_height"])
                if "format" in still_cfg:
                    self.still_format_var.set(still_cfg["format"])
                if "directory" in still_cfg:
                    self.still_dir_var.set(still_cfg["directory"])
                if "prefix" in still_cfg:
                    self.still_prefix_var.set(still_cfg["prefix"])
            
            self.status_var.set("Camera configuration loaded")
            
        except Exception as e:
            self.status_var.set(f"Error loading configuration: {str(e)}")
    
    def refresh_camera_info(self):
        # Re-initialize camera
        self.initialize_camera()
        
        # Reload camera info
        self.load_camera_info()

def main():
    root = tk.Tk()
    app = CameraInfoApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
    