// validate.js — run with: node validate.js
// validates every fixture in schemas/fixtures/ against its matching schema.
//
// Convention:
//   <agent_id>.valid.<label>.json   → must pass
//   <agent_id>.invalid.<label>.json → must fail
// Schema lookup: schemas/<agent_id>.schema.json

const Ajv = require("ajv/dist/2020");
const addFormats = require("ajv-formats");
const fs = require("fs");
const path = require("path");

const ajv = new Ajv({ allErrors: true, strict: false });
addFormats(ajv);

const schemasDir = path.join(__dirname, "schemas");
const fixturesDir = path.join(schemasDir, "fixtures");

const compiledByAgent = {};
function getValidator(agentId) {
  if (compiledByAgent[agentId]) return compiledByAgent[agentId];
  const schemaPath = path.join(schemasDir, `${agentId}.schema.json`);
  if (!fs.existsSync(schemaPath)) return null;
  const schema = JSON.parse(fs.readFileSync(schemaPath, "utf8"));
  compiledByAgent[agentId] = ajv.compile(schema);
  return compiledByAgent[agentId];
}

const files = fs.readdirSync(fixturesDir).filter(f => f.endsWith(".json")).sort();

let passed = 0, failed = 0;

for (const file of files) {
  const parts = file.split(".");
  const agentId = parts[0];
  const expectation = parts[1]; // "valid" or "invalid"
  const validator = getValidator(agentId);

  if (!validator) {
    console.log(`⚠️   SKIP  ${file}  (no schema for "${agentId}")`);
    continue;
  }
  if (expectation !== "valid" && expectation !== "invalid") {
    console.log(`⚠️   SKIP  ${file}  (filename must be <agent>.valid.* or <agent>.invalid.*)`);
    continue;
  }

  const data = JSON.parse(fs.readFileSync(path.join(fixturesDir, file), "utf8"));
  const ok = validator(data);
  const expectedOk = expectation === "valid";

  if (ok === expectedOk) {
    console.log(`✅  PASS  ${file}  (expected ${expectation})`);
    passed++;
  } else {
    console.log(`❌  FAIL  ${file}  (expected ${expectation}, got ${ok ? "valid" : "invalid"})`);
    if (!ok) console.log(JSON.stringify(validator.errors, null, 2));
    failed++;
  }
}

console.log(`\n${passed} passed / ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
