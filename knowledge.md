# Stack Auth Configuration

This project uses Stack Auth for authentication. The following credentials are used:

- Project ID: 1b75b67f-dd3c-4ec9-a484-e4dee6bbaf7f
- Publishable Client Key: pck_4n2gqkgkv8qjz3mtrcwebf5vj197qcy7g5akc698mm5f8
- Secret Server Key: ssk_fez279q74h6g44gt5hte5ta9vb37948vper2g7811vdcg (for server-side use only)

## Authentication Flow

1. User runs CLI without being authenticated
2. Browser opens to Stack Auth login page
3. User authenticates and gets refresh token
4. Refresh token is stored locally
5. Access token is obtained from refresh token for API calls

## Known Issues

- API returns job output with 'stdoutt' (misspelled). CLI handles both 'stdout' and 'stdoutt' fields for compatibility.