from __future__ import annotations

from core.library.summary_record import (
    ProteinLigandSummaryRecord,
    ProteinProteinSummaryRecord,
    ProteinSummaryRecord,
    ProteinVariantSummaryRecord,
    StructureUnitSummaryRecord,
    SummaryLibrarySchema,
)
from scripts.export_summary_library_inventory import (
    build_summary_library_inventory,
    render_summary_library_inventory_markdown,
)


def test_build_summary_library_inventory_counts_v2_record_types() -> None:
    library = SummaryLibrarySchema(
        library_id="summary-library:v2",
        schema_version=2,
        records=(
            ProteinSummaryRecord(summary_id="protein-1", protein_ref="protein:P12345"),
            ProteinVariantSummaryRecord(
                summary_id="variant-1",
                protein_ref="protein:P12345",
                variant_signature="R175H",
            ),
            StructureUnitSummaryRecord(
                summary_id="structure-1",
                protein_ref="protein:P12345",
                structure_source="PDB",
                structure_id="1ABC",
            ),
            ProteinProteinSummaryRecord(
                summary_id="pair-1",
                protein_a_ref="protein:P12345",
                protein_b_ref="protein:Q9XYZ1",
            ),
            ProteinLigandSummaryRecord(
                summary_id="ligand-1",
                protein_ref="protein:P12345",
                ligand_ref="ligand:CHEBI:1",
            ),
        ),
    )

    payload = build_summary_library_inventory(
        library,
        source_path="artifacts\\status\\protein_summary_library.json",
    )

    assert payload["record_count"] == 5
    assert payload["record_type_counts"]["protein"] == 1
    assert payload["record_type_counts"]["protein_variant"] == 1
    assert payload["record_type_counts"]["structure_unit"] == 1
    assert payload["record_type_counts"]["protein_protein"] == 1
    assert payload["record_type_counts"]["protein_ligand"] == 1
    assert payload["join_status_counts"]["joined"] == 5


def test_render_summary_library_inventory_markdown_lists_sections() -> None:
    payload = {
        "library_id": "summary-library:v2",
        "schema_version": 2,
        "source_manifest_id": "manifest:test",
        "source_path": "artifacts\\status\\protein_summary_library.json",
        "record_count": 5,
        "record_type_counts": {
            "protein": 1,
            "protein_variant": 1,
            "structure_unit": 1,
            "protein_protein": 1,
            "protein_ligand": 1,
        },
        "join_status_counts": {"joined": 5},
        "storage_tier_counts": {"feature_cache": 5},
    }

    markdown = render_summary_library_inventory_markdown(payload)

    assert "# Summary Library Inventory" in markdown
    assert "Record Types" in markdown
    assert "Join Status Counts" in markdown
    assert "Storage Tier Counts" in markdown
    assert "protein_variant" in markdown
    assert "structure_unit" in markdown
