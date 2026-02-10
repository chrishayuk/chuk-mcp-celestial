"""Celestial computation storage via chuk-artifacts.

Stores planet position and event computation results with rich metadata
for retrieval, audit, and cross-server integration.

Uses the configured artifact store backend (memory, filesystem, S3)
for all persistence. An in-memory cache provides fast lookups
within the current process.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class CelestialStorage:
    """Manages celestial computation storage via chuk-artifacts.

    Parameters
    ----------
    artifact_store : ArtifactStore or None
        The chuk-artifacts store instance. If None, storage is disabled
        and all operations are no-ops (graceful degradation).
    """

    def __init__(self, artifact_store: Any = None) -> None:
        self._store = artifact_store
        self._cache: dict[str, dict[str, Any]] = {}
        self._artifact_index: dict[str, str] = {}

    @property
    def available(self) -> bool:
        """Whether an artifact store is configured."""
        return self._store is not None

    @property
    def storage_provider(self) -> str:
        """Return a human-readable storage provider name."""
        if self._store is None:
            return "none"
        return getattr(self._store, "storage_provider", "artifacts")

    # ── Save ──────────────────────────────────────────────────────────────

    async def save_position(
        self, planet: str, date: str, time: str, lat: float, lon: float, data: dict[str, Any]
    ) -> str | None:
        """Save planet position computation result.

        Returns artifact_id on success, None if no store configured or on error.
        """
        key = f"position|{planet}|{date}|{time}|{lat}|{lon}"
        self._cache[key] = data

        if not self._store:
            return None

        try:
            json_bytes = json.dumps(data, indent=2).encode("utf-8")
            artifact_id = await self._store.store(
                data=json_bytes,
                mime="application/json",
                summary=f"Planet position: {planet} at {date} {time}",
                filename=f"celestial/positions/{planet}/{date}_{time.replace(':', '')}.json",
                meta={
                    "type": "planet_position",
                    "planet": planet,
                    "date": date,
                    "time": time,
                    "lat": lat,
                    "lon": lon,
                },
            )
            self._artifact_index[key] = artifact_id
            logger.info("Stored planet position for %s (artifact_id=%s)", key, artifact_id)
            return artifact_id
        except Exception as exc:
            logger.warning("Failed to store planet position for %s: %s", key, exc)
            return None

    async def save_events(
        self, planet: str, date: str, lat: float, lon: float, data: dict[str, Any]
    ) -> str | None:
        """Save planet events computation result.

        Returns artifact_id on success, None if no store configured or on error.
        """
        key = f"events|{planet}|{date}|{lat}|{lon}"
        self._cache[key] = data

        if not self._store:
            return None

        try:
            json_bytes = json.dumps(data, indent=2).encode("utf-8")
            artifact_id = await self._store.store(
                data=json_bytes,
                mime="application/json",
                summary=f"Planet events: {planet} on {date}",
                filename=f"celestial/events/{planet}/{date}.json",
                meta={
                    "type": "planet_events",
                    "planet": planet,
                    "date": date,
                    "lat": lat,
                    "lon": lon,
                },
            )
            self._artifact_index[key] = artifact_id
            logger.info("Stored planet events for %s (artifact_id=%s)", key, artifact_id)
            return artifact_id
        except Exception as exc:
            logger.warning("Failed to store planet events for %s: %s", key, exc)
            return None

    async def save_sky(
        self, date: str, time: str, lat: float, lon: float, data: dict[str, Any]
    ) -> str | None:
        """Save sky summary computation result.

        Returns artifact_id on success, None if no store configured or on error.
        """
        key = f"sky|{date}|{time}|{lat}|{lon}"
        self._cache[key] = data

        if not self._store:
            return None

        try:
            json_bytes = json.dumps(data, indent=2).encode("utf-8")
            artifact_id = await self._store.store(
                data=json_bytes,
                mime="application/json",
                summary=f"Sky summary: {date} {time}",
                filename=f"celestial/sky/{date}_{time.replace(':', '')}.json",
                meta={
                    "type": "sky_summary",
                    "date": date,
                    "time": time,
                    "lat": lat,
                    "lon": lon,
                },
            )
            self._artifact_index[key] = artifact_id
            logger.info("Stored sky summary for %s (artifact_id=%s)", key, artifact_id)
            return artifact_id
        except Exception as exc:
            logger.warning("Failed to store sky summary for %s: %s", key, exc)
            return None

    # ── Load ──────────────────────────────────────────────────────────────

    async def load(self, key: str) -> dict[str, Any] | None:
        """Load a stored computation result by key.

        Checks in-memory cache first, then artifact store.
        Returns None if not found.
        """
        if key in self._cache:
            return self._cache[key]

        if key in self._artifact_index and self._store:
            artifact_id = self._artifact_index[key]
            try:
                raw = await self._store.retrieve(artifact_id)
                data = json.loads(raw.decode("utf-8"))
                self._cache[key] = data
                return data
            except Exception as exc:
                logger.warning("Failed to load artifact %s: %s", artifact_id, exc)

        return None

    def stored_count(self) -> int:
        """Return the number of cached computation results."""
        return len(self._cache)
