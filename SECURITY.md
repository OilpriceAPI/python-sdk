# Security Policy

## Supported Versions

We actively support the latest major version of the OilPriceAPI Python SDK.

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability in the OilPriceAPI Python SDK, please report it responsibly.

### How to Report

**Do not** open a public GitHub issue for security vulnerabilities.

Instead, please email us at: **security@oilpriceapi.com**

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Varies based on severity

### Security Best Practices

When using this SDK:

1. **Never commit API keys to version control**
   ```bash
   # Use environment variables
   export OILPRICEAPI_KEY="your_api_key"
   ```

2. **Use .env files for local development**
   ```bash
   cp .env.example .env
   # Add your key to .env (which is gitignored)
   ```

3. **Rotate API keys regularly**
   - Generate new keys from your dashboard
   - Revoke old keys when no longer needed

4. **Limit API key permissions**
   - Use read-only keys when possible
   - Create separate keys for dev/staging/production

5. **Keep the SDK updated**
   ```bash
   pip install --upgrade oilpriceapi
   ```

6. **Validate user input**
   - Sanitize commodity codes
   - Validate date ranges
   - Use the SDK's built-in validation

7. **Handle errors securely**
   ```python
   try:
       price = client.prices.get(commodity)
   except OilPriceAPIError as e:
       # Log error but don't expose API key in logs
       logger.error(f"API error: {e.message}")
   ```

## Known Security Considerations

### API Key Storage
- The SDK reads API keys from environment variables by default
- Never hardcode keys in source code
- Use secret management systems in production (AWS Secrets Manager, HashiCorp Vault, etc.)

### Network Security
- All API requests use HTTPS by default
- Certificate validation is enabled
- No sensitive data is logged

### Rate Limiting
- The SDK respects API rate limits
- Automatic retry with exponential backoff
- No credential stuffing risk

## Security Features

✅ **HTTPS Only** - All requests use TLS 1.2+
✅ **No Credential Storage** - Keys are passed at runtime
✅ **Input Validation** - Pydantic models validate all data
✅ **Type Safety** - Full type hints prevent injection risks
✅ **Error Handling** - Safe error messages don't leak secrets

## Security Updates

Security updates are released as patch versions (e.g., 1.0.1) and announced via:
- GitHub Security Advisories
- PyPI package metadata
- Email to registered users

## Attribution

We appreciate responsible disclosure and will credit reporters (with permission) in:
- CHANGELOG.md
- Security advisories
- Public acknowledgments

Thank you for helping keep OilPriceAPI secure!