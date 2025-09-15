import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- CRITICAL: DEFINE THE CORRECT SCOPE ---
# This scope allows full read/write access. If you only need to read,
# you can use '.../auth/drive.readonly'.
SCOPES = ["https://www.googleapis.com/auth/drive"]

# --- The name of the folder you just created ---
FOLDER_TO_FIND = "MyTestFolderForAPI123"


def main():
    """Shows basic usage of the Drive v3 API."""
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("drive", "v3", credentials=creds)

        # Sanitize the folder name for the query
        sanitized_name = FOLDER_TO_FIND.replace("'", "\\'")
        query = f"name='{sanitized_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"

        print(f"Searching for folder with query: {query}")

        # Call the Drive v3 API
        results = (
            service.files()
            .list(
                q=query,
                fields="files(id, name)",
                # Important for finding things not just in "My Drive"
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )
        items = results.get("files", [])

        if not items:
            print("---")
            print("🔴 No folders found. See troubleshooting steps.")
            print("---")
            return

        print("---")
        print("🟢 Success! Found folder(s):")
        for item in items:
            print(f"  Name: {item['name']}, ID: {item['id']}")
        print("---")

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
