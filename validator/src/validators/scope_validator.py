import os
import json
import re

from graph_client import SharePointListFetcher

class ScopeValidator:
    def __init__(self, mocks_dir: str = None, shared_dir: str = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.shared_dir = shared_dir or os.path.join(base_dir, "shared")
            
        self.graph_fetcher = SharePointListFetcher()
        self.permission_matrix = self.graph_fetcher.fetch_permission_matrix()
        
        if not self.permission_matrix:
            self.mocks_dir = mocks_dir or os.path.join(self.shared_dir, "mocks")
            self.permission_matrix = self._load_json(os.path.join(self.mocks_dir, "permission_matrix.json"), [])

        self.uri_mapping = self._load_json(os.path.join(self.shared_dir, "uri_scope_mapping.json"), [])
        self.uri_mapping.sort(key=lambda x: x.get('priority', 99))

        registry = self._load_json(os.path.join(self.shared_dir, "teams_channel_registry.json"), [])
        self.channel_registry = {row["uri"]: row["scope_id"] for row in registry if row.get("uri") and row.get("scope_id")}

    def _load_json(self, path, default):
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
        return default

    def _resolve_scope(self, target_uri: str) -> str:
        if target_uri in self.channel_registry:
            return self.channel_registry[target_uri]
        for mapping in self.uri_mapping:
            pattern = mapping.get("uri_pattern")
            if pattern and re.match(pattern, target_uri):
                return mapping.get("scope_id")
        return None

    def validate(self, agent_id: str, proposed_writes: list) -> dict:
        if not proposed_writes:
            return {"pass": True}

        violations = []
        for write in proposed_writes:
            target_uri = write.get("target_uri")
            write_type = write.get("write_type", "create")
            
            # Resolve scope
            scope_id = self._resolve_scope(target_uri)
            if not scope_id:
                violations.append({
                    "target_uri": target_uri,
                    "reason": "URI does not match any known scope"
                })
                continue
            
            # Look up permission
            grant = next((row for row in self.permission_matrix 
                         if row.get("agent_id") == agent_id and row.get("scope_id") == scope_id), None)
            
            if not grant:
                violations.append({
                    "target_uri": target_uri,
                    "scope_id": scope_id,
                    "access_granted": "None",
                    "reason": "No permission grant found for this scope"
                })
                continue
                
            access = grant.get("access", "")
            if access not in ["W", "R/W"]:
                violations.append({
                    "target_uri": target_uri,
                    "scope_id": scope_id,
                    "access_required": "W",
                    "access_granted": access,
                    "reason": "Write access denied"
                })
                continue
                
        if violations:
            return {"pass": False, "violations": violations}
            
        return {"pass": True}
