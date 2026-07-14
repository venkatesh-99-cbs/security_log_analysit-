# Security Log Analysis Assistant — Test & Usage Guide 🛡️

This guide outlines how to configure, seed, run, and exhaustively test every component of the Security Log Analysis Assistant project to achieve perfect usage.

---

## 🛠️ Step 1: Initial Infrastructure Setup

Before running the application, make sure local prerequisites are met.

### 1. Verification of Ollama Setup

Start Ollama on your machine and download the required model:

```bash
# Verify Ollama is running (should return version)
ollama --version

# Pull the model used by the settings configuration
ollama pull qwen3.5:9b
```

### 2. Boot up the Docker Container Stack

From the project root directory, launch the orchestration setup:

```bash
docker-compose up --build
```

Verify the following ports are listening:

- `http://localhost:5173` — React Vite Frontend
- `http://localhost:8000` — Flask Backend API
- `http://localhost:8001` — ChromaDB Service
- `http://localhost:11434` — Ollama Host Interface

---

## 🔌 Step 2: System Health Diagnostics & Seeding

1. Open the UI at `http://localhost:5173`.
2. Check the **Infrastructure Status** widget in the bottom left of the sidebar:
   - **Backend Server** should show `ONLINE`.
   - **AI Inference** should show `CONNECTED` (means the backend successfully negotiated with the local Ollama instance).
3. Navigate to **System Settings** in the sidebar.
4. Click the **Ingest Security Knowledge** button.
   - This sends standard playbook manuals, Windows Event Encyclopedias, and MITRE taxonomies to ChromaDB.
   - Confirm you see: `Ingested 6 security playbooks. Vector DB now contains 6 records.`

---

## 📂 Step 3: Testing Log Ingestion with Sample Inputs

To test the multi-format parsers (Windows XML, Linux Syslog, CSV, and JSON), you can upload sample files. Create dummy files or input logs with the formats below to test.

### Scenario A: Windows Event Log XML (Brute Force Simulation)

Create a file named `win_brute_force.xml` containing the following failed login XML entries:

```xml
<Events>
  <Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
    <System>
      <EventID>4625</EventID>
      <TimeCreated SystemTime="2026-07-03T10:00:00.000000Z"/>
      <Computer>DC-01.local</Computer>
      <Channel>Security</Channel>
    </System>
    <EventData>
      <Data Name="TargetUserName">Administrator</Data>
      <Data Name="IpAddress">192.168.1.150</Data>
      <Data Name="FailureReason">0xC000006A</Data>
    </EventData>
  </Event>
  <Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
    <System>
      <EventID>4625</EventID>
      <TimeCreated SystemTime="2026-07-03T10:01:00.000000Z"/>
      <Computer>DC-01.local</Computer>
      <Channel>Security</Channel>
    </System>
    <EventData>
      <Data Name="TargetUserName">Administrator</Data>
      <Data Name="IpAddress">192.168.1.150</Data>
      <Data Name="FailureReason">0xC000006A</Data>
    </EventData>
  </Event>
  <Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
    <System>
      <EventID>4625</EventID>
      <TimeCreated SystemTime="2026-07-03T10:02:00.000000Z"/>
      <Computer>DC-01.local</Computer>
      <Channel>Security</Channel>
    </System>
    <EventData>
      <Data Name="TargetUserName">Administrator</Data>
      <Data Name="IpAddress">192.168.1.150</Data>
      <Data Name="FailureReason">0xC000006A</Data>
    </EventData>
  </Event>
  <Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
    <System>
      <EventID>4625</EventID>
      <TimeCreated SystemTime="2026-07-03T10:03:00.000000Z"/>
      <Computer>DC-01.local</Computer>
      <Channel>Security</Channel>
    </System>
    <EventData>
      <Data Name="TargetUserName">Administrator</Data>
      <Data Name="IpAddress">192.168.1.150</Data>
      <Data Name="FailureReason">0xC000006A</Data>
    </EventData>
  </Event>
  <Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
    <System>
      <EventID>4625</EventID>
      <TimeCreated SystemTime="2026-07-03T10:04:00.000000Z"/>
      <Computer>DC-01.local</Computer>
      <Channel>Security</Channel>
    </System>
    <EventData>
      <Data Name="TargetUserName">Administrator</Data>
      <Data Name="IpAddress">192.168.1.150</Data>
      <Data Name="FailureReason">0xC000006A</Data>
    </EventData>
  </Event>
</Events>
```

### Scenario B: Linux Syslog (Privilege Escalation Simulation)

Create a file named `syslog_priv_esc.log` containing:

```text
<34>1 2026-07-03T10:15:00.000Z ubuntu-server sudo 1284 - - pam_unix(sudo:auth): authentication failure; logname=uid=1001 euid=0 ruser=developer rhost= user=developer
<34>1 2026-07-03T10:15:05.000Z ubuntu-server sudo 1284 - - developer : TTY=pts/0 ; PWD=/home/developer ; USER=root ; COMMAND=/bin/bash
<34>1 2026-07-03T10:15:10.000Z ubuntu-server su 1302 - - pam_unix(su:session): session opened for user root by developer(uid=1001)
```

### Simulation Testing Steps:

1. Go to **Log Ingestion** in the sidebar.
2. Drag and drop `win_brute_force.xml` into the drop zone.
3. Observe the state cycle: **Uploading** $\rightarrow$ **Success**.
4. In the **Ingested Datasets** box, verify the file name appears with a green checkmark indicating successful parsing.
5. In the **Parsed Audit Trail** table, check that all 5 failed logons are translated, showing timestamp, severity (`MEDIUM`), source (`DC-01.local`), category (`authentication`), and the parsed message.
6. Now upload `syslog_priv_esc.log`. Check the parsed logs display showing `sudo` and `su` privilege escalation events.

---

## 🔎 Step 4: Investigating Correlated Incidents

Once logs are parsed, detection engines run in the background, grouping alerts into unified incidents:

1. Navigate to the **Incident Queue** page.
2. Verify that two incidents have been automatically created:
   - **Brute Force Attack — 192.168.1.150** (Severity: `HIGH`, Threat Score calculated using rules).
   - **Privilege Escalation — ubuntu-server** (Severity: `HIGH` or `CRITICAL`).
3. Click the **Investigate** link on the Brute Force incident to open the detail view.
4. Review the details:
   - Mapped tactics under the **MITRE ATT&CK Heatmap Matrix** (e.g., `T1110` highlighted under the _Credential Access_ column).
   - Core incident logs linked at the bottom.

---

## 🤖 Step 5: Utilizing the AI Operations Playbook

1. On the **Incident Detail** page, look at the **AI SOC Playbook Analyst** card on the right.
2. Click **Generate AI Analysis**.
3. The server queries Ollama locally:
   - It sends the incident title, severity, threat score, source host, and MITRE tactics.
   - Wait for the model to generate the root-cause analysis report.
   - The result is rendered in clean markdown formatting showing: _Executive Summary_, _Attack Analysis_, _Immediate Containment Steps_, and _Long-Term Hardening Recommendations_.
4. Navigate to the **AI Copilot** page in the sidebar:
   - Ask a question like: `How do I prevent brute force attacks on DC-01.local?`
   - Make sure **Ground prompt with RAG playbook context** is checked.
   - The AI Copilot will pull standard mitigation guidelines from ChromaDB and return a grounded response.

---

## 📄 Step 6: Compiling Executive Reports

1. Navigate to the **Reports Archive** page.
2. Under **Compile New Report**, specify a title (e.g., `SOC Incident Report Q3`) and select a severity filter if needed.
3. Click **Compile Report**.
4. Once completed, the report will be added to the **Archive Directory** table.
5. Click **Download HTML** to export the print-ready document. Open the downloaded HTML file in your browser to inspect the layout, severity metrics, and mapped MITRE tactics table.
