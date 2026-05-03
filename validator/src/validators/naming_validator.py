import re

class NamingValidator:
    def __init__(self):
        self.project_regex = re.compile(r"^\d{4}-(DWG|RFI|SUB|CO|RPT|PHO|CON)-[A-Za-z0-9]+(?:-\d{8})?-v\d+$")
        self.company_regex = re.compile(r"^(HR|FIN|SAF|OPS|EST|LEG)-(POL|RPT|FRM|TMP|LOG|CRT)-[A-Za-z0-9]+-\d{4}$")

    def validate(self, proposed_filenames: list) -> dict:
        if not proposed_filenames:
            return {"pass": None, "reason": "not_applicable"}
            
        violations = []
        for filename in proposed_filenames:
            # Strip extension for validation against constitution regex
            base_filename = filename.rsplit('.', 1)[0]
            
            if re.match(r"^\d{4}-", base_filename):
                regex = self.project_regex
            elif re.match(r"^(HR|FIN|SAF|OPS|EST|LEG)-", base_filename):
                regex = self.company_regex
            else:
                violations.append({
                    "filename": filename,
                    "reason": "Does not match project or company prefix pattern"
                })
                continue
                
            if not regex.match(base_filename):
                violations.append({
                    "filename": filename,
                    "reason": "Filename violates schema structure"
                })
                
        if violations:
            return {"pass": False, "violations": violations}
            
        return {"pass": True}
