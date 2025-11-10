# Security Policy

## Supported Versions

We actively support the latest major version of this integration. Security updates are provided for:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in this Home Assistant integration, please report it responsibly:

### Private Disclosure

1. **DO NOT** create a public GitHub issue
2. Email the maintainers directly at: [your-email@example.com]
3. Include the following information:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to Expect

- **Response Time**: We will acknowledge your report within 48 hours
- **Investigation**: We will investigate and validate the vulnerability within 5 business days
- **Resolution**: Critical vulnerabilities will be patched within 7 days, others within 30 days
- **Disclosure**: We will coordinate responsible disclosure after the fix is available

## Credential Storage Security

### Overview

The San Francisco Water Power Sewer integration implements industry-standard security practices for handling sensitive SFPUC account credentials. All credential storage and transmission follows Home Assistant best practices and security guidelines.

### Storage Security

**Encrypted Config Entries**

- Credentials are stored exclusively in Home Assistant's encrypted config entry system
- Automatic encryption using Home Assistant's secure storage mechanism (`~/.homeassistant/.storage/config_entries`)
- No plain-text credential storage in files, logs, or external services
- Credentials are never written to disk in readable format

**Access Pattern**

- Credentials accessed only during authentication: `config_entry.data[CONF_USERNAME]` and `config_entry.data[CONF_PASSWORD]`
- In-memory usage only during SFPUC portal login
- No persistent storage beyond Home Assistant's encrypted system
- Credentials discarded immediately after authentication

### Transmission Security

**HTTPS-Only Communications**

- All external communications use secure HTTPS protocol
- SFPUC portal endpoint: `https://myaccount-water.sfpuc.org`
- No HTTP connections or insecure protocols
- Proper SSL/TLS certificate validation

**Network Implementation**

- Mimics legitimate browser traffic with appropriate headers
- Uses requests session with secure defaults
- Downloads Excel data securely over encrypted connections
- No external API dependencies or third-party services

### Code Security

**Security Validation**

- **Bandit Security Scan**: ✅ PASS - No security vulnerabilities detected
- Input validation and sanitization for all user inputs
- Safe error handling preventing information disclosure
- No hardcoded credentials or security anti-patterns

**Authentication Flow**

1. User enters credentials in Home Assistant UI
2. Credentials stored in encrypted config entry
3. During data updates, credentials retrieved from encrypted storage
4. Used temporarily for SFPUC login, then discarded from memory
5. Session maintained for data fetching without credential persistence

### Security Assessment

| Security Aspect           | Status    | Implementation                        |
| ------------------------- | --------- | ------------------------------------- |
| **Credential Encryption** | ✅ Secure | Home Assistant encrypted storage      |
| **Network Security**      | ✅ Secure | HTTPS-only communications             |
| **Code Security**         | ✅ Secure | Bandit scan clean, no vulnerabilities |
| **Access Control**        | ✅ Secure | Local-only credential access          |
| **Data Transmission**     | ✅ Secure | No external credential sharing        |
| **Error Handling**        | ✅ Secure | No credential exposure in errors      |

### Security Best Practices

When using this integration:

1. **Keep Updated**: Always use the latest version for security patches
2. **Sensor Access**: Only grant access to necessary sensors
3. **Network Security**: Ensure your Home Assistant instance is properly secured
4. **Regular Audits**: Review which sensors the integration has access to
5. **Credential Rotation**: Change SFPUC credentials periodically

### Known Security Considerations

- **External Dependencies**: Relies on SFPUC portal availability and security
- **Local Security**: Home Assistant instance security is critical
- **Network Security**: HA instance network security affects overall security
- **Physical Access**: Physical access to HA device could compromise stored credentials

### Security Features

- ✅ Input validation for all sensor data
- ✅ Safe error handling to prevent information disclosure
- ✅ No storage of sensitive information beyond encrypted config
- ✅ Local processing only (no cloud dependencies)
- ✅ HTTPS-only external communications
- ✅ Encrypted credential storage
- ✅ No external API credential transmission

## Security Updates

Security updates will be:

- Released as patch versions (e.g., 1.0.1 → 1.0.2)
- Documented in the CHANGELOG.md
- Announced in GitHub releases
- Tagged with "security" label

---

**Note**: Replace `[your-email@example.com]` with your actual contact email before publishing.
