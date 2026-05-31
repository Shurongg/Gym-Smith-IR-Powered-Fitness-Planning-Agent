# GymSmith: A Two-Stage Retrieval-Augmented Fitness-Planning Agent

**Information Retrieval — Assignment 2**

**GitHub:** https://github.com/Shurongg/Gym-Smith-IR-Powered-Fitness-Planning-Agent
**Demo video:** https://youtu.be/9HiRsYtDEDE

---

## 1. Overview

GymSmith is a retrieval-augmented fitness-planning agent that turns natural-language fitness goals into personalised weekly workout plans. It combines information retrieval, tool calling, user memory, and validation to generate plans grounded in a local exercise knowledge base.

---

## 2. Technical Stack

**Frontend:** React, Vite, JavaScript/TypeScript, CSS, pixel-art interface
**Backend:** FastAPI, Python, REST/JSON API
**Agent and LLMs:** GPT-4o for planning and tool calling; GPT-4o-mini for safety checks
**Retrieval:** ChromaDB with SentenceTransformer `all-MiniLM-L6-v2` embeddings
**Storage:** SQLite for user identity, memory, plan history, and pinned plans
**Knowledge sources:** wger, Free Exercise DB, and hand-authored training-rule cards
**Validation:** chrF++ similarity filtering for exercise-name hallucination control
**Web fallback:** DuckDuckGo search for nutrition and niche exercise fallback

---

## 3. System and IR Pipeline

GymSmith uses one end-to-end pipeline: safety checking, plan reasoning, retrieval-based assembly, and validation.

The local knowledge base contains around 1,400 exercise entries from wger and Free Exercise DB. The sources are normalised into a shared equipment taxonomy so that retrieval can respect the user's selected equipment. The system also indexes around 40 training-rule cards covering split selection, training level, intensity, cardio, and equipment-aware planning. Both exercises and rules are embedded in ChromaDB.

The pipeline has four steps. First, the safety gate checks for medical-risk requests. Second, a GPT-4o reasoning agent receives the user request, selected equipment, training level, and memory, then outputs a structured JSON blueprint with fields such as `interpreted_goal`, `training_split`, `intensity`, `sets_reps_scheme`, and `daily_cardio`. Third, a tool-calling GPT-4o agent uses this blueprint to call retrieval tools such as `search_exercises`, `search_training_rules`, `get_user_memory`, `web_search_exercises`, and `web_search_nutrition`. The main retrieval tool searches ChromaDB by muscle and goal rather than by the raw user prompt. Fourth, the generated exercise names are checked against retrieved candidates using chrF++; unsupported names are removed.

---

## 4. Agent Design and Novelty

The main novelty of GymSmith is the explicit separation between reasoning, retrieval, and validation. Stage 1 interprets the user request and creates a retrieval-ready structure. Stage 2 uses that structure to retrieve exercises and rules through tools. The validation step then checks whether the generated plan is supported by retrieved evidence.

This design is more controlled than a direct prompt-to-plan chatbot. It reduces dependence on the LLM's parametric knowledge and makes the plan easier to inspect. The use of chrF++ is also a practical cross-domain idea: a character-level similarity metric is reused as a lightweight hallucination filter for exercise names.

The interface supports transparency. The Goal Card shows the Stage 1 interpretation, while the IR Process Trace panel shows the reasoning JSON, retrieved exercises, filtered results, rules used, and web fallback queries. The sidebar stores history, supports pinned plans, and allows the system to summarise activity preferences from previous sessions.

---

## 5. Reflection on AI-Assisted Development

This project was developed with assistance from Claude Code. It helped with implementation tasks such as backend route coding, React component generation, API integration, SQLite-related code, and debugging. It was especially useful for frontend development because I had limited prior experience with React and CSS.

However, the system design and technical direction were not delegated to the AI tool. I defined the project scope, the two-stage retrieval workflow, the knowledge-base structure, the local-retrieval versus web-fallback boundary, and the validation strategy. Claude Code helped translate these decisions into working code.

The main limitation was that the assistant sometimes proposed over-complex code. For example, early retrieval logic used too many nested filters, which removed useful exercises and made plans worse. Fixing this required manually reading the code, simplifying the pipeline, and testing the output. Overall, AI coding tools accelerated development, but the final system still depended on human decisions about the IR design, agent behaviour, and validation logic.

---

## 6. Conclusion

GymSmith demonstrates how an AI agent can be extended through information retrieval rather than only through prompting. It uses a local exercise database, indexed training rules, structured query planning, tool-calling retrieval, user memory, and post-generation validation. The result is a fitness-planning agent that retrieves relevant context, exposes its reasoning process, and checks its output against retrieved evidence.
