# Step 4: Azure Observability: Self-Study Plan

This module covers moving from "tailing logs via SSH" to centralized monitoring, alerting, and dashboarding using Azure Monitor and Log Analytics.

---

## Module 1: The Concept of Centralized Logging
**Topics to Research:**
- Why logging directly to local text files on a VM is an anti-pattern in the cloud (ephemeral infrastructure).
- What is an Azure Log Analytics Workspace (LAW)?
- The difference between Logs (text/events) and Metrics (numbers/CPU usage).

**Check for Understanding:**
1. If your VM crashes and is deleted by a scale set, how do you read the logs of why it crashed if you didn't have centralized logging?
2. Why do we separate the Workspace (storage) from the Compute (VM)?

---

## Module 2: Ingesting Docker Logs
**Topics to Research:**
- The Docker logging driver (`--log-driver`).
- Pushing logs to Azure using the Azure Monitor Agent (AMA) vs fluentd/syslog.
- Data Collection Rules (DCR) in Azure.

**Check for Understanding:**
1. How do you configure a `docker-compose` service to route its stdout/stderr to an external system instead of the local JSON file?
2. What role does the Azure Monitor Agent play when installed on a Linux VM?

---

## Module 3: Kusto Query Language (KQL)
**Topics to Research:**
- Basic syntax of KQL (similar to SQL but pipeline-based `|`).
- Searching tables (e.g., `ContainerLog`, `Syslog`, `Heartbeat`).
- Filtering (`where`), formatting (`project`), and aggregating (`summarize`).

**Check for Understanding:**
1. Write a conceptual KQL query to find all logs containing the word "ERROR" from the last 24 hours.
2. Why is KQL necessary for Log Analytics?

---

## Module 4: Application Insights (Optional but Recommended)
**Topics to Research:**
- APM (Application Performance Monitoring).
- How Application Insights differs from plain Log Analytics (distributed tracing, dependency mapping).
- Auto-instrumentation vs SDK integration in Python (FastAPI).

**Check for Understanding:**
1. If your Gateway calls the Math Service, and the Math Service is slow, how does Application Insights trace the entire request path?
