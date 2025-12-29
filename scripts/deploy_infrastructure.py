#!/usr/bin/env python3
"""
Infrastructure Deployment Automation Script
Handles CloudFormation stack operations with rollback capabilities
"""

import os
import sys
import json
import time
import boto3
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import subprocess

class InfrastructureDeployer:
    """Handles AWS CloudFormation infrastructure deployment"""
    
    def __init__(self, region: str = 'us-east-1'):
        self.region = region
        self.cf_client = boto3.client('cloudformation', region_name=region)
        self.deployment_results = {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'region': region,
            'operations': [],
            'stack_outputs': {},
            'rollback_performed': False
        }
    
    def validate_template(self, template_path: str) -> Tuple[bool, str, Dict]:
        """Validate CloudFormation template"""
        try:
            with open(template_path, 'r') as f:
                template_body = f.read()
            
            response = self.cf_client.validate_template(TemplateBody=template_body)
            
            return True, "Template validation successful", {
                'parameters': response.get('Parameters', []),
                'capabilities': response.get('Capabilities', []),
                'description': response.get('Description', '')
            }
            
        except Exception as e:
            return False, f"Template validation failed: {str(e)}", {}
    
    def check_stack_exists(self, stack_name: str) -> Tuple[bool, str]:
        """Check if CloudFormation stack exists"""
        try:
            response = self.cf_client.describe_stacks(StackName=stack_name)
            stack = response['Stacks'][0]
            status = stack['StackStatus']
            
            return True, status
            
        except self.cf_client.exceptions.ClientError as e:
            if 'does not exist' in str(e):
                return False, 'DOES_NOT_EXIST'
            else:
                raise e
    
    def create_stack(self, stack_name: str, template_path: str, 
                    parameters: List[Dict], capabilities: List[str] = None) -> bool:
        """Create new CloudFormation stack"""
        try:
            print(f"🚀 Creating stack: {stack_name}")
            
            with open(template_path, 'r') as f:
                template_body = f.read()
            
            create_params = {
                'StackName': stack_name,
                'TemplateBody': template_body,
                'Parameters': parameters,
                'Capabilities': capabilities or ['CAPABILITY_NAMED_IAM'],
                'OnFailure': 'ROLLBACK',
                'EnableTerminationProtection': False,
                'Tags': [
                    {'Key': 'Environment', 'Value': os.getenv('ENVIRONMENT', 'dev')},
                    {'Key': 'Project', 'Value': 'passport-photo-ai'},
                    {'Key': 'ManagedBy', 'Value': 'CI-CD-Pipeline'}
                ]
            }
            
            response = self.cf_client.create_stack(**create_params)
            stack_id = response['StackId']
            
            self.deployment_results['operations'].append({
                'operation': 'create_stack',
                'stack_name': stack_name,
                'stack_id': stack_id,
                'timestamp': datetime.now().isoformat()
            })
            
            # Wait for stack creation
            return self.wait_for_stack_operation(stack_name, 'CREATE_COMPLETE')
            
        except Exception as e:
            print(f"❌ Stack creation failed: {str(e)}")
            self.deployment_results['success'] = False
            return False
    
    def update_stack(self, stack_name: str, template_path: str, 
                    parameters: List[Dict], capabilities: List[str] = None) -> bool:
        """Update existing CloudFormation stack"""
        try:
            print(f"🔄 Updating stack: {stack_name}")
            
            with open(template_path, 'r') as f:
                template_body = f.read()
            
            update_params = {
                'StackName': stack_name,
                'TemplateBody': template_body,
                'Parameters': parameters,
                'Capabilities': capabilities or ['CAPABILITY_NAMED_IAM']
            }
            
            response = self.cf_client.update_stack(**update_params)
            
            self.deployment_results['operations'].append({
                'operation': 'update_stack',
                'stack_name': stack_name,
                'timestamp': datetime.now().isoformat()
            })
            
            # Wait for stack update
            return self.wait_for_stack_operation(stack_name, 'UPDATE_COMPLETE')
            
        except self.cf_client.exceptions.ClientError as e:
            if 'No updates are to be performed' in str(e):
                print("ℹ️  No updates needed for stack")
                return True
            else:
                print(f"❌ Stack update failed: {str(e)}")
                self.deployment_results['success'] = False
                return False
        except Exception as e:
            print(f"❌ Stack update failed: {str(e)}")
            self.deployment_results['success'] = False
            return False
    
    def wait_for_stack_operation(self, stack_name: str, target_status: str, 
                                timeout: int = 1800) -> bool:
        """Wait for CloudFormation stack operation to complete"""
        print(f"⏳ Waiting for stack operation to complete...")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = self.cf_client.describe_stacks(StackName=stack_name)
                stack = response['Stacks'][0]
                current_status = stack['StackStatus']
                
                print(f"   Status: {current_status}")
                
                if current_status == target_status:
                    print(f"✅ Stack operation completed: {target_status}")
                    return True
                elif current_status.endswith('_FAILED') or current_status.endswith('_ROLLBACK_COMPLETE'):
                    print(f"❌ Stack operation failed: {current_status}")
                    self.get_stack_events(stack_name)
                    return False
                elif current_status.endswith('_IN_PROGRESS'):
                    time.sleep(30)  # Wait 30 seconds before checking again
                else:
                    print(f"⚠️  Unexpected status: {current_status}")
                    time.sleep(10)
                    
            except Exception as e:
                print(f"❌ Error checking stack status: {str(e)}")
                return False
        
        print(f"❌ Timeout waiting for stack operation (>{timeout}s)")
        return False
    
    def get_stack_events(self, stack_name: str, limit: int = 10):
        """Get recent stack events for debugging"""
        try:
            response = self.cf_client.describe_stack_events(StackName=stack_name)
            events = response['StackEvents'][:limit]
            
            print(f"\n📋 Recent stack events for {stack_name}:")
            for event in events:
                timestamp = event['Timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                resource = event.get('LogicalResourceId', 'N/A')
                status = event.get('ResourceStatus', 'N/A')
                reason = event.get('ResourceStatusReason', 'N/A')
                
                print(f"  {timestamp} | {resource} | {status}")
                if reason != 'N/A':
                    print(f"    Reason: {reason}")
                    
        except Exception as e:
            print(f"⚠️  Could not retrieve stack events: {str(e)}")
    
    def get_stack_outputs(self, stack_name: str) -> Dict:
        """Get CloudFormation stack outputs"""
        try:
            response = self.cf_client.describe_stacks(StackName=stack_name)
            stack = response['Stacks'][0]
            outputs = stack.get('Outputs', [])
            
            output_dict = {}
            for output in outputs:
                output_dict[output['OutputKey']] = {
                    'value': output['OutputValue'],
                    'description': output.get('Description', '')
                }
            
            self.deployment_results['stack_outputs'] = output_dict
            return output_dict
            
        except Exception as e:
            print(f"⚠️  Could not retrieve stack outputs: {str(e)}")
            return {}
    
    def rollback_stack(self, stack_name: str) -> bool:
        """Rollback failed stack operation"""
        try:
            print(f"🔄 Rolling back stack: {stack_name}")
            
            # Check current status
            exists, status = self.check_stack_exists(stack_name)
            
            if not exists:
                print("ℹ️  Stack does not exist, no rollback needed")
                return True
            
            if status.endswith('_FAILED'):
                # Cancel update and rollback
                try:
                    self.cf_client.cancel_update_stack(StackName=stack_name)
                    time.sleep(10)
                except:
                    pass  # Cancel might not be available
                
                # Continue with rollback
                self.cf_client.continue_update_rollback(StackName=stack_name)
                
                # Wait for rollback completion
                success = self.wait_for_stack_operation(stack_name, 'UPDATE_ROLLBACK_COMPLETE')
                
                if success:
                    self.deployment_results['rollback_performed'] = True
                    print("✅ Stack rollback completed")
                    return True
                else:
                    print("❌ Stack rollback failed")
                    return False
            else:
                print(f"ℹ️  Stack status {status} does not require rollback")
                return True
                
        except Exception as e:
            print(f"❌ Rollback failed: {str(e)}")
            return False
    
    def deploy_stack(self, stack_name: str, template_path: str, 
                    environment: str = 'dev') -> bool:
        """Deploy CloudFormation stack (create or update)"""
        print(f"🏗️  Deploying infrastructure stack: {stack_name}")
        print(f"📍 Region: {self.region}")
        print(f"🏷️  Environment: {environment}")
        
        # Validate template first
        valid, message, details = self.validate_template(template_path)
        if not valid:
            print(f"❌ {message}")
            self.deployment_results['success'] = False
            return False
        
        print(f"✅ {message}")
        
        # Prepare parameters
        parameters = [
            {
                'ParameterKey': 'ApplicationName',
                'ParameterValue': f'passport-photo-ai-{environment}'
            },
            {
                'ParameterKey': 'EnvironmentName', 
                'ParameterValue': f'passport-photo-ai-{environment}-env'
            }
        ]
        
        # Check if stack exists
        exists, status = self.check_stack_exists(stack_name)
        
        success = False
        
        if not exists:
            # Create new stack
            success = self.create_stack(stack_name, template_path, parameters)
        else:
            print(f"ℹ️  Stack exists with status: {status}")
            
            if status in ['CREATE_COMPLETE', 'UPDATE_COMPLETE']:
                # Update existing stack
                success = self.update_stack(stack_name, template_path, parameters)
            elif status.endswith('_FAILED'):
                # Try to rollback first, then update
                print("⚠️  Stack in failed state, attempting rollback...")
                if self.rollback_stack(stack_name):
                    success = self.update_stack(stack_name, template_path, parameters)
                else:
                    success = False
            else:
                print(f"⚠️  Stack in unexpected state: {status}")
                success = False
        
        if success:
            # Get stack outputs
            outputs = self.get_stack_outputs(stack_name)
            print(f"✅ Stack deployment successful")
            
            if outputs:
                print("📋 Stack outputs:")
                for key, value in outputs.items():
                    print(f"  {key}: {value['value']}")
        else:
            print(f"❌ Stack deployment failed")
            self.deployment_results['success'] = False
        
        return success
    
    def save_results(self, output_file: str = 'infrastructure-deployment-results.json'):
        """Save deployment results to JSON file"""
        os.makedirs('test-results', exist_ok=True)
        output_path = f"test-results/{output_file}"
        
        with open(output_path, 'w') as f:
            json.dump(self.deployment_results, f, indent=2)
        print(f"Results saved to: {output_path}")

def main():
    """Main function"""
    if len(sys.argv) < 3:
        print("Usage: python deploy_infrastructure.py <stack_name> <template_path> [environment] [region]")
        print("Example: python deploy_infrastructure.py passport-photo-ai-dev cloudformation-enhanced.yaml dev us-east-1")
        sys.exit(1)
    
    stack_name = sys.argv[1]
    template_path = sys.argv[2]
    environment = sys.argv[3] if len(sys.argv) > 3 else 'dev'
    region = sys.argv[4] if len(sys.argv) > 4 else 'us-east-1'
    
    deployer = InfrastructureDeployer(region)
    
    try:
        success = deployer.deploy_stack(stack_name, template_path, environment)
        deployer.save_results()
        
        if not success:
            print("\n❌ Infrastructure deployment failed!")
            sys.exit(1)
        else:
            print("\n✅ Infrastructure deployment completed successfully!")
            sys.exit(0)
            
    except Exception as e:
        print(f"❌ Deployment error: {str(e)}")
        deployer.deployment_results['success'] = False
        deployer.save_results()
        sys.exit(1)

if __name__ == '__main__':
    main()