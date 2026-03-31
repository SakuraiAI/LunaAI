from dataclasses import dataclass, field


@dataclass(slots=True)
class ProjectRequirement:
    name: str
    description: str
    priority: str = "medium"


@dataclass(slots=True)
class ProjectTask:
    title: str
    description: str
    status: str = "pending"
    owner: str = "xeno"
    tool: str = "analysis"
    priority: str = "medium"


@dataclass(slots=True)
class AgentStep:
    title: str
    description: str
    status: str = "pending"
    tool: str = "analysis"
    output: str = ""
    risk: str = "low"
    dependencies: list[str] = field(default_factory=list)
    action_ready: bool = False
    action_hint: str = ""
    handoff_note: str = ""


@dataclass(slots=True)
class AgentRun:
    name: str
    objective: str
    current_phase: str = "planning"
    steps: list[AgentStep] = field(default_factory=list)
    execution_mode: str = "guided"
    recommended_next_action: str = ""
    handoff_summary: str = ""


@dataclass(slots=True)
class ProjectBlueprint:
    project_name: str
    goal: str
    project_type: str = "general"
    difficulty: str = "medium"
    target_outcome: str = ""
    suggested_stack: list[str] = field(default_factory=list)
    folders: list[str] = field(default_factory=list)
    core_files: list[str] = field(default_factory=list)
    requirements: list[ProjectRequirement] = field(default_factory=list)
    tasks: list[ProjectTask] = field(default_factory=list)
    milestones: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    execution_notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class BuilderResult:
    summary: str
    blueprint: ProjectBlueprint
    next_step: str
    agent_run: AgentRun | None = None
    xeno_note: str = ""
