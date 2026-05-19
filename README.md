# Lookout SE Web Activity Field Demo

A comprehensive demonstration toolkit for Lookout's Web Activity Feed API and Mobile Risk API integration. This repository contains various tools and examples for integrating with Lookout's security APIs, including web activity monitoring, device management, and threat detection.

## 🚀 Features

- **Web Activity Feed Integration**: Real-time monitoring of web access events
- **Mobile Risk API Client**: Comprehensive device and threat management
- **Device Management**: CLI tools for device discovery and management
- **S3 Logging**: Automated logging to AWS S3 with configurable retention
- **Docker Support**: Containerized deployment options
- **Systemd Integration**: Production-ready service deployment

## 📋 Prerequisites

- Python 3.8+
- Valid Lookout API credentials (Application Key and Access Token)
- AWS account (for S3 logging features)
- Docker (optional, for containerized deployment)
- Go 1.21+ (optional, for the Terminal UI)

## 🔧 Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/fgravato/lookout-se-webactivity_fielddemo.git
   cd lookout-se-webactivity_fielddemo
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements_poc.txt
   # For S3 logging features:
   pip install -r requirements_s3.txt
   ```

## ⚙️ Configuration

### Environment Setup

1. **Copy the example environment file**:
   ```bash
   cp .env.s3.example .env
   ```

2. **Configure your credentials** in `.env`:
   ```bash
   # Lookout API Configuration
   LOOKOUT_ACCESS_TOKEN=your_access_token_here
   APPLICATION_KEY=your_application_key_here
   WEB_ACTIVITY_KEY=your_web_activity_key_here
   
   # AWS Configuration (for S3 logging)
   S3_BUCKET_NAME=your-s3-bucket-name
   AWS_REGION=us-east-1
   ```

### API Credentials

You need to obtain API credentials from your Lookout console:

1. **Application Key**: Generated from Lookout Console → System → Application Keys
2. **Access Token**: Obtained via OAuth2 flow using the Application Key
3. **Web Activity Key**: Specific key for web activity feed access

For detailed instructions, see [README_TOKEN_AUTH.md](README_TOKEN_AUTH.md).

## 🚀 Quick Start

### Basic Web Activity Monitoring

```bash
python lookout_web_activity_feed.py
```

### Web Activity Browser (GUI)

```bash
./setup_web_gui.sh
source .venv/bin/activate
python lookout_web_activity_gui.py
```

The script creates (or reuses) a virtual environment, upgrades pip, and pulls dependencies from `requirements.txt`. Override defaults with `VENV_DIR=/path/to/venv` or `PYTHON_BIN=python3.11` as needed.

If you prefer manual installation, run:

```bash
pip install -r requirements.txt
python lookout_web_activity_gui.py
```

Then browse to http://127.0.0.1:5000 (or the host/port you configure) and use the form to select a time range and apply keyword filters. The application reuses your existing environment variables for authentication.

### Terminal UI (Go TUI)

```bash
cd lookout-tui
cp .env.example .env   # fill in your credentials
make build
./bin/tui              # full interactive TUI
./bin/cli              # CLI output mode
```

See [lookout-tui/README.md](lookout-tui/README.md) for keyboard controls, time window selection, and full setup instructions.

### Device Management

```bash
# List all devices
python device_manager_cli.py list

# Search for specific devices
python device_manager_cli.py search --email user@company.com

# Get device details
python device_manager_cli.py details --guid device-guid-here
```

### S3 Logging Setup

```bash
# Run the setup script
./setup_s3_logging.sh

# Start the S3 logger
python lookout_s3_logger.py
```

## 📚 Components

### Core Modules

- **`lookout_api_client.py`**: Enhanced API client with configurable timeout and retry logic
- **`lookout_web_activity_feed.py`**: Web activity feed monitoring
- **`lookout_web_activity_gui.py`**: Flask web browser for web activity events (port 5000)
- **`lookout_api_client_demo.py`**: Standalone demo client with simulated data (no live credentials needed)
- **`device_manager_cli.py`**: Command-line device management interface
- **`mra_event_reader.py`**: Mobile Risk API event stream reader
- **`lookout_s3_logger.py`**: S3 logging service with automatic rotation

### Utilities

- **`device_database.py`**: SQLite database for device information caching
- **`demo_device_mapping.py`**: Device discovery and mapping utilities
- **`aws_setup.py`**: AWS S3 bucket configuration helper

### Configuration Files

- **`mobilemesapi.json`**: Mobile Risk API OpenAPI specification
- **`webaccessfeedapi.json`**: Web Access Feed API specification
- **`swagger.json`**: Lookout Mobile Rights API OpenAPI 2.0 specification
- **`web-api.swagger.json`**: Simplified web activity API specification
- **`lookout-tui/`**: Go-based terminal UI application (source + Makefile)
- **`docker/`**: Docker configuration files
- **`systemd/`**: Systemd service files for production deployment

## 🐳 Docker Deployment

### Build and Run

```bash
cd docker
docker-compose up -d
```

### Configuration

The Docker setup includes:
- Automated environment variable injection
- Volume mounts for persistent data
- Health checks and restart policies

## 🔧 Production Deployment

### Systemd Service

1. **Install the service**:
   ```bash
   sudo cp systemd/lookout-s3-logger.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable lookout-s3-logger
   ```

2. **Start the service**:
   ```bash
   sudo systemctl start lookout-s3-logger
   ```

### AWS S3 Setup

The S3 logging feature provides:
- Automatic log rotation
- Configurable retention policies
- Error handling and retry logic
- CloudWatch integration

See [README_S3_LOGGING.md](README_S3_LOGGING.md) for detailed setup instructions.

## 📖 Documentation

- [Token Authentication Guide](README_TOKEN_AUTH.md)
- [Device Mapping Documentation](README_DEVICE_MAPPING.md)
- [Enhanced API Client Guide](README_ENHANCED_API_CLIENT.md)
- [S3 Logging Setup](README_S3_LOGGING.md)
- [POC Setup Guide](README_POC.md)
- [Timeout & Retry Configuration](README_TIMEOUT_IMPROVEMENTS.md)
- [Terminal UI Documentation](lookout-tui/README.md)

## 🔒 Security Considerations

- **Never commit sensitive credentials** to version control
- Use environment variables for all API keys and tokens
- Implement proper token rotation and refresh mechanisms
- Follow AWS security best practices for S3 bucket configuration
- Use IAM roles with minimal required permissions

## 🧪 Testing

### Run Tests

```bash
# Test S3 logging functionality
python test_s3_logger.py

# Test with sample data
python test_with_sample_data.py
```

### API Testing

```bash
# Test API connectivity
python -c "from lookout_api_client import LookoutAPIClient; client = LookoutAPIClient(); print('API connection successful')"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:

- Check the documentation in the `README_*.md` files
- Review the example configurations
- Contact your Lookout SE representative

## 🔄 Version History

- **v1.0.0**: Initial release with core functionality
- **v1.1.0**: Added S3 logging and Docker support
- **v1.2.0**: Enhanced device management and CLI tools

## ⚠️ Important Notes

- This is a demonstration toolkit intended for field engineers and integration testing
- Ensure proper security practices when deploying in production environments
- API rate limits apply - implement appropriate throttling for production use
- Some features require specific Lookout license tiers

---

**Lookout SE Web Activity Field Demo** - Empowering secure mobile device management and web activity monitoring.
