import re
from pathlib import Path
from typing import Protocol

from goldcoast.storage import write_bytes


class AssetStore(Protocol):
    def put(self, tenant_id: str, asset_id: str, data: bytes) -> None: ...
    def get(self, tenant_id: str, asset_id: str) -> bytes: ...


class LocalAssetStore:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def path(self, tenant_id, asset_id):
        if not all(re.fullmatch(r"[a-f0-9]{32}", part) for part in [tenant_id, asset_id]):
            raise ValueError("Invalid asset identifier")
        path = (self.root / tenant_id / asset_id).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Asset path outside storage root")
        return path

    def put(self, tenant_id, asset_id, data):
        write_bytes(self.path(tenant_id, asset_id), data)

    def get(self, tenant_id, asset_id):
        return self.path(tenant_id, asset_id).read_bytes()
