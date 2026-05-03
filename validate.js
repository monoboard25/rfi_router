// validate.js — run with: node validate.js
// validates all fixtures in schemas/fixtures/ against rfi_router.schema.json

const Ajv = require("ajv/dist/2020");
const addFormats = require("ajv-formats");
const fs = require("fs");
const path = require("path");

const ajv = new Ajv({ allErrors: true, strict: false });
addFormats(ajv);

const schemaPath = path.join(__dirname, "schemas/rfi_router.schema.json");
const schema = JSON.parse(fs.readFileSync(schemaPath, "utf8"));
const validate = ajv.compile(schema);

const fixturesDir = path.join(__dirname, "schemas/fixtures");
const files = fs.readdirSync(fixturesDir).filter(f => f.endsWith(".json"));

let passed = 0, failed = 0;

for (const file of files) {
  const data = JSON.parse(fs.readFileSync(path.join(fixturesDir, file), "utf8"));
  const valid = validate(data);
  if (valid) {
    console.log(`✅  PASS  ${file}`);
    passed++;
  } else {
    console.log(`❌  FAIL  ${file}`);
    console.log(JSON.stringify(validate.errors, null, 2));
    failed++;
  }
}

console.log(`\n${passed} passed / ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
