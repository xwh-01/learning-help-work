from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class OfficialMaterialSchema(StrictBaseModel):
    tech_name: str
    official_summary: str
    official_example: str
    source_url: str | None = None
    chunks: list[str] = Field(default_factory=list)


class ComparisonResultSchema(StrictBaseModel):
    target_tech: str
    selected_for_comparison: list[str] = Field(default_factory=list)
    baseline_solution: str
    comparison_task: str
    comparison_table: list[dict[str, str]] = Field(default_factory=list)
    when_to_use: list[str] = Field(default_factory=list)
    when_not_to_use: list[str] = Field(default_factory=list)
    skipped_candidates: list[str] = Field(default_factory=list)


class KnowledgePointSchema(StrictBaseModel):
    title: str
    goal: str
    depends_on: list[str] = Field(default_factory=list)
    difficulty: str
    reason: str
    category: str


class LearningExampleSchema(StrictBaseModel):
    knowledge_point_title: str = Field(validation_alias=AliasChoices("knowledge_point_title", "knowledge_point", "title"))
    official_example: str = Field(validation_alias=AliasChoices("official_example", "official_code", "source_example"))
    beginner_example: str = Field(validation_alias=AliasChoices("beginner_example", "friendly_example", "simple_example"))
    baseline_example: str = Field(validation_alias=AliasChoices("baseline_example", "ordinary_example", "plain_example"))
    target_example: str = Field(validation_alias=AliasChoices("target_example", "target_tech_example", "technology_example"))
    observe_questions: list[str] = Field(default_factory=list, validation_alias=AliasChoices("observe_questions", "questions"))


class LearningLevelSchema(StrictBaseModel):
    knowledge_point_title: str = Field(validation_alias=AliasChoices("knowledge_point_title", "knowledge_point", "title"))
    type: str
    title: str
    scenario: str = ""
    question: str = ""
    answer_requirements: list[str] = Field(default_factory=list)
    task: str
    hint: str
    rubric: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    common_mistakes: list[str] = Field(default_factory=list)
    reference_answer: str = ""


class FeedbackResultSchema(StrictBaseModel):
    result: str
    score: int = 0
    passed: bool = False
    strengths: list[str] = Field(default_factory=list)
    correct_points: list[str] = Field(default_factory=list)
    missing_points: list[str] = Field(default_factory=list)
    misconception: str = ""
    feedback: str
    improved_answer: str = ""
    next_hint: str = ""
    suggested_review_points: list[str] = Field(default_factory=list)


class PracticeTaskSchema(StrictBaseModel):
    title: str
    background: str
    required_points: list[str] = Field(default_factory=list)
    task_requirements: list[str] = Field(default_factory=list)
    comparison_requirement: str
    acceptance_criteria: list[str] = Field(default_factory=list)
    review_questions: list[str] = Field(default_factory=list)


class LearningCardSchema(StrictBaseModel):
    tech_name: str
    pain_point: str
    baseline_solution: str
    target_advantage: str
    when_to_use: list[str] = Field(default_factory=list)
    when_not_to_use: list[str] = Field(default_factory=list)
    minimal_example: str
    my_understanding: str
    weak_points: list[str] = Field(default_factory=list)
