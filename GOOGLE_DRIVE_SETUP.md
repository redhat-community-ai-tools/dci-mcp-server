# Google Drive Integration Setup

This document explains how to set up Google Drive integration for the DCI MCP Server to enable converting markdown reports to Google Docs.

## Prerequisites

1. A Google account
2. Access to Google Cloud Console
3. Python environment with the DCI MCP Server installed

## Step-by-Step Setup

### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter a project name (e.g., "DCI-MCP-Server")
4. Location: select Default Projects
5. Click "Create"

### 2. Enable Google Drive API

1. In the Google Cloud Console, go to "APIs & Services" → "Library"
2. Search for "Google Drive API"
3. Click on "Google Drive API" and then "Enable"

### 3. Create OAuth 2.0 Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - Choose "Internal" user type
   - Fill in the required fields (App name, User support email, Developer contact)
   - Add your email to test users
4. For Application type, select "Desktop application"
5. Give it a name (e.g., "DCI MCP Server")
6. Click "Create"
7. Download the JSON file and save it as `credentials.json` in your project root

### 4. Configure Environment Variables

1. Copy `env.example` to `.env`:
   ```bash
   cp env.example .env
   ```

2. Edit `.env` and add your Google Drive configuration:
   ```bash
   # Google Drive Integration
   GOOGLE_CREDENTIALS_PATH=/Absolute/Path/credentials.json
   GOOGLE_TOKEN_PATH=/Absolute/Path/token.json
   ```

### 5. Install Dependencies

The Google Drive dependencies are already included in `pyproject.toml`. Install them with:

```bash
uv sync
```

### 6. Initialize Google Drive Service

Before using the Google Drive tools, you need to initialize the service and complete the OAuth authentication:

```bash
# Test and initialize the Google Drive service
uv run python -c "
from mcp_server.services.google_drive_service import GoogleDriveService
try:
    service = GoogleDriveService()
    print('✅ Google Drive service initialized successfully')
    print('✅ Authentication completed - you can now use Google Drive tools')
except Exception as e:
    print(f'❌ Error: {e}')
"
```

**What happens during initialization:**

1. **First Run**: The command will display an OAuth URL like:
   ```
   Please visit this URL to authorize this application: 
   https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=...
   ```

2. **Browser Authentication**: 
   - Copy and paste the URL into your browser
   - Sign in with your Google account
   - Grant permissions to access your Google Drive
   - You'll see a "Success" page in your browser

3. **Token Storage**: The OAuth token is automatically saved to `token.json` for future use

4. **Success Message**: You'll see "Google Drive service initialized successfully"

**Important Notes:**
- This step only needs to be done once
- The `token.json` file will be created automatically
- Never share or commit the `token.json` file to version control

### 7. Test the Integration

After successful initialization, you can test the Google Drive tools:

```bash
# Test creating a simple Google Doc
uv run python -c "
from mcp_server.services.google_drive_service import GoogleDriveService
service = GoogleDriveService()
result = service.create_google_doc_from_markdown(
    '# Test Document\n\nThis is a **test** document.',
    'Test Document'
)
print(f'✅ Created Google Doc: {result[\"url\"]}')
"
```

Or run the full MCP server:

```bash
uv run python -m mcp_server.main
```

## Available Google Drive Tools

Once configured, the following MCP tools will be available:

### `create_google_doc_from_markdown`
Creates a Google Doc from markdown content.

**Parameters:**
- `markdown_content`: The markdown content to convert
- `doc_title`: The title for the Google Doc
- `folder_id`: Optional folder ID to place the document in

### `create_google_doc_from_file`
Creates a Google Doc from a markdown file.

**Parameters:**
- `file_path`: Path to the markdown file
- `doc_title`: Optional title (defaults to filename)
- `folder_id`: Optional folder ID

### `convert_dci_report_to_google_doc`
Specialized tool for converting DCI reports to Google Docs.

**Parameters:**
- `report_path`: Path to the DCI report markdown file
- `doc_title`: Optional title (defaults to report filename)
- `folder_id`: Optional folder ID

### `list_google_docs`
Lists Google Docs in your Drive.

**Parameters:**
- `query`: Optional search query
- `max_results`: Maximum number of results (1-100)

### `delete_google_doc`
Deletes a Google Doc (use with caution).

**Parameters:**
- `document_id`: The ID of the document to delete

## Usage Examples

### Convert a DCI Report to Google Doc

```python
# Using the MCP tool
result = await convert_dci_report_to_google_doc(
    report_path="/tmp/dci/samsungran_weekly_report_2025-09-09.md",
    doc_title="SamsungRAN Weekly Report - September 2025"
)
```

### Create a Google Doc from Markdown Content

```python
markdown_content = """
# My Report

This is a **markdown** report with:

- Bullet points
- **Bold text**
- *Italic text*

## Table

| Column 1 | Column 2 |
|----------|----------|
| Value 1  | Value 2  |
"""

result = await create_google_doc_from_markdown(
    markdown_content=markdown_content,
    doc_title="My Custom Report"
)
```

## Authentication Flow

1. **First Run**: The application will open a browser window for OAuth authentication
2. **Grant Permissions**: Allow the application to access your Google Drive
3. **Token Storage**: The OAuth token is saved to `token.json` for future use
4. **Subsequent Runs**: The stored token is used automatically

## Troubleshooting

### Common Issues

1. **"Credentials file not found"**
   - Ensure `credentials.json` is in the project root
   - Check the `GOOGLE_CREDENTIALS_PATH` environment variable

2. **"Authentication failed"**
   - Delete `token.json` and re-authenticate using the initialization step
   - Check that the OAuth consent screen is properly configured
   - Make sure you completed the browser authentication flow

3. **"API not enabled"**
   - Ensure Google Drive API is enabled in Google Cloud Console

4. **"Permission denied"**
   - Check that your email is added to test users in OAuth consent screen
   - Verify the OAuth scopes include `https://www.googleapis.com/auth/drive.file`

5. **"Service not initialized"**
   - Run the initialization step (Step 6) before using Google Drive tools
   - Ensure you completed the browser authentication process
   - Check that `token.json` was created successfully

6. **"Browser authentication not working"**
   - Make sure you copy the entire OAuth URL from the terminal
   - Check that your browser can access Google accounts
   - Try using an incognito/private browser window

### File Permissions

Ensure the application has write permissions to create `token.json` in the project directory.

## Security Notes

- Never commit `credentials.json` or `token.json` to version control
- The OAuth token provides access to your Google Drive - keep it secure
- Consider using a dedicated Google account for automation if needed

## Advanced Configuration

### Custom Scopes

The default scope is `https://www.googleapis.com/auth/drive.file` which allows:
- Creating files in Google Drive
- Accessing files created by the application

To modify scopes, edit `mcp_server/services/google_drive_service.py`:

```python
SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.readonly"  # Add read-only access
]
```

### Custom Token Location

Set the `GOOGLE_TOKEN_PATH` environment variable to store the token in a different location:

```bash
export GOOGLE_TOKEN_PATH=/secure/location/token.json
```

## Support

For issues with Google Drive integration:
1. Check the troubleshooting section above
2. Review Google Drive API documentation
3. Check the application logs for detailed error messages
