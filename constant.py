import uuid
import streamlit as st

# Initialize extractor and constants
SECTION_KEYWORDS = {
    "rfp_documents": "Request for Proposal (RFP) Document",
    "tor_documents": "Terms of Reference (ToR)",
    "evaluation_criteria_documents": "Technical Evaluation Criteria",
    "company_profiles_documents": "Company and Team Profiles",
    "social_standards_documents": "Environmental and Social Standards",
    "project_history_documents": "Project History and Relevant Experience",
    "additional_requirements_documents": "Additional Requirements and Compliance Documents",
}


def select_section():
    """Allow users to select a document section."""
    sections = list(SECTION_KEYWORDS.values())
    
    if not sections:
        st.error("No sections available for selection.")
        return None, None  # Return early to prevent further processing
    
    # Generate a unique key using UUID
    unique_key = f"uuid12_{str(uuid.uuid4())}"
    
    section = st.sidebar.selectbox("Select a document section:", options=sections, key=unique_key)
    table_name = next((key for key, value in SECTION_KEYWORDS.items() if value == section), None)
    
    return section, table_name