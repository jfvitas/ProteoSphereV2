from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class UniProtSequenceRecord:
    """Normalized UniProt sequence record for downstream canonicalization."""

    accession: str
    entry_name: str
    protein_name: str
    organism_name: str
    gene_names: tuple[str, ...]
    reviewed: bool
    sequence: str
    sequence_length: int
    source_format: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "accession": self.accession,
            "entry_name": self.entry_name,
            "protein_name": self.protein_name,
            "organism_name": self.organism_name,
            "gene_names": list(self.gene_names),
            "reviewed": self.reviewed,
            "sequence": self.sequence,
            "sequence_length": self.sequence_length,
            "source_format": self.source_format,
        }


def parse_uniprot_entry(entry: Mapping[str, Any]) -> UniProtSequenceRecord:
    accession = _required_text(entry.get("primaryAccession") or entry.get("accession"), "accession")
    entry_name = _first_text(entry.get("uniProtkbId") or entry.get("entryName"), default=accession)
    sequence_block = entry.get("sequence") or {}
    if not isinstance(sequence_block, Mapping):
        raise ValueError("sequence field must be a mapping")

    sequence = _clean_sequence(sequence_block.get("value"))
    if not sequence:
        raise ValueError("UniProt entry did not contain a sequence")

    protein_name = _parse_entry_protein_name(entry)
    organism_name = _parse_entry_organism_name(entry)
    gene_names = _parse_entry_gene_names(entry)
    reviewed = _is_reviewed_entry(entry)

    return UniProtSequenceRecord(
        accession=accession,
        entry_name=entry_name,
        protein_name=protein_name,
        organism_name=organism_name,
        gene_names=gene_names,
        reviewed=reviewed,
        sequence=sequence,
        sequence_length=len(sequence),
        source_format="json",
    )


def parse_uniprot_fasta(text: str) -> UniProtSequenceRecord:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or not lines[0].startswith(">"):
        raise ValueError("UniProt FASTA text must start with a header line")

    header = lines[0][1:]
    sequence = _clean_sequence("".join(lines[1:]))
    if not sequence:
        raise ValueError("UniProt FASTA text did not contain a sequence")

    reviewed, accession, entry_name, protein_name, organism_name = _parse_fasta_header(header)
    return UniProtSequenceRecord(
        accession=accession,
        entry_name=entry_name,
        protein_name=protein_name,
        organism_name=organism_name,
        gene_names=(),
        reviewed=reviewed,
        sequence=sequence,
        sequence_length=len(sequence),
        source_format="fasta",
    )


def parse_uniprot_text(text: str) -> UniProtSequenceRecord:
    accession = ""
    entry_name = ""
    reviewed = False
    protein_name = ""
    organism_name = ""
    gene_names: list[str] = []
    description_lines: list[str] = []
    sequence_lines: list[str] = []
    in_sequence = False

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
        if line.startswith("//"):
            break
        if in_sequence:
            if line.startswith("     "):
                sequence_lines.append(line)
            continue

        tag = line[:2]
        payload = line[5:].strip() if len(line) > 5 else ""
        if tag == "ID":
            entry_name, reviewed = _parse_text_id_line(payload, default=entry_name)
        elif tag == "AC" and not accession:
            accession = _parse_text_accession(payload)
        elif tag == "DE":
            description_lines.append(payload)
        elif tag == "OS":
            organism_name = _merge_text_payload(organism_name, payload)
        elif tag == "GN":
            gene_names.extend(_parse_text_gene_names(payload))
        elif tag == "SQ":
            in_sequence = True

    if not sequence_lines:
        raise ValueError("UniProt text did not contain a sequence")

    sequence = _clean_sequence("".join(sequence_lines))
    if not sequence:
        raise ValueError("UniProt text did not contain a valid sequence")

    protein_name = _parse_text_protein_name(description_lines)
    entry_name = entry_name or accession
    accession = accession or entry_name
    organism_name = organism_name.rstrip(".")

    return UniProtSequenceRecord(
        accession=accession,
        entry_name=entry_name,
        protein_name=protein_name,
        organism_name=organism_name,
        gene_names=_dedupe(gene_names),
        reviewed=reviewed,
        sequence=sequence,
        sequence_length=len(sequence),
        source_format="text",
    )


def _parse_entry_protein_name(entry: Mapping[str, Any]) -> str:
    description = entry.get("proteinDescription")
    if not isinstance(description, Mapping):
        return ""

    for key in ("recommendedName", "submissionNames", "alternativeNames"):
        candidate = description.get(key)
        name = _extract_protein_name(candidate)
        if name:
            return name
    return ""


def _extract_protein_name(candidate: Any) -> str:
    if isinstance(candidate, Mapping):
        full_name = candidate.get("fullName")
        if isinstance(full_name, Mapping):
            value = _first_text(full_name.get("value"))
            if value:
                return value
        for nested_key in ("alternativeNames", "subNames", "recommendedName"):
            nested = candidate.get(nested_key)
            name = _extract_protein_name(nested)
            if name:
                return name
    if isinstance(candidate, list):
        for item in candidate:
            name = _extract_protein_name(item)
            if name:
                return name
    return ""


def _parse_entry_organism_name(entry: Mapping[str, Any]) -> str:
    organism = entry.get("organism")
    if not isinstance(organism, Mapping):
        return ""
    return _first_text(organism.get("scientificName") or organism.get("commonName"))


def _parse_entry_gene_names(entry: Mapping[str, Any]) -> tuple[str, ...]:
    genes = entry.get("genes")
    if not isinstance(genes, list):
        return ()

    names: list[str] = []
    for gene in genes:
        if not isinstance(gene, Mapping):
            continue
        names.extend(_parse_gene_payload(gene))
    return _dedupe(names)


def _parse_gene_payload(gene: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("geneName", "orfNames", "orderedLocusNames", "synonyms"):
        payload = gene.get(key)
        if isinstance(payload, Mapping):
            values.extend(_maybe_text(payload.get("value")))
        elif isinstance(payload, list):
            for item in payload:
                if isinstance(item, Mapping):
                    values.extend(_maybe_text(item.get("value")))
    return [value for value in values if value]


def _is_reviewed_entry(entry: Mapping[str, Any]) -> bool:
    entry_type = _first_text(entry.get("entryType"))
    if "reviewed" in entry_type.lower():
        return True
    if "unreviewed" in entry_type.lower():
        return False
    return False


def _parse_fasta_header(header: str) -> tuple[bool, str, str, str, str]:
    parts = header.split("|", 2)
    if len(parts) != 3:
        raise ValueError("UniProt FASTA header must contain pipe-delimited fields")

    reviewed = parts[0].strip().lower() == "sp"
    accession = parts[1].strip().upper()
    if not accession:
        raise ValueError("UniProt FASTA header did not contain an accession")

    entry_and_desc = parts[2].strip()
    entry_name, protein_name = _split_entry_and_description(entry_and_desc)
    organism_name = _extract_bracketed_organism(protein_name)
    if organism_name:
        protein_name = protein_name[: protein_name.rfind("[")].strip()
    return reviewed, accession, entry_name, protein_name, organism_name


def _split_entry_and_description(text: str) -> tuple[str, str]:
    if " " not in text:
        return text.strip(), ""
    entry_name, description = text.split(" ", 1)
    return entry_name.strip(), description.strip()


def _extract_bracketed_organism(text: str) -> str:
    match = re.search(r"\[([^\[\]]+)\]\s*$", text)
    if not match:
        return ""
    return match.group(1).strip()


def _parse_text_id_line(payload: str, *, default: str = "") -> tuple[str, bool]:
    parts = payload.split()
    if not parts:
        return default, False
    entry_name = parts[0].strip()
    reviewed = "reviewed" in payload.lower() and "unreviewed" not in payload.lower()
    return entry_name or default, reviewed


def _parse_text_accession(payload: str) -> str:
    accession = payload.split(";", 1)[0].strip().upper()
    if not accession:
        raise ValueError("UniProt text did not contain an accession")
    return accession


def _merge_text_payload(existing: str, payload: str) -> str:
    merged = f"{existing} {payload}".strip()
    return re.sub(r"\s+", " ", merged).rstrip(".")


def _parse_text_gene_names(payload: str) -> list[str]:
    values = re.findall(r"(?:Name|Synonyms|OrderedLocusNames|ORFNames)=([^;]+)", payload)
    genes: list[str] = []
    for value in values:
        genes.extend(_split_multi_value(value))
    return genes


def _parse_text_protein_name(description_lines: list[str]) -> str:
    description = " ".join(description_lines).strip()
    if not description:
        return ""

    for marker in ("RecName: Full=", "SubName: Full=", "Short=", "Flags:"):
        if marker in description:
            description = description.split(marker, 1)[1]
            break

    match = re.search(r"Full=([^;]+);", description)
    if match:
        return match.group(1).strip()
    match = re.search(r"Short=([^;]+);", description)
    if match:
        return match.group(1).strip()
    return description.replace(";", " ").strip()


def _clean_sequence(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).upper()
    return re.sub(r"[^A-Z]", "", text)


def _required_text(value: Any, label: str) -> str:
    text = _first_text(value)
    if not text:
        raise ValueError(f"UniProt {label} is required")
    return text


def _first_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip() or default
    if isinstance(value, Mapping):
        if "value" in value:
            return _first_text(value.get("value"), default=default)
        for nested in value.values():
            text = _first_text(nested, default="")
            if text:
                return text
        return default
    if isinstance(value, list):
        for item in value:
            text = _first_text(item, default="")
            if text:
                return text
        return default
    return str(value).strip() or default


def _maybe_text(value: Any) -> list[str]:
    text = _first_text(value)
    return [text] if text else []


def _split_multi_value(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"[;,]", text) if part.strip()]


def _dedupe(values: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


__all__ = [
    "UniProtSequenceRecord",
    "parse_uniprot_entry",
    "parse_uniprot_fasta",
    "parse_uniprot_text",
]
