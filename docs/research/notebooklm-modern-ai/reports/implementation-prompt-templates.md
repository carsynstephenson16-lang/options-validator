### Implementation Prompt Templates for Autonomous RAG Agents

This architectural reference provides production-ready prompt templates for building high-fidelity, autonomous agents. These templates implement complex agentic components—Planning, Memory, Tool Use, and RAG—utilizing technical frameworks defined by Lilian Weng, LangGraph, and IBM Research.

#### 1\. Phase One: Planning and Task Decomposition

In this phase, the Large Language Model (LLM) functions as the central controller, utilizing test-time computation to break down complex objectives into executable trajectories.

##### 1.1 Standard Task Decomposition (Chain of Thought)

**Objective:**  Enhance reasoning via "Think Step by Step" logic to identify subgoals."You are a Task Decomposition Module. Your goal is to transform a high-level user request into a sequence of discrete, manageable subgoals.**User Request:**  {{USER\_REQUEST}}**Execution Strategy:**

1. Analyze the terminal state required by the request.  
2. Think step-by-step to identify necessary prerequisites.  
3. List the subgoals in logical order.**Plan:**  1."

##### 1.2 Subgoal Generation (Tree of Thoughts)

**Objective:**  Explore multiple reasoning paths simultaneously using BFS/DFS-style evaluation."Act as a Reasoning Orchestrator using the Tree of Thoughts (ToT) framework. For the given problem, generate three distinct potential first steps. For each step, evaluate its feasibility and project the likely outcome.**Problem:**  {{PROBLEM}}**Structure:**

* Root: {{PROBLEM}}  
* Path A Confidence Score: 0-1: Action \-\> Expected Result  
* Path B Confidence Score: 0-1: Action \-\> Expected Result  
* Path C Confidence Score: 0-1: Action \-\> Expected ResultSelect the path with the highest confidence score and repeat the decomposition for the next level."

##### 1.3 External Planning Interface (LLM+P)

**Objective:**  Translate natural language into Planning Domain Definition Language (PDDL) for classical planners."You are an LLM+P translation interface. Translate the following natural language problem into a valid 'Problem PDDL' file.**Constraints:**

* You MUST strictly use ONLY the predicates and actions defined in the provided Domain PDDL: {{DOMAIN\_PDDL}}.  
* Do not invent new predicates or state variables.**Natural Language Problem:**  {{PROBLEM\_DESCRIPTION}}**Problem PDDL Output:** "

##### 1.4 Self-Reflection and Refinement (Reflexion Framework)

**Objective:**  Use two-shot self-criticism to correct hallucinations and logic errors."You are a Self-Correction Module operating under the Reflexion framework. Review the following execution trajectory for two specific failure modes:

1. **Hallucination:**  Defined as a sequence of consecutive identical actions that lead to the same observation.  
2. **Inefficient Planning:**  Defined as trajectories that exceed time/step limits without measurable progress toward the goal.{{FEW\_SHOT\_EXAMPLES}}**Current Trajectory:**  {{TRAJECTORY\_HISTORY}}  **Last Observation:**  {{LAST\_OBSERVATION}}**Reflection:**  Identify if a Hallucination or Inefficient Plan occurred.  **Refined Strategy:**  Provide a corrective instruction for the next trial to bypass previous errors."

#### 2\. Phase Two: Memory and Context Management

These templates facilitate the transition between short-term "Working Memory" (In-Context Learning) and long-term "External Memory" (Vector Stores).

##### 2.1 Short-Term Memory (In-Context Learning)

**Objective:**  Manage the finite attention span of the Transformer architecture using the Miller (1956) limit."System Message: You are an agent with a finite Working Memory. To maintain cognitive performance, you must prioritize information effectively.**Working Memory Constraints:**

* Human cognitive capacity is limited to approximately 7 items.  
* You must extract and retain only the 7 most salient facts or state variables from the current conversation history.**Conversation History:**  {{CONVERSATION\_HISTORY}}  **Active Working Memory:**  List the 7 prioritized items here"

##### 2.2 Long-Term Memory Retrieval (MIPS)

**Objective:**  Formulate queries for Maximum Inner Product Search (MIPS) in Pinecone, accounting for ANN latency."You need to retrieve context from a Pinecone vector database. Formulate a search query embedding focused on semantic intent rather than keyword matching.**Optimization Note:**  The system uses Approximate Nearest Neighbors (ANN) algorithms (HNSW/FAISS) to optimize retrieval speed. To counteract potential precision loss from ANN latency trade-offs, ensure your query is highly descriptive and emphasizes core entities.**User Intent:**  {{USER\_INPUT}}  **MIPS-Optimized Query:** "

##### 2.3 Experience Reflection (Generative Agents)

**Objective:**  Synthesize high-level inferences using Recency, Importance, and Relevance scoring."Review the 100 most recent observations in your memory stream.**Scoring Criteria:**

1. **Recency:**  Higher weight for the most recent events.  
2. **Importance:**  Distinguish core memories from mundane observations (Score 1-10).  
3. **Relevance:**  How related the observation is to the current goal: {{CURRENT\_GOAL}}.**Observations:**  {{RECENT\_100\_OBSERVATIONS}}**Salient Questions:**  Based on the highest-scoring observations across these three criteria, generate the 3 most salient high-level questions to summarize your past experiences."

#### 3\. Phase Three: RAG Pipeline Implementation

This section defines the core grounding and retrieval logic required for high-trust Retrieval-Augmented Generation.

##### 3.1 The Retrieval Query Generator

**Objective:**  Rewrite complex queries for semantic vector search."Re-write the following user query into a format optimized for semantic vector search.

1. Extract the primary intent.  
2. Identify all key entities.  
3. Remove conversational filler.**User Query:**  {{COMPLEX\_QUERY}}  **Vector-Search Query:** "

##### 3.2 The "Augmented" Response Generator

**Objective:**  Generate responses constrained by a structured context-control mechanism."Generate a response to the User Query based strictly on the provided context. The following table defines your operational boundaries:**Response:** "

##### 3.3 Source Citation and Grounding

**Objective:**  Increase user trust and penalize hallucinations via verbatim citations."Answer the user question using ONLY the provided context.**Strict Grounding Rules:**

* You must include verbatim citations for every claim.  
* Citations must follow the machine-parseable format: \[source\_id\].  
* **Negative Constraint:**  Your performance score will be penalized for any information used that is not present in the context (hallucinations) or for claims missing a corresponding \[source\_id\].**Context:**  {{CONTEXT}}  **Question:**  {{USER\_QUESTION}}**Response:** "

#### 4\. Phase Four: Orchestration and Tool Use

Managing the interaction between the LLM "brain" and expert modules or symbolic tools (MRKL/HuggingGPT).

##### 4.1 Task Parsing for Expert Modules (HuggingGPT)

**Objective:**  Parse input into executable JSON with task-dependency tags."Parse the user request into a JSON list of tasks.**Schema Requirements:**

* task: Type of task (must be from {{AVAILABLE\_TASKS}}).  
* id: Unique integer ID.  
* dep: List of dependency IDs. Use the special tag '-task\_id' (e.g., '-1') to reference the output of a previous task.  
* args: Dictionary of required tool arguments.{{FEW\_SHOT\_EXAMPLES}}**User Request:**  {{USER\_REQUEST}}  **JSON Task List:** "

##### 4.2 Model/Tool Selection (Router)

**Objective:**  Function as a router using task-type filtration for limited context windows."Given the user requirement, select the most appropriate expert module. To optimize for the limited context window, first filter by Task Type (e.g., Image Processing vs. Text Analytics).**User Requirement:**  {{REQUIREMENT}}  **Candidate Tools:**  {{TOOL\_DESCRIPTIONS}}**Selection Output (JSON):**  { "id": "TOOL\_ID", "reason": "Explain why this tool fits the specific Task Type." }"

##### 4.3 Human-in-the-Loop (HITL) Trigger

**Objective:**  Moderate and control high-stakes actions."Analyze the planned action. If the action meets any of the following 'High-Stakes' criteria, you must PAUSE execution:

1. Executing code on a production server.  
2. Financial transactions \> $0.00.  
3. Deleting or modifying a database record.**Action:**  {{ACTION\_DETAILS}}  **Status:**  APPROVE/PAUSE  **Reasoning:** "

##### 4.4 The ReAct Cycle (Thought/Action/Observation)

**Objective:**  Implement the Reasoning \+ Acting iterative loop."Solve the task using the Thought/Action/Observation cycle.**Task:**  {{TASK\_DESCRIPTION}}**Thought:**  Reason about the current state and next requirement  **Action:**  Select tool from {{AVAILABLE\_TOOLS}}  **Action Input:**  Provide arguments**STOP AND WAIT:**  You must stop here. Do NOT invent an observation. Wait for the system to provide the result of the Action.**Observation:**  To be provided by System ... (Repeat until Goal achieved)"

#### 5\. System Constraints and Troubleshooting

##### 5.1 Context Length Management

* **Prioritization:**  "If the context window is near the token limit, prioritize information in this order: 1\. System Prompt, 2\. Current Goal, 3\. The 3 most recent observations, 4\. Summarized history. Discard all intermediate reasoning steps older than 5 turns."

##### 5.2 Reliability and Formatting Enforcement

* **JSON Strictness:**  "You are an API-centric module. You MUST output only valid JSON. Do not include introductory text (e.g., 'Here is the JSON...') or conversational filler. If you cannot fulfill the request, return an empty JSON object {}. Failure to output valid JSON will result in a system error."  
* **Tool Grounding:**  "Only call tools explicitly defined in the provided toolbelt. Do not guess API endpoints or parameters."

