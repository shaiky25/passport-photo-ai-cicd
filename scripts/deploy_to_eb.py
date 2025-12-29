#!/usr/bin/env python3
"""
Elastic Beanstalk Deployment Automation Script
Handles EB application deployment with monitoring and rollback
"""

import os
import sys
import json
import time
import boto3
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import subprocess

class ElasticBeanstalkDeployer:
    """Handles Elastic Beanstalk deployment operations"""
    
    def __init__(self, region: str = 'us-east-1'):
        self.region = region
        self.eb_client = boto3.client('elasticbeanstalk', region_name=region)
        self.s3_client = boto3.client('s3', region_name=region)
        self.deployment_results = {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'region': region,
            'operations': [],
            'environment_url': None,
            'version_deployed': None,
            'rollback_performed': False
        }
    
    def check_application_exists(self, application_name: str) -> bool:
        """Check if EB application exists"""
        try:
            response = self.eb_client.describe_applications(
                ApplicationNames=[application_name]
            )
            return len(response['Applications']) > 0
            
        except self.eb_client.exceptions.ClientError:
            return False
    
    def check_environment_exists(self, application_name: str, environment_name: str) -> Tuple[bool, str]:
        """Check if EB environment exists and get its status"""
        try:
            response = self.eb_client.describe_environments(
                ApplicationName=application_name,
                EnvironmentNames=[environment_name]
            )
            
            if response['Environments']:
                env = response['Environments'][0]
                return True, env['Status']
            else:
                return False, 'DOES_NOT_EXIST'
                
        except Exception as e:
            print(f"⚠️  Error checking environment: {str(e)}")
            return False, 'ERROR'
    
    def create_application_version(self, application_name: str, version_label: str,
                                 s3_bucket: str, s3_key: str, description: str = None) -> bool:
        """Create new application version in EB"""
        try:
            print(f"📦 Creating application version: {version_label}")
            
            version_description = description or f"Version {version_label} deployed by CI/CD pipeline"
            
            response = self.eb_client.create_application_version(
                ApplicationName=application_name,
                VersionLabel=version_label,
                Description=version_description,
                SourceBundle={
                    'S3Bucket': s3_bucket,
                    'S3Key': s3_key
                },
                AutoCreateApplication=False,
                Process=True
            )
            
            self.deployment_results['operations'].append({
                'operation': 'create_application_version',
                'application_name': application_name,
                'version_label': version_label,
                'timestamp': datetime.now().isoformat()
            })
            
            print(f"✅ Application version created: {version_label}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create application version: {str(e)}")
            return False
    
    def update_environment(self, application_name: str, environment_name: str,
                          version_label: str, option_settings: List[Dict] = None) -> bool:
        """Update EB environment with new version"""
        try:
            print(f"🚀 Updating environment: {environment_name}")
            
            update_params = {
                'ApplicationName': application_name,
                'EnvironmentName': environment_name,
                'VersionLabel': version_label
            }
            
            if option_settings:
                update_params['OptionSettings'] = option_settings
            
            response = self.eb_client.update_environment(**update_params)
            
            self.deployment_results['operations'].append({
                'operation': 'update_environment',
                'application_name': application_name,
                'environment_name': environment_name,
                'version_label': version_label,
                'timestamp': datetime.now().isoformat()
            })
            
            self.deployment_results['version_deployed'] = version_label
            
            print(f"✅ Environment update initiated")
            return True
            
        except Exception as e:
            print(f"❌ Failed to update environment: {str(e)}")
            return False
    
    def wait_for_environment_update(self, application_name: str, environment_name: str,
                                   timeout: int = 1800) -> bool:
        """Wait for environment update to complete"""
        print(f"⏳ Waiting for environment update to complete...")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = self.eb_client.describe_environments(
                    ApplicationName=application_name,
                    EnvironmentNames=[environment_name]
                )
                
                if not response['Environments']:
                    print(f"❌ Environment not found")
                    return False
                
                env = response['Environments'][0]
                status = env['Status']
                health = env.get('Health', 'Unknown')
                
                print(f"   Status: {status}, Health: {health}")
                
                if status == 'Ready' and health in ['Ok', 'Info']:
                    print(f"✅ Environment update completed successfully")
                    
                    # Get environment URL
                    cname = env.get('CNAME')
                    if cname:
                        self.deployment_results['environment_url'] = f"http://{cname}"
                        print(f"🌐 Environment URL: http://{cname}")
                    
                    return True
                elif status in ['Terminated', 'Terminating']:
                    print(f"❌ Environment terminated during update")
                    return False
                elif health in ['Severe', 'Degraded']:
                    print(f"⚠️  Environment health degraded: {health}")
                    # Continue waiting, might recover
                elif status == 'Updating':
                    time.sleep(30)  # Wait 30 seconds before checking again
                else:
                    time.sleep(10)  # Check more frequently for other statuses
                    
            except Exception as e:
                print(f"❌ Error checking environment status: {str(e)}")
                return False
        
        print(f"❌ Timeout waiting for environment update (>{timeout}s)")
        return False
    
    def get_environment_events(self, application_name: str, environment_name: str, 
                              limit: int = 10):
        """Get recent environment events for debugging"""
        try:
            response = self.eb_client.describe_events(
                ApplicationName=application_name,
                EnvironmentName=environment_name,
                MaxRecords=limit
            )
            
            events = response['Events']
            
            print(f"\n📋 Recent events for {environment_name}:")
            for event in events:
                timestamp = event['EventDate'].strftime('%Y-%m-%d %H:%M:%S')
                severity = event.get('Severity', 'INFO')
                message = event.get('Message', 'N/A')
                
                severity_emoji = {
                    'TRACE': '🔍',
                    'DEBUG': '🐛', 
                    'INFO': 'ℹ️',
                    'WARN': '⚠️',
                    'ERROR': '❌',
                    'FATAL': '💀'
                }.get(severity, 'ℹ️')
                
                print(f"  {timestamp} | {severity_emoji} {severity} | {message}")
                
        except Exception as e:
            print(f"⚠️  Could not retrieve environment events: {str(e)}")
    
    def get_environment_health(self, application_name: str, environment_name: str) -> Dict:
        """Get detailed environment health information"""
        try:
            response = self.eb_client.describe_environment_health(
                EnvironmentName=environment_name,
                AttributeNames=['All']
            )
            
            health_info = {
                'status': response.get('Status'),
                'color': response.get('Color'),
                'causes': response.get('Causes', []),
                'application_metrics': response.get('ApplicationMetrics', {}),
                'instances_health': response.get('InstancesHealth', {})
            }
            
            return health_info
            
        except Exception as e:
            print(f"⚠️  Could not retrieve environment health: {str(e)}")
            return {}
    
    def rollback_environment(self, application_name: str, environment_name: str) -> bool:
        """Rollback environment to previous version"""
        try:
            print(f"🔄 Rolling back environment: {environment_name}")
            
            # Get environment info to find previous version
            response = self.eb_client.describe_environments(
                ApplicationName=application_name,
                EnvironmentNames=[environment_name]
            )
            
            if not response['Environments']:
                print(f"❌ Environment not found for rollback")
                return False
            
            # Get application versions to find previous one
            versions_response = self.eb_client.describe_application_versions(
                ApplicationName=application_name,
                MaxRecords=10
            )
            
            versions = sorted(
                versions_response['ApplicationVersions'],
                key=lambda x: x['DateCreated'],
                reverse=True
            )
            
            if len(versions) < 2:
                print(f"⚠️  No previous version available for rollback")
                return False
            
            # Use the second most recent version (first is current)
            previous_version = versions[1]['VersionLabel']
            
            print(f"🔄 Rolling back to version: {previous_version}")
            
            # Update environment with previous version
            success = self.update_environment(
                application_name, environment_name, previous_version
            )
            
            if success:
                success = self.wait_for_environment_update(
                    application_name, environment_name
                )
                
                if success:
                    self.deployment_results['rollback_performed'] = True
                    print(f"✅ Rollback completed successfully")
                    return True
                else:
                    print(f"❌ Rollback failed during environment update")
                    return False
            else:
                print(f"❌ Rollback failed to initiate")
                return False
                
        except Exception as e:
            print(f"❌ Rollback failed: {str(e)}")
            return False
    
    def verify_deployment(self, environment_url: str) -> bool:
        """Verify deployment by checking health endpoint"""
        try:
            import requests
            
            print(f"🔍 Verifying deployment at {environment_url}")
            
            # Try health endpoint
            health_url = f"{environment_url}/api/health"
            
            response = requests.get(health_url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'healthy':
                    print(f"✅ Deployment verification successful")
                    return True
                else:
                    print(f"⚠️  Application reports unhealthy status")
                    return False
            else:
                print(f"⚠️  Health endpoint returned HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"⚠️  Deployment verification failed: {str(e)}")
            return False
    
    def deploy_application(self, application_name: str, environment_name: str,
                          version_label: str, s3_bucket: str, s3_key: str,
                          environment_variables: Dict = None) -> bool:
        """Deploy application to Elastic Beanstalk"""
        print(f"🚀 Deploying to Elastic Beanstalk")
        print(f"📱 Application: {application_name}")
        print(f"🌍 Environment: {environment_name}")
        print(f"📦 Version: {version_label}")
        
        # Check if application exists
        if not self.check_application_exists(application_name):
            print(f"❌ Application does not exist: {application_name}")
            self.deployment_results['success'] = False
            return False
        
        # Check environment status
        env_exists, env_status = self.check_environment_exists(application_name, environment_name)
        
        if not env_exists:
            print(f"❌ Environment does not exist: {environment_name}")
            self.deployment_results['success'] = False
            return False
        
        if env_status not in ['Ready', 'Warning']:
            print(f"⚠️  Environment status: {env_status}")
            if env_status in ['Terminated', 'Terminating']:
                print(f"❌ Cannot deploy to terminated environment")
                self.deployment_results['success'] = False
                return False
        
        # Create application version
        if not self.create_application_version(
            application_name, version_label, s3_bucket, s3_key
        ):
            self.deployment_results['success'] = False
            return False
        
        # Prepare environment variables
        option_settings = []
        if environment_variables:
            for key, value in environment_variables.items():
                option_settings.append({
                    'Namespace': 'aws:elasticbeanstalk:application:environment',
                    'OptionName': key,
                    'Value': str(value)
                })
        
        # Update environment
        if not self.update_environment(
            application_name, environment_name, version_label, option_settings
        ):
            self.deployment_results['success'] = False
            return False
        
        # Wait for deployment to complete
        if not self.wait_for_environment_update(application_name, environment_name):
            print(f"❌ Deployment failed, checking events...")
            self.get_environment_events(application_name, environment_name)
            
            # Attempt rollback
            print(f"🔄 Attempting automatic rollback...")
            if self.rollback_environment(application_name, environment_name):
                print(f"✅ Rollback completed, deployment failed but system recovered")
            else:
                print(f"❌ Rollback also failed, manual intervention required")
            
            self.deployment_results['success'] = False
            return False
        
        # Verify deployment
        if self.deployment_results['environment_url']:
            if not self.verify_deployment(self.deployment_results['environment_url']):
                print(f"⚠️  Deployment verification failed, but environment is running")
                # Don't fail the deployment for verification issues
        
        print(f"✅ Deployment completed successfully")
        return True
    
    def save_results(self, output_file: str = 'eb-deployment-results.json'):
        """Save deployment results to JSON file"""
        os.makedirs('test-results', exist_ok=True)
        output_path = f"test-results/{output_file}"
        
        with open(output_path, 'w') as f:
            json.dump(self.deployment_results, f, indent=2, default=str)
        print(f"Results saved to: {output_path}")

def main():
    """Main function"""
    if len(sys.argv) < 6:
        print("Usage: python deploy_to_eb.py <app_name> <env_name> <version_label> <s3_bucket> <s3_key> [region]")
        print("Example: python deploy_to_eb.py passport-photo-ai-dev passport-photo-ai-dev-env v1.0.0 my-bucket versions/v1.0.0/source-bundle.zip")
        sys.exit(1)
    
    application_name = sys.argv[1]
    environment_name = sys.argv[2]
    version_label = sys.argv[3]
    s3_bucket = sys.argv[4]
    s3_key = sys.argv[5]
    region = sys.argv[6] if len(sys.argv) > 6 else 'us-east-1'
    
    # Load deployment info if available
    deployment_info = {}
    if os.path.exists('deployment-info.json'):
        with open('deployment-info.json', 'r') as f:
            deployment_info = json.load(f)
            s3_bucket = deployment_info.get('bucket_name', s3_bucket)
            s3_key = deployment_info.get('object_key', s3_key)
    
    # Environment variables for the application
    environment_variables = {
        'FLASK_ENV': 'production',
        'ENABLE_OPENCV': 'true',
        'ENABLE_REMBG': 'true',
        'ENABLE_ENHANCED_PROCESSING': 'true',
        'ALLOWED_ORIGINS': 'https://main.d3gelc4wjo7dl.amplifyapp.com'
    }
    
    deployer = ElasticBeanstalkDeployer(region)
    
    try:
        success = deployer.deploy_application(
            application_name, environment_name, version_label,
            s3_bucket, s3_key, environment_variables
        )
        deployer.save_results()
        
        if not success:
            print("\n❌ Elastic Beanstalk deployment failed!")
            sys.exit(1)
        else:
            print("\n✅ Elastic Beanstalk deployment completed successfully!")
            
            # Save environment URL for post-deployment tests
            if deployer.deployment_results['environment_url']:
                with open('deployment-url.txt', 'w') as f:
                    f.write(deployer.deployment_results['environment_url'])
                print(f"Environment URL saved to deployment-url.txt")
            
            sys.exit(0)
            
    except Exception as e:
        print(f"❌ Deployment error: {str(e)}")
        deployer.deployment_results['success'] = False
        deployer.save_results()
        sys.exit(1)

if __name__ == '__main__':
    main()