#!/bin/bash

# Deploy Passport Photo AI Enhanced Backend
# Full ML/AI backend with OpenCV, rembg, and advanced face detection

set -e  # Exit on any error

# Configuration
STACK_NAME="passport-photo-ai-enhanced-stack"
APPLICATION_NAME="passport-photo-ai-enhanced"
ENVIRONMENT_NAME="passport-photo-ai-enhanced-env"
AMPLIFY_DOMAIN="https://main.d3gelc4wjo7dl.amplifyapp.com"
INSTANCE_TYPE="t3.small"
REGION="us-east-1"
KEY_PAIR_NAME=""  # Optional: Add your EC2 key pair name
SENDER_EMAIL="faiz.24365@gmail.com"
DYNAMODB_TABLE="passport-photo-ai-enhanced"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Run 'aws configure' first."
        exit 1
    fi
    
    # Check if CloudFormation template exists
    if [ ! -f "cloudformation-enhanced.yaml" ]; then
        log_error "CloudFormation template not found: cloudformation-enhanced.yaml"
        exit 1
    fi
    
    # Check required files
    REQUIRED_FILES=(
        "application.py"
        "cors_config.py"
        "requirements.txt"
        "services/email_validation.py"
        "services/rate_limiting.py"
        "services/download_controller.py"
        "database/dynamodb_client.py"
    )
    
    for file in "${REQUIRED_FILES[@]}"; do
        if [ ! -f "$file" ]; then
            log_error "Required file not found: $file"
            exit 1
        fi
    done
    
    log_success "Prerequisites check passed"
}

# Create application source bundle
create_source_bundle() {
    log_info "Creating enhanced application source bundle..."
    
    # Create temporary directory
    TEMP_DIR=$(mktemp -d)
    SOURCE_DIR="$TEMP_DIR/source"
    mkdir -p "$SOURCE_DIR"
    
    # Copy application files
    cp application.py "$SOURCE_DIR/"
    cp cors_config.py "$SOURCE_DIR/"
    cp requirements.txt "$SOURCE_DIR/"
    
    # Copy services directory
    cp -r services "$SOURCE_DIR/"
    
    # Copy database directory
    cp -r database "$SOURCE_DIR/"
    
    # Create .ebextensions directory and configuration
    mkdir -p "$SOURCE_DIR/.ebextensions"
    
    # Enhanced configuration for ML/AI processing
    cat > "$SOURCE_DIR/.ebextensions/01_enhanced.config" << 'EOF'
option_settings:
  aws:elasticbeanstalk:container:python:
    WSGIPath: application.py
  aws:elasticbeanstalk:environment:proxy:
    ProxyServer: nginx
  aws:elasticbeanstalk:container:python:staticfiles:
    "/static/": "static/"

commands:
  01_update_system:
    command: "yum update -y"
  02_install_system_deps:
    command: "yum install -y gcc gcc-c++ cmake pkgconfig libffi-devel"
  03_install_opencv_deps:
    command: "yum install -y opencv opencv-devel opencv-python"
    ignoreErrors: true

container_commands:
  01_upgrade_pip:
    command: "source $PYTHONPATH/activate && pip install --upgrade pip setuptools wheel"
  02_install_numpy_first:
    command: "source $PYTHONPATH/activate && pip install numpy==1.24.4"
  03_install_opencv:
    command: "source $PYTHONPATH/activate && pip install opencv-python-headless==4.8.1.78"
  04_install_requirements:
    command: "source $PYTHONPATH/activate && pip install -r requirements.txt"
    leader_only: true

files:
  "/opt/elasticbeanstalk/tasks/taillogs.d/01_application_logs.conf":
    mode: "000644"
    owner: root
    group: root
    content: |
      /var/log/eb-engine.log
      /var/log/eb-hooks.log
      /opt/python/log/application.log
EOF

    # Create zip file
    cd "$SOURCE_DIR"
    zip -r "../application-source.zip" . -x "*.pyc" "__pycache__/*" "*.DS_Store"
    cd - > /dev/null
    
    SOURCE_ZIP="$TEMP_DIR/application-source.zip"
    
    log_success "Enhanced application source bundle created: $SOURCE_ZIP"
    echo "$SOURCE_ZIP"
}

# Deploy CloudFormation stack
deploy_infrastructure() {
    local source_zip="$1"
    
    log_info "Deploying CloudFormation stack: $STACK_NAME"
    
    # Create S3 bucket for deployment artifacts (if it doesn't exist)
    DEPLOYMENT_BUCKET="$APPLICATION_NAME-deployment-$RANDOM"
    aws s3 mb "s3://$DEPLOYMENT_BUCKET" --region "$REGION" 2>/dev/null || true
    
    # Upload source bundle to S3
    log_info "Uploading enhanced source bundle to S3..."
    aws s3 cp "$source_zip" "s3://$DEPLOYMENT_BUCKET/application-source.zip" --region "$REGION"
    
    # Deploy CloudFormation stack
    log_info "Creating/updating CloudFormation stack..."
    
    PARAMETERS=(
        "ParameterKey=ApplicationName,ParameterValue=$APPLICATION_NAME"
        "ParameterKey=EnvironmentName,ParameterValue=$ENVIRONMENT_NAME"
        "ParameterKey=InstanceType,ParameterValue=$INSTANCE_TYPE"
        "ParameterKey=AmplifyDomain,ParameterValue=$AMPLIFY_DOMAIN"
        "ParameterKey=SenderEmail,ParameterValue=$SENDER_EMAIL"
        "ParameterKey=DynamoDBTableName,ParameterValue=$DYNAMODB_TABLE"
    )
    
    if [ -n "$KEY_PAIR_NAME" ]; then
        PARAMETERS+=("ParameterKey=KeyPairName,ParameterValue=$KEY_PAIR_NAME")
    fi
    
    # Check if stack exists
    if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" &>/dev/null; then
        log_info "Stack exists, updating..."
        aws cloudformation update-stack \
            --stack-name "$STACK_NAME" \
            --template-body file://cloudformation-enhanced.yaml \
            --parameters "${PARAMETERS[@]}" \
            --capabilities CAPABILITY_NAMED_IAM \
            --region "$REGION"
        
        log_info "Waiting for stack update to complete..."
        aws cloudformation wait stack-update-complete --stack-name "$STACK_NAME" --region "$REGION"
    else
        log_info "Creating new stack..."
        aws cloudformation create-stack \
            --stack-name "$STACK_NAME" \
            --template-body file://cloudformation-enhanced.yaml \
            --parameters "${PARAMETERS[@]}" \
            --capabilities CAPABILITY_NAMED_IAM \
            --region "$REGION"
        
        log_info "Waiting for stack creation to complete..."
        aws cloudformation wait stack-create-complete --stack-name "$STACK_NAME" --region "$REGION"
    fi
    
    # Clean up deployment bucket
    aws s3 rm "s3://$DEPLOYMENT_BUCKET/application-source.zip" --region "$REGION"
    aws s3 rb "s3://$DEPLOYMENT_BUCKET" --region "$REGION"
    
    log_success "CloudFormation stack deployed successfully"
}

# Get stack outputs
get_stack_outputs() {
    log_info "Getting stack outputs..."
    
    OUTPUTS=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs' \
        --output json)
    
    ENVIRONMENT_URL=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="EnvironmentURL") | .OutputValue')
    BACKEND_API_URL=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="BackendAPIURL") | .OutputValue')
    DYNAMODB_TABLE_NAME=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="DynamoDBTableName") | .OutputValue')
    
    log_success "Stack outputs retrieved:"
    echo "  Environment URL: $ENVIRONMENT_URL"
    echo "  Backend API URL: $BACKEND_API_URL"
    echo "  DynamoDB Table: $DYNAMODB_TABLE_NAME"
}

# Test enhanced functionality
test_deployment() {
    log_info "Testing enhanced backend functionality..."
    
    # Wait for environment to be ready
    log_info "Waiting for environment to be ready..."
    sleep 60
    
    # Test health endpoint
    log_info "Testing health endpoint..."
    HEALTH_RESPONSE=$(curl -s -H "Origin: $AMPLIFY_DOMAIN" "$ENVIRONMENT_URL/api/health" || echo "failed")
    
    if echo "$HEALTH_RESPONSE" | grep -q "enhanced"; then
        log_success "Health endpoint responding with enhanced features"
        
        # Parse and display features
        OPENCV_AVAILABLE=$(echo "$HEALTH_RESPONSE" | jq -r '.features.opencv_available // false')
        REMBG_AVAILABLE=$(echo "$HEALTH_RESPONSE" | jq -r '.features.rembg_available // false')
        ENHANCED_PROCESSING=$(echo "$HEALTH_RESPONSE" | jq -r '.features.enhanced_processing // false')
        
        echo "  OpenCV: $OPENCV_AVAILABLE"
        echo "  Background Removal: $REMBG_AVAILABLE"
        echo "  Enhanced Processing: $ENHANCED_PROCESSING"
    else
        log_warning "Health endpoint not responding correctly (may need more time)"
    fi
    
    # Test CORS headers
    log_info "Testing CORS headers..."
    CORS_RESPONSE=$(curl -s -I -H "Origin: $AMPLIFY_DOMAIN" "$ENVIRONMENT_URL/api/health")
    
    if echo "$CORS_RESPONSE" | grep -i "access-control-allow-origin" > /dev/null; then
        log_success "CORS headers present"
    else
        log_warning "CORS headers not found (may need more time for deployment)"
    fi
    
    # Test enhanced processing endpoint
    log_info "Testing enhanced processing capabilities..."
    TEST_RESPONSE=$(curl -s -X OPTIONS -H "Origin: $AMPLIFY_DOMAIN" "$ENVIRONMENT_URL/api/full-workflow")
    
    if echo "$TEST_RESPONSE" | grep -q "preflight_ok"; then
        log_success "Enhanced processing endpoint accessible"
    else
        log_warning "Enhanced processing endpoint not ready yet"
    fi
}

# Main deployment function
main() {
    echo "🚀 Deploying Passport Photo AI Enhanced Backend"
    echo "=============================================="
    echo "Stack Name: $STACK_NAME"
    echo "Application: $APPLICATION_NAME"
    echo "Environment: $ENVIRONMENT_NAME"
    echo "Instance Type: $INSTANCE_TYPE"
    echo "Amplify Domain: $AMPLIFY_DOMAIN"
    echo "Region: $REGION"
    echo "DynamoDB Table: $DYNAMODB_TABLE"
    echo "=============================================="
    
    # Check prerequisites
    check_prerequisites
    
    # Create source bundle
    SOURCE_ZIP=$(create_source_bundle)
    
    # Deploy infrastructure
    deploy_infrastructure "$SOURCE_ZIP"
    
    # Get outputs
    get_stack_outputs
    
    # Test deployment
    test_deployment
    
    # Cleanup
    rm -rf "$(dirname "$SOURCE_ZIP")"
    
    echo ""
    echo "=============================================="
    log_success "Enhanced Backend Deployment completed!"
    echo "=============================================="
    echo "🌐 Backend URL: $ENVIRONMENT_URL"
    echo "🔗 API URL: $BACKEND_API_URL"
    echo "🗄️  DynamoDB Table: $DYNAMODB_TABLE_NAME"
    echo ""
    echo "📋 Enhanced Features:"
    echo "  ✅ CORS Support"
    echo "  ✅ Advanced OpenCV Face Detection"
    echo "  ✅ rembg Background Removal"
    echo "  ✅ Email Validation System"
    echo "  ✅ Rate Limiting & Quotas"
    echo "  ✅ High-Resolution Processing"
    echo "  ✅ Professional Watermarking"
    echo ""
    echo "🧪 Test URLs:"
    echo "  Health: $BACKEND_API_URL/health"
    echo "  CORS Test: $BACKEND_API_URL/test-cors"
    echo "  Full Workflow: $BACKEND_API_URL/full-workflow"
    echo "  Send OTP: $BACKEND_API_URL/send-otp"
    echo "  Verify OTP: $BACKEND_API_URL/verify-otp"
    echo ""
    echo "⚙️  Instance Configuration:"
    echo "  Type: $INSTANCE_TYPE (2 vCPU, 2GB RAM)"
    echo "  Auto Scaling: 1-3 instances"
    echo "  Load Balancer: Application Load Balancer"
    echo "  Health Monitoring: Enhanced"
}

# Run main function
main "$@"