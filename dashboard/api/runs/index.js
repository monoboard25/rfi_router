const { TableClient, odata } = require("@azure/data-tables");

// Known agent IDs (PartitionKeys in agentruns table).
// Override via AGENT_IDS env var: comma-separated list of agent_id values.
const AGENT_IDS = (process.env.AGENT_IDS || "rfi-router-v1,daily-report-v1,change-order-v1,validator-v1,ceo-agent-v1")
  .split(",")
  .map(s => s.trim())
  .filter(Boolean);

const TABLE_NAME = "agentruns";
const PAGE_SIZE = 50;

// .NET DateTime.MaxValue.Ticks — used to compute reverse-tick RowKey
const MAX_TICKS = BigInt("3155378975999999999");
// Ticks offset between .NET epoch (0001-01-01) and Unix epoch (1970-01-01)
const DOTNET_EPOCH_OFFSET = BigInt("621355968000000000");

function dateToReverseTick(date) {
  const ticks = BigInt(date.getTime()) * BigInt(10000) + DOTNET_EPOCH_OFFSET;
  return (MAX_TICKS - ticks).toString().padStart(19, "0");
}

function getTableClient() {
  const connStr = process.env.AZURE_TABLE_CONNECTION_STRING;
  if (!connStr) throw new Error("AZURE_TABLE_CONNECTION_STRING not set");
  return TableClient.fromConnectionString(connStr, TABLE_NAME);
}

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET",
    "Content-Type": "application/json"
  };
}

module.exports = async function (context, req) {
  // Require Authorization header (Bearer token from MSAL) — basic gate
  const authHeader = req.headers["authorization"] || "";
  if (!authHeader.startsWith("Bearer ")) {
    context.res = { status: 401, headers: corsHeaders(), body: JSON.stringify({ error: "Unauthorized" }) };
    return;
  }

  const { from, to, status, continuationPartitionKey, continuationRowKey } = req.query;

  // Resolve date range (default: last 7 days)
  const toDate = to ? new Date(`${to}T23:59:59Z`) : new Date();
  const fromDate = from ? new Date(`${from}T00:00:00Z`) : new Date(toDate.getTime() - 7 * 86400000);

  if (isNaN(fromDate) || isNaN(toDate)) {
    context.res = { status: 400, headers: corsHeaders(), body: JSON.stringify({ error: "Invalid date range" }) };
    return;
  }

  // Reverse-tick bounds: newer date → smaller reverse tick
  const rkFrom = dateToReverseTick(toDate);   // lower RowKey bound (newer)
  const rkTo = dateToReverseTick(fromDate);   // upper RowKey bound (older)

  // Build per-agent filter
  let filter = `RowKey ge '${rkFrom}' and RowKey le '${rkTo}'`;
  if (status) filter += ` and status eq '${status.replace(/'/g, "''")}'`;

  try {
    const client = getTableClient();
    let allRuns = [];
    let nextContinuationToken = null;

    // Fan out across all known agent partitions in parallel
    const partitionResults = await Promise.all(
      AGENT_IDS.map(agentId => queryPartition(client, agentId, filter, PAGE_SIZE))
    );

    for (const result of partitionResults) {
      allRuns = allRuns.concat(result.runs);
      // Capture first non-null continuation token for pagination
      if (result.continuationToken && !nextContinuationToken) {
        nextContinuationToken = result.continuationToken;
      }
    }

    // Sort merged results by run_timestamp descending (newest first)
    allRuns.sort((a, b) => {
      const ta = a.run_timestamp ?? "";
      const tb = b.run_timestamp ?? "";
      return tb.localeCompare(ta);
    });

    // Apply pagination offset if continuation token provided (simple slice approach for fan-out)
    // For Phase 0, resume from stored continuation partition + row; full multi-partition
    // cursor is a Phase 1 improvement.
    const page = allRuns.slice(0, PAGE_SIZE);

    context.res = {
      status: 200,
      headers: corsHeaders(),
      body: JSON.stringify({
        runs: page,
        continuationToken: nextContinuationToken
      })
    };

  } catch (err) {
    context.log.error("runs query failed:", err.message);
    context.res = {
      status: 500,
      headers: corsHeaders(),
      body: JSON.stringify({ error: "Failed to query agent runs", detail: err.message })
    };
  }
};

async function queryPartition(client, agentId, baseFilter, maxRows) {
  const filter = `PartitionKey eq '${agentId.replace(/'/g, "''")}' and ${baseFilter}`;
  const runs = [];
  let continuationToken = null;

  const iter = client.listEntities({ queryOptions: { filter } });
  const pager = iter.byPage({ maxPageSize: maxRows });

  for await (const page of pager) {
    for (const entity of page) {
      runs.push(normalizeEntity(entity));
      if (runs.length >= maxRows) break;
    }
    // Capture Table Storage continuation token from page metadata
    if (page.continuationToken) {
      continuationToken = {
        partitionKey: page.continuationToken.nextPartitionKey,
        rowKey: page.continuationToken.nextRowKey
      };
    }
    break; // one page per partition per request
  }

  return { runs, continuationToken };
}

function normalizeEntity(entity) {
  return {
    agent_id: entity.partitionKey ?? entity.PartitionKey,
    run_timestamp: entity.run_timestamp ?? null,
    status: entity.status ?? null,
    validator_schema: entity.validator_schema ?? null,
    validator_scope: entity.validator_scope ?? null,
    validator_naming: entity.validator_naming ?? null,
    validator_escalation: entity.validator_escalation ?? null,
    failure_reason: entity.failure_reason ?? null,
    payload_size_bytes: entity.payload_size_bytes ?? null,
    target_site: entity.target_site ?? null
  };
}
