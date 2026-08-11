## Raneem Submission — Report Generation Agent

For the Day 3 submission, I extended the Day 2 multi-agent architecture into a
reusable Report Generation Agent.

The original Day 2 workflow consists of multiple agents working together:

    User Task
        ↓
    Supervisor
        ↓
    Researcher
        ↓
    Analyst
        ↓
    Writer
        ↓
    Critic
        ↓
    Final Report

For Day 3, the workflow was extended so that the user can provide a report
topic dynamically instead of using a hardcoded task.

The final approved report is automatically saved as a Markdown artifact:

    day3/
    ├── src/
    │   └── report_agent.py
    └── output/
        └── report.md

### How it works

1. The user enters a report topic or question.
2. The Supervisor determines which agent should act next.
3. The Researcher gathers relevant information.
4. The Analyst processes the research and extracts useful insights.
5. The Writer generates the report.
6. The Critic reviews the generated report.
7. If the report requires revision, the workflow can return to the appropriate
   agent.
8. Once the Critic approves the report, the final draft is saved to
   `output/report.md`.

### Example

Input:

    Assess the challenges and recommendations for implementing federated
    data governance in a healthcare organization.

Output:

    output/report.md

The generated artifact contains the report topic and the final approved report.

### Why this demonstrates the Day 3 concept

This submission demonstrates how an agent workflow can be turned into a
reusable software component with a clear input/output boundary.

The important distinction is:

    Day 2:
    Multi-agent workflow → final response

    Day 3:
    Multi-agent workflow → generated artifact

The report-generation agent is designed as a reusable agent component that can be exposed through the networked interfaces 
developed throughout Day 3.