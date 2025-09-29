# Contributing to OilPriceAPI Python SDK

Thank you for your interest in contributing! We welcome contributions from the community.

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/oilpriceapi/python-sdk
cd python-sdk

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with all dependencies
pip install -e ".[dev]"

# Set up your API key
cp .env.example .env
# Edit .env and add your OILPRICEAPI_KEY

# Run tests
pytest

# Format code
black .

# Type checking
mypy oilpriceapi
```

## 📋 Ways to Contribute

### 1. Report Bugs

Found a bug? Please create an issue with:
- Clear title and description
- Steps to reproduce
- Expected vs actual behavior
- Python version and OS
- Code sample if applicable

### 2. Suggest Features

Have an idea? Open an issue tagged with `enhancement`:
- Describe the use case
- Explain why it's useful
- Provide examples if possible

### 3. Submit Pull Requests

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**
4. **Add tests** for new functionality
5. **Update documentation**
6. **Run tests and linting**
7. **Commit with clear messages**
8. **Push and create a Pull Request**

## 🧪 Development Workflow

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=oilpriceapi --cov-report=html

# Specific test file
pytest tests/test_client.py

# Specific test
pytest tests/test_client.py::test_get_price
```

### Code Quality

```bash
# Format code
black oilpriceapi tests

# Lint
ruff check oilpriceapi tests

# Type check
mypy oilpriceapi

# Run all checks
pre-commit run --all-files
```

### Testing with Local API

```bash
# Set environment variables
export OILPRICEAPI_KEY="your_test_key"
export OILPRICEAPI_BASE_URL="http://localhost:5000"

# Run live tests
python test_sdk_live.py
```

## 📐 Code Style

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with these specifics:
- **Line length**: 100 characters
- **Formatter**: Black
- **Linter**: Ruff
- **Type hints**: Required for all public APIs
- **Docstrings**: Google style

### Example

```python
from typing import Optional

def get_price(commodity: str, date: Optional[str] = None) -> float:
    """Get commodity price.

    Args:
        commodity: Commodity code (e.g., "BRENT_CRUDE_USD")
        date: Optional date in YYYY-MM-DD format

    Returns:
        Price as float

    Raises:
        DataNotFoundError: If commodity not found

    Example:
        >>> price = get_price("BRENT_CRUDE_USD")
        >>> print(f"Oil: ${price:.2f}")
    """
    # Implementation
    pass
```

## 🔒 Security Guidelines

### Never Commit Secrets

- ❌ API keys in code
- ❌ Passwords or tokens
- ❌ Environment files (`.env`)
- ✅ Use environment variables
- ✅ Use `.env.example` templates

### Security Checklist

Before committing:
- [ ] No hardcoded credentials
- [ ] Added `.env` to `.gitignore`
- [ ] Sensitive data in environment variables
- [ ] Error messages don't leak secrets
- [ ] Input validation added

## 📝 Documentation

### Docstrings Required For:
- All public classes
- All public methods/functions
- Complex private functions

### Update Documentation When:
- Adding new features
- Changing APIs
- Fixing bugs that affect usage
- Adding examples

## 🧩 Pull Request Process

### PR Checklist

- [ ] Tests pass locally
- [ ] New tests added for new features
- [ ] Code formatted with Black
- [ ] Type hints added
- [ ] Docstrings updated
- [ ] CHANGELOG.md updated
- [ ] No merge conflicts
- [ ] PR description explains changes

### PR Title Format

Use conventional commits:
- `feat: add WebSocket support`
- `fix: handle rate limit headers correctly`
- `docs: update installation instructions`
- `test: add integration tests for historical data`
- `refactor: simplify error handling`
- `chore: update dependencies`

### Review Process

1. Automated tests run on GitHub Actions
2. Code review by maintainers
3. Address feedback
4. Approval and merge

## 🎯 Development Priorities

### High Priority
- Bug fixes
- Security improvements
- Documentation improvements
- Test coverage

### Medium Priority
- New features (with issue discussion)
- Performance optimizations
- Examples and tutorials

### Low Priority
- Code style refactoring
- Minor optimizations

## 🤝 Community Guidelines

### Be Respectful
- Assume good intentions
- Be constructive in feedback
- Help newcomers
- Focus on the code, not the person

### Be Collaborative
- Share knowledge
- Ask questions
- Document solutions
- Give credit

## 📞 Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: Create an issue
- **Security**: Email security@oilpriceapi.com
- **General**: support@oilpriceapi.com

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🎉 Recognition

Contributors will be:
- Listed in CHANGELOG.md
- Mentioned in release notes
- Added to GitHub contributors

Thank you for contributing to OilPriceAPI! 🙏