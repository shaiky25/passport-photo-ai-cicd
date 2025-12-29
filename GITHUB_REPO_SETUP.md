# GitHub Repository Setup Guide for CI/CD Pipeline

This guide will help you create a new GitHub repository with the complete CI/CD pipeline for the Passport Photo AI Enhanced Backend.

## 📋 Step 1: Create New GitHub Repository

1. Go to [GitHub.com](https://github.com)
2. Click **"New repository"** or go to https://github.com/new
3. Fill in repository details:
   - **Repository name**: `passport-photo-ai-cicd`
   - **Description**: `CI/CD Pipeline for Passport Photo AI Enhanced Backend with ML/AI capabilities`
   - **Visibility**: Private (recommended) or Public
   - **Initialize**: ✅ Add a README file
   - **Add .gitignore**: Python
   - **Choose a license**: MIT (optional)

## 📁 Step 2: Repository Structure

Create the following directory structure in your new repository:

```
passport-photo-ai-cicd/
├── .github/
│   └── workflows/
│       └── deploy.yml
├── scripts/
│   ├── validate_dependencies.py
│   ├── run_local_tests.py
│   ├── validate_image_processing.py
│   ├── validate_cloudformation.py
│   ├── create_source_bundle.py
│   ├── deploy_infrastructure.py
│   ├── upload_to_s3.py
│   ├── deploy_to_eb.py
│   ├── run_health_checks.py
│   ├── test_ml_features.py
│   ├── test_performance.py
│   ├── test_cors.py
│   └── error_handler.py
├── test_images/
│   ├── faiz.png
│   ├── faiz_with_glasses.png
│   ├── multi_face.jpg
│   ├── people_in_bg_unfocused.JPG
│   ├── sample_image_1.jpg
│   └── sample_image_2.jpg
├── database/
│   ├── __init__.py
│   └── dynamodb_client.py
├── services/
│   ├── __init__.py
│   ├── download_controller.py
│   ├── email_validation.py
│   └── rate_limiting.py
├── application.py
├── requirements.txt
├── cloudformation-enhanced.yaml
├── cors_config.py
├── README.md
└── .gitignore
```

## 🔧 Step 3: Configure GitHub Secrets

In your GitHub repository, go to **Settings** → **Secrets and variables** → **Actions** and add these secrets:

### Required Secrets:
```
AWS_ACCESS_KEY_ID       # Your AWS access key ID
AWS_SECRET_ACCESS_KEY   # Your AWS secret access key
AWS_ACCOUNT_ID          # Your AWS account ID (12-digit number)
```

### How to get AWS credentials:
1. Go to [AWS IAM Console](https://console.aws.amazon.com/iam/)
2. Create a new user or use existing user
3. Attach policies:
   - `AmazonElasticBeanstalkFullAccess`
   - `AmazonS3FullAccess`
   - `CloudFormationFullAccess`
   - `AmazonDynamoDBFullAccess`
   - `AmazonSESFullAccess`
4. Create access keys and copy them to GitHub secrets

## 📄 Step 4: Files to Copy

Copy these files from the current workspace to your new repository:

### Core Application Files:
- `application.py` - Main Flask application
- `requirements.txt` - Python dependencies
- `cloudformation-enhanced.yaml` - AWS infrastructure template
- `cors_config.py` - CORS configuration

### CI/CD Pipeline Files:
- `.github/workflows/deploy.yml` - GitHub Actions workflow
- All files from `scripts/` directory
- All files from `test_images/` directory
- All files from `database/` directory
- All files from `services/` directory

### Documentation:
- `CI-CD-PIPELINE-README.md` → rename to `README.md`

## 🚀 Step 5: Initial Commit and Push

```bash
# Clone your new repository
git clone https://github.com/YOUR_USERNAME/passport-photo-ai-cicd.git
cd passport-photo-ai-cicd

# Copy all the files from this workspace to the new repository
# (Follow the structure above)

# Add all files
git add .

# Commit
git commit -m "Initial commit: Complete CI/CD pipeline with ML/AI testing"

# Push to main branch
git push origin main
```

## 🔄 Step 6: Test the Pipeline

### Option 1: Automatic Trigger
```bash
# Make a small change and push to trigger the pipeline
echo "# Pipeline Test" >> README.md
git add README.md
git commit -m "Test: Trigger CI/CD pipeline"
git push origin main
```

### Option 2: Manual Trigger
1. Go to your repository on GitHub
2. Click **Actions** tab
3. Select **"CI/CD Pipeline - Passport Photo AI Enhanced Backend"**
4. Click **"Run workflow"**
5. Choose environment (dev/staging/prod)
6. Click **"Run workflow"**

## 📊 Step 7: Monitor Pipeline Execution

1. Go to **Actions** tab in your GitHub repository
2. Click on the running workflow
3. Monitor each stage:
   - ✅ Pre-Deployment Validation
   - ✅ Infrastructure Provisioning  
   - ✅ Application Deployment
   - ✅ Post-Deployment Verification

## 🎯 Expected Results

When the pipeline runs successfully, you should see:

1. **Pre-deployment**: Dependencies validated, local tests passed, ML/AI features tested
2. **Infrastructure**: AWS resources created/updated via CloudFormation
3. **Deployment**: Application deployed to Elastic Beanstalk
4. **Post-deployment**: Health checks passed, ML/AI features working, performance validated

## 🔧 Troubleshooting

### Common Issues:

1. **AWS Credentials**: Verify secrets are set correctly
2. **Permissions**: Ensure AWS user has required permissions
3. **Resource Limits**: Check AWS service limits
4. **Test Images**: Ensure test_images directory has sample images

### Debug Steps:
1. Check GitHub Actions logs
2. Review AWS CloudWatch logs
3. Verify CloudFormation stack status
4. Test individual scripts locally

## 📞 Next Steps

After successful setup:
1. Test with different environments (dev/staging/prod)
2. Add more test images to `test_images/` directory
3. Customize pipeline for your specific needs
4. Set up monitoring and alerting
5. Configure branch protection rules

---

**🎉 Congratulations!** You now have a complete CI/CD pipeline with:
- Automated infrastructure provisioning
- Comprehensive ML/AI testing
- Error handling and recovery
- Multi-environment support
- Detailed monitoring and reporting