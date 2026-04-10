def quality_score(structure, assay, annotations):
    score = 0

    # Structure quality
    if structure.get("resolution"):
        score += max(0, 3 - structure["resolution"])

    if structure.get("plddt"):
        score += structure["plddt"] / 100

    # Assay confidence
    if assay.get("confidence"):
        score += assay["confidence"]

    # Missing data penalty
    score -= structure.get("missing_fraction", 0)

    return score
