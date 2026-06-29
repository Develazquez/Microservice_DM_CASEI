from __future__ import annotations

from app.services.academic_bm25_search_service import run_search_engine


class SearchController:
    """Controller for the BM25 academic search extra roadmap item."""

    def run(self) -> None:
        run_search_engine()

