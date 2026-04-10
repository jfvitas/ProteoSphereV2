import json
from pathlib import Path

tasks = [
    {"id":"P1-T001","title":"Implement minimum RCSB connector for locked baseline","type":"coding","phase":1,"files":["connectors/rcsb/","tests/unit/connectors/test_rcsb.py"],"dependencies":[],"status":"pending","success_criteria":["baseline structure retrieval works","unit tests pass"]},
    {"id":"P1-T002","title":"Implement minimum UniProt connector for locked baseline","type":"coding","phase":1,"files":["connectors/uniprot/","tests/unit/connectors/test_uniprot.py"],"dependencies":[],"status":"pending","success_criteria":["canonical sequence retrieval works","unit tests pass"]},
    {"id":"P1-T003","title":"Implement minimum BindingDB connector for locked baseline","type":"coding","phase":1,"files":["connectors/bindingdb/","tests/unit/connectors/test_bindingdb.py"],"dependencies":[],"status":"pending","success_criteria":["baseline assay retrieval works","unit tests pass"]},
    {"id":"P1-T004","title":"Implement minimum canonical records for locked baseline","type":"coding","phase":1,"files":["core/canonical_models/","tests/unit/core/test_canonical_models.py"],"dependencies":[],"status":"pending","success_criteria":["minimum canonical records exist","typed validation works"]},
    {"id":"P1-T005","title":"Implement baseline chain-to-protein mapping","type":"coding","phase":1,"files":["normalization/mapping/","tests/unit/normalization/test_chain_mapping.py"],"dependencies":["P1-T002","P1-T004"],"status":"pending","success_criteria":["exact matches map","ambiguity preserved"]},
    {"id":"P1-T006","title":"Implement baseline feature extraction","type":"coding","phase":1,"files":["features/","tests/unit/features/"],"dependencies":["P1-T001","P1-T002","P1-T003","P1-T004"],"status":"pending","success_criteria":["baseline feature tensors available","tests pass"]},
    {"id":"P1-T007","title":"Implement dataset builder for locked baseline","type":"coding","phase":1,"files":["datasets/builders/","tests/unit/datasets/test_baseline_builder.py"],"dependencies":["P1-T005","P1-T006"],"status":"pending","success_criteria":["baseline dataset builds end-to-end"]},
    {"id":"P1-T008","title":"Implement baseline model/training/evaluation path","type":"coding","phase":1,"files":["models/","training/","evaluation/","tests/integration/test_reference_pipeline.py"],"dependencies":["P1-T007"],"status":"pending","success_criteria":["reference pipeline trains and evaluates","integration test passes"]},
    {"id":"P3-A001","title":"Analyze RCSB source content and compatibility","type":"data_analysis","phase":3,"files":["artifacts/reports/"],"dependencies":[],"status":"pending","success_criteria":["source report written"]},
    {"id":"P3-A002","title":"Analyze UniProt identity backbone usage","type":"data_analysis","phase":3,"files":["artifacts/reports/"],"dependencies":[],"status":"pending","success_criteria":["source report written"]},
    {"id":"P3-A003","title":"Analyze BindingDB assay normalization and package implications","type":"data_analysis","phase":3,"files":["artifacts/reports/"],"dependencies":[],"status":"pending","success_criteria":["source report written"]}
]
Path("tasks/task_queue.json").write_text(json.dumps(tasks, indent=2), encoding="utf-8")
print(f"Wrote {len(tasks)} tasks.")
