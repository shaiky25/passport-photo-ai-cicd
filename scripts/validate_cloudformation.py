#!/usr/bin/env python3
"""
CloudFormation Template Validation Script
Validates CloudFormation templates and parameters
"""

import os
import sys
import json
import boto3
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
import subprocess

class CloudFormationValidator:
    """Validates CloudFormation templates and configurations"""
    
    def __init__(self, template_file: str = 'cloudformation-enhanced.yaml', region: str = 'us-east-1'):
        self.template_file = Path(template_file)
        self.region = region
        self.cf_client = None
        self.validation_results = {
            'success': True,
            'errors': [],
            'warnings': [],
            'template_valid': False,
            'parameters_valid': False,
            'resources_analyzed': 0,
            'estimated_cost': 'unknown'
        }
    
    def initialize_aws_client(self) -> bool:
        """Initialize AWS CloudFormation client"""
        try:
            self.cf_client = boto3.client('cloudformation', region_name=self.region)
            
            # Test AWS credentials
            self.cf_client.describe_stacks(MaxItems=1)
            print(f"✅ AWS CloudFormation client initialized for region: {self.region}")
            return True
            
        except Exception as e:
            self.validation_results['warnings'].append(
                f"Could not initialize AWS client: {str(e)}. Will perform offline validation only."
            )
            return False
    
    def load_template(self) -> Optional[Dict]:
        """Load and parse CloudFormation template"""
        if not self.template_file.exists():
            self.validation_results['errors'].append(f"Template file not found: {self.template_file}")
            return None
        
        try:
            with open(self.template_file, 'r') as f:
                if self.template_file.suffix.lower() in ['.yaml', '.yml']:
                    template = yaml.safe_load(f)
                else:
                    template = json.load(f)
            
            print(f"✅ Template loaded: {self.template_file}")
            return template
            
        except Exception as e:
            self.validation_results['errors'].append(f"Error loading template: {str(e)}")
            return None
    
    def validate_template_structure(self, template: Dict) -> bool:
        """Validate basic CloudFormation template structure"""
        required_sections = ['AWSTemplateFormatVersion', 'Resources']
        optional_sections = ['Description', 'Parameters', 'Outputs', 'Conditions', 'Mappings']
        
        all_valid = True
        
        # Check required sections
        for section in required_sections:
            if section not in template:
                self.validation_results['errors'].append(f"Missing required section: {section}")
                all_valid = False
        
        # Validate AWSTemplateFormatVersion
        if 'AWSTemplateFormatVersion' in template:
            version = template['AWSTemplateFormatVersion']
            if version not in ['2010-09-09']:
                self.validation_results['warnings'].append(f"Unusual template version: {version}")
        
        # Count resources
        if 'Resources' in template:
            resource_count = len(template['Resources'])
            self.validation_results['resources_analyzed'] = resource_count
            print(f"📦 Found {resource_count} resources in template")
            
            if resource_count == 0:
                self.validation_results['errors'].append("No resources defined in template")
                all_valid = False
        
        return all_valid
    
    def validate_parameters(self, template: Dict) -> bool:
        """Validate template parameters"""
        if 'Parameters' not in template:
            print("ℹ️  No parameters defined in template")
            return True
        
        parameters = template['Parameters']
        all_valid = True
        
        print(f"🔧 Validating {len(parameters)} parameters...")
        
        for param_name, param_config in parameters.items():
            # Check required parameter properties
            if 'Type' not in param_config:
                self.validation_results['errors'].append(f"Parameter {param_name} missing Type")
                all_valid = False
                continue
            
            param_type = param_config['Type']
            
            # Validate parameter type
            valid_types = [
                'String', 'Number', 'List<Number>', 'CommaDelimitedList',
                'AWS::EC2::AvailabilityZone::Name', 'AWS::EC2::Image::Id',
                'AWS::EC2::Instance::Id', 'AWS::EC2::KeyPair::KeyName',
                'AWS::EC2::SecurityGroup::GroupName', 'AWS::EC2::SecurityGroup::Id',
                'AWS::EC2::Subnet::Id', 'AWS::EC2::Volume::Id', 'AWS::EC2::VPC::Id',
                'AWS::Route53::HostedZone::Id', 'AWS::SSM::Parameter::Name',
                'AWS::SSM::Parameter::Value<String>'
            ]
            
            if param_type not in valid_types:
                self.validation_results['warnings'].append(f"Parameter {param_name} has unusual type: {param_type}")
            
            # Check for default values on required parameters
            if 'Default' not in param_config and param_name.lower() in ['keypairname']:
                self.validation_results['warnings'].append(f"Parameter {param_name} has no default value")
            
            # Validate AllowedValues if present
            if 'AllowedValues' in param_config:
                allowed_values = param_config['AllowedValues']
                if not isinstance(allowed_values, list) or len(allowed_values) == 0:
                    self.validation_results['errors'].append(f"Parameter {param_name} has invalid AllowedValues")
                    all_valid = False
        
        self.validation_results['parameters_valid'] = all_valid
        return all_valid
    
    def validate_resources(self, template: Dict) -> bool:
        """Validate template resources"""
        if 'Resources' not in template:
            return False
        
        resources = template['Resources']
        all_valid = True
        
        print(f"🏗️  Validating {len(resources)} resources...")
        
        # Track resource types for analysis
        resource_types = {}
        
        for resource_name, resource_config in resources.items():
            if 'Type' not in resource_config:
                self.validation_results['errors'].append(f"Resource {resource_name} missing Type")
                all_valid = False
                continue
            
            resource_type = resource_config['Type']
            resource_types[resource_type] = resource_types.get(resource_type, 0) + 1
            
            # Validate resource naming
            if not resource_name.replace('_', '').replace('-', '').isalnum():
                self.validation_results['warnings'].append(f"Resource {resource_name} has unusual naming")
            
            # Check for Properties section
            if 'Properties' not in resource_config and resource_type not in ['AWS::CloudFormation::WaitConditionHandle']:
                self.validation_results['warnings'].append(f"Resource {resource_name} has no Properties")
        
        # Analyze resource composition
        print("📊 Resource composition:")
        for res_type, count in resource_types.items():
            print(f"  • {res_type}: {count}")
        
        # Check for common patterns
        self._validate_common_patterns(resources)
        
        return all_valid
    
    def _validate_common_patterns(self, resources: Dict):
        """Validate common CloudFormation patterns"""
        # Check for IAM roles and policies
        iam_roles = [name for name, config in resources.items() if config.get('Type') == 'AWS::IAM::Role']
        iam_policies = [name for name, config in resources.items() if config.get('Type') == 'AWS::IAM::Policy']
        
        if iam_roles:
            print(f"🔐 Found {len(iam_roles)} IAM roles")
            
        # Check for Elastic Beanstalk resources
        eb_apps = [name for name, config in resources.items() if config.get('Type') == 'AWS::ElasticBeanstalk::Application']
        eb_envs = [name for name, config in resources.items() if config.get('Type') == 'AWS::ElasticBeanstalk::Environment']
        
        if eb_apps and not eb_envs:
            self.validation_results['warnings'].append("Elastic Beanstalk application without environment")
        
        # Check for DynamoDB tables
        dynamo_tables = [name for name, config in resources.items() if config.get('Type') == 'AWS::DynamoDB::Table']
        if dynamo_tables:
            print(f"🗄️  Found {len(dynamo_tables)} DynamoDB tables")
        
        # Check for S3 buckets
        s3_buckets = [name for name, config in resources.items() if config.get('Type') == 'AWS::S3::Bucket']
        if s3_buckets:
            print(f"🪣 Found {len(s3_buckets)} S3 buckets")
    
    def validate_outputs(self, template: Dict) -> bool:
        """Validate template outputs"""
        if 'Outputs' not in template:
            self.validation_results['warnings'].append("No outputs defined in template")
            return True
        
        outputs = template['Outputs']
        all_valid = True
        
        print(f"📤 Validating {len(outputs)} outputs...")
        
        for output_name, output_config in outputs.items():
            if 'Value' not in output_config:
                self.validation_results['errors'].append(f"Output {output_name} missing Value")
                all_valid = False
            
            # Check for export names
            if 'Export' in output_config:
                export_config = output_config['Export']
                if 'Name' not in export_config:
                    self.validation_results['errors'].append(f"Output {output_name} Export missing Name")
                    all_valid = False
        
        return all_valid
    
    def validate_with_aws(self, template: Dict) -> bool:
        """Validate template using AWS CloudFormation API"""
        if not self.cf_client:
            return True  # Skip if no AWS client
        
        try:
            print("☁️  Validating template with AWS CloudFormation...")
            
            # Convert template to JSON string for API
            template_body = json.dumps(template)
            
            response = self.cf_client.validate_template(TemplateBody=template_body)
            
            print("✅ AWS CloudFormation validation passed")
            
            # Extract useful information
            if 'Parameters' in response:
                print(f"📋 AWS detected {len(response['Parameters'])} parameters")
            
            if 'Capabilities' in response:
                capabilities = response['Capabilities']
                if capabilities:
                    print(f"🔑 Required capabilities: {', '.join(capabilities)}")
            
            self.validation_results['template_valid'] = True
            return True
            
        except Exception as e:
            error_msg = str(e)
            self.validation_results['errors'].append(f"AWS validation failed: {error_msg}")
            return False
    
    def estimate_costs(self, template: Dict) -> str:
        """Provide rough cost estimation"""
        # Simple cost estimation based on resource types
        cost_estimates = {
            'AWS::ElasticBeanstalk::Environment': 'EC2 instance costs (~$20-100/month)',
            'AWS::DynamoDB::Table': 'Pay-per-request (~$1-10/month for low usage)',
            'AWS::S3::Bucket': 'Storage costs (~$0.50-5/month)',
            'AWS::IAM::Role': 'Free',
            'AWS::IAM::Policy': 'Free',
            'AWS::ElasticBeanstalk::Application': 'Free (container only)'
        }
        
        if 'Resources' not in template:
            return "Cannot estimate - no resources"
        
        resources = template['Resources']
        estimates = []
        
        for resource_name, resource_config in resources.items():
            resource_type = resource_config.get('Type', 'Unknown')
            if resource_type in cost_estimates:
                estimates.append(f"• {resource_type}: {cost_estimates[resource_type]}")
        
        if estimates:
            return "Estimated monthly costs:\n" + "\n".join(estimates)
        else:
            return "No cost estimates available"
    
    def run_validation(self) -> bool:
        """Run complete CloudFormation validation"""
        print("☁️  Starting CloudFormation template validation...")
        print("="*60)
        
        # Initialize AWS client (optional)
        aws_available = self.initialize_aws_client()
        
        # Load template
        template = self.load_template()
        if not template:
            self.validation_results['success'] = False
            return False
        
        # Validate template structure
        structure_valid = self.validate_template_structure(template)
        
        # Validate parameters
        params_valid = self.validate_parameters(template)
        
        # Validate resources
        resources_valid = self.validate_resources(template)
        
        # Validate outputs
        outputs_valid = self.validate_outputs(template)
        
        # Validate with AWS (if available)
        aws_valid = True
        if aws_available:
            aws_valid = self.validate_with_aws(template)
        
        # Generate cost estimate
        cost_estimate = self.estimate_costs(template)
        self.validation_results['estimated_cost'] = cost_estimate
        
        # Determine overall success
        self.validation_results['success'] = (
            structure_valid and 
            params_valid and 
            resources_valid and 
            outputs_valid and 
            aws_valid and
            len(self.validation_results['errors']) == 0
        )
        
        return self.validation_results['success']
    
    def print_results(self):
        """Print validation results"""
        print("\n" + "="*60)
        print("CLOUDFORMATION VALIDATION RESULTS")
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
        
        print(f"\n📊 Template Analysis:")
        print(f"  • Resources: {self.validation_results['resources_analyzed']}")
        print(f"  • Template Valid: {'✅' if self.validation_results['template_valid'] else '❌'}")
        print(f"  • Parameters Valid: {'✅' if self.validation_results['parameters_valid'] else '❌'}")
        
        if self.validation_results['estimated_cost'] != 'unknown':
            print(f"\n💰 {self.validation_results['estimated_cost']}")
    
    def save_results(self, output_file: str = 'cloudformation-validation-results.json'):
        """Save validation results to JSON file"""
        os.makedirs('test-results', exist_ok=True)
        output_path = f"test-results/{output_file}"
        
        with open(output_path, 'w') as f:
            json.dump(self.validation_results, f, indent=2)
        print(f"Results saved to: {output_path}")

def main():
    """Main function"""
    template_file = sys.argv[1] if len(sys.argv) > 1 else 'cloudformation-enhanced.yaml'
    region = sys.argv[2] if len(sys.argv) > 2 else 'us-east-1'
    
    validator = CloudFormationValidator(template_file, region)
    
    try:
        success = validator.run_validation()
        validator.print_results()
        validator.save_results()
        
        if not success:
            print("\n❌ CloudFormation validation failed!")
            sys.exit(1)
        else:
            print("\n✅ CloudFormation validation passed!")
            sys.exit(0)
            
    except Exception as e:
        print(f"❌ Validation error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()