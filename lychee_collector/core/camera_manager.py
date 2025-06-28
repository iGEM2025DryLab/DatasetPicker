"""
Camera Management Module
Handles camera detection, connection, and feed management with live editing support
"""

import cv2
import numpy as np
import threading
import time
from typing import Optional, List, Dict, Callable, Tuple
import subprocess
import json


class ImageProcessor:
    """Handles real-time image processing operations"""
    
    def __init__(self):
        self.rotation_angle = 0  # 0, 90, 180, 270
        self.flip_horizontal = False
        self.flip_vertical = False
        self.crop_region = None  # (x, y, w, h) or None
        
    def reset(self):
        """Reset all processing parameters"""
        self.rotation_angle = 0
        self.flip_horizontal = False
        self.flip_vertical = False
        self.crop_region = None
    
    def set_rotation(self, angle: int):
        """Set rotation angle (0, 90, 180, 270)"""
        self.rotation_angle = angle % 360
    
    def rotate_clockwise(self):
        """Rotate 90 degrees clockwise"""
        self.rotation_angle = (self.rotation_angle + 90) % 360
    
    def rotate_counterclockwise(self):
        """Rotate 90 degrees counterclockwise"""
        self.rotation_angle = (self.rotation_angle - 90) % 360
    
    def toggle_flip_horizontal(self):
        """Toggle horizontal flip"""
        self.flip_horizontal = not self.flip_horizontal
    
    def toggle_flip_vertical(self):
        """Toggle vertical flip"""
        self.flip_vertical = not self.flip_vertical
    
    def set_crop_region(self, x: int, y: int, w: int, h: int):
        """Set crop region (x, y, width, height)"""
        self.crop_region = (x, y, w, h)
    
    def clear_crop(self):
        """Clear crop region"""
        self.crop_region = None
    
    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """Apply all processing operations to a frame"""
        if frame is None:
            return None
        
        processed = frame.copy()
        
        # Apply rotation first
        if self.rotation_angle == 90:
            processed = cv2.rotate(processed, cv2.ROTATE_90_CLOCKWISE)
        elif self.rotation_angle == 180:
            processed = cv2.rotate(processed, cv2.ROTATE_180)
        elif self.rotation_angle == 270:
            processed = cv2.rotate(processed, cv2.ROTATE_90_COUNTERCLOCKWISE)
        
        # Apply flips
        if self.flip_horizontal and self.flip_vertical:
            processed = cv2.flip(processed, -1)  # Both axes
        elif self.flip_horizontal:
            processed = cv2.flip(processed, 1)   # Horizontal
        elif self.flip_vertical:
            processed = cv2.flip(processed, 0)   # Vertical
        
        # Apply crop last (after rotation, so crop coordinates match displayed image)
        if self.crop_region:
            x, y, w, h = self.crop_region
            height, width = processed.shape[:2]
            
            # Ensure crop region is within bounds
            x = max(0, min(x, width - 1))
            y = max(0, min(y, height - 1))
            w = max(1, min(w, width - x))
            h = max(1, min(h, height - y))
            
            processed = processed[y:y+h, x:x+w]
        
        return processed
    
    def get_settings_dict(self) -> Dict:
        """Get current settings as dictionary"""
        return {
            'rotation_angle': self.rotation_angle,
            'flip_horizontal': self.flip_horizontal,
            'flip_vertical': self.flip_vertical,
            'crop_region': self.crop_region
        }
    
    def load_settings_dict(self, settings: Dict):
        """Load settings from dictionary"""
        self.rotation_angle = settings.get('rotation_angle', 0)
        self.flip_horizontal = settings.get('flip_horizontal', False)
        self.flip_vertical = settings.get('flip_vertical', False)
        self.crop_region = settings.get('crop_region', None)


class CameraFeed:
    """Manages a single camera feed with live processing"""
    
    def __init__(self, camera_index: int, name: str = "Camera"):
        self.camera_index = camera_index
        self.name = name
        self.camera = None
        self.is_active = False
        self.is_connected = False
        self.processor = ImageProcessor()
        
        # Threading for continuous capture
        self.capture_thread = None
        self.stop_capture = False
        self.current_frame = None
        self.processed_frame = None
        self.frame_lock = threading.Lock()
        
        # Frame callbacks
        self.frame_callbacks: List[Callable] = []
        
    def add_frame_callback(self, callback: Callable):
        """Add callback function to be called when new frame is available"""
        self.frame_callbacks.append(callback)
    
    def remove_frame_callback(self, callback: Callable):
        """Remove frame callback"""
        if callback in self.frame_callbacks:
            self.frame_callbacks.remove(callback)
    
    def connect(self) -> bool:
        """Connect to the camera with improved settings for iPhone"""
        try:
            # Try AVFoundation first with explicit backend
            self.camera = cv2.VideoCapture(self.camera_index, cv2.CAP_AVFOUNDATION)
            
            if self.camera.isOpened():
                # Set optimal settings for iPhone camera
                self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
                self.camera.set(cv2.CAP_PROP_FPS, 30)
                
                # Test frame capture with timeout
                ret, frame = self.camera.read()
                if ret and frame is not None:
                    self.is_connected = True
                    print(f"Camera {self.camera_index} connected successfully: {frame.shape}")
                    return True
                else:
                    print(f"Camera {self.camera_index}: Failed to read frame")
                    self.camera.release()
                    self.camera = None
            else:
                print(f"Camera {self.camera_index}: Failed to open")
                self.camera = None
            
        except Exception as e:
            print(f"Error connecting to camera {self.camera_index}: {e}")
            self.camera = None
        
        self.is_connected = False
        return False
    
    def disconnect(self):
        """Disconnect from the camera"""
        self.stop_feed()
        if self.camera:
            self.camera.release()
            self.camera = None
        self.is_connected = False
    
    def start_feed(self) -> bool:
        """Start the camera feed"""
        if not self.is_connected:
            if not self.connect():
                return False
        
        if self.is_active:
            return True
        
        self.stop_capture = False
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        self.is_active = True
        return True
    
    def stop_feed(self):
        """Stop the camera feed"""
        self.stop_capture = True
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=1.0)
        self.is_active = False
    
    def _capture_loop(self):
        """Continuous capture loop running in separate thread"""
        while not self.stop_capture and self.camera and self.camera.isOpened():
            ret, frame = self.camera.read()
            if ret:
                with self.frame_lock:
                    self.current_frame = frame.copy()
                    self.processed_frame = self.processor.process_frame(frame)
                
                # Call frame callbacks
                for callback in self.frame_callbacks:
                    try:
                        callback(self.processed_frame)
                    except Exception as e:
                        print(f"Error in frame callback: {e}")
            
            time.sleep(1/30)  # ~30 FPS
    
    def get_current_frame(self, processed: bool = True) -> Optional[np.ndarray]:
        """Get the current frame"""
        with self.frame_lock:
            if processed:
                return self.processed_frame.copy() if self.processed_frame is not None else None
            else:
                return self.current_frame.copy() if self.current_frame is not None else None
    
    def capture_frame(self, processed: bool = True) -> Optional[np.ndarray]:
        """Capture a single frame"""
        if not self.is_active or not self.camera:
            return None
        
        ret, frame = self.camera.read()
        if ret:
            if processed:
                return self.processor.process_frame(frame)
            else:
                return frame
        return None
    
    def get_camera_info(self) -> Dict:
        """Get camera information"""
        if not self.camera:
            return {}
        
        return {
            'index': self.camera_index,
            'name': self.name,
            'width': int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'fps': self.camera.get(cv2.CAP_PROP_FPS),
            'backend': self.camera.getBackendName(),
            'is_connected': self.is_connected,
            'is_active': self.is_active
        }


class CameraManager:
    """Manages multiple cameras and their feeds"""
    
    def __init__(self):
        self.available_cameras = []
        self.camera_feeds: Dict[str, CameraFeed] = {}
        self.detect_cameras()
    
    def detect_cameras(self, max_cameras: int = 20) -> List[int]:
        """Detect available cameras with improved iPhone detection"""
        available = []
        print(f"Detecting cameras (0-{max_cameras-1})...")
        
        for i in range(max_cameras):
            try:
                print(f"Testing camera {i}...")
                cap = cv2.VideoCapture(i, cv2.CAP_AVFOUNDATION)
                
                if cap.isOpened():
                    # Set buffer size to prevent lag
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    
                    # Try to read a frame with timeout
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                        backend = cap.getBackendName()
                        
                        print(f"Camera {i}: {width}x{height} ({backend})")
                        available.append(i)
                    else:
                        print(f"Camera {i}: No frame data")
                    
                    cap.release()
                else:
                    print(f"Camera {i}: Failed to open")
                    
            except Exception as e:
                print(f"Camera {i}: Exception - {e}")
        
        print(f"Found cameras: {available}")
        self.available_cameras = available
        return available
    
    def detect_iphone_camera(self) -> Optional[int]:
        """Enhanced iPhone Continuity Camera detection"""
        print("Searching for iPhone Continuity Camera...")
        
        try:
            # Method 1: Use ffmpeg to list AVFoundation devices
            result = subprocess.run([
                'ffmpeg', '-f', 'avfoundation', '-list_devices', 'true', '-i', ''
            ], capture_output=True, text=True, timeout=10)
            
            output = result.stderr
            lines = output.split('\n')
            
            print("AVFoundation devices:")
            for line in lines:
                if 'AVFoundation video devices:' in line:
                    print(line)
                elif '] ' in line and ('Camera' in line or 'iPhone' in line or 'iPad' in line):
                    print(f"  {line}")
                    
                    # Look for iPhone in device name
                    if 'iPhone' in line or 'iPad' in line:
                        try:
                            # Extract device index from [0] format
                            index_str = line.split('[')[1].split(']')[0]
                            iphone_index = int(index_str)
                            print(f"Found iPhone device at index {iphone_index}")
                            
                            # Test if this camera actually works
                            test_cap = cv2.VideoCapture(iphone_index, cv2.CAP_AVFOUNDATION)
                            if test_cap.isOpened():
                                test_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                                ret, frame = test_cap.read()
                                test_cap.release()
                                
                                if ret and frame is not None:
                                    print(f"iPhone camera {iphone_index} is functional")
                                    return iphone_index
                                else:
                                    print(f"iPhone camera {iphone_index} not responding")
                            else:
                                print(f"iPhone camera {iphone_index} failed to open")
                        except Exception as e:
                            print(f"Error parsing iPhone camera index: {e}")
            
            # Method 2: Check higher indices systematically
            print("\nTesting high-resolution cameras (potential iPhone)...")
            for i in range(2, 15):
                try:
                    cap = cv2.VideoCapture(i, cv2.CAP_AVFOUNDATION)
                    if cap.isOpened():
                        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        ret, frame = cap.read()
                        
                        if ret and frame is not None:
                            width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                            height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                            
                            print(f"Camera {i}: {width}x{height}")
                            
                            # iPhone cameras typically have high resolution
                            if width >= 1920 and height >= 1080:
                                cap.release()
                                return i
                        
                        cap.release()
                except Exception as e:
                    continue
                            
        except Exception as e:
            print(f"Error in iPhone detection: {e}")
        
        print("No iPhone camera detected")
        return None
    
    def get_camera_names(self) -> Dict[int, str]:
        """Get camera names using system_profiler"""
        camera_names = {}
        
        try:
            result = subprocess.run([
                'system_profiler', 'SPCameraDataType', '-json'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                cameras = data.get('SPCameraDataType', [])
                
                for i, camera in enumerate(cameras):
                    if i < len(self.available_cameras):
                        camera_names[self.available_cameras[i]] = camera.get('_name', f'Camera {self.available_cameras[i]}')
        except:
            pass
        
        # Fill in missing names
        for idx in self.available_cameras:
            if idx not in camera_names:
                camera_names[idx] = f"Camera {idx}"
        
        return camera_names
    
    def create_camera_feed(self, camera_index: int, feed_name: str) -> Optional[CameraFeed]:
        """Create a new camera feed"""
        if camera_index not in self.available_cameras:
            # Try to add it anyway (for iPhone camera)
            print(f"Warning: Camera {camera_index} not in detected cameras, trying anyway...")
        
        camera_names = self.get_camera_names()
        camera_name = camera_names.get(camera_index, f"Camera {camera_index}")
        
        feed = CameraFeed(camera_index, camera_name)
        self.camera_feeds[feed_name] = feed
        return feed
    
    def get_feed(self, feed_name: str) -> Optional[CameraFeed]:
        """Get camera feed by name"""
        return self.camera_feeds.get(feed_name)
    
    def remove_feed(self, feed_name: str):
        """Remove and cleanup camera feed"""
        if feed_name in self.camera_feeds:
            feed = self.camera_feeds[feed_name]
            feed.disconnect()
            del self.camera_feeds[feed_name]
    
    def get_available_camera_options(self) -> List[Tuple[int, str]]:
        """Get list of (index, name) tuples for available cameras"""
        camera_names = self.get_camera_names()
        options = []
        
        # Add detected cameras
        for idx in self.available_cameras:
            name = camera_names.get(idx, f"Camera {idx}")
            options.append((idx, name))
        
        # Try to add iPhone camera if not already in list
        iphone_idx = self.detect_iphone_camera()
        if iphone_idx is not None and iphone_idx not in self.available_cameras:
            options.append((iphone_idx, f"iPhone Camera (Index {iphone_idx})"))
        
        # Add some common iPhone camera indices to try
        for idx in [2, 3, 4, 5]:
            if idx not in [opt[0] for opt in options]:
                options.append((idx, f"Try Camera {idx} (Possible iPhone)"))
        
        return options
    
    def cleanup(self):
        """Cleanup all camera feeds"""
        for feed_name in list(self.camera_feeds.keys()):
            self.remove_feed(feed_name)