### Modern AI Project: Source Inventory

This inventory serves as the primary architectural reference for the Modern AI project, synthesizing foundational research, orchestration frameworks, and retrieval infrastructure. It provides a high-level technical map of the components necessary for engineering autonomous, stateful, and context-aware agentic systems.

##### 1\. LLM Powered Autonomous Agents | Lil'Log

* **URL:**  https://lilianweng.github.io/posts/2023-06-23-agent/  
* **Date:**  June 23, 2023  
* **Summary:**  This seminal article defines the Large Language Model (LLM) as the "brain" or core controller of an autonomous agent system. The architected framework comprises:  
* **Planning:**  Involves  **Task Decomposition**  (utilizing  **Chain of Thought**  or  **Tree of Thoughts**  to break complex goals into subgoals) and  **Self-Reflection** . Key reasoning frameworks include  **ReAct**  (synergizing reasoning and acting),  **Reflexion**  (dynamic memory and heuristic-based self-criticism), and  **Chain of Hindsight**  (learning from a history of feedback-annotated outputs).  
* **Memory:**  Distinguishes between  **Short-term Memory**  (leveraging  **In-context Learning**  and the model's finite attention span) and  **Long-term Memory**  (external vector stores). Retrieval is optimized via  **Maximum Inner Product Search (MIPS)** .  
* **Tool Use:**  The ability to call external APIs (e.g.,  **MRKL** ,  **HuggingGPT** ) to acquire real-time data or execute code, extending the agent's capabilities beyond its frozen pre-trained weights.

##### 2\. LangGraph: Agent Orchestration Framework for Reliable AI Agents

* **URL:**  https://www.langchain.com/langgraph  
* **Date:**  N/A  
* **Summary:**  LangGraph provides low-level orchestration primitives for designing reliable, stateful agentic workflows. Unlike "black-box" cognitive architectures, it allows architects to define:  
* **State Management:**  Built-in persistence that maintains context and conversation history across multiple sessions.  
* **Human-in-the-Loop:**  Explicit control points for human moderation, approval, and steering of agent actions to ensure safety and alignment.  
* **Custom Control Flows:**  Flexibility to build diverse architectures, including single-agent,  **Multi-agent** , and  **Hierarchical Control Flows** , moving beyond simple sequential chains to complex, cyclical graphs.

##### 3\. Project GraphRAG \- Microsoft Research

* **URL:**  N/A  
* **Date:**  N/A  
* **Summary:**  The provided source context for this entry contained no descriptive text, technical data, or contribution details. Under strict grounding rules, a synthesis of its role in the project cannot be provided.

##### 4\. The Illustrated Transformer

* **URL:**  https://jalammar.github.io/illustrated-transformer/  
* **Date:**  June 27, 2018  
* **Summary:**  This source details the fundamental Transformer architecture, the baseline for all modern agent "brains." The model consists of a  **stacked**  series of Encoders and Decoders (the original paper utilizes six).  
* **Self-Attention & Multi-headed Attention:**  Mechanisms that allow the model to focus on different positions and  **representation subspaces**  simultaneously, which is critical for an agent's ability to resolve context and dependencies.  
* **Positional Encoding:**  A specific mechanism using sine and cosine functions to bake the order of the sequence into the input embeddings, as the architecture lacks inherent recurrence.  
* **Parallelization:**  The architecture's ability to process sequence data in parallel (unlike RNNs) is what enables the massive scale and reasoning throughput required for modern AI controllers.

##### 5\. Welcome to LlamaIndex 🦙 \!

* **URL:**  https://developers.llamaindex.ai/python/framework/  
* **Date:**  N/A  
* **Summary:**  LlamaIndex is a comprehensive framework for  **Context Augmentation** , facilitating the connection of private, domain-specific data to LLMs. It defines several key architectural layers:  
* **Data Connectors & Indices:**  Tools for ingesting native data formats and structuring them into intermediate representations for performant retrieval.  
* **Engines:**  Provides natural language interfaces to data, specifically distinguishing between  **Query Engines**  (for discrete RAG flows) and  **Chat Engines**  (for stateful, multi-message interactions).  
* **Workflows:**  An  **event-driven system**  that offers a more flexible alternative to graph-based approaches, allowing for complex, reactive agentic logic with reflection and error correction.

##### 6\. What is retrieval augmented generation (RAG)? | IBM

1. **URL:**  https://www.ibm.com/think/topics/retrieval-augmented-generation  
2. **Date:**  N/A  
3. **Summary:**  IBM defines RAG as an architecture to optimize AI performance by grounding models in external, authoritative knowledge bases. The source identifies a specific  **five-stage process** :  
4. **Prompt:**  The user submits a query.  
5. **Retrieval:**  The system queries the knowledge base for data.  
6. **Relevant information returned:**  The knowledge base sends data back to the integration layer.  
7. **Augmented:**  The system engineers a prompt that combines the original query with the retrieved context.  
8. **Generation:**  The LLM produces the final output. Key architectural benefits include cost-efficiency (avoiding retraining), reduced  **hallucinations** , and the ability to access up-to-date, domain-specific data.

##### 7\. What is a Vector Database & How Does it Work?

* **URL:**  https://www.pinecone.io/learn/vector-database  
* **Date:**  May 3, 2023  
* **Summary:**  Vector databases act as the "long-term memory" for AI agents, managing  **Vector Embeddings**  created by LLMs. They are distinguished from standalone vector indices (like FAISS) by providing enterprise-grade data management, including:  
* **Operational Management:**  Native support for  **CRUD operations** ,  **Metadata Filtering** , and  **Real-time Updates** .  
* **Algorithms:**  Utilization of  **Approximate Nearest Neighbor (ANN)**  search algorithms—including  **HNSW**  (Hierarchical Navigable Small World) and  **Product Quantization (PQ)** —to balance retrieval speed with accuracy.  
* **Infrastructure:**  Modern  **Serverless**  architectures that decouple storage from compute, allowing for horizontal scaling and high elasticity to meet the demands of intelligence-heavy workloads.

