import { apiGet, apiPost } from "./client";
import type {
  ComparisonResult,
  CreateLearningSessionRequest,
  CreateLearningSessionResponse,
  FeedbackResult,
  KnowledgePoint,
  LearningCard,
  LearningExample,
  LearningLevel,
  LearningSession,
  LearningSessionStatus,
  PracticeTask,
  SubmitAnswerResponse,
} from "../types/api";

export const createLearningSession = (body: CreateLearningSessionRequest) =>
  apiPost<CreateLearningSessionResponse, CreateLearningSessionRequest>("/api/learning-sessions", body);

export const getLearningSession = (sessionId: number) =>
  apiGet<LearningSession>(`/api/learning-sessions/${sessionId}`);

export const getLearningSessionStatus = (sessionId: number) =>
  apiGet<LearningSessionStatus>(`/api/learning-sessions/${sessionId}/status`);

export const getKnowledgePoints = (sessionId: number) =>
  apiGet<KnowledgePoint[]>(`/api/learning-sessions/${sessionId}/knowledge-points`);

export const getExamples = (knowledgePointId: number) =>
  apiGet<LearningExample[]>(`/api/knowledge-points/${knowledgePointId}/examples`);

export const getLevels = (knowledgePointId: number) =>
  apiGet<LearningLevel[]>(`/api/knowledge-points/${knowledgePointId}/levels`);

export const getLevel = (levelId: number) => apiGet<LearningLevel>(`/api/levels/${levelId}`);

export const getComparisons = (sessionId: number) =>
  apiGet<ComparisonResult[]>(`/api/comparisons/session/${sessionId}`);

export const submitAnswer = (levelId: number, answerText: string) =>
  apiPost<SubmitAnswerResponse, { answer_text: string }>(`/api/levels/${levelId}/answers`, {
    answer_text: answerText,
  });

export const getFeedback = (answerId: number) => apiGet<FeedbackResult>(`/api/answers/${answerId}/feedback`);

export const generatePracticeTask = (sessionId: number) =>
  apiPost<PracticeTask>(`/api/learning-sessions/${sessionId}/practice-task`);

export const getPracticeTask = (sessionId: number) =>
  apiGet<PracticeTask>(`/api/learning-sessions/${sessionId}/practice-task`);

export const generateLearningCard = (sessionId: number) =>
  apiPost<LearningCard>(`/api/learning-sessions/${sessionId}/learning-card`);

export const getLearningCard = (sessionId: number) =>
  apiGet<LearningCard>(`/api/learning-sessions/${sessionId}/learning-card`);
