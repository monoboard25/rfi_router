# Monoboard AI Kill Switch Runbook
**Version:** 1.0
**Target Environment:** Phase 0 (Power Automate + Azure Functions + Azure OpenAI)
**Last Tested:** N/A (Initial Draft)

---

## 1. Overview and Authority
This runbook provides step-by-step instructions for executing the Emergency Kill Switch per the [Monoboard Agent Constitution (v1.2)](./monoboard_agent_constitution.md). 

**Authorized Invokers:**
*   Abdiel B. Escoto (Principal Owner)
*   Luis W. Delgado (Principal Owner)
*   Safety Officer (Safety Monitor agent only)
*   Engineering On-Call (Must notify Principal Owner within 15 mins)

**Target SLA:** 60 seconds from decision to full platform shutdown.

---

## 2. Primary Mechanism: The "Big Red Button" 
The primary kill switch is an authenticated Azure Function Webhook that can be triggered directly from a mobile device or browser.

### Action Steps:
1. **Navigate to the Kill Switch Portal:** 
   `https://monoboard-gov.azurewebsites.net/api/emergency-kill` *(Bookmark this link)*
2. **Authenticate:** Log in with your M365 Admin/Owner credentials.
3. **Select Scope:**
   *   `Level 1`: Single Agent (e.g., "RFI Router")
   *   `Level 2`: Agent Class 
   *   `Level 3`: Full System Shutdown
4. **Confirm:** Type `KILL` in the confirmation box and submit.

### What the automation does:
*   **Disables Triggers:** Issues an API call to Power Automate Management to turn off the target Flow(s).
*   **Revokes Identity:** Calls Entra ID (Azure AD) to revoke all active refresh tokens for the `monoboard-svc` service account, killing any in-flight operations.
*   **Alerts:** Posts an immediate critical alert to `Teams → Company HQ → Agent Governance`.

---

## 3. Backup Mechanism: Entra ID Manual Revocation
If the primary webhook fails, 503s, or is unreachable, proceed immediately to the manual identity kill.

### Action Steps:
1. Open the [Microsoft Entra Admin Center](https://entra.microsoft.com/#view/Microsoft_AAD_IAM/UsersManagementMenuBlade/~/AllUsers).
2. Search for the agent service account: `monoboard-svc@yourdomain.com`
3. Click the user profile.
4. Click **Revoke Sessions** (this instantly invalidates all active access tokens).
5. Click **Block Sign-in** (this prevents the agent from generating new tokens).
6. Manually post an alert to `Teams → Company HQ → Agent Governance`.

---

## 4. Final Escalation: Tenant Admin
If Entra ID access is compromised or the service account cannot be blocked, the ultimate fallback is locking down the SharePoint target sites.

### Action Steps:
1. Open the [SharePoint Admin Center](https://admin.microsoft.com/sharepoint).
2. Navigate to **Active Sites**.
3. Select the affected Project Sites or the Intranet Site.
4. Change the **Site Status** to `Read-Only`.
*Note: This will disrupt human users as well, but guarantees the agent cannot cause further destructive writes.*

---

## 5. Post-Kill Protocol & Recovery

Once the kill switch is pulled, the system enters the Post-Kill Protocol. **Agents cannot be turned back on until this is completed.**

1. **Incident Declaration:** A ticket must be created within 15 minutes of invocation.
2. **Investigation:** Engineering reviews the Observability Store logs located in Azure Table Storage (`agentruns` table).
3. **Fix & Sign-off:** 
   *   A root-cause fix must be implemented.
   *   Level 1 & 2 Kills require sign-off by **Engineering + 1 Principal Owner**.
   *   Level 3 Kills require sign-off by **Engineering + BOTH Principal Owners**.
4. **Re-enablement:**
   *   Unblock sign-in for `monoboard-svc` in Entra ID.
   *   Manually turn the Power Automate flows back to "On".

---

## 6. Quarterly Drill Log
*Drills must verify trigger disablement, token revocation, and <60s execution time on a non-critical agent.*

| Date | Scope Tested | Invoker | Time to Kill | Pass/Fail | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| [Date] | Level 1 (Daily Report) | [Name] | [Seconds] | [Pass/Fail] | Initial baseline drill |
