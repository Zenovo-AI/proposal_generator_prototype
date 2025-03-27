from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError


def debug_find_placeholders(docs_service, doc_id):
        """
        Fetch the document and print detected text content to check if placeholders exist.
        """
        try:
            doc = docs_service.documents().get(documentId=doc_id).execute()
            content = doc.get("body", {}).get("content", [])

            detected_text = []
            for element in content:
                if "paragraph" in element:
                    for text_run in element["paragraph"].get("elements", []):
                        if "textRun" in text_run:
                            detected_text.append(text_run["textRun"]["content"])

            print("\n--- Detected Text in Google Doc ---\n")
            print("\n".join(detected_text))  # Print all detected text in the document
            print("\n--- End of Document Text ---\n")

        except HttpError as e:
            print(f"Error fetching document: {e}")


class GoogleDocsHelper:
    """
    Handles Google Docs integration using template-based approach.
    """

    def __init__(self, docs_service, drive_service):
        if not isinstance(docs_service, Resource) or not isinstance(drive_service, Resource):
            raise ValueError("Requires valid Docs and Drive service instances")
        self.docs_service = docs_service
        self.drive_service = drive_service

    def create_from_template(self, template_id, replacements, document_name):
        """
        Copies a Google Docs template, replaces placeholders, and returns the new document ID.
        """
        try:
            # ✅ Step 1: Copy the existing Google Docs template
            copied_file = self.drive_service.files().copy(
                fileId=template_id,
                body={"name": document_name}
            ).execute()
            new_doc_id = copied_file["id"]

            # ✅ Step 2: Fetch document content for debugging
            debug_find_placeholders(self.docs_service, new_doc_id)

            # ✅ Step 3: Build text replacement requests
            requests = []
            for placeholder, content in replacements.items():
                requests.append({
                    "replaceAllText": {
                        "containsText": {"text": f"{{{placeholder}}}", "matchCase": True},
                        "replaceText": content or "[MISSING CONTENT]"
                    }
                })

            # ✅ Step 4: Execute text replacement
            self.docs_service.documents().batchUpdate(
                documentId=new_doc_id,
                body={"requests": requests}
            ).execute()

            return new_doc_id  # Returns the Google Docs file ID

        except HttpError as e:
            print(f"❌ Error creating document from template: {e}")
            raise


    def generate_view_link(self, file_id):
        """
        Generates a shareable Google Drive link to view the Google Doc file.
        """
        try:
            # ✅ Set file permissions to allow viewing
            self.drive_service.permissions().create(
                fileId=file_id,
                body={"role": "reader", "type": "anyone"},
                fields="id"
            ).execute()

            # ✅ Get the file's view link
            file = self.drive_service.files().get(fileId=file_id, fields="webViewLink").execute()
            return file.get("webViewLink")

        except HttpError as e:
            print(f"Error generating view link: {e}")
            return None


class GoogleDriveAPI:
    """
    Handles Google Drive operations such as retrieving templates and organizing files.
    """

    def __init__(self, service):
        self.service = service

    def get_template_id(self, template_name):
        """
        Find the template file ID in Google Drive by name.
        Searches for both Google Docs and .docx formats.
        """
        try:
            query = f"(name='{template_name}' and mimeType='application/vnd.google-apps.document')"  # Google Docs format
            
            response = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, mimeType)'
            ).execute()

            return response['files'][0]['id']
        
        except (KeyError, IndexError):
            raise ValueError(f"Template '{template_name}' not found in Google Drive")


    def create_folder(self, folder_name, parent_folder_id=None):
        """
        Creates a folder in Google Drive if it doesn't already exist.
        """
        try:
            # ✅ Check if the folder already exists
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
            if parent_folder_id:
                query += f" and '{parent_folder_id}' in parents"

            existing = self.service.files().list(
                q=query,
                fields='files(id)'
            ).execute().get('files', [])

            if existing:
                return existing[0]['id']  # Return existing folder ID

            # ✅ Create a new folder
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_folder_id] if parent_folder_id else []
            }
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            return folder['id']

        except HttpError as e:
            print(f"Folder creation failed: {e}")
            raise



# class GoogleDocsHelper:
#     """
#     Handles Google Docs integration using template-based approach
#     """
    
#     def __init__(self, docs_service, drive_service):
#         if not isinstance(docs_service, Resource) or not isinstance(drive_service, Resource):
#             raise ValueError("Requires valid Docs and Drive service instances")
#         self.docs_service = docs_service
#         self.drive_service = drive_service

#     def create_from_template(self, template_id, replacements, document_name="New Document"):
#         """
#         Creates document from template with placeholder replacements
#         """
#         try:
#             # Copy template file
#             new_file = self.drive_service.files().copy(
#                 fileId=template_id,
#                 body={'name': document_name}
#             ).execute()
#             new_doc_id = new_file['id']

#             # Build replacement requests
#             requests = []
#             for placeholder, content in replacements.items():
#                 requests.append({
#                     'replaceAllText': {
#                         'containsText': {
#                             'text': f'{{{placeholder}}}',
#                             'matchCase': True
#                         },
#                         'replaceText': content
#                     }
#                 })

#             # Execute batch update
#             self.docs_service.documents().batchUpdate(
#                 documentId=new_doc_id,
#                 body={'requests': requests}
#             ).execute()

#             return new_doc_id

#         except HttpError as e:
#             print(f"Template processing failed: {e}")
#             raise

#     def update_template_content(self, doc_id, replacements):
#         """
#         Updates existing document with new content using template placeholders
#         """
#         try:
#             requests = []
#             for placeholder, content in replacements.items():
#                 requests.append({
#                     'replaceAllText': {
#                         'containsText': {
#                             'text': f'{{{placeholder}}}',
#                             'matchCase': True
#                         },
#                         'replaceText': content
#                     }
#                 })

#             self.docs_service.documents().batchUpdate(
#                 documentId=doc_id,
#                 body={'requests': requests}
#             ).execute()

#         except HttpError as e:
#             print(f"Document update failed: {e}")
#             raise

# class GoogleDriveAPI:
#     def __init__(self, service):
#         self.service = service

#     def create_template_document(self, template_name="ProposalTemplate"):
#         """Create a properly formatted template document with placeholders"""
#         try:
#             # Create empty document
#             doc_service = build('docs', 'v1', credentials=self.service._http.credentials)
#             document = doc_service.documents().create(body={'title': template_name}).execute()
#             doc_id = document['documentId']
            
#             # Build template content with proper request separation
#             requests = [
#                 # Document title
#                 {
#                     'insertText': {
#                         'location': {'index': 1},
#                         'text': "Proposal Template\n"
#                     }
#                 },
#                 {
#                     'updateParagraphStyle': {
#                         'range': {'startIndex': 1, 'endIndex': 17},
#                         'paragraphStyle': {'namedStyleType': 'TITLE'},
#                         'fields': 'namedStyleType'
#                     }
#                 },
                
#                 # Header section
#                 {
#                     'insertText': {
#                         'location': {'index': 2},
#                         'text': "{{HEADER}}\n"
#                     }
#                 },
                
#                 # RFQ Number
#                 {
#                     'insertText': {
#                         'location': {'index': 3},
#                         'text': "Proposal for RFQ No. {{RFQ_NUMBER}}\n"
#                     }
#                 },
#                 {
#                     'updateParagraphStyle': {
#                         'range': {'startIndex': 3, 'endIndex': 3 + len("Proposal for RFQ No. {{RFQ_NUMBER}}") + 1},
#                         'paragraphStyle': {'namedStyleType': 'HEADING_1'},
#                         'fields': 'namedStyleType'
#                     }
#                 },
                
#                 # Executive Summary
#                 {
#                     'insertText': {
#                         'location': {'index': 4},
#                         'text': "Executive Summary\n{{EXECUTIVE_SUMMARY}}\n\n"
#                     }
#                 },
                
#                 # Scope of Work
#                 {
#                     'insertText': {
#                         'location': {'index': 5},
#                         'text': "Scope of Work\n{{SCOPE_OF_WORK}}\n\n"
#                     }
#                 },
                
#                 # Timeline Table
#                 {
#                     'insertText': {
#                         'location': {'index': 6},
#                         'text': "Project Timeline\n{{TIMELINE_TABLE}}\n\n"
#                     }
#                 },
                
#                 # Contact Info
#                 {
#                     'insertText': {
#                         'location': {'index': 7},
#                         'text': "Contact Information\n{{CONTACT_INFO}}\n"
#                     }
#                 }
#             ]
            
#             # Execute batch update
#             doc_service.documents().batchUpdate(
#                 documentId=doc_id,
#                 body={'requests': requests}
#             ).execute()
            
#             return doc_id
            
#         except Exception as e:
#             raise RuntimeError(f"Template creation failed: {str(e)}")

#     def _create_heading_request(self, text, level):
#         return {
#             'insertText': {
#                 'location': {'index': 1},
#                 'text': f'{text}\n'
#             },
#             'updateParagraphStyle': {
#                 'range': {'startIndex': 1, 'endIndex': len(text)+2},
#                 'paragraphStyle': {'namedStyleType': f'HEADING_{level}'},
#                 'fields': 'namedStyleType'
#             }
#         }

#     def _create_section_request(self, title, placeholder):
#         return {
#             'insertText': {
#                 'location': {'index': 1},
#                 'text': f'{title}\n{placeholder}\n\n'
#             }
#         }

#     def _create_table_request(self, title, placeholder):
#         return {
#             'insertText': {
#                 'location': {'index': 1},
#                 'text': f'{title}\n{placeholder}\n\n'
#             }
#         }

#     def get_or_create_template(self, template_name="ProposalTemplate"):
#         """Self-healing template retrieval with error handling"""
#         try:
#             template_id = self.create_template_document(template_name)
            
#             # Move to templates folder
#             templates_folder_id = self.create_folder("ProposalTemplates")
#             self.service.files().update(
#                 fileId=template_id,
#                 addParents=templates_folder_id,
#                 removeParents='root',
#                 fields='id, parents'
#             ).execute()
            
#             return template_id
                
#         except Exception as e:
#             return None
        
#     def get_template_id(self, template_name):
#         """Find template ID by name"""
#         try:
#             response = self.service.files().list(
#                 q=f"name='{template_name}' and mimeType='application/vnd.google-apps.document'",
#                 spaces='drive',
#                 fields='files(id, name)'
#             ).execute()
#             return response['files'][0]['id']
#         except (KeyError, IndexError):
#             raise ValueError(f"Template '{template_name}' not found in Google Drive")

#     def create_folder(self, folder_name, parent_folder_id=None):
#         """Create folder with duplicate check"""
#         try:
#             # Check for existing folder
#             query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
#             if parent_folder_id:
#                 query += f" and '{parent_folder_id}' in parents"
                
#             existing = self.service.files().list(
#                 q=query,
#                 fields='files(id)'
#             ).execute().get('files', [])
            
#             if existing:
#                 return existing[0]['id']

#             # Create new folder
#             folder_metadata = {
#                 'name': folder_name,
#                 'mimeType': 'application/vnd.google-apps.folder',
#                 'parents': [parent_folder_id] if parent_folder_id else []
#             }
#             folder = self.service.files().create(
#                 body=folder_metadata,
#                 fields='id'
#             ).execute()
#             return folder['id']
#         except HttpError as e:
#             print(f"Folder creation failed: {e}")
#             raise