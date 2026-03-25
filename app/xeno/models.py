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


@dataclass(slots=True)
class AgentStep:
    title: str
    description: str
    status: str = "pending"
    tool: str = "analysis"
    output: str = ""


@dataclass(slots=True)
class AgentRun:
    name: str
    objective: str
    current_phase: str = "planning"
    steps: list[AgentStep] = field(default_factory=list)


@dataclass(slots=True)
class ProjectBlueprint:
    project_name: str
    goal: str
    suggested_stack: list[str] = field(default_factory=list)
    folders: list[str] = field(default_factory=list)
    core_files: list[str] = field(default_factory=list)
    requirements: list[ProjectRequirement] = field(default_factory=list)
    tasks: list[ProjectTask] = field(default_factory=list)


@dataclass(slots=True)
class BuilderResult:
    summary: str
    blueprint: ProjectBlueprint
    next_step: str
    agent_run: AgentRun | None = None
