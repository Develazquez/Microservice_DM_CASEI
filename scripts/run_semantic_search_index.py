from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.academic_bm25_search_service import load_search_documents
from app.services.academic_semantic_embedding_service import build_and_persist_semantic_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Construye el índice semántico académico.")
    parser.add_argument(
        "--prototypes-only",
        action="store_true",
        help="Aborta si algún embedding documental necesita recalcularse.",
    )
    args = parser.parse_args()
    manifest = build_and_persist_semantic_index(
        load_search_documents(),
        require_full_document_reuse=args.prototypes_only,
    )
    print(
        "Indice semantico generado: "
        f"{manifest['search_version']} | documentos={manifest['documents']} | dimension={manifest['dimension']} | "
        f"modo={manifest['build_mode']} | reutilizados={manifest['reused_documents']} | "
        f"calculados={manifest['embedded_documents']}"
    )


if __name__ == "__main__":
    main()
