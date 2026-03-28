# Intelix Project

## Overview
Intelix is an intelligent API client application that provides streamlined interaction with various APIs. It includes built-in authentication, request handling, response analysis, and comprehensive reporting capabilities.

## Features
- **Secure Authentication**: Support for multiple authentication methods
- **HTTP Request Handling**: Simplified API interaction and request management
- **Response Analysis**: Intelligent parsing and analysis of API responses
- **Reporting**: Generate detailed reports of API interactions and results
- **Configuration Management**: Environment-based configuration system
- **Error Handling**: Robust error handling and logging

## Project Structure
```
intelix-project/
├── src/
│   ├── auth.py        # Authentication module for API credentials
│   ├── client.py      # Main HTTP client for API requests
│   ├── config.py      # Configuration management
│   ├── main.py        # Main application entry point
│   └── reporter.py    # Reporting and analysis module
├── samples/           # Example usage and sample data
├── requirements.txt   # Python dependencies
├── .gitignore        # Git ignore file
└── README.md         # This file
```

## Module Descriptions

### auth.py
Handles authentication for API requests. Supports various authentication mechanisms including API keys, OAuth tokens, and basic authentication.

### client.py
Core HTTP client module that manages API requests and responses. Provides methods for GET, POST, PUT, DELETE operations with automatic error handling.

### config.py
Configuration management system that loads settings from environment variables (.env file) and provides a centralized configuration object for the application.

### main.py
Application entry point that orchestrates the different modules. Manages the workflow of authentication, making requests, analyzing responses, and generating reports.

### reporter.py
Generates comprehensive reports of API interactions. Provides analysis of response times, status codes, and other relevant metrics.

## Dependencies
- `requests` - HTTP library for making API calls
- `python-dotenv` - Load environment variables from .env file

Install dependencies:
```bash
pip install -r requirements.txt
```

## Setup

### 1. Clone the Repository
```bash
git clone https://github.com/randkhouri/intelix-project.git
cd intelix-project
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
Create a `.env` file in the project root:
```
API_KEY=your_api_key_here
API_BASE_URL=https://api.example.com
TIMEOUT=30
```

### 4. Run the Application
```bash
python src/main.py
```

## Usage Examples

### Basic Usage
```python
from src.client import APIClient
from src.auth import Authentication
from src.config import Config

# Load configuration
config = Config()

# Initialize authentication
auth = Authentication(config.api_key)

# Create client
client = APIClient(auth, config.base_url)

# Make a request
response = client.get('/endpoint')
print(response.json())
```

### Generate Reports
```python
from src.reporter import Reporter

reporter = Reporter()
report = reporter.generate_report(responses)
print(report)
```

## Configuration

The application uses a `.env` file for configuration. Required variables:
- `API_KEY` - Your API authentication key
- `API_BASE_URL` - Base URL for the API
- `TIMEOUT` - Request timeout in seconds (optional, default: 30)

## Contributing
Contributions are welcome! Please follow these guidelines:
1. Create a feature branch
2. Make your changes
3. Submit a pull request with a clear description of changes

## License
This project is provided as-is for educational purposes.
