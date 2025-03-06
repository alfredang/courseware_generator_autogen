import streamlit as st
from gemini_processor import process_documents, configure_google_sheets, SHEET_ID, SHEET_NAME

def main():
    st.title("Document Entity Extraction and Comparison")

    uploaded_files = st.file_uploader(
        "Upload Documents (Payslips, CPF Statements, ERP Screenshots, etc.)",
        type=["txt", "pdf", "png", "jpg", "jpeg"],  # Add more types if needed
        accept_multiple_files=True
    )

    if uploaded_files:
        st.write(f"You uploaded {len(uploaded_files)} document(s).")

        # Save uploaded files temporarily
        document_paths = []
        for uploaded_file in uploaded_files:
            with open(uploaded_file.name, "wb") as f:
                f.write(uploaded_file.getbuffer())
            document_paths.append(uploaded_file.name)

        if st.button("Process Documents"):
            with st.spinner("Processing documents..."):
                extracted_data, sheet_data, comparison_results = process_documents(document_paths)

                # Display extracted data
                st.header("Extracted Data")
                st.json(extracted_data)

                # Display Google Sheet data
                st.header("Google Sheet Data")
                st.json(sheet_data)

                # Display comparison results
                st.header("Comparison Results")
                for result in comparison_results:
                    st.subheader("Document Data:")
                    st.write(result["document_data"])

                    if result["best_match_from_sheet"]:
                        st.subheader("Best Match from Google Sheet:")
                        st.write(result["best_match_from_sheet"])

                        st.subheader("Match Scores:")
                        for key, score in result["match_scores"].items():
                            st.write(f"{key}: {score}%")
                    else:
                        st.write("No matching data found in Google Sheet.")

            st.success("Document processing complete!")

if __name__ == "__main__":
    main()