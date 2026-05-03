import os
import logging
import asyncio
from typing import List, Dict
from functools import lru_cache
from azure.identity import DefaultAzureCredential
from msgraph import GraphServiceClient

class SharePointListFetcher:
    def __init__(self):
        self.tenant_id = os.getenv("SP_TENANT_ID")
        self.site_id = os.getenv("SP_SITE_ID")
        self.permission_list_id = os.getenv("SP_PERMISSION_LIST_ID")
        self.escalation_list_id = os.getenv("SP_ESCALATION_LIST_ID")
        
        if self.tenant_id and self.site_id:
            try:
                credential = DefaultAzureCredential()
                self.client = GraphServiceClient(credentials=credential, scopes=["https://graph.microsoft.com/.default"])
            except Exception as e:
                logging.error(f"Failed to initialize Graph client: {e}")
                self.client = None
        else:
            self.client = None

    async def _get_list_items(self, list_id: str) -> List[Dict]:
        if not self.client or not list_id:
            return []
        try:
            result = await self.client.sites.by_site_id(self.site_id).lists.by_list_id(list_id).items.get()
            
            rows = []
            if result and result.value:
                for item in result.value:
                    if hasattr(item, 'fields') and item.fields:
                        fields_dict = item.fields.additional_data
                        for k, v in fields_dict.items():
                            if v == "1": fields_dict[k] = True
                            elif v == "0": fields_dict[k] = False
                        rows.append(fields_dict)
            return rows
        except Exception as e:
            logging.error(f"MS Graph API Error fetching list {list_id}: {e}")
            return []

    @lru_cache(maxsize=1)
    def fetch_permission_matrix(self) -> List[Dict]:
        """Fetches the Permission Matrix list items synchronously. Cached in memory."""
        return asyncio.run(self._get_list_items(self.permission_list_id))

    @lru_cache(maxsize=1)
    def fetch_escalation_matrix(self) -> List[Dict]:
        """Fetches the Escalation Matrix list items synchronously. Cached in memory."""
        return asyncio.run(self._get_list_items(self.escalation_list_id))
