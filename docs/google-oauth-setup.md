# Google OAuth 2.0 Setup Guide

This guide walks you through creating OAuth 2.0 credentials in Google Cloud Console for the iConcierge Google Calendar integration.

## Prerequisites

- Google Cloud project (already set up for Google Maps API)
- Admin access to the Google Cloud Console

---

## Step 1: Enable Google Calendar API

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Select your project (the one used for Google Maps API)
3. Navigate to **APIs & Services > Library**
4. Search for "Google Calendar API"
5. Click on **Google Calendar API**
6. Click **Enable**

---

## Step 2: Configure OAuth Consent Screen

1. Go to **APIs & Services > OAuth consent screen**
2. If not already configured:
   - Select **External** user type (for testing with your Google account)
   - Click **Create**

3. Fill in the **OAuth consent screen** form:
   - **App name:** iConcierge
   - **User support email:** Your email
   - **App logo:** (optional)
   - **Application home page:** `http://localhost:3000` (for development)
   - **Authorized domains:** Leave empty for local development
   - **Developer contact information:** Your email
   - Click **Save and Continue**

4. **Scopes** page:
   - Click **Add or Remove Scopes**
   - Search for and select these scopes:
     - `https://www.googleapis.com/auth/calendar.readonly` - View your calendars
     - `https://www.googleapis.com/auth/calendar.events` - Create and edit events
   - Click **Update**
   - Click **Save and Continue**

5. **Test users** page (for External apps in testing):
   - Click **Add Users**
   - Add your Google account email (the one you'll use for testing)
   - Click **Save and Continue**

6. **Summary** page:
   - Review and click **Back to Dashboard**

---

## Step 3: Create OAuth 2.0 Credentials

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials** > **OAuth client ID**
3. Select **Application type:** Web application
4. Fill in the form:
   - **Name:** iConcierge Web Client
   - **Authorized JavaScript origins:**
     - `http://localhost:3000` (development)
     - Add production domain later (e.g., `https://yourdomain.com`)
   - **Authorized redirect URIs:**
     - `http://localhost:3000/api/auth/callback/google` (development)
     - Add production callback later (e.g., `https://yourdomain.com/api/auth/callback/google`)
   - Click **Create**

5. A popup appears with your credentials:
   - **Client ID** - looks like: `123456789-abcdefg.apps.googleusercontent.com`
   - **Client Secret** - looks like: `GOCSPX-abc123xyz`
   - Click **OK**

6. Download the credentials (optional backup):
   - Click the download icon next to your newly created OAuth 2.0 Client ID
   - Save the JSON file securely (DO NOT commit to git)

---

## Step 4: Generate Token Encryption Key

For encrypting OAuth tokens in the database, generate a Fernet key:

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

This will output something like:
```
xYz123ABC-def456GHI_jkl789MNO=
```

---

## Step 5: Add Credentials to Environment

1. Open `backend/.env` (create from `.env.example` if it doesn't exist)

2. Add the credentials:

```env
GOOGLE_CLIENT_ID=123456789-abcdefg.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-abc123xyz
TOKEN_ENCRYPTION_KEY=xYz123ABC-def456GHI_jkl789MNO=
```

3. **IMPORTANT:** Never commit the `.env` file to git. It's already in `.gitignore`.

---

## Step 6: Verify Setup

1. Restart your backend:
   ```bash
   docker-compose restart backend
   ```

2. Check that the app starts without errors:
   ```bash
   docker-compose logs backend | grep -i "google\|oauth"
   ```

---

## OAuth Flow Overview (for reference)

Once credentials are configured, the OAuth flow works as follows:

1. **User clicks "Connect Google Calendar"** in the frontend
2. **Backend generates authorization URL** and redirects user to Google
3. **User grants permissions** in Google's consent screen
4. **Google redirects back** to your app with an authorization code
5. **Backend exchanges code for tokens** (access + refresh)
6. **Backend encrypts and stores tokens** in the `oauth_tokens` table
7. **Backend can now access user's calendar** using the stored tokens

---

## Troubleshooting

### "Access blocked: This app's request is invalid"

- Check that the redirect URI in Google Cloud Console exactly matches the one your app uses
- Common mistake: `http://localhost:3000/callback` vs `http://localhost:3000/api/auth/callback/google`

### "Error 400: redirect_uri_mismatch"

- The redirect URI must be registered in Google Cloud Console under **Authorized redirect URIs**
- Make sure there are no trailing slashes

### "This app isn't verified"

- For testing with External user type, add your Google account under **Test users**
- Or publish the app (requires verification for production)

### Tokens expire or become invalid

- Access tokens expire after 1 hour
- The backend uses the refresh token to get a new access token automatically
- If refresh token is invalid, user needs to reconnect their Google Calendar

---

## Security Best Practices

1. **Never commit credentials to git**
   - `.env` is in `.gitignore`
   - Don't hardcode credentials in code

2. **Use environment variables**
   - Store all secrets in `.env`
   - Use `settings.GOOGLE_CLIENT_ID` in code

3. **Tokens are encrypted in the database**
   - The `TOKEN_ENCRYPTION_KEY` encrypts access/refresh tokens
   - Keep this key secure and don't share it

4. **Rotate credentials if exposed**
   - If credentials leak, delete them in Google Cloud Console
   - Generate new OAuth client ID and secret

5. **Use HTTPS in production**
   - Never send credentials over unencrypted HTTP
   - Update redirect URIs to use HTTPS when deploying

---

## Production Deployment

When deploying to production:

1. **Update OAuth consent screen**:
   - Change authorized domains to your production domain
   - Optionally publish the app (requires Google verification)

2. **Update OAuth client**:
   - Add production JavaScript origin: `https://yourdomain.com`
   - Add production redirect URI: `https://yourdomain.com/api/auth/callback/google`

3. **Update environment variables**:
   - Set production values in your hosting platform's env config
   - Never use the same credentials for dev and production

4. **Remove test users** (if you verified the app)

---

## Additional Resources

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Google Calendar API Reference](https://developers.google.com/calendar/api/v3/reference)
- [OAuth 2.0 Scopes for Google APIs](https://developers.google.com/identity/protocols/oauth2/scopes)
