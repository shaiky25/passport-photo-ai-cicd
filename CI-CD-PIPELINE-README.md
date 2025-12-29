# CI/CD Pipeline for Passport Photo AI Enhanced Backend

This repository contains a comprehensive CI/CD pipeline that automates the deployment of the Passport Photo AI Enhanced Backend. The pipeline handles infrastructure provisioning, pre-deployment validation, AWS deployment, and post-deployment verification.

## 🚀 Features

### Core Pipeline Capabilities
- **Infrastructure Provisioning**: Automated AWS resource creation using CloudFormation
- **Pre-deployment Validation**: Dependency checking, local testing, and security scanning
- **ML/AI Testing**: Comprehensive testing with images from `test_images` directory
- **AWS Deployment**: Automated deployment to Elastic Beanstalk with monitoring
- **Post-deployment Verification**: Health checks, performance testing, and feature validation
- **Error Handling**: Robust error handling with automatic rollback capabilities

### Testing Strategy
- **Unit Tests**: Specific scenarios and edge cases
- **Property-Based Tests**: Universal correctness properties (planned)
- **Integration Tests**: End-to-end pipeline validation
- **Performance Tests**: Response time and load testing
- **Security Scans**: Dependency vulnerability checking

### Error Handling and Recovery
- **Comprehensive Error Capture**: All pipeline errors are logged with full context
- **Automatic Recovery**: Built-in recovery mechanisms for common failure scenarios
- **Rollback Capabilities**: Automatic rollback for failed deployments
- **Cleanup Operations**: Automatic cleanup of temporary files and resources
- **Detailed Reporting**: Comprehensive error reports with recommendations

## 📁 Project Structure

```
.github/workflows/
├── deploy.yml          # Main deployment workflow
└── test.yml           # Test suite workflow

scripts/
├── validate_dependencies.py    # Dependency validation
├── run_local_tests.py          # Local application testing
├── validate_image_processing.py # ML/AI image processing tests
├── validate_cloudformation.py   # CloudFormation template validation
├── create_source_bundle.py     # Deployment bundle creation
├── deploy_infrastructure.py    # Infrastructure deployment automation
├── upload_to_s3.py            # S3 upload with versioning
├── deploy_to_eb.py            # Elastic Beanstalk deployment
├── run_health_checks.py        # Post-deployment health checks
├── test_ml_features.py         # ML/AI feature testing
├── test_performance.py         # Performance testing
├── test_cors.py               # CORS functionality testing
└── error_handler.py           # Error handling and recovery

test-results/                   # Generated test results
└── *.json                     # Test result files
```

## 🛠️ Setup and Configuration

### Prerequisites

1. **AWS Account** with appropriate permissions
2. **GitHub Repository** with Actions enabled
3. **AWS CLI** configured locally (for manual testing)
4. **Python 3.9+** for running scripts locally

### GitHub Actions Secrets

Configure these secrets in your GitHub repository:

```
AWS_ACCESS_KEY_ID       # AWS access key
AWS_SECRET_ACCESS_KEY   # AWS secret key
AWS_ACCOUNT_ID          # Your AWS account ID (for S3 bucket naming)
```

### Environment Configuration

The pipeline supports multiple environments:
- **dev**: Development environment (feature branches)
- **staging**: Staging environment (develop branch)
- **prod**: Production environment (main branch)

## 🚀 Usage

### Automatic Deployment

The pipeline triggers automatically on:
- **Push to main**: Deploys to production
- **Push to develop**: Deploys to staging
- **Push to feature branches**: Deploys to development
- **Pull requests**: Runs tests only

### Manual Deployment

You can trigger manual deployments using GitHub Actions workflow dispatch:

1. Go to **Actions** tab in your GitHub repository
2. Select **CI/CD Pipeline - Passport Photo AI Enhanced Backend**
3. Click **Run workflow**
4. Choose environment and options

### Local Testing

You can run individual pipeline components locally:

```bash
# Validate dependencies
python scripts/validate_dependencies.py

# Run local tests
python scripts/run_local_tests.py

# Validate CloudFormation template
python scripts/validate_cloudformation.py

# Test image processing (requires test_images directory)
python scripts/validate_image_processing.py

# Create deployment bundle
python scripts/create_source_bundle.py

# Run health checks (requires deployed application)
python scripts/run_health_checks.py http://your-app-url.com

# Test ML/AI features (requires deployed application)
python scripts/test_ml_features.py http://your-app-url.com

# Test performance (requires deployed application)
python scripts/test_performance.py http://your-app-url.com

# Test CORS functionality (requires deployed application)
python scripts/test_cors.py http://your-app-url.com

# Deploy infrastructure (CloudFormation)
python scripts/deploy_infrastructure.py stack-name cloudformation-enhanced.yaml dev us-east-1

# Upload source bundle to S3
python scripts/upload_to_s3.py source-bundle.zip app-name version-label dev us-east-1

# Deploy to Elastic Beanstalk
python scripts/deploy_to_eb.py app-name env-name version-label s3-bucket s3-key us-east-1
```

## 📊 Pipeline Stages

### 1. Pre-Deployment Validation

**Purpose**: Validate code and dependencies before deployment

**Steps**:
- Dependency validation (ML/AI library compatibility)
- Local application testing
- Security vulnerability scanning
- Image processing validation with `test_images`
- CORS configuration testing

**Success Criteria**: All validation checks pass

### 2. Infrastructure Provisioning

**Purpose**: Create and configure AWS resources

**Steps**:
- CloudFormation template validation
- AWS resource creation/update
- Resource configuration verification
- Stack output collection

**Success Criteria**: All AWS resources created successfully

### 3. Application Deployment

**Purpose**: Deploy application to Elastic Beanstalk

**Steps**:
- Source bundle creation
- S3 upload
- Elastic Beanstalk deployment
- Environment variable configuration
- Deployment monitoring

**Success Criteria**: Application deployed and accessible

### 4. Post-Deployment Verification

**Purpose**: Verify deployed application functionality

**Steps**:
- Comprehensive health checks
- ML/AI feature testing with `test_images`
- Performance validation
- CORS functionality testing
- Error handling verification

**Success Criteria**: All tests pass with acceptable performance

## 🧪 Testing with test_images Directory

The pipeline includes comprehensive ML/AI testing using images from the `test_images` directory:

### Supported Image Formats
- JPEG (.jpg, .jpeg)
- PNG (.png)
- BMP (.bmp)
- TIFF (.tiff)
- WebP (.webp)

### ML/AI Tests Performed
1. **Face Detection**: Tests OpenCV-based face detection
2. **Background Removal**: Tests rembg functionality
3. **Image Enhancement**: Tests image processing pipeline
4. **Performance**: Measures processing times
5. **Error Handling**: Tests with various image types

### Adding Test Images
1. Place images in the `test_images/` directory
2. Ensure images are in supported formats
3. Include various scenarios (single face, multiple faces, no faces)
4. Keep file sizes reasonable (< 10MB per image)

## 📈 Monitoring and Observability

### Test Results
All test results are saved as JSON files in the `test-results/` directory:
- `dependency-validation-results.json`
- `local-test-results.json`
- `image-processing-validation-results.json`
- `cloudformation-validation-results.json`
- `health-check-results.json`
- `ml-feature-test-results.json`
- `performance-test-results.json`
- `cors-test-results.json`

### GitHub Actions Artifacts
Test results and logs are uploaded as GitHub Actions artifacts for each pipeline run.

### CloudWatch Integration
The deployed application includes CloudWatch logging and monitoring for production observability.

## 🔧 Customization

### Adding New Tests
1. Create a new script in the `scripts/` directory
2. Follow the existing pattern for test result reporting
3. Add the script to the appropriate workflow stage
4. Update this README with documentation

### Modifying Environments
1. Update the workflow files in `.github/workflows/`
2. Modify environment-specific parameters
3. Update CloudFormation templates if needed
4. Test changes in a development environment first

### Changing Performance Thresholds
Edit the performance thresholds in:
- `scripts/test_performance.py` (response time limits)
- `scripts/run_health_checks.py` (health check criteria)
- Workflow files (timeout values)

## 🚨 Troubleshooting

### Common Issues

#### 1. AWS Credentials
**Problem**: AWS authentication failures
**Solution**: 
- Verify GitHub secrets are set correctly
- Check AWS IAM permissions
- Ensure AWS account ID is correct

#### 2. CloudFormation Failures
**Problem**: Stack creation/update failures
**Solution**:
- Check CloudFormation template syntax
- Verify AWS service limits
- Review IAM permissions for CloudFormation

#### 3. Deployment Timeouts
**Problem**: Elastic Beanstalk deployment timeouts
**Solution**:
- Increase timeout values in workflow
- Check application startup logs
- Verify instance type has sufficient resources

#### 4. Test Failures
**Problem**: Post-deployment tests failing
**Solution**:
- Check application logs in CloudWatch
- Verify test_images directory exists
- Review test result JSON files for details

#### 5. ML/AI Feature Issues
**Problem**: OpenCV or rembg not working
**Solution**:
- Check system dependencies in .ebextensions
- Verify instance type has sufficient memory
- Review application startup logs

### Debug Mode
Enable debug mode by setting environment variables in the workflow:
```yaml
env:
  DEBUG: true
  VERBOSE_LOGGING: true
```

## 📞 Support

### Getting Help
1. Check the test result JSON files for detailed error information
2. Review GitHub Actions logs for pipeline execution details
3. Check AWS CloudWatch logs for application runtime issues
4. Review this README for configuration guidance

### Contributing
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request with detailed description

## 📋 Checklist for New Deployments

- [ ] AWS credentials configured in GitHub secrets
- [ ] SES sender email verified in AWS
- [ ] test_images directory populated with test images
- [ ] CloudFormation template validated
- [ ] Environment-specific parameters configured
- [ ] Monitoring and alerting set up
- [ ] Backup and rollback strategy defined

## 🔄 Pipeline Status

The pipeline provides comprehensive status reporting:
- ✅ **All tests passing**: Ready for production
- ⚠️ **Some tests failing**: Review and fix issues
- ❌ **Critical failures**: Do not deploy to production
- 🔄 **In progress**: Pipeline currently running

---

**Note**: This pipeline is specifically designed for the Passport Photo AI Enhanced Backend with ML/AI capabilities. Modify as needed for other applications.