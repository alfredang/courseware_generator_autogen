"""
TODO: 
1. Create Input (TSC Form) parser that parses the TSC form and maps it to a JSON schema to be sent to the planning team/agent.
2. Planning team will create a retrieval plan on how to retrieve the information required to support the A and K factors. Perhaps limited to 5 key topics to be retrieved.
3. Retrieval team will receive the retrieval plan (topics) and attempt to parse the vector store for information. If it is decided that information cannot be found, then perhaps an online search tool function can be added.
4. Retrieved information will be sent to the planning team for review and to determine if the information is relevant to the TSC form.
5. The planning team will then send the relevant information to the assessment creation team for it to create questions and answers, returning in a JSON schema that allows for easy mapping to a document file.

Functions to deliver:
- Input (TSC Form) parser: DONE
- Planning team
- Retrieval team
- Assessment Creation team
- Assessment template
- RAG pipeline (Ingestion, Vector Store, Semantic Search)
"""