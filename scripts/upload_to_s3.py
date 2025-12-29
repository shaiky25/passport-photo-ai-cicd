#!/usr/bin/env python3
"""
S3 Upload Automation Script
Handles source bundle upload to S3 with versioning and cleanup
"""

import os
import sys
import json
import time
import boto3
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from pathlib import Path
import hashlib

class S3Uploader:
    """Handles S3 upload operations for deployment bundles"""
    
    def __init__(self, region: str = 'us-east-1'):
        self.region = region
        self.s3_client = boto3.client('s3', region_name=region)
        self.upload_results = {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'region': region,
            'uploads': [],
            'cleanup_performed': False,
            'versions_managed': 0
        }
    
    def create_bucket_if_not_exists(self, bucket_name: str) -> bool:
        """Create S3 bucket if it doesn't exist"""
        try:
            # Check if bucket exists
            self.s3_client.head_bucket(Bucket=bucket_name)
            print(f"✅ Bucket exists: {bucket_name}")
            return True
            
        except self.s3_client.exceptions.NoSuchBucket:
            print(f"🪣 Creating bucket: {bucket_name}")
            
            try:
                if self.region == 'us-east-1':
                    # us-east-1 doesn't need LocationConstraint
                    self.s3_client.create_bucket(Bucket=bucket_name)
                else:
                    self.s3_client.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': self.region}
                    )
                
                # Enable versioning
                self.s3_client.put_bucket_versioning(
                    Bucket=bucket_name,
                    VersioningConfiguration={'Status': 'Enabled'}
                )
                
                # Set lifecycle policy for cleanup
                lifecycle_config = {
                    'Rules': [
                        {
                            'ID': 'DeleteOldVersions',
                            'Status': 'Enabled',
                            'Filter': {'Prefix': ''},
                            'NoncurrentVersionExpiration': {'NoncurrentDays': 30},
                            'AbortIncompleteMultipartUpload': {'DaysAfterInitiation': 7}
                        }
                    ]
                }
                
                self.s3_client.put_bucket_lifecycle_configuration(
                    Bucket=bucket_name,
                    LifecycleConfiguration=lifecycle_config
                )
                
                print(f"✅ Bucket created with versioning and lifecycle policy")
                return True
                
            except Exception as e:
                print(f"❌ Failed to create bucket: {str(e)}")
                return False
                
        except Exception as e:
            print(f"❌ Error checking bucket: {str(e)}")
            return False
    
    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate MD5 hash of file"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def upload_file(self, file_path: str, bucket_name: str, 
                   object_key: str, metadata: Dict = None) -> Tuple[bool, str, Dict]:
        """Upload file to S3 with progress monitoring"""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return False, f"File not found: {file_path}", {}
            
            file_size = file_path.stat().st_size
            file_hash = self.calculate_file_hash(str(file_path))
            
            print(f"📤 Uploading {file_path.name} ({file_size / 1024 / 1024:.1f} MB)")
            
            # Prepare metadata
            upload_metadata = {
                'file-hash': file_hash,
                'upload-timestamp': datetime.now().isoformat(),
                'file-size': str(file_size),
                'uploaded-by': 'CI-CD-Pipeline'
            }
            
            if metadata:
                upload_metadata.update(metadata)
            
            # Upload with progress callback
            def progress_callback(bytes_transferred):
                percentage = (bytes_transferred / file_size) * 100
                print(f"   Progress: {percentage:.1f}% ({bytes_transferred / 1024 / 1024:.1f} MB)")
            
            # Perform upload
            start_time = time.time()
            
            self.s3_client.upload_file(
                str(file_path),
                bucket_name,
                object_key,
                ExtraArgs={
                    'Metadata': upload_metadata,
                    'ServerSideEncryption': 'AES256'
                },
                Callback=progress_callback
            )
            
            upload_time = time.time() - start_time
            
            # Get object info
            response = self.s3_client.head_object(Bucket=bucket_name, Key=object_key)
            
            upload_info = {
                'file_path': str(file_path),
                'bucket': bucket_name,
                'key': object_key,
                'size': file_size,
                'hash': file_hash,
                'upload_time': upload_time,
                'version_id': response.get('VersionId'),
                'etag': response.get('ETag', '').strip('"'),
                's3_url': f"s3://{bucket_name}/{object_key}"
            }
            
            self.upload_results['uploads'].append(upload_info)
            
            print(f"✅ Upload completed in {upload_time:.1f}s")
            print(f"   S3 URL: s3://{bucket_name}/{object_key}")
            print(f"   Version ID: {response.get('VersionId', 'N/A')}")
            
            return True, "Upload successful", upload_info
            
        except Exception as e:
            error_msg = f"Upload failed: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg, {}
    
    def list_object_versions(self, bucket_name: str, object_key: str) -> List[Dict]:
        """List all versions of an object"""
        try:
            response = self.s3_client.list_object_versions(
                Bucket=bucket_name,
                Prefix=object_key
            )
            
            versions = []
            for version in response.get('Versions', []):
                if version['Key'] == object_key:
                    versions.append({
                        'version_id': version['VersionId'],
                        'last_modified': version['LastModified'],
                        'size': version['Size'],
                        'is_latest': version['IsLatest']
                    })
            
            # Sort by last modified (newest first)
            versions.sort(key=lambda x: x['last_modified'], reverse=True)
            return versions
            
        except Exception as e:
            print(f"⚠️  Could not list object versions: {str(e)}")
            return []
    
    def cleanup_old_versions(self, bucket_name: str, object_key: str, 
                           keep_versions: int = 5) -> bool:
        """Clean up old versions of an object"""
        try:
            print(f"🧹 Cleaning up old versions of {object_key}")
            
            versions = self.list_object_versions(bucket_name, object_key)
            
            if len(versions) <= keep_versions:
                print(f"ℹ️  Only {len(versions)} versions exist, no cleanup needed")
                return True
            
            # Keep the most recent versions, delete the rest
            versions_to_delete = versions[keep_versions:]
            
            delete_objects = []
            for version in versions_to_delete:
                delete_objects.append({
                    'Key': object_key,
                    'VersionId': version['version_id']
                })
            
            if delete_objects:
                response = self.s3_client.delete_objects(
                    Bucket=bucket_name,
                    Delete={'Objects': delete_objects}
                )
                
                deleted_count = len(response.get('Deleted', []))
                self.upload_results['versions_managed'] += deleted_count
                self.upload_results['cleanup_performed'] = True
                
                print(f"✅ Deleted {deleted_count} old versions")
                return True
            else:
                print("ℹ️  No versions to delete")
                return True
                
        except Exception as e:
            print(f"⚠️  Cleanup failed: {str(e)}")
            return False
    
    def verify_upload(self, bucket_name: str, object_key: str, 
                     expected_hash: str) -> Tuple[bool, str]:
        """Verify uploaded file integrity"""
        try:
            print(f"🔍 Verifying upload integrity...")
            
            # Get object metadata
            response = self.s3_client.head_object(Bucket=bucket_name, Key=object_key)
            
            # Check if hash matches
            stored_hash = response.get('Metadata', {}).get('file-hash')
            
            if stored_hash == expected_hash:
                print(f"✅ Upload verification successful")
                return True, "Hash verification passed"
            else:
                print(f"❌ Hash mismatch: expected {expected_hash}, got {stored_hash}")
                return False, f"Hash verification failed"
                
        except Exception as e:
            error_msg = f"Verification failed: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg
    
    def upload_source_bundle(self, bundle_path: str, application_name: str, 
                           version_label: str, environment: str = 'dev') -> bool:
        """Upload source bundle for Elastic Beanstalk deployment"""
        print(f"📦 Uploading source bundle for {application_name}")
        
        # Generate bucket name and object key
        aws_account_id = os.getenv('AWS_ACCOUNT_ID', '123456789012')
        bucket_name = f"{application_name}-deployment-{aws_account_id}"
        object_key = f"versions/{version_label}/source-bundle.zip"
        
        # Create bucket if needed
        if not self.create_bucket_if_not_exists(bucket_name):
            self.upload_results['success'] = False
            return False
        
        # Calculate file hash for verification
        file_hash = self.calculate_file_hash(bundle_path)
        
        # Prepare metadata
        metadata = {
            'application-name': application_name,
            'version-label': version_label,
            'environment': environment,
            'bundle-type': 'source-bundle'
        }
        
        # Upload file
        success, message, details = self.upload_file(
            bundle_path, bucket_name, object_key, metadata
        )
        
        if not success:
            self.upload_results['success'] = False
            return False
        
        # Verify upload
        verified, verify_msg = self.verify_upload(bucket_name, object_key, file_hash)
        
        if not verified:
            self.upload_results['success'] = False
            return False
        
        # Clean up old versions
        self.cleanup_old_versions(bucket_name, object_key)
        
        # Store deployment info for later use
        deployment_info = {
            'bucket_name': bucket_name,
            'object_key': object_key,
            'version_id': details.get('version_id'),
            's3_url': details.get('s3_url')
        }
        
        # Save deployment info to file for other scripts
        with open('deployment-info.json', 'w') as f:
            json.dump(deployment_info, f, indent=2)
        
        print(f"✅ Source bundle upload completed successfully")
        return True
    
    def save_results(self, output_file: str = 's3-upload-results.json'):
        """Save upload results to JSON file"""
        os.makedirs('test-results', exist_ok=True)
        output_path = f"test-results/{output_file}"
        
        with open(output_path, 'w') as f:
            json.dump(self.upload_results, f, indent=2, default=str)
        print(f"Results saved to: {output_path}")

def main():
    """Main function"""
    if len(sys.argv) < 4:
        print("Usage: python upload_to_s3.py <bundle_path> <application_name> <version_label> [environment] [region]")
        print("Example: python upload_to_s3.py source-bundle.zip passport-photo-ai-dev v1.0.0 dev us-east-1")
        sys.exit(1)
    
    bundle_path = sys.argv[1]
    application_name = sys.argv[2]
    version_label = sys.argv[3]
    environment = sys.argv[4] if len(sys.argv) > 4 else 'dev'
    region = sys.argv[5] if len(sys.argv) > 5 else 'us-east-1'
    
    uploader = S3Uploader(region)
    
    try:
        success = uploader.upload_source_bundle(
            bundle_path, application_name, version_label, environment
        )
        uploader.save_results()
        
        if not success:
            print("\n❌ S3 upload failed!")
            sys.exit(1)
        else:
            print("\n✅ S3 upload completed successfully!")
            sys.exit(0)
            
    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        uploader.upload_results['success'] = False
        uploader.save_results()
        sys.exit(1)

if __name__ == '__main__':
    main()