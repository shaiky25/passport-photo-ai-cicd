#!/usr/bin/env python3
"""
Source Bundle Creation Script
Creates deployment-ready ZIP archives for Elastic Beanstalk
"""

import os
import sys
import zipfile
import json
import shutil
from pathlib import Path
from typing import List, Dict, Set
import tempfile
from datetime import datetime

class SourceBundleCreator:
    """Creates source bundles for Elastic Beanstalk deployment"""
    
    def __init__(self, output_file: str = 'source-bundle.zip'):
        self.output_file = output_file
        self.temp_dir = None
        self.bundle_info = {
            'created_at': datetime.now().isoformat(),
            'files_included': [],
            'total_size': 0,
            'success': False
        }
        
        # Files and directories to include
        self.include_files = [
            'application.py',
            'cors_config.py',
            'requirements.txt'
        ]
        
        self.include_directories = [
            'services',
            'database'
        ]
        
        # Files and patterns to exclude
        self.exclude_patterns = {
            '__pycache__',
            '*.pyc',
            '*.pyo',
            '.git',
            '.gitignore',
            '.DS_Store',
            'Thumbs.db',
            '*.log',
            'test-results',
            'node_modules',
            '.env',
            '.venv',
            'venv',
            '*.zip',
            'deploy-enhanced.sh',
            'test-enhanced.py',
            '.github',
            'scripts',
            '.kiro'
        }
    
    def should_exclude(self, path: Path) -> bool:
        """Check if a file or directory should be excluded"""
        path_str = str(path)
        name = path.name
        
        # Check exact matches
        if name in self.exclude_patterns:
            return True
        
        # Check pattern matches
        for pattern in self.exclude_patterns:
            if pattern.startswith('*') and name.endswith(pattern[1:]):
                return True
            if pattern.endswith('*') and name.startswith(pattern[:-1]):
                return True
        
        # Check if any parent directory should be excluded
        for parent in path.parents:
            if parent.name in self.exclude_patterns:
                return True
        
        return False
    
    def create_ebextensions(self, bundle_dir: Path):
        """Create .ebextensions configuration"""
        ebext_dir = bundle_dir / '.ebextensions'
        ebext_dir.mkdir(exist_ok=True)
        
        # Enhanced configuration for ML/AI processing
        config = {
            'option_settings': {
                'aws:elasticbeanstalk:container:python': {
                    'WSGIPath': 'application.py'
                },
                'aws:elasticbeanstalk:environment:proxy': {
                    'ProxyServer': 'nginx'
                },
                'aws:elasticbeanstalk:container:python:staticfiles': {
                    '/static/': 'static/'
                }
            },
            'commands': {
                '01_update_system': {
                    'command': 'yum update -y'
                },
                '02_install_system_deps': {
                    'command': 'yum install -y gcc gcc-c++ cmake pkgconfig libffi-devel'
                },
                '03_install_opencv_deps': {
                    'command': 'yum install -y opencv opencv-devel opencv-python',
                    'ignoreErrors': True
                }
            },
            'container_commands': {
                '01_upgrade_pip': {
                    'command': 'source $PYTHONPATH/activate && pip install --upgrade pip setuptools wheel'
                },
                '02_install_numpy_first': {
                    'command': 'source $PYTHONPATH/activate && pip install numpy==1.24.4'
                },
                '03_install_opencv': {
                    'command': 'source $PYTHONPATH/activate && pip install opencv-python-headless==4.8.1.78'
                },
                '04_install_requirements': {
                    'command': 'source $PYTHONPATH/activate && pip install -r requirements.txt',
                    'leader_only': True
                }
            },
            'files': {
                '/opt/elasticbeanstalk/tasks/taillogs.d/01_application_logs.conf': {
                    'mode': '000644',
                    'owner': 'root',
                    'group': 'root',
                    'content': '/var/log/eb-engine.log\n/var/log/eb-hooks.log\n/opt/python/log/application.log\n'
                }
            }
        }
        
        config_file = ebext_dir / '01_enhanced.config'
        with open(config_file, 'w') as f:
            # Convert to YAML-like format for .ebextensions
            self._write_ebextensions_config(f, config)
        
        print(f"✅ Created .ebextensions configuration")
        return True
    
    def _write_ebextensions_config(self, file, config: Dict, indent: int = 0):
        """Write configuration in .ebextensions format"""
        for key, value in config.items():
            if isinstance(value, dict):
                file.write('  ' * indent + f"{key}:\n")
                self._write_ebextensions_config(file, value, indent + 1)
            elif isinstance(value, list):
                file.write('  ' * indent + f"{key}:\n")
                for item in value:
                    file.write('  ' * (indent + 1) + f"- {item}\n")
            elif isinstance(value, bool):
                file.write('  ' * indent + f"{key}: {str(value).lower()}\n")
            else:
                file.write('  ' * indent + f"{key}: {value}\n")
    
    def copy_files(self, bundle_dir: Path) -> bool:
        """Copy application files to bundle directory"""
        files_copied = 0
        
        # Copy individual files
        for file_name in self.include_files:
            file_path = Path(file_name)
            if file_path.exists() and not self.should_exclude(file_path):
                dest_path = bundle_dir / file_name
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, dest_path)
                files_copied += 1
                self.bundle_info['files_included'].append(file_name)
                print(f"📄 Copied: {file_name}")
            else:
                print(f"⚠️  Missing required file: {file_name}")
        
        # Copy directories
        for dir_name in self.include_directories:
            dir_path = Path(dir_name)
            if dir_path.exists() and dir_path.is_dir():
                dest_dir = bundle_dir / dir_name
                
                # Copy directory contents
                for item in dir_path.rglob('*'):
                    if item.is_file() and not self.should_exclude(item):
                        rel_path = item.relative_to(dir_path)
                        dest_file = dest_dir / rel_path
                        dest_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dest_file)
                        files_copied += 1
                        self.bundle_info['files_included'].append(str(item))
                
                print(f"📁 Copied directory: {dir_name}")
            else:
                print(f"⚠️  Missing directory: {dir_name}")
        
        print(f"📦 Total files copied: {files_copied}")
        return files_copied > 0
    
    def validate_bundle(self, bundle_dir: Path) -> bool:
        """Validate the created bundle"""
        required_files = ['application.py', 'requirements.txt']
        
        for req_file in required_files:
            file_path = bundle_dir / req_file
            if not file_path.exists():
                print(f"❌ Missing required file in bundle: {req_file}")
                return False
        
        # Check if .ebextensions exists
        ebext_dir = bundle_dir / '.ebextensions'
        if not ebext_dir.exists():
            print("⚠️  No .ebextensions directory found")
        
        # Check bundle size
        total_size = sum(f.stat().st_size for f in bundle_dir.rglob('*') if f.is_file())
        self.bundle_info['total_size'] = total_size
        
        size_mb = total_size / (1024 * 1024)
        print(f"📊 Bundle size: {size_mb:.2f} MB")
        
        if size_mb > 512:  # Elastic Beanstalk limit
            print("⚠️  Bundle size exceeds 512MB limit")
            return False
        
        return True
    
    def create_zip(self, bundle_dir: Path) -> bool:
        """Create ZIP file from bundle directory"""
        try:
            with zipfile.ZipFile(self.output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in bundle_dir.rglob('*'):
                    if file_path.is_file():
                        arc_name = file_path.relative_to(bundle_dir)
                        zipf.write(file_path, arc_name)
            
            # Verify ZIP file
            zip_size = Path(self.output_file).stat().st_size
            zip_size_mb = zip_size / (1024 * 1024)
            
            print(f"✅ Created ZIP bundle: {self.output_file} ({zip_size_mb:.2f} MB)")
            return True
            
        except Exception as e:
            print(f"❌ Error creating ZIP file: {str(e)}")
            return False
    
    def create_bundle_info(self):
        """Create bundle information file"""
        info_file = 'bundle-info.json'
        
        # Add additional metadata
        self.bundle_info.update({
            'bundle_file': self.output_file,
            'file_count': len(self.bundle_info['files_included']),
            'size_mb': self.bundle_info['total_size'] / (1024 * 1024)
        })
        
        with open(info_file, 'w') as f:
            json.dump(self.bundle_info, f, indent=2)
        
        print(f"📋 Bundle info saved to: {info_file}")
    
    def create_source_bundle(self) -> bool:
        """Create complete source bundle"""
        print("📦 Creating source bundle for Elastic Beanstalk...")
        print("="*60)
        
        try:
            # Create temporary directory
            self.temp_dir = tempfile.mkdtemp(prefix='eb_bundle_')
            bundle_dir = Path(self.temp_dir)
            
            print(f"🗂️  Working directory: {bundle_dir}")
            
            # Copy application files
            if not self.copy_files(bundle_dir):
                print("❌ Failed to copy files")
                return False
            
            # Create .ebextensions
            self.create_ebextensions(bundle_dir)
            
            # Validate bundle
            if not self.validate_bundle(bundle_dir):
                print("❌ Bundle validation failed")
                return False
            
            # Create ZIP file
            if not self.create_zip(bundle_dir):
                print("❌ Failed to create ZIP file")
                return False
            
            # Create bundle info
            self.bundle_info['success'] = True
            self.create_bundle_info()
            
            print("✅ Source bundle created successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error creating source bundle: {str(e)}")
            return False
            
        finally:
            # Cleanup temporary directory
            if self.temp_dir and Path(self.temp_dir).exists():
                shutil.rmtree(self.temp_dir)
    
    def print_summary(self):
        """Print bundle creation summary"""
        print("\n" + "="*60)
        print("SOURCE BUNDLE SUMMARY")
        print("="*60)
        
        if self.bundle_info['success']:
            print("✅ Status: SUCCESS")
        else:
            print("❌ Status: FAILED")
        
        print(f"📦 Bundle File: {self.output_file}")
        print(f"📊 Files Included: {self.bundle_info.get('file_count', 0)}")
        print(f"💾 Bundle Size: {self.bundle_info.get('size_mb', 0):.2f} MB")
        print(f"🕐 Created: {self.bundle_info['created_at']}")
        
        if Path(self.output_file).exists():
            print(f"✅ Bundle ready for deployment")
        else:
            print(f"❌ Bundle file not found")

def main():
    """Main function"""
    output_file = sys.argv[1] if len(sys.argv) > 1 else 'source-bundle.zip'
    
    creator = SourceBundleCreator(output_file)
    
    try:
        success = creator.create_source_bundle()
        creator.print_summary()
        
        if not success:
            print("\n❌ Source bundle creation failed!")
            sys.exit(1)
        else:
            print("\n✅ Source bundle creation completed!")
            sys.exit(0)
            
    except Exception as e:
        print(f"❌ Bundle creation error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()