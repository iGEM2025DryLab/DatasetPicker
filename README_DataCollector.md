# Lychee Data Collection Interface

A comprehensive GUI application for collecting lychee sample data with dual camera support (RGB and NIR).

## Features

### Camera Management
- **RGB Camera**: Connect to and capture RGB images from camera index 0
- **NIR Camera**: Connect to and capture NIR (Near-Infrared) images from camera index 1
- **Live Preview**: Real-time camera feeds displayed in the interface
- **Image Capture**: Save images with automatic sample-based naming

### Data Entry
- **Sample ID**: Auto-generated sequential sample IDs (sample_001, sample_002, etc.)
- **Lychee Variation**: Dropdown selection (NMZ, GW, FZX)
- **Days After Picked**: Spinbox input for harvest age
- **Sugar Content**: Brix measurement input
- **Acid Content**: Percentage input
- **pH Level**: pH measurement input
- **Sugar/Acid Ratio**: Automatically calculated when both values are entered
- **Notes**: Free-text area for additional observations

### Data Management
- **Missing Data Handling**: Visual status indicators show which fields are missing
- **Flexible Entry**: Fields can be left empty and filled later
- **Data Export**: Export collected data as CSV
- **Backup Storage**: Automatic JSON backup of all samples
- **Load/Edit**: Support for loading and editing existing samples

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure cameras are connected:
   - RGB camera should be accessible at index 0
   - NIR camera should be accessible at index 1

## Usage

1. **Start the Application**:
```bash
python lychee_data_collector.py
```

2. **Connect Cameras**:
   - Click "Connect RGB" to connect the RGB camera
   - Click "Connect NIR" to connect the NIR camera
   - Live feeds will appear in the camera panels

3. **Enter Sample Data**:
   - Sample ID is auto-generated
   - Select lychee variation from dropdown
   - Enter days after picked
   - Fill in measurements as available (sugar, acid, pH)
   - Sugar/acid ratio calculates automatically
   - Add notes if needed

4. **Capture Images**:
   - Click "Capture RGB" to save RGB image
   - Click "Capture NIR" to save NIR image
   - Images are saved with sample ID in filename

5. **Save Sample**:
   - Click "Save Sample" to store all data
   - Data is saved to both CSV and JSON formats

6. **Continue with Next Sample**:
   - Click "New Sample" to clear fields and increment sample ID
   - Repeat the process for each sample

## Data Storage

### File Structure
```
organized/lychee_dataset/
├── images/
│   ├── rgb/           # RGB camera images
│   │   ├── sample_001_rgb.jpg
│   │   └── sample_002_rgb.jpg
│   └── nir/           # NIR camera images
│       ├── sample_001_nir.jpg
│       └── sample_002_nir.jpg
├── metadata_extended.csv  # Main data file
└── samples_backup.json    # JSON backup
```

### CSV Format
The extended metadata CSV includes all collected fields:
- sample_id
- lychee_variation
- days_after_picked
- sugar_content
- acid_content
- pH
- sugar_acid_ratio
- notes
- timestamp
- rgb_image
- nir_image

## Handling Missing Data

The interface is designed to accommodate real-world data collection where some measurements might not be available immediately:

1. **Visual Indicators**: Red "Missing" labels show unfilled fields
2. **Flexible Saving**: Samples can be saved with missing data
3. **Later Updates**: Use "Load Sample" to edit existing entries
4. **Status Tracking**: Green "Entered"/"Captured" labels confirm data entry

## Camera Setup Notes

- **RGB Camera**: Typically the default system camera (webcam)
- **NIR Camera**: May require specific NIR camera hardware
- **Camera Indices**: Adjust camera indices in code if your setup differs
- **Resolution**: Camera feeds are displayed at 320x240 for interface efficiency
- **Capture Quality**: Full resolution images are saved regardless of preview size

## Troubleshooting

### Camera Connection Issues
- Ensure cameras are not being used by other applications
- Check camera permissions in system settings
- Try different camera indices if default ones don't work
- Verify camera hardware is functioning

### Data Storage Issues
- Ensure write permissions for the organized/ directory
- Check available disk space for image storage
- Verify CSV file is not open in other applications when saving

## Extending the Interface

The modular design allows for easy customization:
- Add new measurement fields in `create_data_entry_panel()`
- Modify camera settings in camera connection methods
- Extend data export formats in `export_data()`
- Add validation rules in `save_sample()`

## Technical Requirements

- Python 3.7+
- OpenCV for camera handling
- Tkinter for GUI (usually included with Python)
- PIL/Pillow for image processing
- Two camera devices (RGB and NIR)