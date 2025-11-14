# Developer Guide

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Home Assistant development environment (optional)
- Git

### Install Development Dependencies

```bash
pip install -r requirements-dev.txt
```

### Code Quality Tools

#### Format Code

```bash
black custom_components/
isort custom_components/
```

#### Lint Code

```bash
flake8 custom_components/
mypy custom_components/
bandit -r custom_components/
```

#### Run Tests

```bash
pytest tests/ -v
pytest tests/ -v --cov=custom_components/sfpuc
```

## Project Structure

```
custom_components/sfpuc/
├── __init__.py              # Integration setup
├── config_flow.py           # UI configuration flow
├── const.py                 # Constants and configuration
├── manifest.json            # Integration manifest
├── sensor.py                # Individual sensor entities
├── strings.json             # UI strings
├── version.py               # Version information
├── translations/            # UI translations
│   ├── en.json             # English translations
│   └── es.json             # Spanish translations
```

## Development Workflow

### 1. Set up Development Environment

```bash
# Clone the repository
git clone https://github.com/caplaz/home-assistant-sfpuc.git
cd home-assistant-sfpuc

# Set up Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt
```

### 2. Code Changes

- Follow PEP 8 style guidelines
- Use type hints for all function parameters and return values
- Write comprehensive docstrings
- Add unit tests for new functionality

### 3. Testing

#### Run All Tests

```bash
pytest tests/ -v
```

#### Run Tests with Coverage

```bash
pytest --cov=custom_components/sfpuc --cov-report=html
open htmlcov/index.html  # View coverage report
```

#### Run Specific Test

```bash
pytest tests/test_config_flow.py -v
```

### 4. Code Quality Checks

#### Format Code

```bash
black custom_components/
isort custom_components/
```

#### Lint Code

```bash
# Check for style issues
flake8 custom_components/

# Type checking
mypy custom_components/

# Security scan
bandit -r custom_components/
```

### 5. Home Assistant Integration Testing

#### Using Docker Development Environment

```bash
# Start development environment
./dev.sh

# Access Home Assistant at http://localhost:8123
```

#### Manual Testing

1. Copy `custom_components/sfpuc` to your HA config directory
2. Restart Home Assistant
3. Check logs for any errors:

```yaml
logger:
  default: info
  logs:
    custom_components.sfpuc: debug
```

## SFPUC Integration Details

### Data Collection

The integration uses web scraping to collect water usage data from the SFPUC portal:

- **Login Process**: Authenticates using provided credentials
- **Data Download**: Downloads Excel files containing usage history
- **Data Parsing**: Extracts daily usage values in gallons
- **Storage**: Maintains historical data for trend analysis

### Configuration

- **Username**: SFPUC account username
- **Password**: SFPUC account password
- **Update Interval**: How often to check for new data (default: 1 hour)

### Sensors

- **Daily Usage**: Current day's water usage in gallons
- **State Class**: TOTAL_INCREASING (cumulative usage)
- **Device Class**: WATER

## Contributing

### Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes and add tests
4. Run all tests and quality checks
5. Commit your changes: `git commit -m 'Add some feature'`
6. Push to the branch: `git push origin feature/your-feature`
7. Open a Pull Request

### Code Standards

- **Python Version**: 3.11+
- **Formatting**: Black
- **Imports**: isort
- **Linting**: flake8
- **Types**: mypy
- **Testing**: pytest with coverage

### Commit Messages

Use conventional commit format:

```
feat: add new sensor for monthly usage
fix: handle login failures gracefully
docs: update installation instructions
test: add tests for data parsing
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
2. **Login Failures**: Verify SFPUC credentials are correct
3. **Data Parsing Issues**: Check SFPUC portal changes
4. **HA Integration Issues**: Check Home Assistant logs

### Debug Logging

Enable debug logging in `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.sfpuc: debug
```

### Testing with Mock Data

For development without real SFPUC access, modify the SFPUCScraper class in `coordinator.py` to use mock data.
