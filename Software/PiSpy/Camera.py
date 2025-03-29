import tkinter as tk
from tkinter import ttk
import threading
from picamera2 import Picamera2

class CameraInfoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Picamera2 Camera Information")
        self.root.geometry("800x600")
        
        # Main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create header
        header_label = ttk.Label(self.main_frame, text="Camera Information", font=("Arial", 16, "bold"))
        header_label.pack(pady=10)
        
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Create tabs
        self.camera_list_tab = ttk.Frame(self.notebook)
        self.sensor_modes_tab = ttk.Frame(self.notebook)
        self.config_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.camera_list_tab, text="Camera List")
        self.notebook.add(self.sensor_modes_tab, text="Sensor Modes")
        self.notebook.add(self.config_tab, text="Configurations")
        
        # Camera list tab content
        self.camera_list_frame = ttk.Frame(self.camera_list_tab, padding="10")
        self.camera_list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Sensor modes tab content
        self.sensor_modes_frame = ttk.Frame(self.sensor_modes_tab, padding="10")
        self.sensor_modes_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configurations tab content
        self.config_frame = ttk.Frame(self.config_tab, padding="10")
        self.config_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create text widgets for each tab
        self.camera_list_text = tk.Text(self.camera_list_frame, wrap=tk.WORD, height=20, width=80)
        self.camera_list_text.pack(fill=tk.BOTH, expand=True)
        
        self.sensor_modes_text = tk.Text(self.sensor_modes_frame, wrap=tk.WORD, height=20, width=80)
        self.sensor_modes_text.pack(fill=tk.BOTH, expand=True)
        
        self.config_text = tk.Text(self.config_frame, wrap=tk.WORD, height=20, width=80)
        self.config_text.pack(fill=tk.BOTH, expand=True)
        
        # Add scrollbars
        self.add_scrollbar(self.camera_list_frame, self.camera_list_text)
        self.add_scrollbar(self.sensor_modes_frame, self.sensor_modes_text)
        self.add_scrollbar(self.config_frame, self.config_text)
        
        # Add refresh button
        self.refresh_button = ttk.Button(self.main_frame, text="Refresh Camera Info", command=self.refresh_camera_info)
        self.refresh_button.pack(pady=10)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Load camera info when app starts
        self.load_camera_info()
    
    def add_scrollbar(self, parent, text_widget):
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.config(yscrollcommand=scrollbar.set)
    
    def load_camera_info(self):
        self.status_var.set("Loading camera information...")
        # Run camera detection in a separate thread to prevent GUI freezing
        threading.Thread(target=self.get_camera_info, daemon=True).start()
    
    def refresh_camera_info(self):
        # Clear all text widgets
        self.camera_list_text.delete(1.0, tk.END)
        self.sensor_modes_text.delete(1.0, tk.END)
        self.config_text.delete(1.0, tk.END)
        
        # Reload camera info
        self.load_camera_info()
    
    def get_camera_info(self):
        try:
            # Initialize the camera
            picam2 = Picamera2()
            
            # Get camera information
            camera_info = picam2.global_camera_info()
            
            # Update camera list text widget
            self.root.after(0, lambda: self.update_camera_list(camera_info))
            
            # Get sensor modes
            sensor_modes = picam2.sensor_modes
            self.root.after(0, lambda: self.update_sensor_modes(sensor_modes))
            
            # Get configurations
            preview_config = picam2.create_preview_configuration()
            video_config = picam2.create_video_configuration()
            still_config = picam2.create_still_configuration()
            
            # Update configurations text widget
            self.root.after(0, lambda: self.update_configurations(
                preview_config, video_config, still_config
            ))
            
            # Close the camera
            picam2.close()
            
            # Update status
            self.root.after(0, lambda: self.status_var.set("Camera information loaded successfully"))
            
        except Exception as e:
            error_msg = f"Error loading camera information: {str(e)}"
            self.root.after(0, lambda: self.status_var.set(error_msg))
            self.root.after(0, lambda: self.camera_list_text.insert(tk.END, error_msg))
    
    def update_camera_list(self, camera_info):
        self.camera_list_text.insert(tk.END, "Available Cameras:\n\n")
        if not camera_info:
            self.camera_list_text.insert(tk.END, "No cameras detected")
            return
            
        for i, cam in enumerate(camera_info):
            self.camera_list_text.insert(tk.END, f"Camera #{i+1}:\n")
            self.camera_list_text.insert(tk.END, f"  ID: {cam.get('Id', 'Unknown')}\n")
            self.camera_list_text.insert(tk.END, f"  Model: {cam.get('Model', 'Unknown')}\n")
            self.camera_list_text.insert(tk.END, f"  Location: {cam.get('Location', 'Unknown')}\n")
            
            # Add other camera properties if available
            for key, value in cam.items():
                if key not in ['Id', 'Model', 'Location']:
                    self.camera_list_text.insert(tk.END, f"  {key}: {value}\n")
            
            self.camera_list_text.insert(tk.END, "\n")
    
    def update_sensor_modes(self, sensor_modes):
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
    
    def update_configurations(self, preview_config, video_config, still_config):
        self.config_text.insert(tk.END, "Default Stream Configurations:\n\n")
        
        # Preview configuration
        self.config_text.insert(tk.END, "Preview Configuration:\n")
        self.format_configuration(self.config_text, preview_config)
        
        # Video configuration
        self.config_text.insert(tk.END, "\nVideo Configuration:\n")
        self.format_configuration(self.config_text, video_config)
        
        # Still configuration
        self.config_text.insert(tk.END, "\nStill Configuration:\n")
        self.format_configuration(self.config_text, still_config)
    
    def format_configuration(self, text_widget, config):
        if hasattr(config, 'items'):
            for key, value in config.items():
                text_widget.insert(tk.END, f"  {key}: {value}\n")
        else:
            text_widget.insert(tk.END, f"  {config}\n")

def main():
    root = tk.Tk()
    app = CameraInfoApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()