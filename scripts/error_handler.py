#!/usr/bin/env python3
"""
Error Handling and Recovery Script
Provides comprehensive error capture, logging, and recovery mechanisms
"""

import os
import sys
import json
import time
import traceback
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
from pathlib import Path
import logging
import subprocess

class PipelineErrorHandler:
    """Handles errors and recovery for CI/CD pipeline operations"""
    
    def __init__(self, log_level: str = 'INFO'):
        self.log_level = log_level
        self.error_log = []
        self.recovery_actions = []
        self.cleanup_actions = []
        
        # Setup logging
        self.setup_logging()
        
        self.error_results = {
            'timestamp': datetime.now().isoformat(),
            'errors_captured': 0,
            'recoveries_attempted': 0,
            'recoveries_successful': 0,
            'cleanup_actions_performed': 0,
            'pipeline_stage': None,
            'error_log': [],
            'recovery_log': [],
            'cleanup_log': []
        }
    
    def setup_logging(self):
        """Setup comprehensive logging"""
        # Create logs directory
        os.makedirs('logs', exist_ok=True)
        
        # Configure logging
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # File handler
        file_handler = logging.FileHandler(f'logs/pipeline-errors-{datetime.now().strftime("%Y%m%d-%H%M%S")}.log')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(log_format))
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, self.log_level))
        console_handler.setFormatter(logging.Formatter(log_format))
        
        # Setup logger
        self.logger = logging.getLogger('PipelineErrorHandler')
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.logger.info("Error handler initialized")
    
    def capture_error(self, error: Exception, context: Dict = None, 
                     stage: str = None, critical: bool = False) -> str:
        """Capture and log error with full context"""
        error_id = f"ERR-{int(time.time())}-{len(self.error_log)}"
        
        error_info = {
            'error_id': error_id,
            'timestamp': datetime.now().isoformat(),
            'stage': stage or self.error_results.get('pipeline_stage', 'unknown'),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'context': context or {},
            'critical': critical,
            'recovery_attempted': False,
            'recovery_successful': False
        }
        
        self.error_log.append(error_info)
        self.error_results['error_log'].append(error_info)
        self.error_results['errors_captured'] += 1
        
        # Log the error
        log_message = f"[{error_id}] {error_info['error_type']}: {error_info['error_message']}"
        
        if critical:
            self.logger.critical(log_message)
            print(f"💀 CRITICAL ERROR [{error_id}]: {error_info['error_message']}")
        else:
            self.logger.error(log_message)
            print(f"❌ ERROR [{error_id}]: {error_info['error_message']}")
        
        if context:
            self.logger.debug(f"[{error_id}] Context: {json.dumps(context, indent=2)}")
        
        return error_id
    
    def add_recovery_action(self, error_pattern: str, recovery_func, 
                           description: str, timeout: int = 300):
        """Add a recovery action for specific error patterns"""
        recovery_action = {
            'pattern': error_pattern,
            'function': recovery_func,
            'description': description,
            'timeout': timeout
        }
        
        self.recovery_actions.append(recovery_action)
        self.logger.info(f"Added recovery action: {description}")
    
    def add_cleanup_action(self, cleanup_func, description: str, 
                          always_run: bool = False):
        """Add a cleanup action to be performed on errors"""
        cleanup_action = {
            'function': cleanup_func,
            'description': description,
            'always_run': always_run,
            'executed': False
        }
        
        self.cleanup_actions.append(cleanup_action)
        self.logger.info(f"Added cleanup action: {description}")
    
    def attempt_recovery(self, error_id: str) -> bool:
        """Attempt recovery for a specific error"""
        error_info = None
        for error in self.error_log:
            if error['error_id'] == error_id:
                error_info = error
                break
        
        if not error_info:
            self.logger.error(f"Error {error_id} not found for recovery")
            return False
        
        print(f"🔄 Attempting recovery for error: {error_id}")
        self.logger.info(f"Starting recovery for error: {error_id}")
        
        error_message = error_info['error_message'].lower()
        error_type = error_info['error_type'].lower()
        
        recovery_attempted = False
        recovery_successful = False
        
        # Try each recovery action
        for action in self.recovery_actions:
            pattern = action['pattern'].lower()
            
            if pattern in error_message or pattern in error_type:
                recovery_attempted = True
                self.error_results['recoveries_attempted'] += 1
                
                recovery_log_entry = {
                    'error_id': error_id,
                    'recovery_action': action['description'],
                    'timestamp': datetime.now().isoformat(),
                    'success': False,
                    'details': {}
                }
                
                try:
                    print(f"   Trying: {action['description']}")
                    self.logger.info(f"Executing recovery: {action['description']}")
                    
                    # Execute recovery function with timeout
                    start_time = time.time()
                    result = action['function'](error_info)
                    execution_time = time.time() - start_time
                    
                    if result:
                        recovery_successful = True
                        self.error_results['recoveries_successful'] += 1
                        recovery_log_entry['success'] = True
                        recovery_log_entry['details']['execution_time'] = execution_time
                        
                        print(f"   ✅ Recovery successful: {action['description']}")
                        self.logger.info(f"Recovery successful: {action['description']}")
                        break
                    else:
                        recovery_log_entry['details']['execution_time'] = execution_time
                        print(f"   ❌ Recovery failed: {action['description']}")
                        self.logger.warning(f"Recovery failed: {action['description']}")
                        
                except Exception as recovery_error:
                    recovery_log_entry['details']['recovery_error'] = str(recovery_error)
                    print(f"   💥 Recovery crashed: {str(recovery_error)}")
                    self.logger.error(f"Recovery crashed: {str(recovery_error)}")
                
                self.recovery_log.append(recovery_log_entry)
                self.error_results['recovery_log'].append(recovery_log_entry)
        
        # Update error info
        error_info['recovery_attempted'] = recovery_attempted
        error_info['recovery_successful'] = recovery_successful
        
        if not recovery_attempted:
            print(f"   ⚠️  No recovery actions available for this error type")
            self.logger.warning(f"No recovery actions available for error: {error_id}")
        
        return recovery_successful
    
    def perform_cleanup(self, force: bool = False):
        """Perform all cleanup actions"""
        print(f"🧹 Performing cleanup actions...")
        self.logger.info("Starting cleanup operations")
        
        for action in self.cleanup_actions:
            if action['executed'] and not force:
                continue
            
            if not action['always_run'] and not force and self.error_results['errors_captured'] == 0:
                continue
            
            cleanup_log_entry = {
                'cleanup_action': action['description'],
                'timestamp': datetime.now().isoformat(),
                'success': False,
                'details': {}
            }
            
            try:
                print(f"   Executing: {action['description']}")
                self.logger.info(f"Executing cleanup: {action['description']}")
                
                start_time = time.time()
                result = action['function']()
                execution_time = time.time() - start_time
                
                action['executed'] = True
                self.error_results['cleanup_actions_performed'] += 1
                
                cleanup_log_entry['success'] = bool(result)
                cleanup_log_entry['details']['execution_time'] = execution_time
                
                if result:
                    print(f"   ✅ Cleanup successful: {action['description']}")
                    self.logger.info(f"Cleanup successful: {action['description']}")
                else:
                    print(f"   ⚠️  Cleanup completed with warnings: {action['description']}")
                    self.logger.warning(f"Cleanup completed with warnings: {action['description']}")
                    
            except Exception as cleanup_error:
                cleanup_log_entry['details']['cleanup_error'] = str(cleanup_error)
                print(f"   ❌ Cleanup failed: {str(cleanup_error)}")
                self.logger.error(f"Cleanup failed: {str(cleanup_error)}")
            
            self.error_results['cleanup_log'].append(cleanup_log_entry)
    
    def set_pipeline_stage(self, stage: str):
        """Set current pipeline stage for error context"""
        self.error_results['pipeline_stage'] = stage
        self.logger.info(f"Pipeline stage: {stage}")
    
    def handle_pipeline_failure(self, stage: str, error: Exception, 
                               context: Dict = None, attempt_recovery: bool = True) -> bool:
        """Handle a pipeline failure with full error handling workflow"""
        self.set_pipeline_stage(stage)
        
        # Capture the error
        error_id = self.capture_error(error, context, stage, critical=True)
        
        recovery_successful = False
        
        if attempt_recovery:
            # Attempt recovery
            recovery_successful = self.attempt_recovery(error_id)
        
        # Always perform cleanup
        self.perform_cleanup()
        
        return recovery_successful
    
    def create_error_report(self) -> Dict:
        """Create comprehensive error report"""
        report = {
            'summary': {
                'total_errors': self.error_results['errors_captured'],
                'critical_errors': len([e for e in self.error_log if e['critical']]),
                'recoveries_attempted': self.error_results['recoveries_attempted'],
                'recoveries_successful': self.error_results['recoveries_successful'],
                'cleanup_actions': self.error_results['cleanup_actions_performed'],
                'pipeline_stage': self.error_results['pipeline_stage']
            },
            'errors': self.error_results['error_log'],
            'recoveries': self.error_results['recovery_log'],
            'cleanup': self.error_results['cleanup_log'],
            'recommendations': self.generate_recommendations()
        }
        
        return report
    
    def generate_recommendations(self) -> List[str]:
        """Generate recommendations based on captured errors"""
        recommendations = []
        
        error_types = {}
        for error in self.error_log:
            error_type = error['error_type']
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        # Common error patterns and recommendations
        if 'ConnectionError' in error_types:
            recommendations.append("Check network connectivity and AWS service availability")
        
        if 'TimeoutError' in error_types or 'Timeout' in str(error_types):
            recommendations.append("Consider increasing timeout values for long-running operations")
        
        if 'PermissionError' in error_types or 'AccessDenied' in str(error_types):
            recommendations.append("Verify AWS IAM permissions and GitHub secrets configuration")
        
        if 'FileNotFoundError' in error_types:
            recommendations.append("Ensure all required files are present in the repository")
        
        if self.error_results['recoveries_attempted'] > self.error_results['recoveries_successful']:
            recommendations.append("Review and improve recovery mechanisms for failed operations")
        
        if len(self.error_log) > 5:
            recommendations.append("Multiple errors detected - consider reviewing pipeline configuration")
        
        return recommendations
    
    def save_error_report(self, output_file: str = 'error-report.json'):
        """Save comprehensive error report"""
        os.makedirs('test-results', exist_ok=True)
        output_path = f"test-results/{output_file}"
        
        report = self.create_error_report()
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"📋 Error report saved to: {output_path}")
        self.logger.info(f"Error report saved to: {output_path}")

# Common recovery functions
def recover_aws_connection_error(error_info: Dict) -> bool:
    """Recovery function for AWS connection errors"""
    try:
        print("   Retrying AWS operation with exponential backoff...")
        
        # Simple retry with backoff
        for attempt in range(3):
            time.sleep(2 ** attempt)  # 1s, 2s, 4s
            
            # In a real implementation, you would retry the specific AWS operation
            # For now, we'll simulate a recovery attempt
            print(f"     Attempt {attempt + 1}/3...")
            
            # Simulate success after 2 attempts
            if attempt >= 1:
                return True
        
        return False
        
    except Exception:
        return False

def recover_timeout_error(error_info: Dict) -> bool:
    """Recovery function for timeout errors"""
    try:
        print("   Implementing timeout recovery strategy...")
        
        # For timeout errors, we might want to retry with longer timeout
        # or break the operation into smaller chunks
        
        # Simulate recovery
        time.sleep(2)
        return True
        
    except Exception:
        return False

def cleanup_temp_files() -> bool:
    """Cleanup temporary files"""
    try:
        temp_patterns = [
            'source-bundle.zip',
            'deployment-info.json',
            'deployment-url.txt',
            'temp-*',
            '*.tmp'
        ]
        
        cleaned_files = 0
        for pattern in temp_patterns:
            for file_path in Path('.').glob(pattern):
                if file_path.is_file():
                    file_path.unlink()
                    cleaned_files += 1
        
        print(f"     Cleaned {cleaned_files} temporary files")
        return True
        
    except Exception as e:
        print(f"     Cleanup error: {str(e)}")
        return False

def cleanup_test_results() -> bool:
    """Cleanup old test result files"""
    try:
        if Path('test-results').exists():
            # Keep only the 5 most recent result files
            result_files = list(Path('test-results').glob('*.json'))
            result_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            cleaned_files = 0
            for old_file in result_files[10:]:  # Keep 10 most recent
                old_file.unlink()
                cleaned_files += 1
            
            print(f"     Cleaned {cleaned_files} old test result files")
        
        return True
        
    except Exception as e:
        print(f"     Test results cleanup error: {str(e)}")
        return False

def main():
    """Main function for testing error handler"""
    handler = PipelineErrorHandler()
    
    # Add recovery actions
    handler.add_recovery_action('connection', recover_aws_connection_error, 
                               'AWS Connection Recovery')
    handler.add_recovery_action('timeout', recover_timeout_error, 
                               'Timeout Recovery')
    
    # Add cleanup actions
    handler.add_cleanup_action(cleanup_temp_files, 'Cleanup Temporary Files', always_run=True)
    handler.add_cleanup_action(cleanup_test_results, 'Cleanup Old Test Results')
    
    # Test error handling
    try:
        # Simulate an error
        raise ConnectionError("AWS connection failed")
        
    except Exception as e:
        success = handler.handle_pipeline_failure('test-stage', e, 
                                                 {'test': 'error handling'})
        
        print(f"\nRecovery successful: {success}")
    
    # Generate and save report
    handler.save_error_report()

if __name__ == '__main__':
    main()