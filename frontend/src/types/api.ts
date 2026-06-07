export type AsyncTask = {
  task_id: string;
  session_id: number | null;
  task_type: string;
  status: string;
  progress: number;
  message: string | null;
  result_json: Record<string, unknown> | unknown[] | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type LearningSession = {
  id: number;
  tech_name: string;
  user_level: string | null;
  learning_goal: string | null;
  status: string;
  current_knowledge_point_id: number | null;
  current_level_id: number | null;
  created_at: string;
  updated_at: string;
  task: AsyncTask | null;
};

export type LearningSessionStatus = {
  session_id: number;
  status: string;
  current_knowledge_point_id: number | null;
  current_level_id: number | null;
  task: AsyncTask | null;
};

export type CreateLearningSessionRequest = {
  tech_name: string;
  user_level: string;
  learning_goal: string;
};

export type CreateLearningSessionResponse = {
  session_id: number;
  task_id: string;
  status: string;
};

export type KnowledgePoint = {
  id: number;
  session_id: number;
  tech_name: string;
  title: string;
  goal: string | null;
  depends_on: string[];
  difficulty: string | null;
  reason: string | null;
  category: string | null;
  sort_order: number;
};

export type LearningExample = {
  id: number;
  session_id: number;
  knowledge_point_id: number;
  official_example: string | null;
  beginner_example: string | null;
  baseline_example: string | null;
  target_example: string | null;
  observe_questions: string[];
};

export type LearningLevel = {
  id: number;
  session_id: number;
  knowledge_point_id: number;
  type: string;
  title: string;
  scenario: string | null;
  question: string | null;
  answer_requirements: string[];
  task: string | null;
  hint: string | null;
  rubric: string[];
  acceptance_criteria: string[];
  common_mistakes: string[];
  reference_answer: string | null;
  sort_order: number;
};

export type ComparisonResult = {
  id: number;
  session_id: number;
  tech_name: string;
  target_tech: string;
  selected_for_comparison: string[];
  baseline_solution: string;
  comparison_task: string;
  comparison_table: Record<string, string>[];
  when_to_use: string[];
  when_not_to_use: string[];
  skipped_candidates: string[];
};

export type SubmitAnswerResponse = {
  answer_id: number;
  feedback_id: number;
  result: "pass" | "partial" | "fail";
  next_level_id: number | null;
  current_level_id: number | null;
  message: string;
};

export type FeedbackResult = {
  id: number;
  session_id: number;
  answer_id: number;
  level_id: number | null;
  result: "pass" | "partial" | "fail";
  score: number;
  passed: boolean;
  strengths: string[];
  correct_points: string[];
  missing_points: string[];
  misconception: string;
  feedback: string;
  improved_answer: string;
  next_hint: string;
  suggested_review_points: string[];
};

export type PracticeTask = {
  id: number;
  session_id: number;
  title: string;
  background: string;
  required_points: string[];
  task_requirements: string[];
  comparison_requirement: string;
  acceptance_criteria: string[];
  review_questions: string[];
};

export type LearningCard = {
  id: number;
  session_id: number;
  tech_name: string;
  pain_point: string;
  baseline_solution: string;
  target_advantage: string;
  when_to_use: string[];
  when_not_to_use: string[];
  minimal_example: string;
  my_understanding: string;
  weak_points: string[];
  card_markdown: string | null;
};
