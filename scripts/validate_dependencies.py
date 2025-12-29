#!/usr/bin/env python3
"""
Dependency Validation Script for CI/CD Pipeline
Validates requirements.txt and checks ML/AI library compatibility
"""

import sys
import re
import subprocess
import pkg_resources
from typing import Dict, List, Tuple, Optional
import json
from pathlib import Path

class DependencyValidator:
    """Validates Python dependencies for the Passport Photo AI backend"""
    
    # Critical ML/AI libraries with version constraints
    CRITICAL_LIBRARIES = {
        'opencv-python-headless': {
            'min_version': '4.8.0',
            'max_version': '4.9.0',
            'description': 'OpenCV for advanced face detection'
        },
        'rembg': {
            'min_version': '2.0.0',
            'max_version': '2.1.0',
            'description': 'Background removal library'
        },
        'numpy': {
            'min_version': '1.24.0',
            'max_version': '1.26.0',
            'description': 'Numerical computing library'
        },
        'pillow': {
            'min_version': '10.0.0',
            'max_version': '11.0.0',
            'description': 'Image processing library'
        },
        'flask': {
            'min_version': '2.3.0',
            'max_version': '3.0.0',
            'description': 'Web framework'
        },
        'boto3': {
            'min_version': '1.29.0',
            'max_version': '1.35.0',
            'description': 'AWS SDK'
        }
    }
    
    # Python version compatibility
    PYTHON_MIN_VERSION = (3, 9)
    PYTHON_MAX_VERSION = (3, 12)
    
    def __init__(self, requirements_file: str = 'requirements.txt'):
        self.requirements_file = Path(requirements_file)
        self.validation_results = {
            'success': True,
            'errors': [],
            'warnings': [],
            'dependencies': {},
            'python_version': None,
            'critical_libraries': {}
        }
    
    def validate_python_version(self) -> bool:
        """Validate Python version compatibility"""
        current_version = sys.version_info[:2]
        self.validation_results['python_version'] = f"{current_version[0]}.{current_version[1]}"
        
        if current_version < self.PYTHON_MIN_VERSION:
            self.validation_results['errors'].append(
                f"Python version {current_version[0]}.{current_version[1]} is too old. "
                f"Minimum required: {self.PYTHON_MIN_VERSION[0]}.{self.PYTHON_MIN_VERSION[1]}"
            )
            return False
        
        if current_version > self.PYTHON_MAX_VERSION:
            self.validation_results['warnings'].append(
                f"Python version {current_version[0]}.{current_version[1]} is newer than tested. "
                f"Maximum tested: {self.PYTHON_MAX_VERSION[0]}.{self.PYTHON_MAX_VERSION[1]}"
            )
        
        return True
    
    def parse_requirements(self) -> Dict[str, str]:
        """Parse requirements.txt file"""
        if not self.requirements_file.exists():
            self.validation_results['errors'].append(f"Requirements file not found: {self.requirements_file}")
            return {}
        
        dependencies = {}
        try:
            with open(self.requirements_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse package==version format
                    match = re.match(r'^([a-zA-Z0-9_-]+)([>=<!=]+)([0-9.]+).*$', line)
                    if match:
                        package, operator, version = match.groups()
                        dependencies[package.lower()] = {
                            'version': version,
                            'operator': operator,
                            'line': line_num,
                            'raw': line
                        }
                    else:
                        self.validation_results['warnings'].append(
                            f"Could not parse dependency on line {line_num}: {line}"
                        )
        
        except Exception as e:
            self.validation_results['errors'].append(f"Error reading requirements file: {str(e)}")
            return {}
        
        self.validation_results['dependencies'] = dependencies
        return dependencies
    
    def validate_critical_libraries(self, dependencies: Dict[str, str]) -> bool:
        """Validate critical ML/AI libraries"""
        all_valid = True
        
        for lib_name, constraints in self.CRITICAL_LIBRARIES.items():
            lib_key = lib_name.lower()
            
            if lib_key not in dependencies:
                self.validation_results['errors'].append(
                    f"Critical library missing: {lib_name} ({constraints['description']})"
                )
                all_valid = False
                continue
            
            dep_info = dependencies[lib_key]
            version = dep_info['version']
            
            # Validate version constraints
            try:
                if not self._check_version_constraint(version, constraints['min_version'], '>='):
                    self.validation_results['errors'].append(
                        f"{lib_name} version {version} is below minimum {constraints['min_version']}"
                    )
                    all_valid = False
                
                if not self._check_version_constraint(version, constraints['max_version'], '<'):
                    self.validation_results['warnings'].append(
                        f"{lib_name} version {version} is above tested maximum {constraints['max_version']}"
                    )
                
                self.validation_results['critical_libraries'][lib_name] = {
                    'version': version,
                    'status': 'valid',
                    'description': constraints['description']
                }
                
            except Exception as e:
                self.validation_results['errors'].append(
                    f"Error validating {lib_name} version {version}: {str(e)}"
                )
                all_valid = False
        
        return all_valid
    
    def _check_version_constraint(self, version: str, constraint_version: str, operator: str) -> bool:
        """Check if version satisfies constraint"""
        try:
            req = pkg_resources.Requirement.parse(f"package{operator}{constraint_version}")
            return pkg_resources.parse_version(version) in req
        except Exception:
            # Fallback to simple string comparison
            if operator == '>=':
                return version >= constraint_version
            elif operator == '<':
                return version < constraint_version
            elif operator == '==':
                return version == constraint_version
            return True
    
    def check_installed_packages(self) -> bool:
        """Check if packages can be imported"""
        import_tests = {
            'cv2': 'OpenCV',
            'rembg': 'Background removal',
            'numpy': 'NumPy',
            'PIL': 'Pillow',
            'flask': 'Flask',
            'boto3': 'AWS SDK'
        }
        
        all_importable = True
        for module, description in import_tests.items():
            try:
                __import__(module)
                print(f"✅ {description} ({module}) - importable")
            except ImportError as e:
                self.validation_results['warnings'].append(
                    f"Cannot import {description} ({module}): {str(e)}"
                )
                all_importable = False
        
        return all_importable
    
    def validate_security(self) -> bool:
        """Run basic security validation"""
        try:
            # Check for known vulnerabilities using safety
            result = subprocess.run(
                ['safety', 'check', '--json'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                try:
                    safety_data = json.loads(result.stdout)
                    if safety_data:
                        self.validation_results['warnings'].append(
                            f"Security vulnerabilities found: {len(safety_data)} issues"
                        )
                        return False
                except json.JSONDecodeError:
                    pass
            
            return True
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.validation_results['warnings'].append(
                "Could not run security check (safety not available)"
            )
            return True
    
    def run_validation(self) -> bool:
        """Run complete dependency validation"""
        print("🔍 Starting dependency validation...")
        
        # Validate Python version
        python_valid = self.validate_python_version()
        print(f"Python version: {self.validation_results['python_version']} - {'✅' if python_valid else '❌'}")
        
        # Parse requirements
        dependencies = self.parse_requirements()
        if not dependencies:
            self.validation_results['success'] = False
            return False
        
        print(f"Found {len(dependencies)} dependencies in requirements.txt")
        
        # Validate critical libraries
        critical_valid = self.validate_critical_libraries(dependencies)
        print(f"Critical libraries: {'✅' if critical_valid else '❌'}")
        
        # Check if packages can be imported
        import_valid = self.check_installed_packages()
        print(f"Package imports: {'✅' if import_valid else '⚠️'}")
        
        # Run security validation
        security_valid = self.validate_security()
        print(f"Security check: {'✅' if security_valid else '⚠️'}")
        
        # Determine overall success
        self.validation_results['success'] = (
            python_valid and 
            critical_valid and 
            len(self.validation_results['errors']) == 0
        )
        
        return self.validation_results['success']
    
    def print_results(self):
        """Print validation results"""
        print("\n" + "="*60)
        print("DEPENDENCY VALIDATION RESULTS")
        print("="*60)
        
        if self.validation_results['success']:
            print("✅ Overall Status: PASSED")
        else:
            print("❌ Overall Status: FAILED")
        
        if self.validation_results['errors']:
            print(f"\n❌ Errors ({len(self.validation_results['errors'])}):")
            for error in self.validation_results['errors']:
                print(f"  • {error}")
        
        if self.validation_results['warnings']:
            print(f"\n⚠️  Warnings ({len(self.validation_results['warnings'])}):")
            for warning in self.validation_results['warnings']:
                print(f"  • {warning}")
        
        if self.validation_results['critical_libraries']:
            print(f"\n📦 Critical Libraries:")
            for lib, info in self.validation_results['critical_libraries'].items():
                print(f"  • {lib}: v{info['version']} - {info['description']}")
        
        print(f"\n🐍 Python Version: {self.validation_results['python_version']}")
        print(f"📄 Dependencies Found: {len(self.validation_results['dependencies'])}")
    
    def save_results(self, output_file: str = 'dependency-validation-results.json'):
        """Save validation results to JSON file"""
        with open(output_file, 'w') as f:
            json.dump(self.validation_results, f, indent=2)
        print(f"Results saved to: {output_file}")

def main():
    """Main function"""
    validator = DependencyValidator()
    
    try:
        success = validator.run_validation()
        validator.print_results()
        validator.save_results()
        
        if not success:
            print("\n❌ Dependency validation failed!")
            sys.exit(1)
        else:
            print("\n✅ Dependency validation passed!")
            sys.exit(0)
            
    except Exception as e:
        print(f"❌ Validation error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()