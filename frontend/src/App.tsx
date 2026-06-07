import { type ReactNode, useMemo, useState } from "react";
import Editor from "@monaco-editor/react";
import ReactMarkdown from "react-markdown";
import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createLearningSession,
  generateLearningCard,
  getComparisons,
  getExamples,
  getFeedback,
  getKnowledgePoints,
  getLearningCard,
  getLearningSession,
  getLearningSessionStatus,
  getLevel,
  getLevels,
  submitAnswer,
} from "./api/learning";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./components/ui/card";
import { Input } from "./components/ui/input";
import type { FeedbackResult, LearningCard, LearningLevel } from "./types/api";

type View = "home" | "progress" | "lesson" | "card";
type LessonSection = "compare" | "practice" | "reflect";

type SubmissionState = {
  kind: "practice" | "reflection";
  feedback: FeedbackResult;
  message: string;
  nextLevelId: number | null;
};

const SESSION_KEY = "techleveler.session_id";
const savedSessionId = Number(localStorage.getItem(SESSION_KEY) ?? 0) || null;
const readyStatuses = new Set(["ready", "partial", "levels_completed", "completed"]);

const steps = [
  { key: "fetch_official_material", label: "Reading official material", start: 0, end: 20 },
  { key: "generate_comparison", label: "Building comparison", start: 20, end: 40 },
  { key: "generate_knowledge_points", label: "Planning core concepts", start: 40, end: 60 },
  { key: "generate_examples", label: "Creating examples", start: 60, end: 80 },
  { key: "generate_levels", label: "Designing exercises", start: 80, end: 100 },
];

const messageText: Record<string, string> = {
  fetch_official_material: "Reading official material",
  generate_comparison: "Building baseline comparison",
  generate_knowledge_points: "Planning core concepts",
  generate_examples: "Creating baseline vs target examples",
  generate_levels: "Designing small exercises",
  completed: "Ready",
  ready: "Ready",
};

const sectionLabels: Record<LessonSection, string> = {
  compare: "Compare",
  practice: "Practice",
  reflect: "Reflect",
};

const sectionToLevelType: Record<LessonSection, string> = {
  compare: "observe",
  practice: "hands_on",
  reflect: "summary",
};

export default function App() {
  const [sessionId, setSessionId] = useState<number | null>(savedSessionId);
  const [view, setView] = useState<View>(savedSessionId ? "progress" : "home");

  const openSession = (nextSessionId: number, nextView: View) => {
    localStorage.setItem(SESSION_KEY, String(nextSessionId));
    setSessionId(nextSessionId);
    setView(nextView);
  };

  const reset = () => {
    localStorage.removeItem(SESSION_KEY);
    setSessionId(null);
    setView("home");
  };

  return (
    <main className="min-h-screen bg-background text-foreground">
      <TopBar sessionId={sessionId} view={view} setView={setView} reset={reset} />
      {!sessionId || view === "home" ? (
        <HomePage onCreated={(id) => openSession(id, "progress")} />
      ) : view === "progress" ? (
        <ProgressPage sessionId={sessionId} onReady={() => setView("lesson")} />
      ) : view === "lesson" ? (
        <LessonPage sessionId={sessionId} openProgress={() => setView("progress")} openCard={() => setView("card")} />
      ) : (
        <LearningCardPage sessionId={sessionId} backToLesson={() => setView("lesson")} />
      )}
    </main>
  );
}

function TopBar({
  sessionId,
  view,
  setView,
  reset,
}: {
  sessionId: number | null;
  view: View;
  setView: (view: View) => void;
  reset: () => void;
}) {
  return (
    <header className="border-b border-border bg-background">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-5">
        <button className="text-sm font-semibold tracking-tight" onClick={reset}>
          TechLeveler
        </button>
        {sessionId ? (
          <nav className="flex items-center gap-1 text-sm">
            <Button variant={view === "progress" ? "subtle" : "ghost"} size="sm" onClick={() => setView("progress")}>
              Progress
            </Button>
            <Button variant={view === "lesson" ? "subtle" : "ghost"} size="sm" onClick={() => setView("lesson")}>
              Lesson
            </Button>
            <Button variant={view === "card" ? "subtle" : "ghost"} size="sm" onClick={() => setView("card")}>
              Card
            </Button>
            <Button variant="outline" size="sm" onClick={reset}>
              New
            </Button>
          </nav>
        ) : null}
      </div>
    </header>
  );
}

function HomePage({ onCreated }: { onCreated: (sessionId: number) => void }) {
  const [techName, setTechName] = useState("LangGraph");
  const createMutation = useMutation({
    mutationFn: createLearningSession,
    onSuccess: (data) => onCreated(data.session_id),
  });

  return (
    <section className="mx-auto flex min-h-[calc(100vh-56px)] max-w-3xl flex-col justify-center px-5 py-12">
      <div className="space-y-8">
        <div className="space-y-3">
          <h1 className="text-4xl font-semibold tracking-tight">TechLeveler</h1>
          <p className="max-w-xl text-base text-muted-foreground">
            Build intuition for a new tech stack through comparison and practice.
          </p>
        </div>

        <form
          className="flex flex-col gap-3 sm:flex-row"
          onSubmit={(event) => {
            event.preventDefault();
            createMutation.mutate({
              tech_name: techName.trim(),
              user_level: "beginner",
              learning_goal:
                [
                  "请为中文学习者生成 TechLeveler 学习内容。",
                  "所有题目、知识点、样例说明、练习任务、反思任务、验收标准、常见错误、反馈和技术卡片都使用中文呈现。",
                  "技术名、API 名、类名、函数名、命令、代码关键字保持英文原文。",
                  "题目请使用清晰的中文课程格式：背景、任务、要求、提交内容、验收标准。",
                  "练习题要短小、具体、可在 10-15 分钟内完成，并围绕当前知识点，不引入后续高级概念。",
                  "继续保留核心闭环：官方资料优先、普通写法 vs 目标技术写法、小练习、反馈、技术卡片。",
                ].join("\n"),
            });
          }}
        >
          <Input
            className="h-11 text-base"
            value={techName}
            onChange={(event) => setTechName(event.target.value)}
            placeholder="Enter a technology, e.g. LangGraph"
          />
          <Button className="h-11 whitespace-nowrap" disabled={createMutation.isPending || !techName.trim()} type="submit">
            {createMutation.isPending ? "Generating..." : "Generate learning path"}
          </Button>
        </form>
        {createMutation.error ? <ErrorText error={createMutation.error} /> : null}

        <div className="grid gap-3 text-sm text-muted-foreground sm:grid-cols-3">
          <FeatureLine title="Official-first material" />
          <FeatureLine title="Baseline vs target comparison" />
          <FeatureLine title="Small practice tasks" />
        </div>
      </div>
    </section>
  );
}

function ProgressPage({ sessionId, onReady }: { sessionId: number; onReady: () => void }) {
  const statusQuery = useQuery({
    queryKey: ["session-status", sessionId],
    queryFn: () => getLearningSessionStatus(sessionId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return readyStatuses.has(status ?? "") || status === "failed" ? false : 2000;
    },
  });

  const task = statusQuery.data?.task;
  const status = statusQuery.data?.status ?? "loading";
  const progress = task?.progress ?? 0;
  const isReady = readyStatuses.has(status);

  return (
    <section className="mx-auto max-w-3xl px-5 py-10">
      <div className="mb-8 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Generating learning path</h1>
          <p className="mt-2 text-sm text-muted-foreground">{readableMessage(task?.message, status)}</p>
        </div>
        <Button onClick={onReady} disabled={!isReady}>
          Open lesson
        </Button>
      </div>

      <Card>
        <CardContent className="space-y-1 py-2">
          {steps.map((step) => (
            <StepRow key={step.key} label={step.label} state={stepState(progress, step.start, step.end, status)} />
          ))}
        </CardContent>
      </Card>
      {task?.error_message ? <div className="mt-4"><ErrorText error={task.error_message} /></div> : null}
    </section>
  );
}

function LessonPage({
  sessionId,
  openProgress,
  openCard,
}: {
  sessionId: number;
  openProgress: () => void;
  openCard: () => void;
}) {
  const queryClient = useQueryClient();
  const [selectedPointId, setSelectedPointId] = useState<number | null>(null);
  const [selectedSection, setSelectedSection] = useState<LessonSection>("compare");
  const [practiceAnswer, setPracticeAnswer] = useState("");
  const [reflectionAnswer, setReflectionAnswer] = useState("");
  const [submission, setSubmission] = useState<SubmissionState | null>(null);

  const sessionQuery = useQuery({ queryKey: ["session", sessionId], queryFn: () => getLearningSession(sessionId) });
  const pointsQuery = useQuery({ queryKey: ["knowledge-points", sessionId], queryFn: () => getKnowledgePoints(sessionId) });
  const comparisonsQuery = useQuery({ queryKey: ["comparisons", sessionId], queryFn: () => getComparisons(sessionId), retry: false });

  const points = (pointsQuery.data ?? []).filter((point) => point.category === "must_learn");
  const fallbackPoints = points.length ? points : pointsQuery.data ?? [];
  const currentPoint = useMemo(() => {
    return (
      fallbackPoints.find((point) => point.id === selectedPointId) ??
      fallbackPoints.find((point) => point.id === sessionQuery.data?.current_knowledge_point_id) ??
      fallbackPoints[0]
    );
  }, [fallbackPoints, selectedPointId, sessionQuery.data?.current_knowledge_point_id]);

  const levelQueries = useQueries({
    queries: fallbackPoints.map((point) => ({
      queryKey: ["levels", point.id],
      queryFn: () => getLevels(point.id),
      enabled: !!point.id,
    })),
  });

  const levelsByPoint = useMemo(() => {
    const result = new Map<number, LearningLevel[]>();
    fallbackPoints.forEach((point, index) => result.set(point.id, sortLevels(levelQueries[index]?.data ?? [])));
    return result;
  }, [fallbackPoints, levelQueries]);

  const currentLevels = currentPoint ? levelsByPoint.get(currentPoint.id) ?? [] : [];
  const compareLevel = findLevel(currentLevels, "observe");
  const practiceLevel = findLevel(currentLevels, "hands_on");
  const reflectionLevel = findLevel(currentLevels, "summary");
  const activeLevel = findLevel(currentLevels, sectionToLevelType[selectedSection]);

  const examplesQuery = useQuery({
    queryKey: ["examples", currentPoint?.id],
    queryFn: () => getExamples(currentPoint!.id),
    enabled: !!currentPoint,
  });
  const example = examplesQuery.data?.[0] ?? null;
  const comparison = comparisonsQuery.data?.[0];

  const submitMutation = useMutation({
    mutationFn: async ({ level, answer, kind }: { level: LearningLevel; answer: string; kind: "practice" | "reflection" }) => {
      const response = await submitAnswer(level.id, answer);
      const feedback = await getFeedback(response.answer_id);
      const nextLevel = response.next_level_id ? await getLevel(response.next_level_id) : null;
      return { response, feedback, nextLevel, kind };
    },
    onSuccess: ({ response, feedback, nextLevel, kind }) => {
      setSubmission({ kind, feedback, message: response.message, nextLevelId: response.next_level_id });
      if (response.result === "pass" && nextLevel) {
        setSelectedPointId(nextLevel.knowledge_point_id);
      }
      queryClient.invalidateQueries({ queryKey: ["session", sessionId] });
    },
  });

  if (pointsQuery.isLoading || sessionQuery.isLoading) {
    return <LoadingState label="Loading lesson" />;
  }

  if (!fallbackPoints.length) {
    return (
      <EmptyPage
        title="No lesson content yet"
        description="Generation may still be running."
        actionLabel="View progress"
        onAction={openProgress}
      />
    );
  }

  return (
    <section className="mx-auto grid max-w-7xl grid-cols-1 gap-6 px-5 py-6 lg:grid-cols-[260px_minmax(0,1fr)_300px]">
      <aside className="space-y-4">
        <div>
          <div className="text-xs uppercase tracking-wide text-muted-foreground">Contents</div>
          <h2 className="mt-1 text-lg font-semibold">{sessionQuery.data?.tech_name ?? "Lesson"}</h2>
        </div>
        <nav className="space-y-4">
          {fallbackPoints.map((point, index) => (
            <div key={point.id} className="space-y-1">
              <button
                className={`block w-full text-left text-sm font-medium ${point.id === currentPoint?.id ? "text-foreground" : "text-muted-foreground hover:text-foreground"}`}
                onClick={() => {
                  setSelectedPointId(point.id);
                  setSelectedSection("compare");
                  setSubmission(null);
                }}
              >
                {index + 1}. {point.title}
              </button>
              <div className="ml-3 grid gap-1 border-l border-border pl-3">
                {(["compare", "practice", "reflect"] as LessonSection[]).map((section) => (
                  <button
                    key={section}
                    className={`text-left text-xs ${point.id === currentPoint?.id && selectedSection === section ? "text-foreground" : "text-muted-foreground hover:text-foreground"}`}
                    onClick={() => {
                      setSelectedPointId(point.id);
                      setSelectedSection(section);
                      setSubmission(null);
                    }}
                  >
                    {sectionLabels[section]}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </nav>
      </aside>

      <article className="space-y-8">
        <LessonSectionBlock title="Overview">
          <h1 className="text-2xl font-semibold tracking-tight">{currentPoint?.title}</h1>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">{currentPoint?.goal}</p>
          {currentPoint?.reason ? <p className="mt-2 text-sm leading-6 text-muted-foreground">{currentPoint.reason}</p> : null}
        </LessonSectionBlock>

        <LessonSectionBlock title="Baseline">
          <CodeBlock value={example?.baseline_example} />
          <p className="mt-3 text-sm text-muted-foreground">How this is typically handled without the target technology.</p>
        </LessonSectionBlock>

        <LessonSectionBlock title="Target">
          <CodeBlock value={example?.target_example} />
          <p className="mt-3 text-sm text-muted-foreground">How the target technology changes the shape of the solution.</p>
        </LessonSectionBlock>

        <LessonSectionBlock title="What to notice">
          <List items={example?.observe_questions ?? []} />
          {compareLevel?.task ? <MarkdownBlock>{compareLevel.task}</MarkdownBlock> : null}
        </LessonSectionBlock>

        <LessonSectionBlock title="Practice">
          <MarkdownBlock>{practiceLevel?.task ?? activeLevel?.task ?? "暂无练习题。"}</MarkdownBlock>
          <AnswerEditor value={practiceAnswer} onChange={setPracticeAnswer} height="240px" />
          <div className="mt-3">
            <Button
              disabled={!practiceLevel || !practiceAnswer.trim() || submitMutation.isPending}
              onClick={() => practiceLevel && submitMutation.mutate({ level: practiceLevel, answer: practiceAnswer, kind: "practice" })}
            >
              {submitMutation.isPending ? "Submitting..." : "Submit answer"}
            </Button>
          </div>
        </LessonSectionBlock>

        <LessonSectionBlock title="Reflection">
          <MarkdownBlock>{reflectionLevel?.task ?? "请用自己的话总结：普通写法和目标技术写法相比，结构、职责或使用时机发生了什么变化。"}</MarkdownBlock>
          <AnswerEditor value={reflectionAnswer} onChange={setReflectionAnswer} height="180px" />
          <div className="mt-3">
            <Button
              variant="outline"
              disabled={!reflectionLevel || !reflectionAnswer.trim() || submitMutation.isPending}
              onClick={() => reflectionLevel && submitMutation.mutate({ level: reflectionLevel, answer: reflectionAnswer, kind: "reflection" })}
            >
              Submit reflection
            </Button>
          </div>
        </LessonSectionBlock>

        {submitMutation.error ? <ErrorText error={submitMutation.error} /> : null}
        {submission ? <FeedbackPanel submission={submission} /> : null}
      </article>

      <aside className="space-y-5">
        <div>
          <div className="text-xs uppercase tracking-wide text-muted-foreground">Notes</div>
          <h2 className="mt-1 text-lg font-semibold">{sectionLabels[selectedSection]}</h2>
        </div>
        <NoteBlock title="Hint">
          <p>{activeLevel?.hint ?? practiceLevel?.hint ?? "No hint yet."}</p>
        </NoteBlock>
        <NoteBlock title="Acceptance criteria">
          <List items={activeLevel?.acceptance_criteria ?? practiceLevel?.acceptance_criteria ?? []} />
        </NoteBlock>
        <NoteBlock title="Common mistakes">
          <List items={activeLevel?.common_mistakes ?? practiceLevel?.common_mistakes ?? []} />
        </NoteBlock>
        <NoteBlock title="When to use">
          <List items={comparison?.when_to_use ?? []} />
        </NoteBlock>
        <NoteBlock title="When not to use">
          <List items={comparison?.when_not_to_use ?? []} />
        </NoteBlock>
        <Button variant="outline" className="w-full" onClick={openCard}>
          View technical card
        </Button>
      </aside>
    </section>
  );
}

function LearningCardPage({ sessionId, backToLesson }: { sessionId: number; backToLesson: () => void }) {
  const queryClient = useQueryClient();
  const cardQuery = useQuery({ queryKey: ["card", sessionId], queryFn: () => getLearningCard(sessionId), retry: false });
  const generateMutation = useMutation({
    mutationFn: () => generateLearningCard(sessionId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["card", sessionId] }),
  });
  const card = cardQuery.data ?? generateMutation.data;

  return (
    <section className="mx-auto max-w-4xl px-5 py-8">
      <div className="mb-8 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Technical card</h1>
          <p className="mt-2 text-sm text-muted-foreground">A compact document for review after the lesson.</p>
        </div>
        <Button variant="outline" onClick={backToLesson}>
          Back to lesson
        </Button>
      </div>

      {card ? (
        <CardDocument card={card} />
      ) : (
        <Card>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">No technical card has been generated yet.</p>
            {cardQuery.error ? <ErrorText error={cardQuery.error} /> : null}
            {generateMutation.error ? <ErrorText error={generateMutation.error} /> : null}
            <Button disabled={generateMutation.isPending} onClick={() => generateMutation.mutate()}>
              {generateMutation.isPending ? "Generating..." : "Generate technical card"}
            </Button>
          </CardContent>
        </Card>
      )}
    </section>
  );
}

function CardDocument({ card }: { card: LearningCard }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl">{card.tech_name}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-8">
        <DocumentField title="What it solves" value={card.pain_point} />
        <DocumentField title="Baseline solution" value={card.baseline_solution} />
        <DocumentField title="Why baseline becomes messy" value={card.target_advantage} />
        <DocumentField title="When to use" value={card.when_to_use} />
        <DocumentField title="When not to use" value={card.when_not_to_use} />
        <DocumentField title="Minimal example" value={card.minimal_example} />
        <DocumentField title="My understanding" value={card.my_understanding} />
      </CardContent>
    </Card>
  );
}

function FeatureLine({ title }: { title: string }) {
  return <div className="border-t border-border pt-3">{title}</div>;
}

function StepRow({ label, state }: { label: string; state: "done" | "active" | "pending" | "failed" }) {
  return (
    <div className="flex items-center justify-between border-b border-border py-3 last:border-b-0">
      <span className={state === "pending" ? "text-muted-foreground" : "text-foreground"}>{label}</span>
      <span className="text-xs text-muted-foreground">{state === "done" ? "Done" : state === "active" ? "In progress" : state === "failed" ? "Failed" : ""}</span>
    </div>
  );
}

function LessonSectionBlock({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="border-b border-border pb-8 last:border-b-0">
      <div className="mb-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</div>
      {children}
    </section>
  );
}

function NoteBlock({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="border-b border-border pb-4">
      <div className="mb-2 text-sm font-semibold">{title}</div>
      <div className="text-sm leading-6 text-muted-foreground">{children}</div>
    </section>
  );
}

function DocumentField({ title, value }: { title: string; value: string | string[] }) {
  return (
    <section>
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">{title}</h2>
      {Array.isArray(value) ? <List items={value} /> : <MarkdownBlock>{value || "暂无内容。"}</MarkdownBlock>}
    </section>
  );
}

function AnswerEditor({ value, onChange, height }: { value: string; onChange: (value: string) => void; height: string }) {
  return (
    <div className="mt-4 overflow-hidden rounded-md border border-border bg-white">
      <Editor
        height={height}
        defaultLanguage="markdown"
        theme="vs-light"
        value={value}
        onChange={(next) => onChange(next ?? "")}
        options={{ minimap: { enabled: false }, wordWrap: "on", fontSize: 14, scrollBeyondLastLine: false }}
      />
    </div>
  );
}

function CodeBlock({ value }: { value: string | null | undefined }) {
  return (
    <pre className="code-block overflow-auto rounded-md border border-border p-4 text-sm leading-6">
      <code>{value?.trim() || "暂无样例。"}</code>
    </pre>
  );
}

function FeedbackPanel({ submission }: { submission: SubmissionState }) {
  const result = submission.feedback.result;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Feedback: {result === "pass" ? "Pass" : result === "partial" ? "Partial" : "Needs work"}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <p className="text-muted-foreground">{submission.feedback.feedback || submission.message}</p>
        <div className="grid gap-4 md:grid-cols-3">
          <DocumentField title="Correct" value={submission.feedback.correct_points} />
          <DocumentField title="Missing" value={submission.feedback.missing_points} />
          <DocumentField title="Review" value={submission.feedback.suggested_review_points} />
        </div>
      </CardContent>
    </Card>
  );
}

function readableMessage(message: string | null | undefined, status: string) {
  if (status === "failed") return "Generation failed.";
  if (status === "partial") return "Some content is ready. You can start the lesson and continue from there.";
  if (readyStatuses.has(status)) return "Ready";
  return message ? messageText[message] ?? message : "Waiting for the generation task to start.";
}

function stepState(progress: number, start: number, end: number, status: string): "done" | "active" | "pending" | "failed" {
  if (status === "failed") return progress >= start && progress < end ? "failed" : progress >= end ? "done" : "pending";
  if (progress >= end || readyStatuses.has(status)) return "done";
  if (progress >= start) return "active";
  return "pending";
}

function sortLevels(levels: LearningLevel[]) {
  const order: Record<string, number> = { observe: 1, hands_on: 2, summary: 3 };
  return [...levels].sort((a, b) => (order[a.type] ?? 99) - (order[b.type] ?? 99) || a.sort_order - b.sort_order);
}

function findLevel(levels: LearningLevel[], type: string) {
  return levels.find((level) => level.type === type) ?? null;
}

function List({ items }: { items: string[] }) {
  if (!items.length) return <p>暂无内容。</p>;
  return (
    <ul className="space-y-1">
      {items.map((item, index) => (
        <li key={`${item}-${index}`}>{item}</li>
      ))}
    </ul>
  );
}

function MarkdownBlock({ children }: { children: string }) {
  return (
    <div className="markdown max-w-none text-foreground">
      <ReactMarkdown>{children}</ReactMarkdown>
    </div>
  );
}

function LoadingState({ label }: { label: string }) {
  return <div className="flex min-h-[320px] items-center justify-center text-sm text-muted-foreground">{label}</div>;
}

function EmptyPage({
  title,
  description,
  actionLabel,
  onAction,
}: {
  title: string;
  description: string;
  actionLabel: string;
  onAction: () => void;
}) {
  return (
    <section className="mx-auto max-w-xl px-5 py-12">
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">{description}</p>
          <Button onClick={onAction}>{actionLabel}</Button>
        </CardContent>
      </Card>
    </section>
  );
}

function ErrorText({ error }: { error: unknown }) {
  return <div className="rounded-md border border-border bg-white px-3 py-2 text-sm text-muted-foreground">{friendlyError(error)}</div>;
}

function friendlyError(error: unknown) {
  const message = error instanceof Error ? error.message : String(error);
  if (message.includes("No official source configured")) return "Official source is not configured for this technology.";
  if (message.includes("JSON") || message.includes("parse")) return "The generated content format was invalid. Please regenerate.";
  if (message.includes("timeout") || message.includes("running too long")) return "Generation is taking longer than expected.";
  return message;
}
