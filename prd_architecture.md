
AL TASNIM ENTERPRISES LLC

AI-Powered Conversational Data Intelligence Platform


Technical Architecture and Implementation Proposal



# 1.  Executive Summary


Al Tasnim Enterprises LLC currently produces four weekly reports that drive all project management discussions: the Well Monitoring Report for Nimr, the Well Monitoring Report for Marmul, the Job Progress Report for Nimr, and the PH Productivity Report. These reports collectively span well-level construction progress, plan-versus-actual financial performance, crew productivity scores, and rig scheduling data.


At present, these reports are consumed as static documents. Team members cannot ask follow-up questions, filter by a specific rig or well category, or cross-reference productivity against schedule performance without manual effort from an analyst. Every insight requires going back to the data source.


This document describes the architecture and implementation plan for a conversational data intelligence platform that replaces this workflow. Team members type questions in plain English during weekly meetings and receive live, accurate answers drawn directly from the existing Microsoft SQL Server database. No data leaves the client network at any point. All processing happens on-premises.


## 1.1  The Problem Being Solved


## 1.2  Headline Outcomes

- Any question answerable from the four weekly reports can be answered in under ten seconds.

- The system learns from every meeting , it becomes more accurate each week.

- Zero data leaves the client network at any point in the process.

- No changes are required to the existing SQL Server database or its schema.

- The entire platform is delivered and operational within one week.



# 2.  Data Landscape


The existing database (AppMasterDB on the client Microsoft SQL Server) contains all data required to power this platform. The following tables are the primary sources and their approximate sizes as of the date of this document.



All tables are read via a read-only connection. The platform does not write to, modify, or delete any data in the SQL Server.


## 2.1  The Four Weekly Reports

The platform is specifically trained to understand and answer questions from the four reports that the team reviews in every weekly meeting.




# 3.  Technical Architecture


The platform consists of five layers that work together. Every layer runs within the client network. No external service is called at runtime except the language model, which is either deployed locally on-premises or accessed through the client's existing enterprise cloud agreement.


## 3.1  Architecture Overview



## 3.2  Data Flow — Step by Step

The following describes what happens from the moment a team member types a question to the moment the answer appears on screen.





## 3.3  Schema Intelligence Layer

This layer is the most critical component for accuracy. It ensures the language model never guesses at column names or table structures. The knowledge base is pre-populated with three categories of information before the system goes live.



The knowledge base is stored as a local binary file on the server. It contains no actual well data — only structural descriptions and example patterns. Size is approximately 2 megabytes. It is rebuilt in under 30 seconds whenever the database schema changes.


## 3.4  Query Optimisation Layer

Standard text-to-SQL systems use a fixed prompt written by a developer. This works for simple questions but degrades for complex multi-table queries specific to the client's data.


The query optimisation layer uses a technique where the system automatically tests different prompt formulations against known question-answer pairs and selects the one that produces the highest rate of correct SQL. This process runs once during setup using the team's own historical questions and is repeated monthly as more examples accumulate.


The practical result is that the system learns the exact language that Al Tasnim's team uses the terms like Purpose Value, ODC South, PH score, Nimr Flowline  and incorporates them correctly into SQL without manual programming.


## 3.5  Hallucination Control

The primary risk in any natural language to database system is the language model generating plausible-sounding but incorrect results. The architecture addresses this at three independent levels.



# 4.  Security Architecture


Security is the primary design constraint of this platform. The architecture was designed from the ground up assuming zero tolerance for data leaving the client network.



## 4.1  Data Boundary


## 4.2  Language Model Deployment Options

The language model is the only component that could involve external communication. Two options are available and the client chooses based on their security policy.




## 4.3  Database Access Controls

- The platform connects to AppMasterDB using a dedicated service account created specifically for this application.

- That service account is granted SELECT-only permissions on the required tables. No other permissions are assigned.

- The connection string and credentials are stored in an encrypted configuration file on the server, not in the application code.

- All queries are parameterised. SQL injection is structurally prevented.

- A query allow-list can be optionally configured to restrict the application to pre-approved table and column combinations.



# 5.  Platform Capabilities


The following questions represent a representative sample of what the platform can answer from the existing database. All answers are generated in real time with no manual intervention.


## 5.1  Well Progress Questions


## 5.2  Plan vs Actual Performance Questions


## 5.3  Crew Productivity Questions


## 5.4  Chart Types Available

- Bar chart - comparisons between wells, rigs, or categories.

- Line chart - progress trends over time for individual wells or groups.

- Horizontal bar chart - ranked lists such as rig performance or supervisor productivity.

- Scatter chart - relationship between two variables such as progress versus days on site.

- Data table - downloadable grid for offline analysis.

- All charts include a download button and the underlying SQL query for transparency.

# 6.  One-Week Implementation Plan


The platform is designed for rapid deployment. The following plan delivers a fully operational system within one calendar week from access confirmation.



## 6.1  Client Requirements for Implementation

- Access to AppMasterDB on the existing SQL Server with IP address, port, and credentials for a service account (to be created by client DBA).

- A server or virtual machine within the client network for hosting the platform. Minimum specification: 16 GB RAM, 4 CPU cores, 50 GB disk, Windows Server or Ubuntu Linux.

- If Option B (enterprise cloud) is selected: confirmation of existing enterprise cloud agreement and permission to create a language model resource within the client's tenant.

# 7.  Future Capability Roadmap


The platform delivered in Week 1 is the foundation. The following capabilities can be added in subsequent phases without rebuilding the core architecture.




# 8.  Glossary of Technical Terms


The following definitions are provided for non-technical stakeholders reviewing this document.




End of Document

Al Tasnim Enterprises LLC  |  AI Conversational Data Intelligence Platform  |  Version 1.0  |  March 2026  |  Confidential


| Prepared for | Al Tasnim Enterprises LLC |
| --- | --- |
| Prepared by | Strategy and Digital Solutions Team |
| Document version | 1.0 — For Client Presentation |
| Date | March 2026 |
| Classification | Confidential |


| Current state | Static weekly reports reviewed once. No ability to interrogate data in real time. |
| --- | --- |
| Current limitation | Any question not anticipated by the report designer requires a new manual analysis. |
| Meeting impact | Decisions are deferred because data is not available in the room. |
| Revenue risk | Plan-versus-actual gaps identified a week late instead of in the same meeting. |
| Proposed change | Any team member types a question in plain English and receives an accurate chart or table within seconds. |


| Table | Business meaning | Approximate rows |
| --- | --- | --- |
| WellMonitoringReport | Weekly progress snapshot per well - 128 columns covering all construction stages, dates, rig assignments, and progress percentages for Nimr and Marmul clusters. | - |
| WellMonitoringReport_Latest | Most recent week only, used for faster queries when historical trend is not required. | Current week |
| Job_Progress_Report_GB | Plan versus actual progress percentage and revenue figures by well, by week, for each month. | Derived view |
| Job_Progress_PlanSnapshot | Weekly plan fractions per well  W1 through W5 plus cumulative figures. | - |
| ActivityTaskPlan | Every task planned and executed against each well — progress, manhours, crew assignments, quantities. | - |
| task_daily | Daily execution records - actual start, end, crew, quantity, progress per task. | - |
| Revenue | Planned and actual revenue (Purpose Value in OMR) per activity code per well. | - |
| PH_PRODUCTIVITY_WEEKLY_REPORT | Weekly productivity index scores per crew supervisor (PH) across all categories. | Populated weekly |
| SAP_DRILLING_SEQUENCE | Rig assignments, activity sequences, and move days from SAP. | - |
| Employee / company_employees | All Al Tasnim staff with supervisor hierarchy and location codes. | - |
| crews | Crew compositions including supervisor, employees, and equipment. | - |


| Report | Key questions it answers | Data source in SQL Server |
| --- | --- | --- |
| WMR Nimr | Which Nimr wells are below 50% progress? Which are behind their expected rig-off date? What is the location preparation status per rig? | WellMonitoringReport WHERE Cluster = Nimr |
| WMR Marmul | Same questions for Marmul cluster. Comparison of Nimr vs Marmul portfolio progress. | WellMonitoringReport WHERE Cluster = Marmul |
| Job Progress Nimr | Which wells are below the weekly plan target? What is the cumulative revenue gap vs plan for March? Which well categories are consistently underperforming? | Job_Progress_Report_GB + Revenue |
| PH Productivity | Which crew supervisors scored below 80% this week? Who improved vs last week? Which discipline has the lowest average score this month? | PH_PRODUCTIVITY_WEEKLY_REPORT + Employee |


| Layer | Function | Location |
| --- | --- | --- |
| Layer 1: User Interface | Web-based chat interface. Team member types a question and receives an answer with a chart or table. | Runs on internal server, accessed via browser on local network IP |
| Layer 2: Schema Intelligence | Converts question into the relevant database context using vector similarity search. Retrieves the correct table and column definitions without exposing all 60+ tables to the language model. | Python process on same internal server no external calls |
| Layer 3: Query Optimisation | Automatically learns and improves the prompt instructions from historical question-answer pairs. Reduces errors by training on the team's own question patterns. | Python process  entirely local |
| Layer 4: Language Model | Receives the question and relevant schema context and writes the SQL query. Two deployment options available depending on client preference. | Option A: local model on same server. Option B: client-owned enterprise cloud. |
| Layer 5: Database | Executes the SQL query read-only against AppMasterDB. Returns data to the interface as a chart or table. | Existing client SQL Server  unchanged |


| Step | What happens | Time taken |
| --- | --- | --- |
| 1. Question entered | Team member types question in the chat interface. Example: which Nimr wells are more than 10% below their weekly plan target? | Instant |
| 2. Vector search | The question is converted to a numerical representation and compared against stored representations of all database column descriptions. The five most relevant schema chunks are retrieved. | Under 50 milliseconds |
| 3. Keyword search | A second parallel search matches exact technical terms such as column names and well identifiers. Results are merged with step 2. | Under 20 milliseconds |
| 4. Context assembly | The question, the five retrieved schema chunks, and any relevant examples from past questions are assembled into a structured instruction for the language model. | Under 10 milliseconds |
| 5. SQL generation | The language model reads the assembled context and writes a SQL query tailored to AppMasterDB. | Two to eight seconds |
| 6. Validation | The generated SQL is checked for safety (read-only, no destructive operations). If the SQL references a column that does not exist, an automatic correction request is sent to the language model. | Under 100 milliseconds |
| 7. Execution | The validated SQL is executed against AppMasterDB via a read-only database connection. | Varies by query complexity: typically under two seconds |
| 8. Answer display | The result is rendered as a bar chart, line chart, or table depending on the data type. The SQL that generated the answer is shown alongside for transparency. | Instant |
| 9. Learning | The question-answer pair is stored in the local knowledge base. Future similar questions benefit from this example. | Background - no delay to user |


| Category | Content | Example |
| --- | --- | --- |
| Table definitions | The complete column structure of every relevant table in AppMasterDB, including data types and nullable constraints. | WellMonitoringReport: well_name_after_spud (text), over_all_progress_percentages (decimal 0-1), rig_no (text), Week_Number (date)... |
| Business context | Plain English explanations of what each column means in Al Tasnim's operational context. Written once during setup by the implementation team. | over_all_progress_percentages is a decimal between 0 and 1 representing total completion, where 1.0 means the well is fully commissioned. Multiply by 100 to express as a percentage. |
| Question patterns | Example questions and their correct SQL answers, derived from the four weekly reports and common meeting discussion topics. | Which wells are below their weekly plan? -> SELECT well_name, cum_progress_for_this_week, weekly_plan FROM WellMonitoringReport WHERE cum_progress_for_this_week < weekly_plan |


| Risk | Control mechanism | Residual risk after control |
| --- | --- | --- |
| Model invents a column name that does not exist | Schema intelligence layer provides exact column names before SQL is generated. Model cannot guess — it works from retrieved facts. | Near zero |
| Model misunderstands a business term | Business context layer explains every ambiguous term. Query optimisation layer learns from corrections over time. | Low: under 5% for complex queries |
| Query returns unexpected results (zero rows, extreme values) | A validation step checks result plausibility before displaying. System shows a warning flag if result appears anomalous. | Caught and flagged to user |
| Model generates a query that modifies data | All queries pass through a read-only enforcement filter. Any query containing INSERT, UPDATE, DELETE, or DROP is rejected before execution. | Zero: structural prevention |
| Model answers a question it does not have data for | Confidence assessment before display. If retrieved schema chunks are not sufficiently relevant to the question, the system responds: I could not find sufficient data to answer this question reliably. | Transparent to user |


| Data type | Does it leave the client network? | Detail |
| --- | --- | --- |
| Well progress data | Never | All SQL queries execute locally against AppMasterDB. Results are displayed on screen and never stored externally. |
| Employee and crew data | Never | Same as above. All data remains within AppMasterDB. |
| Revenue and financial data | Never | Same as above. |
| Database schema (column names, table names) | Schema descriptions only and no actual data values | Column names and descriptions are sent to the language model as context. These contain no operational data, only structural metadata equivalent to a data dictionary. |
| User questions | Only to language model : see Section 4.2 | The text of the question is sent to the language model to generate SQL. It does not contain any data values from the database. |
| SQL queries generated | Never | Generated queries are executed locally and never transmitted externally. |


| Option A — Fully local deployment | The language model runs entirely on a server within the client network. No internet connection is required or used at any point during operation. Questions, schema context, and SQL never leave the physical premises. This is the highest security option. Queries take eight to twenty seconds to complete. |
| --- | --- |
| Option B — Client-owned enterprise cloud | If you already have an active enterprise agreement with a major cloud provider (Microsoft Azure is most common given the existing SQL Server deployment), the language model can be accessed via that agreement. All data governance, data residency, and non-training commitments in that enterprise contract apply. No data passes through any third-party service. This option provides faster responses of two to four seconds. |
| Recommendation | For the initial one-week deployment, Option A is recommended to eliminate all external dependencies. If you have a existing Azure enterprise agreement, migration to Option B can be completed in under four hours with no changes to the rest of the system. |


| Question type | Example question | Data sources joined |
| --- | --- | --- |
| Portfolio overview | What is the average overall progress for Nimr wells this week compared to last week? | WellMonitoringReport |
| Risk identification | Which wells have made zero progress in the last two reporting periods? | WellMonitoringReport |
| Rig performance | Show me the average well progress grouped by rig number, ranked from highest to lowest. | WellMonitoringReport |
| Category breakdown | How does average progress differ between Nimr Flowline and Nimr Location categories? | WellMonitoringReport + ProjectIDs |
| Schedule risk | Which wells have an expected rig-off date within the next 14 days but are below 60% progress? | WellMonitoringReport |


| Question type | Example question | Data sources joined |
| --- | --- | --- |
| Weekly gap | Which wells are more than 15% below their Week 2 plan target for March? | Job_Progress_Report_GB |
| Revenue tracking | What is the total actual revenue versus planned revenue for Nimr Flowline wells this month? | Revenue + Job_Progress_Report_GB |
| Trend analysis | Show me the week-on-week plan achievement rate for the top 10 wells by purpose value. | Job_Progress_Report_GB + Revenue |
| Cumulative position | What is the cumulative actual progress versus cumulative plan for all Nimr wells as of today? | Job_Progress_PlanSnapshot + WellMonitoringReport |


| Question type | Example question | Data sources joined |
| --- | --- | --- |
| Supervisor ranking | Show me all project holders ranked by their average productivity score this month. | PH_PRODUCTIVITY_WEEKLY_REPORT |
| Below-threshold alert | Which project holders scored below 80% in Week 3 of this month? | PH_PRODUCTIVITY_WEEKLY_REPORT |
| Discipline comparison | Compare average productivity between civil and electrical crews for March. | PH_PRODUCTIVITY_WEEKLY_REPORT + crews |
| Cross-report insight | Show me wells where progress is below 40% AND the assigned project holder's productivity score is below 75%. | WellMonitoringReport + PH_PRODUCTIVITY_WEEKLY_REPORT + task_daily |


| Day | Activity | Deliverable |
| --- | --- | --- |
| Day 1 | Environment setup on client-designated server. Read-only database account creation. Initial schema extraction from AppMasterDB. Verification of connectivity. | Working database connection. Complete schema map of all 60+ tables. |
| Day 1 (continued) | Knowledge base construction. All relevant table definitions converted to vector representations. Business context documentation written for the four report data sources. | Knowledge base file ready. All column meanings documented. |
| Day 1(continued) | Language model deployment (Option A local or Option B cloud per client decision). Integration between all five layers. First end-to-end test queries. | System generates correct SQL for 20 test questions covering all four weekly reports. |
| Day 2 | Query optimisation training. Running automated improvement process on 30 sample questions derived from the four reports. Self-correction loop testing. | Optimised prompt configuration. Error rate below 5% on test question set. |
| Day 2 (continued) | Chart rendering for all supported chart types. Download functionality. SQL transparency display. | All chart types rendering correctly with live data. |
| Day 3 | User interface finalisation. Conversation history. Session management. Internal network deployment on client server. | Platform accessible on internal IP address from any browser on client network. |
| Day 3 (continued) | Security review. Read-only access verification. Query injection testing. Data boundary confirmation. | Security sign-off document. |
| Day 4-5 | User acceptance testing with client team. Live walkthrough of 15 questions from weekly meeting agenda. Corrections based on feedback. | Platform approved for use. Client team trained. |
| Week 2 onward | Weekly knowledge base update. New question-answer pairs added after each meeting. Monthly prompt re-optimisation. | System improves in accuracy with each weekly meeting. |


| Phase | Capability | Estimated effort |
| --- | --- | --- |
| Phase 2 | Predictive risk scoring. The four-week progress forecast model (already built and validated) is integrated into the chatbot. Users can ask: which wells are predicted to miss their target date? | Three to four days |
| Phase 2 | Automated weekly summary. Every Monday morning the system generates a written briefing covering the top five risks, the five highest-performing wells, and the plan-versus-actual gap for the previous week. No human involvement required. | Two days |
| Phase 3 | Causal analysis. The system can answer intervention questions: if we reassign Rig SWER149 from Well A to Well B, how does that change the predicted completion date for both? | One week |
| Phase 3 | Mobile access. A simplified version of the chat interface accessible from mobile devices within the client network, for use by supervisors in the field. | Three days |
| Phase 3 | Multi-language support. Arabic language input and output, allowing field supervisors to interact in their preferred language. | One week |
| Phase 3 | Automated alert system. The platform monitors progress data daily and sends an internal alert when a well drops below a configurable threshold or when a plan-versus-actual gap exceeds a set limit. | Three days |


| Term | Plain English definition |
| --- | --- |
| Vector similarity search | A method of finding relevant information by mathematical comparison of meaning rather than keyword matching. Used to retrieve the correct database schema context for each question. |
| Schema | The structural definition of a database: table names, column names, and data types. Contains no actual data values. |
| Language model | A software system that understands natural language and generates SQL queries  analogous to a translator from English to database language. |
| SQL | Structured Query Language. The standard language for retrieving data from relational databases such as Microsoft SQL Server. |
| Query optimisation | An automated process that improves the instructions given to the language model by testing different formulations against known correct answers. |
| Read-only access | A database permission that allows data retrieval but prevents any modification, addition, or deletion of records. |
| On-premises deployment | Software running entirely within the client's own infrastructure with no dependency on external internet services. |
| Knowledge base | A local file containing pre-processed representations of database schema descriptions and business context documentation. Updated periodically. |
