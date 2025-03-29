import tkinter as tk
from tkinter import ttk
import threading
from picamera2 import Picamera2

class CameraInfoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Picamera2 Camera Information")
        self.root.geometry("800x600")
        
        # Store camera information
        self.all_camera_info = []
        self.selected_camera_index = tk.StringVar()
        
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
        
        # Setup Camera List tab with dropdown
        self.setup_camera_list_tab()
        
        # Set up other tabs with text widget and scrollbar
        self.setup_text_with_scrollbar(self.sensor_modes_tab, "sensor_modes_text")
        self.setup_text_with_scrollbar(self.config_tab, "config_text")
        
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
    
    def setup_camera_list_tab(self):
        # Create a frame for the tab content
        frame = ttk.Frame(self.camera_list_tab, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a frame for the dropdown
        dropdown_frame = ttk.Frame(frame)
        dropdown_frame.pack(fill=tk.X, expand=False, pady=(0, 10))
        
        # Create label
        dropdown_label = ttk.Label(dropdown_frame, text="Select Camera:")
        dropdown_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Create dropdown
        self.camera_dropdown = ttk.Combobox(dropdown_frame, textvariable=self.selected_camera_index, state="readonly")
        self.camera_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.camera_dropdown.bind("<<ComboboxSelected>>", self.on_camera_selected)
        
        # Create a frame for the text widget
        text_frame = ttk.Frame(frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create scrollbar
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create text widget
        self.camera_list_text = tk.Text(text_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set)
        self.camera_list_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Configure scrollbar
        scrollbar.config(command=self.camera_list_text.yview)
    
    def setup_text_with_scrollbar(self, parent, text_attr_name):
        # Create a frame to hold the text widget and scrollbar
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create vertical scrollbar
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create text widget
        text_widget = tk.Text(frame, wrap=tk.WORD, yscrollcommand=scrollbar.set)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Configure scrollbar to work with text widget
        scrollbar.config(command=text_widget.yview)
        
        # Store reference to text widget
        setattr(self, text_attr_name, text_widget)
    
    def on_camera_selected(self, event=None):
        try:
            # Get the selected index
            selected_index = self.camera_dropdown.current()
            
            if selected_index >= 0 and selected_index < len(self.all_camera_info):
                # Clear the text widget
                self.camera_list_text.delete(1.0, tk.END)
                
                # Display information for the selected camera
                self.display_camera_info(self.all_camera_info[selected_index])
        except Exception as e:
            self.status_var.set(f"Error displaying camera info: {str(e)}")
    
    def display_camera_info(self, camera_info):
        # Display camera details in the text widget
        self.camera_list_text.insert(tk.END, f"Camera Details:\n\n")
        self.camera_list_text.insert(tk.END, f"ID: {camera_info.get('Id', 'Unknown')}\n")
        self.camera_list_text.insert(tk.END, f"Model: {camera_info.get('Model', 'Unknown')}\n")
        self.camera_list_text.insert(tk.END, f"Location: {camera_info.get('Location', 'Unknown')}\n\n")
        
        # Display all other properties
        self.camera_list_text.insert(tk.END, "All Properties:\n\n")
        for key, value in camera_info.items():
            self.camera_list_text.insert(tk.END, f"{key}: {value}\n")
    
    def load_camera_info(self):
        self.status_var.set("Loading camera information...")
        # Run camera detection in a separate thread to prevent GUI freezing
        threading.Thread(target=self.get_camera_info, daemon=True).start()
    
    def refresh_camera_info(self):
        # Clear all text widgets
        self.camera_list_text.delete(1.0, tk.END)
        self.sensor_modes_text.delete(1.0, tk.END)
        self.config_text.delete(1.0, tk.END)
        
        # Reset camera info
        self.all_camera_info = []
        
        # Reload camera info
        self.load_camera_info()
    
    def get_camera_info(self):
        try:
            # Initialize the camera
            picam2 = Picamera2()
            
            # Get camera information
            self.all_camera_info = picam2.global_camera_info()
            
            # Update camera dropdown
            self.root.after(0, self.update_camera_dropdown)
            
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
    
    def update_camera_dropdown(self):
        # Clear the dropdown
        self.camera_dropdown['values'] = []
        
        if not self.all_camera_info:
            self.camera_dropdown['values'] = ["No cameras detected"]
            self.camera_dropdown.current(0)
            self.camera_list_text.delete(1.0, tk.END)
            self.camera_list_text.insert(tk.END, "No cameras detected")
            return
        
        # Add camera entries to dropdown
        dropdown_values = []
        for i, cam in enumerate(self.all_camera_info):
            model = cam.get('Model', 'Unknown Camera')
            location = cam.get('Location', '')
            dropdown_text = f"Camera #{i+1}: {model}"
            if location:
                dropdown_text += f" ({location})"
            dropdown_values.append(dropdown_text)
        
        self.camera_dropdown['values'] = dropdown_values
        
        # Select the first camera by default
        if dropdown_values:
            self.camera_dropdown.current(0)
            self.on_camera_selected()
    
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
    