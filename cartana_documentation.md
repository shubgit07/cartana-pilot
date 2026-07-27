# Cartana

**Cartana** is an AI-powered requirements and execution copilot. It helps students, freelancers,
and small software teams turn messy project documents into a clear execution plan. Instead of only
letting users "chat with PDFs," Cartana focuses on a more useful problem: understanding what a
project actually requires, converting those requirements into actionable work, and detecting what
is still missing before deadlines are missed.

> **Companion document:** `cartana_agent_3_phase_plan.md` is the agent build direction — stack,
> data model, phasing, and the human-in-the-loop decision protocol. This document describes the
> **product**; that one describes **how to build it**. Keep the two consistent: any approved change
> to scope should be reflected in both.

---

# 1. Problem Statement

In most real projects, the source of truth is scattered across multiple places:

- a project brief or PRD PDF
- assignment instructions
- client requirement documents
- meeting notes
- screenshots or comments from discussions
- follow-up text notes

The actual execution, however, happens somewhere else:
- a task board
- a to-do list
- a spreadsheet
- a team chat
- a notebook of manually created tasks

This creates a common real-world problem:

- important requirements in the document never become tasks
- deadlines mentioned in the brief are forgotten or not linked to actual work
- vague requirements are left unclarified until late in the project
- teams think they are "done," but parts of the original requirement are still uncovered
- during review or submission, people realize that key features were never implemented

Cartana solves this gap between **what the project requires** and **what the team is actually
planning or building**.

---

# 2. Product Vision

Cartana should act like a **project specification copilot**.

A user uploads project-related material such as a requirement document, assignment brief, or
meeting notes. Cartana reads that material, understands the requirements, allows the user to ask
questions over it, extracts actionable tasks, and continuously checks whether the actual task list
truly covers the requirements.

The product is not just a chatbot over documents. Its core purpose is to answer one important
question:

> **"Have we actually covered everything the project/brief/spec asked us to do?"**

---

# 3. Target Users

Cartana is intended for users who work from written project requirements but often lose execution
clarity.

## 3.1 Student project teams
Students receive project briefs, assignment instructions, deadlines, and evaluation requirements.
They often create tasks manually and miss some part of the brief.

## 3.2 Freelancers and small agencies
A freelancer receives a client brief, notes from a meeting, and additional requests over time.
Important details get lost between the original document and actual work planning.

## 3.3 Small software/product teams
Teams working from PRDs, sprint notes, or feature briefs need a quick way to check if all
requirements have corresponding work items and whether anything critical is missing.

---

# 4. Core Product Idea

Cartana takes project inputs and turns them into four useful outputs:

1. **A searchable project knowledge base**
   - Users can ask questions about the uploaded project documents.

2. **A structured requirement list**
   - The system identifies and organizes the actual requirements hidden inside raw documents.

3. **An actionable task list**
   - The system converts requirements into suggested work items, which the user can accept,
     edit, reject, or supplement with their own tasks.

4. **A coverage and risk audit**
   - The system checks whether requirements are properly covered by tasks and highlights missing
     or risky areas.

---

# 5. Real-World Workflow

## Step 1: User uploads project material
A user creates a project inside Cartana and uploads one or more inputs such as:
- a PRD
- a project brief
- an assignment PDF
- meeting notes
- requirement notes
- screenshots or supporting references *(image understanding is a future expansion; the first
  version handles PDF and plain text)*

## Step 2: Cartana reads and understands the material
The system processes the uploaded content and builds an internal understanding of the project.

It identifies:
- key features
- deliverables
- deadlines
- constraints
- acceptance criteria
- mentioned modules or components
- action-oriented statements

## Step 3: Cartana creates a project knowledge layer
Once the document is processed, the user can ask questions such as:
- What are the main requirements of this project?
- What are the deadlines mentioned in the brief?
- What does the client expect for the dashboard module?
- What are the acceptance criteria for authentication?

This makes the project documents searchable and usable without manually reading everything again
and again.

## Step 4: Cartana extracts requirements
The system converts raw project text into a structured list of requirements.

Example:
- User authentication with email OTP
- Admin dashboard
- CSV export
- Analytics page
- Role-based access
- Report download

## Step 5: Cartana suggests or extracts tasks
From the requirements, the system creates actionable work items. The user can accept, edit, or
reject each suggestion, and can also add their own tasks manually.

Example:
- Build OTP login flow
- Create admin dashboard page
- Implement export API
- Add analytics charts
- Build report download feature

## Step 6: Cartana checks requirement coverage
This is the main value of the product.

The system compares:
- the requirement list
- the effective task list (AI-suggested tasks the user has kept, plus tasks the user created)

and determines:
- which requirements are fully covered
- which are partially covered
- which have no linked tasks
- which tasks do not clearly map back to any requirement

## Step 7: Cartana runs an audit
The product then produces a project health view:
- uncovered requirements
- vague or ambiguous requirements
- deadlines approaching with incomplete work coverage
- possible missing implementation items
- items mentioned in meeting notes but not represented in tasks

This helps the user catch execution gaps before submission or delivery.

---

# 6. Primary Problem Cartana Solves

Cartana solves **requirement-to-execution drift**.

Requirement-to-execution drift means:
- the original document says one thing
- the actual task board reflects only part of it
- important items are missed, misunderstood, or forgotten

Cartana reduces that drift by keeping the project brief, extracted requirements, and actual tasks
connected in one place.

---

# 7. Product Goals

Cartana should aim to do the following well:

## 7.1 Make project documents understandable
Users should not have to repeatedly read long PDFs or notes just to find one requirement.

## 7.2 Turn vague documentation into structured work
The system should extract tasks, deadlines, and requirement groupings in a way that helps
execution.

## 7.3 Detect what is missing
The product should clearly highlight missing task coverage rather than just showing a chat answer.

## 7.4 Improve planning confidence
A user should be able to open the project and quickly understand:
- what the project expects
- what work exists
- what is still missing
- what is at risk

---

# 8. Product Scope

## 8.1 In scope for the first version
The first version of Cartana should focus on a narrow, finishable workflow.

### Project setup
- create a project/workspace
- upload project-related material
- view processed documents and extracted information
- **single-user local MVP** — no login in the first version (one implicit user); the data model
  is multi-user-ready so real authentication can be added later without a rewrite

### Document understanding
- parse uploaded text-based project material (PDF + plain text)
- identify requirements, deadlines, deliverables, and key instructions

### Knowledge chat
- ask grounded questions over the uploaded material
- receive answers tied to the project source

### Requirement extraction
- produce a structured list of requirements from the source material, each traceable to its source

### Task extraction & management
- generate or suggest tasks from requirements and project notes
- let the user **accept, reject, edit, create, and relink** tasks — the task list is not read-only

### Coverage audit
- compare requirements with the effective task list
- show covered, partially covered, and missing items

### Risk summary
- generate a project audit summary highlighting likely execution gaps

## 8.2 Out of scope for the first version
To keep the project focused, the first version should avoid becoming a full project management
platform.

Out of scope for the MVP:
- full team chat system
- a large enterprise permission system
- advanced calendar and notification workflows
- heavy multi-agent orchestration
- arbitrary website scraping as a primary feature
- becoming a generic "chatbot for everything"
- replacing existing tools like Jira or Notion completely

---

# 9. Key Concepts in the Product

## 9.1 Source
Any uploaded project input, such as a PDF, note, or meeting summary.

## 9.2 Requirement
A meaningful project expectation extracted from the source.
Example: "The system should support role-based access for admins and employees."

## 9.3 Task
An actionable work item that helps implement one or more requirements. A task may be AI-suggested
or created by the user, and the user can edit, accept, reject, or relink it.

## 9.4 Coverage
The relationship between a requirement and one or more tasks that satisfy it. A coverage link may
be AI-suggested or user-confirmed; user-confirmed links are treated as ground truth.

## 9.5 Audit finding
A problem or risk detected by the system, such as:
- missing task coverage
- unclear requirement wording
- approaching deadline with incomplete requirement coverage

---

# 10. User Stories

## 10.1 Student team
As a student team member, I want to upload an assignment brief and automatically see the project
requirements and task suggestions, so that my team does not miss important evaluation points.

## 10.2 Freelancer
As a freelancer, I want to upload a client brief and meeting notes and see what deliverables are
expected, so that I do not forget a feature the client mentioned earlier.

## 10.3 Small dev team member
As a team member, I want to know whether every requirement in the PRD has a corresponding
implementation task, so that we can catch gaps before release.

## 10.4 Project lead
As a project lead, I want an audit summary of missing or partially covered requirements, so that I
can review project health quickly.

---

# 11. Main Product Modules

## 11.1 Project Workspace
A workspace for a single project where all project-related sources, requirements, tasks, and audit
findings live together.

## 11.2 Source Ingestion
Handles uploaded material and prepares it for understanding and question-answering (text
extraction, chunking, embeddings).

## 11.3 Project Knowledge Chat
Allows users to ask questions about the uploaded material and receive grounded answers tied to the
source.

## 11.4 Requirement Extractor
Converts source material into a structured requirement list, traceable back to the source.

## 11.5 Task Generator / Task Extractor
Produces task suggestions or extracted action items from project material, which the user can then
manage manually.

## 11.6 Coverage Mapper
Links requirements to tasks and identifies missing or partial coverage.

## 11.7 Audit Engine
Generates a project health report with missing items, ambiguities, and deadline risks.

> Note: Coverage Mapper and Audit Engine are delivered together in the final build phase, but they
> remain conceptually distinct — mapping produces the requirement↔task links; the audit reasons
> over those links to produce findings and a risk summary.

---

# 12. Suggested User Flow

## 12.1 Create project
User creates a new project and gives it a name.

## 12.2 Upload documents
User uploads one or more project-related files or notes.

## 12.3 Wait for processing
Cartana processes the uploaded material (in the background) and prepares:
- project knowledge
- requirement list
- task suggestions
- coverage mapping

## 12.4 Review project overview
User sees:
- number of requirements found
- number of tasks suggested
- missing coverage count
- upcoming deadlines
- recent audit findings

## 12.5 Ask questions
User uses the chat interface to ask questions about the project brief or requirements.

## 12.6 Review requirements
User opens the requirements view and sees all extracted requirements.

## 12.7 Review tasks
User sees generated tasks and can accept, edit, reject, create, or relink them.

## 12.8 Run or review audit
User views the coverage report and project risk summary.

---

# 13. Example Project Scenario

A student team uploads a final-year project brief. The brief says the project must include:
- authentication
- an admin dashboard
- analytics
- export functionality
- final report submission by a fixed date

Cartana processes the brief and extracts those requirements. It suggests tasks such as building the
login flow, dashboard UI, export feature, and analytics module. During the audit, it notices that
report submission is mentioned in the brief but there is no task related to preparing or generating
the report. It also notices that export functionality is mentioned, but only one partial task
exists for backend export and no UI task exists for download access.

The team can now catch these missing pieces early instead of discovering them just before
submission.

---

# 14. What Makes Cartana Different From a Basic RAG Chatbot

A basic document chatbot usually stops at:
- upload file
- ask question
- get answer

Cartana should go further by connecting understanding to execution.

It should not only answer:
- "What does the document say?"

It should also answer:
- "What work needs to be done because of what the document says?"
- "What requirements still have no task coverage?"
- "What is risky or incomplete right now?"

That is the central difference in product value.

---

# 15. Success Criteria for the MVP

The first version of Cartana can be considered successful if a user can:

1. Upload a project brief or PRD
2. Ask questions and get useful grounded answers
3. View extracted requirements
4. View generated or extracted tasks (and manage them)
5. See which requirements are covered, partially covered, or missing
6. Read a simple audit report showing likely project gaps

If these six things work reliably and cleanly, the MVP is strong enough.

---

# 16. Non-Goals

Cartana is not trying to become:
- a complete replacement for all project management tools
- a generic chatbot for any topic
- a giant enterprise workflow suite
- a broad no-code automation platform

Its first goal is much narrower:

> **Help users move from project documents to a trustworthy execution plan, while detecting what
> is still missing.**

---

# 17. Future Expansion Directions

These are possible later additions, but they should not define the first version.

## 17.1 Meeting note ingestion
Allow users to upload meeting summaries and include them in requirement and task extraction.

## 17.2 Screenshot and image understanding
Support screenshots of UI designs, comments, or requirement notes and convert them into project
context.

## 17.3 Team collaboration
Allow multiple project members to review tasks, coverage, and audit findings together (builds on
the multi-user-ready data model).

## 17.4 Deadline tracking and reminders
Provide project alerts for uncovered requirements close to submission dates.

## 17.5 Requirement change tracking
Detect when newly uploaded documents change the scope of the project and update the audit
accordingly. (Basic idempotent re-extraction exists earlier; full scope-diffing is a future step.)

---

# 18. Final Product Summary

Cartana is an AI-powered project specification copilot that helps users understand project
documents, extract requirements, generate tasks, and detect execution gaps before they become
delivery problems.

Its core value is not simply answering questions from a PDF. Its core value is making sure that
what the project **asks for** is actually reflected in what the team is **planning and building**.

In simple terms:

- upload the brief
- understand the requirements
- turn them into work
- check what is still missing
- reduce last-minute surprises

That is the purpose of Cartana.
