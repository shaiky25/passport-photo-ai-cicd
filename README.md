# Passport Photo AI - Enhanced Backend

Full-featured ML/AI backend with advanced face detection, background removal, and comprehensive email validation system. Optimized for t3.small instances with professional-grade image processing capabilities.

## 🚀 Features

### Core ML/AI Capabilities
- **Advanced Face Detection**: OpenCV-based face detection with eye recognition and quality scoring
- **Background Removal**: rembg integration with multiple model support (u2net, u2net_human_seg, u2netp, silueta)
- **Intelligent Cropping**: Smart passport photo cropping with proper head positioning
- **Image Enhancement**: Professional brightness, contrast, and sharpness adjustments
- **High-Resolution Output**: 1200x1200 pixel passport photos with 300 DPI

### Email Validation System
- **OTP Verification**: Secure 6-digit OTP generation and verification
- **AWS SES Integration**: Professional email delivery with HTML templates
- **Rate Limiting**: IP-based and email-based quotas with exponential backoff
- **DynamoDB Storage**: Scalable user management and analytics

### Security & Performance
- **CORS Support**: Comprehensive CORS configuration for Amplify frontend
- **Watermark Management**: Conditional watermarking based on email verification
- **Request Logging**: Detailed analytics and monitoring
- **Auto-scaling**: 1-3 instances with load balancing

## 📋 Requirements

### System Requirements
- **Instance Type**: t3.small (2 vCPU, 2GB RAM) minimum
- **Python**: 3.9+
- **AWS Services**: Elastic Beanstalk, DynamoDB, SES, S3

### Dependencies
- Flask 2.3.3 with CORS support
- OpenCV 4.8.1.78 (headless)
- rembg 2.0.50 with ONNX runtime
- NumPy 1.24.4
- Pillow 10.0.1 with HEIC support
- Boto3 for AWS services

## 🛠️ Installation & Deployment

### Prerequisites
1. **AWS CLI** configured with appropriate credentials
2. **SES Email Verification**: Verify sender email in AWS SES
3. **Domain Setup**: Ensure Amplify domain is accessible

### Quick Deployment
```bash
# Make deployment script executable
chmod +x deploy-enhanced.sh

# Deploy the enhanced backend
./deploy-enhanced.sh
```

### Manual Deployment Steps

1. **Prepare Environment**
```bash
# Install dependencies locally for testing
pip install -r requirements.txt

# Test locally (optional)
python application.py
```

2. **Deploy Infrastructure**
```bash
# Create CloudFormation stack
aws cloudformation create-stack \
  --stack-name passport-photo-ai-enhanced-stack \
  --template-body file://cloudformation-enhanced.yaml \
  --parameters ParameterKey=ApplicationName,ParameterValue=passport-photo-ai-enhanced \
               ParameterKey=AmplifyDomain,ParameterValue=https://main.d3gelc4wjo7dl.amplifyapp.com \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

3. **Monitor Deployment**
```bash
# Wait for stack creation
aws cloudformation wait stack-create-complete \
  --stack-name passport-photo-ai-enhanced-stack \
  --region us-east-1

# Get outputs
aws cloudformation describe-stacks \
  --stack-name passport-photo-ai-enhanced-stack \
  --query 'Stacks[0].Outputs'
```

## 🧪 Testing

### Automated Testing
```bash
# Run comprehensive test suite
python test-enhanced.py <backend-url>

# Example
python test-enhanced.py http://passport-photo-ai-enhanced.us-east-1.elasticbeanstalk.com
```

### Manual Testing

1. **Health Check**
```bash
curl -H "Origin: https://main.d3gelc4wjo7dl.amplifyapp.com" \
     https://your-backend-url/api/health
```

2. **CORS Test**
```bash
curl -X OPTIONS \
     -H "Origin: https://main.d3gelc4wjo7dl.amplifyapp.com" \
     -H "Access-Control-Request-Method: POST" \
     https://your-backend-url/api/full-workflow
```

3. **Email Validation**
```bash
# Send OTP
curl -X POST \
     -H "Content-Type: application/json" \
     -H "Origin: https://main.d3gelc4wjo7dl.amplifyapp.com" \
     -d '{"email":"test@example.com"}' \
     https://your-backend-url/api/send-otp

# Verify OTP
curl -X POST \
     -H "Content-Type: application/json" \
     -H "Origin: https://main.d3gelc4wjo7dl.amplifyapp.com" \
     -d '{"email":"test@example.com","otp":"123456"}' \
     https://your-backend-url/api/verify-otp
```

## 📊 API Endpoints

### Core Endpoints
- `GET /` - Root health check
- `GET /api/health` - Detailed health and feature status
- `GET|POST /api/test-cors` - CORS functionality test

### Image Processing
- `POST /api/full-workflow` - Main image processing pipeline
  - **Parameters**: `image` (file), `remove_background` (boolean), `email` (string)
  - **Returns**: Processed image with analysis data

### Email Validation
- `POST /api/send-otp` - Send verification code
  - **Parameters**: `email` (string)
  - **Returns**: Success status and expiration time

- `POST /api/verify-otp` - Verify email with OTP
  - **Parameters**: `email` (string), `otp` (string)
  - **Returns**: Verification status

### Analytics
- `POST /api/log-event` - Log analytics events
  - **Parameters**: Event data (JSON)
  - **Returns**: Success confirmation

## ⚙️ Configuration

### Environment Variables
```bash
# Core settings
FLASK_ENV=production
ALLOWED_ORIGINS=https://main.d3gelc4wjo7dl.amplifyapp.com
AWS_DEFAULT_REGION=us-east-1

# Email settings
SES_SENDER_EMAIL=faiz.24365@gmail.com
DYNAMODB_TABLE_NAME=passport-photo-ai-enhanced

# Feature flags
ENABLE_OPENCV=true
ENABLE_REMBG=true
ENABLE_ENHANCED_PROCESSING=true
```

### Rate Limits
- **Unverified Users**: 3 requests per hour (IP-based)
- **Verified Users**: 20 requests per day (email-based)
- **OTP Generation**: 3 attempts per hour per email
- **Exponential Backoff**: After 5 failed attempts

## 🔧 Troubleshooting

### Common Issues

1. **OpenCV Installation Fails**
```bash
# Install system dependencies
sudo yum install -y gcc gcc-c++ cmake pkgconfig
sudo yum install -y opencv opencv-devel

# Install Python packages in order
pip install numpy==1.24.4
pip install opencv-python-headless==4.8.1.78
```

2. **rembg Model Loading Issues**
```bash
# Check available memory
free -h

# Use lighter models for t3.small
export REMBG_MODEL=u2netp  # Lighter model
```

3. **SES Email Delivery Issues**
```bash
# Verify sender email in SES
aws ses verify-email-identity --email-address your-email@domain.com

# Check SES sending statistics
aws ses get-send-statistics
```

4. **DynamoDB Connection Issues**
```bash
# Verify table exists
aws dynamodb describe-table --table-name passport-photo-ai-enhanced

# Check IAM permissions
aws sts get-caller-identity
```

### Performance Optimization

1. **Memory Management**
   - Use lighter rembg models (u2netp, silueta)
   - Implement image size limits
   - Monitor CloudWatch metrics

2. **Processing Speed**
   - Enable OpenCV optimizations
   - Use appropriate instance types
   - Implement request queuing

3. **Cost Optimization**
   - Monitor DynamoDB usage
   - Set up CloudWatch alarms
   - Use reserved instances for production

## 📈 Monitoring

### CloudWatch Metrics
- Application health and response times
- Memory and CPU utilization
- Request counts and error rates
- DynamoDB read/write capacity

### Logging
- Application logs in CloudWatch Logs
- Request/response logging
- Error tracking and alerting
- Performance metrics

## 🔒 Security

### Best Practices
- All sensitive data encrypted in transit and at rest
- Email addresses hashed in DynamoDB
- Rate limiting and abuse prevention
- CORS properly configured
- No sensitive data in logs

### Compliance
- GDPR-compliant data handling
- Automatic data cleanup via TTL
- Secure OTP generation and storage
- Professional email templates

## 📞 Support

For issues or questions:
1. Check CloudWatch logs for errors
2. Run the test suite for diagnostics
3. Review AWS service health dashboards
4. Monitor application metrics

## 🚀 Deployment Checklist

- [ ] AWS credentials configured
- [ ] SES sender email verified
- [ ] Amplify domain accessible
- [ ] CloudFormation template validated
- [ ] Test suite passes
- [ ] Monitoring configured
- [ ] Backup strategy in place# passport-photo-ai-cicd
