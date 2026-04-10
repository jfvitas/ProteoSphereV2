from __future__ import annotations

from dataclasses import dataclass

from scripts.task_catalog import make_task


@dataclass(frozen=True, slots=True)
class ProgramDefinition:
    program_id: int
    slug: str
    title: str
    base_path: str


PROGRAMS: tuple[ProgramDefinition, ...] = (
    ProgramDefinition(
        1, "studio_contracts", "Studio architecture and contracts", "api/model_studio"
    ),
    ProgramDefinition(2, "studio_backend", "Studio backend service", "api/model_studio"),
    ProgramDefinition(3, "data_strategy", "Data strategy designer", "gui/model_studio_web"),
    ProgramDefinition(
        4,
        "representation_graphs",
        "Representation and graph designer",
        "gui/model_studio_web",
    ),
    ProgramDefinition(
        5,
        "preprocess_materialization",
        "Preprocessing and materialization engine",
        "execution",
    ),
    ProgramDefinition(6, "pipeline_composer", "Model pipeline composer", "gui/model_studio_web"),
    ProgramDefinition(7, "training_runtime", "Training and evaluation runtime", "training"),
    ProgramDefinition(
        8,
        "recommendations",
        "Recommendations and intelligent assistance",
        "api/model_studio",
    ),
    ProgramDefinition(9, "ui_ux", "UI and visual system", "gui/model_studio_web"),
    ProgramDefinition(
        10, "operator_governance", "Studio operator and governance layer", "scripts"
    ),
    ProgramDefinition(11, "qa_review", "QA, user-sim, and visual review", "tests"),
    ProgramDefinition(12, "docs_enablement", "Docs and enablement", "docs/reports"),
)

WORKSTREAMS: tuple[str, ...] = (
    "contracts",
    "service",
    "data_policy",
    "graph_policy",
    "preprocess",
    "training",
    "evaluation",
    "qa",
)

MILESTONES: tuple[str, ...] = (
    "phase0_foundations",
    "phase1_draftable_studio",
    "phase2_executable_preprocess",
    "phase3_training_evaluation",
    "phase4_robust_autonomy",
)

ROLE_TO_TYPE = {
    "contracts": "coding",
    "service": "coding",
    "data_policy": "data_analysis",
    "graph_policy": "coding",
    "preprocess": "coding",
    "training": "integration",
    "evaluation": "test_hardening",
    "qa": "docs_reporting",
}


def _task_id(program_id: int, workstream_index: int, milestone_index: int, item_index: int) -> str:
    return f"MS{program_id:02d}-{workstream_index + 1}{milestone_index + 1}{item_index:02d}"


def _phase_for_milestone(milestone_index: int) -> int:
    return milestone_index + 20


def _files_for(
    program: ProgramDefinition,
    workstream: str,
    milestone: str,
    item_index: int,
) -> list[str]:
    stem = f"{program.slug}_{workstream}_{milestone}_{item_index:02d}"
    if program.base_path.startswith("gui/"):
        return [f"{program.base_path}/{stem}.md", f"tests/unit/model_studio/test_{stem}.py"]
    if program.base_path.startswith("api/"):
        return [f"{program.base_path}/{stem}.py", f"tests/unit/model_studio/test_{stem}.py"]
    if program.base_path == "execution":
        return [f"execution/model_studio/{stem}.py", f"tests/unit/model_studio/test_{stem}.py"]
    if program.base_path == "training":
        return [f"training/model_studio/{stem}.py", f"tests/unit/model_studio/test_{stem}.py"]
    if program.base_path == "scripts":
        return [f"scripts/{stem}.py", f"tests/unit/model_studio/test_{stem}.py"]
    if program.base_path == "tests":
        return [f"tests/integration/model_studio/test_{stem}.py", f"docs/reports/{stem}.md"]
    return [f"{program.base_path}/{stem}.md", f"tests/unit/model_studio/test_{stem}.py"]


def build_model_studio_tasks() -> list[dict]:
    tasks: list[dict] = []
    previous_ids: dict[tuple[int, int], str] = {}
    for program in PROGRAMS:
        for workstream_index, workstream in enumerate(WORKSTREAMS):
            for milestone_index, milestone in enumerate(MILESTONES):
                for item_index in range(1, 4):
                    task_id = _task_id(
                        program.program_id,
                        workstream_index,
                        milestone_index,
                        item_index,
                    )
                    dependencies: list[str] = []
                    prior_key = (program.program_id, workstream_index)
                    if prior_key in previous_ids:
                        dependencies.append(previous_ids[prior_key])
                    title = (
                        f"Model Studio {program.title}: {workstream} "
                        f"{milestone} task {item_index:02d}"
                    )
                    success_criteria = [
                        (
                            f"{program.title} {workstream} work for {milestone} "
                            "is implemented or documented"
                        ),
                        "task remains consistent with the canonical studio contracts",
                        "task emits reviewable artifacts or tests",
                    ]
                    tasks.append(
                        make_task(
                            task_id=task_id,
                            title=title,
                            task_type=ROLE_TO_TYPE[workstream],
                            phase=_phase_for_milestone(milestone_index),
                            files=_files_for(program, workstream, milestone, item_index),
                            dependencies=dependencies,
                            success_criteria=success_criteria,
                            priority="high" if milestone_index < 2 else "medium",
                        )
                    )
                    previous_ids[prior_key] = task_id
    return tasks
