"""
Data Management Module
Handles sample data storage, retrieval, and management
"""

import csv
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd


class SampleData:
    """Represents a single lychee sample with all its data"""
    
    def __init__(self, sample_id: str = None):
        self.sample_id = sample_id
        self.lychee_variation = ""
        self.days_after_picked = None
        self.sugar_content = None
        self.acid_content = None
        self.ph = None
        self.sugar_acid_ratio = None
        self.notes = ""
        self.timestamp = None
        self.rgb_image = None
        self.nir_image = None
        self.rgb_processing_settings = None
        self.nir_processing_settings = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'sample_id': self.sample_id,
            'lychee_variation': self.lychee_variation,
            'days_after_picked': self.days_after_picked,
            'sugar_content': self.sugar_content,
            'acid_content': self.acid_content,
            'pH': self.ph,
            'sugar_acid_ratio': self.sugar_acid_ratio,
            'notes': self.notes,
            'timestamp': self.timestamp,
            'rgb_image': self.rgb_image,
            'nir_image': self.nir_image,
            'rgb_processing_settings': self.rgb_processing_settings,
            'nir_processing_settings': self.nir_processing_settings
        }
    
    def from_dict(self, data: Dict[str, Any]):
        """Load from dictionary"""
        self.sample_id = data.get('sample_id')
        self.lychee_variation = data.get('lychee_variation', '')
        self.days_after_picked = data.get('days_after_picked')
        self.sugar_content = data.get('sugar_content')
        self.acid_content = data.get('acid_content')
        self.ph = data.get('pH') or data.get('ph')  # Handle both cases
        self.sugar_acid_ratio = data.get('sugar_acid_ratio')
        self.notes = data.get('notes', '')
        self.timestamp = data.get('timestamp')
        self.rgb_image = data.get('rgb_image')
        self.nir_image = data.get('nir_image')
        self.rgb_processing_settings = data.get('rgb_processing_settings')
        self.nir_processing_settings = data.get('nir_processing_settings')
    
    def calculate_sugar_acid_ratio(self):
        """Calculate sugar/acid ratio if both values are available"""
        try:
            if self.sugar_content and self.acid_content:
                sugar = float(self.sugar_content)
                acid = float(self.acid_content)
                if acid > 0:
                    self.sugar_acid_ratio = round(sugar / acid, 2)
                else:
                    self.sugar_acid_ratio = None
            else:
                self.sugar_acid_ratio = None
        except (ValueError, TypeError):
            self.sugar_acid_ratio = None
    
    def is_complete(self) -> bool:
        """Check if all required fields are filled"""
        required_fields = [
            self.sample_id,
            self.lychee_variation,
            self.days_after_picked
        ]
        return all(field is not None and field != "" for field in required_fields)
    
    def get_missing_fields(self) -> List[str]:
        """Get list of missing optional fields"""
        missing = []
        
        optional_fields = {
            'sugar_content': self.sugar_content,
            'acid_content': self.acid_content,
            'pH': self.ph,
            'rgb_image': self.rgb_image,
            'nir_image': self.nir_image
        }
        
        for field_name, value in optional_fields.items():
            if value is None or value == "":
                missing.append(field_name)
        
        return missing


class DataManager:
    """Manages all sample data operations"""
    
    def __init__(self, data_directory: str = "organized/lychee_dataset"):
        self.data_directory = data_directory
        self.csv_file = os.path.join(data_directory, "metadata_extended.csv")
        self.json_backup_file = os.path.join(data_directory, "samples_backup.json")
        self.rgb_image_dir = os.path.join(data_directory, "images", "rgb")
        self.nir_image_dir = os.path.join(data_directory, "images", "nir")
        
        # Ensure directories exist
        self._create_directories()
    
    def _create_directories(self):
        """Create necessary directories"""
        os.makedirs(self.data_directory, exist_ok=True)
        os.makedirs(self.rgb_image_dir, exist_ok=True)
        os.makedirs(self.nir_image_dir, exist_ok=True)
    
    def get_next_sample_id(self) -> str:
        """Get the next available sample ID"""
        existing_samples = self.get_all_sample_ids()
        
        if not existing_samples:
            return "sample_001"
        
        # Extract numeric parts and find the maximum
        max_num = 0
        for sample_id in existing_samples:
            if sample_id.startswith('sample_'):
                try:
                    num = int(sample_id.replace('sample_', ''))
                    max_num = max(max_num, num)
                except ValueError:
                    continue
        
        return f"sample_{max_num + 1:03d}"
    
    def get_all_sample_ids(self) -> List[str]:
        """Get all existing sample IDs"""
        if not os.path.exists(self.csv_file):
            return []
        
        sample_ids = []
        try:
            df = pd.read_csv(self.csv_file)
            if 'sample_id' in df.columns:
                sample_ids = df['sample_id'].tolist()
        except Exception as e:
            print(f"Error reading CSV file: {e}")
            # Fallback to manual CSV reading
            try:
                with open(self.csv_file, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if 'sample_id' in row:
                            sample_ids.append(row['sample_id'])
            except Exception as e2:
                print(f"Error reading CSV manually: {e2}")
        
        return sample_ids
    
    def save_sample(self, sample: SampleData) -> bool:
        """Save a sample to storage"""
        try:
            # Calculate ratio if needed
            sample.calculate_sugar_acid_ratio()
            
            # Set timestamp if not set
            if not sample.timestamp:
                sample.timestamp = datetime.now().isoformat()
            
            # Save to CSV
            self._save_to_csv(sample)
            
            # Save to JSON backup
            self._save_to_json_backup(sample)
            
            return True
            
        except Exception as e:
            print(f"Error saving sample: {e}")
            return False
    
    def _save_to_csv(self, sample: SampleData):
        """Save sample to CSV file"""
        file_exists = os.path.exists(self.csv_file)
        
        fieldnames = [
            'sample_id', 'lychee_variation', 'days_after_picked', 
            'sugar_content', 'acid_content', 'pH', 'sugar_acid_ratio',
            'notes', 'timestamp', 'rgb_image', 'nir_image',
            'rgb_processing_settings', 'nir_processing_settings'
        ]
        
        # Convert processing settings to JSON strings
        data = sample.to_dict()
        if data['rgb_processing_settings']:
            data['rgb_processing_settings'] = json.dumps(data['rgb_processing_settings'])
        if data['nir_processing_settings']:
            data['nir_processing_settings'] = json.dumps(data['nir_processing_settings'])
        
        with open(self.csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(data)
    
    def _save_to_json_backup(self, sample: SampleData):
        """Save sample to JSON backup file"""
        # Load existing data
        data = []
        if os.path.exists(self.json_backup_file):
            try:
                with open(self.json_backup_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except:
                data = []
        
        # Add new sample (or update existing)
        sample_dict = sample.to_dict()
        
        # Check if sample already exists and update it
        existing_index = None
        for i, existing_sample in enumerate(data):
            if existing_sample.get('sample_id') == sample.sample_id:
                existing_index = i
                break
        
        if existing_index is not None:
            data[existing_index] = sample_dict
        else:
            data.append(sample_dict)
        
        # Save updated data
        with open(self.json_backup_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_sample(self, sample_id: str) -> Optional[SampleData]:
        """Load a specific sample"""
        if not os.path.exists(self.csv_file):
            return None
        
        try:
            df = pd.read_csv(self.csv_file)
            sample_row = df[df['sample_id'] == sample_id]
            
            if sample_row.empty:
                return None
            
            # Convert to dictionary and create sample
            row_dict = sample_row.iloc[0].to_dict()
            
            # Parse JSON settings if they exist
            if 'rgb_processing_settings' in row_dict and row_dict['rgb_processing_settings']:
                try:
                    row_dict['rgb_processing_settings'] = json.loads(row_dict['rgb_processing_settings'])
                except:
                    row_dict['rgb_processing_settings'] = None
            
            if 'nir_processing_settings' in row_dict and row_dict['nir_processing_settings']:
                try:
                    row_dict['nir_processing_settings'] = json.loads(row_dict['nir_processing_settings'])
                except:
                    row_dict['nir_processing_settings'] = None
            
            sample = SampleData()
            sample.from_dict(row_dict)
            return sample
            
        except Exception as e:
            print(f"Error loading sample {sample_id}: {e}")
            return None
    
    def get_all_samples(self) -> List[SampleData]:
        """Get all samples"""
        if not os.path.exists(self.csv_file):
            return []
        
        samples = []
        try:
            df = pd.read_csv(self.csv_file)
            
            for _, row in df.iterrows():
                row_dict = row.to_dict()
                
                # Parse JSON settings
                if 'rgb_processing_settings' in row_dict and row_dict['rgb_processing_settings']:
                    try:
                        row_dict['rgb_processing_settings'] = json.loads(row_dict['rgb_processing_settings'])
                    except:
                        row_dict['rgb_processing_settings'] = None
                
                if 'nir_processing_settings' in row_dict and row_dict['nir_processing_settings']:
                    try:
                        row_dict['nir_processing_settings'] = json.loads(row_dict['nir_processing_settings'])
                    except:
                        row_dict['nir_processing_settings'] = None
                
                sample = SampleData()
                sample.from_dict(row_dict)
                samples.append(sample)
                
        except Exception as e:
            print(f"Error loading all samples: {e}")
        
        return samples
    
    def delete_sample(self, sample_id: str) -> bool:
        """Delete a sample and its associated files"""
        try:
            if not os.path.exists(self.csv_file):
                return False
            
            # Load existing data
            df = pd.read_csv(self.csv_file)
            
            # Find the sample to get image filenames
            sample_row = df[df['sample_id'] == sample_id]
            if sample_row.empty:
                return False
            
            # Get image filenames before deletion
            rgb_image = sample_row.iloc[0].get('rgb_image')
            nir_image = sample_row.iloc[0].get('nir_image')
            
            # Remove from dataframe
            df = df[df['sample_id'] != sample_id]
            
            # Save updated CSV
            df.to_csv(self.csv_file, index=False)
            
            # Delete image files
            if rgb_image:
                rgb_path = os.path.join(self.rgb_image_dir, rgb_image)
                if os.path.exists(rgb_path):
                    os.remove(rgb_path)
            
            if nir_image:
                nir_path = os.path.join(self.nir_image_dir, nir_image)
                if os.path.exists(nir_path):
                    os.remove(nir_path)
            
            # Update JSON backup
            self._remove_from_json_backup(sample_id)
            
            return True
            
        except Exception as e:
            print(f"Error deleting sample {sample_id}: {e}")
            return False
    
    def _remove_from_json_backup(self, sample_id: str):
        """Remove sample from JSON backup"""
        if not os.path.exists(self.json_backup_file):
            return
        
        try:
            with open(self.json_backup_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Filter out the sample
            data = [sample for sample in data if sample.get('sample_id') != sample_id]
            
            with open(self.json_backup_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Error updating JSON backup: {e}")
    
    def export_csv(self, export_path: str) -> bool:
        """Export data to specified CSV file"""
        try:
            if os.path.exists(self.csv_file):
                import shutil
                shutil.copy2(self.csv_file, export_path)
                return True
            return False
        except Exception as e:
            print(f"Error exporting CSV: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get dataset statistics"""
        samples = self.get_all_samples()
        
        if not samples:
            return {}
        
        stats = {
            'total_samples': len(samples),
            'variations': {},
            'days_distribution': {},
            'missing_data': {
                'sugar_content': 0,
                'acid_content': 0,
                'pH': 0,
                'rgb_image': 0,
                'nir_image': 0
            },
            'complete_samples': 0
        }
        
        for sample in samples:
            # Count variations
            if sample.lychee_variation:
                stats['variations'][sample.lychee_variation] = stats['variations'].get(sample.lychee_variation, 0) + 1
            
            # Count days
            if sample.days_after_picked:
                day_key = f"day_{sample.days_after_picked}"
                stats['days_distribution'][day_key] = stats['days_distribution'].get(day_key, 0) + 1
            
            # Count missing data
            missing_fields = sample.get_missing_fields()
            for field in missing_fields:
                if field in stats['missing_data']:
                    stats['missing_data'][field] += 1
            
            # Count complete samples
            if sample.is_complete() and not missing_fields:
                stats['complete_samples'] += 1
        
        return stats