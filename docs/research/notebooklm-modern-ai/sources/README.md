# NotebookLM Source Bundle

Downloaded for use by Claude Code, Codex, or another coding agent.

## Sources

| File | Original URL | Status |
|---|---|---|
| `lilian-weng-autonomous-agents.html` | https://lilianweng.github.io/posts/2023-06-23-agent/ | Downloaded |
| `langgraph.html` | https://www.langchain.com/langgraph | Downloaded |
| `microsoft-graphrag.md` | https://www.microsoft.com/en-us/research/project/graphrag/ | Browser-captured summary; direct HTML returned HTTP 403 |
| `illustrated-transformer.html` | https://jalammar.github.io/illustrated-transformer/ | Downloaded |
| `llamaindex-framework.html` | https://developers.llamaindex.ai/python/framework/ | Downloaded |
| `ibm-rag.html` | https://www.ibm.com/think/topics/retrieval-augmented-generation | Downloaded |
| `pinecone-vector-database.html` | https://www.pinecone.io/learn/vector-database/ | Downloaded |

The HTML files are the original fetched pages. They may contain navigation and styling markup; preserve them as source snapshots and use the canonical URLs for current documentation checks.

## How to give this to an agent

Point the agent at this directory and say:

> Read every file in `outputs/notebooklm-sources/` before proposing an implementation. Treat the original URLs as current-documentation references, but do not add a dependency or framework solely because a source mentions it. Extract claims into a requirements traceability matrix, label source-grounded facts versus design choices, and verify all version-sensitive choices against the project’s installed dependencies and authoritative documentation.

Do not treat the downloaded pages as permission to upload private project data or activate external tools.
