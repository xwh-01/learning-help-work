import { useMemo, useState } from "react";
import Editor from "@monaco-editor/react";
import ReactMarkdown from "react-markdown";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  ChevronRight,
  ClipboardCheck,
  Layers,
  Loader2,
  Send,
  Target,
} from "lucide-react";

import {
  createLearningSession,
  generateLearningCard,
  generatePracticeTask,
  getComparisons,
  getExamples,
  getFeedback,
  getKnowledgePoints,
  getLearningCard,
  getLearningSession,
  getLearningSessionStatus,
  getLevel,
  getLevels,
  getPracticeTask,
  submitAnswer,
} from "./api/learning";
import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./components/ui/card";
import { Input } from "./components/ui/input";
import { Textarea } from "./components/ui/textarea";
import type { FeedbackResult, KnowledgePoint, LearningLevel } from "./types/api";

type View = "create" | "progress" | "learn" | "practice" | "card";

const savedSessionId = Number(localStorage.getItem("techleveler.session_id") ?? 0) || null;

export default function App() {
  const [sessionId, setSessionId] = useState<number | null>(savedSessionId);
  const [view, setView] = useState<View>(savedSessionId ? "progress" : "create");

  const openSession = (nextSessionId: number, nextView: View) => {
    localStorage.setItem("techleveler.session_id", String(nextSessionId));
    setSessionId(nextSessionId);
    setView(nextView);
  };

  return (
    <main className="min-h-screen bg-background text-foreground">
      <TopBar sessionId={sessionId} view={view} setView={setView} reset={() => openSession(0, "create")} />
      {!sessionId || view === "create" ? (
        <CreateSessionPage onCreated={(id) => openSession(id, "progress")} />
      ) : view === "progress" ? (
        <ProgressPage sessionId={sessionId} onReady={() => setView("learn")} />
      ) : view === "learn" ? (
        <LearningWorkspacePage sessionId={sessionId} openPractice={() => setView("practice")} openCard={() => setView("card")} />
      ) : view === "practice" ? (
        <PracticePage sessionId={sessionId} />
      ) : (
        <LearningCardPage sessionId={sessionId} />
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
    <header className="sticky top-0 z-10 border-b border-border bg-background/95 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <Layers className="h-4 w-4" />
          </div>
          <div>
            <div className="text-sm font-semibold">TechLeveler</div>
            <div className="text-xs text-muted-foreground">Session {sessionId ?? "-"}</div>
          </div>
        </div>
        <nav className="flex items-center gap-1">
          {sessionId ? (
            <>
              <Button variant={view === "progress" ? "subtle" : "ghost"} size="sm" onClick={() => setView("progress")}>
                进度
              </Button>
              <Button variant={view === "learn" ? "subtle" : "ghost"} size="sm" onClick={() => setView("learn")}>
                学习
              </Button>
              <Button variant={view === "practice" ? "subtle" : "ghost"} size="sm" onClick={() => setView("practice")}>
                Boss
              </Button>
              <Button variant={view === "card" ? "subtle" : "ghost"} size="sm" onClick={() => setView("card")}>
                卡片
              </Button>
            </>
          ) : null}
          <Button variant="outline" size="sm" onClick={reset}>
            新建
          </Button>
        </nav>
      </div>
    </header>
  );
}

function CreateSessionPage({ onCreated }: { onCreated: (sessionId: number) => void }) {
  const [techName, setTechName] = useState("LangGraph");
  const [userLevel, setUserLevel] = useState("beginner");
  const [learningGoal, setLearningGoal] = useState("理解什么时候应该用目标技术，而不是普通写法。");
  const mutation = useMutation({
    mutationFn: createLearningSession,
    onSuccess: (data) => onCreated(data.session_id),
  });

  return (
    <section className="mx-auto grid max-w-5xl gap-6 px-4 py-8 lg:grid-cols-[1fr_360px]">
      <div className="space-y-5">
        <div>
          <h1 className="text-2xl font-semibold">开始一条技术学习链路</h1>
          <p className="mt-2 text-sm text-muted-foreground">输入目标技术后，后端会创建真实 session 并启动 Celery 生成任务。</p>
        </div>
        <Card>
          <CardHeader>
            <CardTitle>学习目标</CardTitle>
          </CardHeader>
          <CardContent>
            <form
              className="space-y-4"
              onSubmit={(event) => {
                event.preventDefault();
                mutation.mutate({ tech_name: techName, user_level: userLevel, learning_goal: learningGoal });
              }}
            >
              <label className="block space-y-2">
                <span className="text-sm font-medium">技术名</span>
                <Input value={techName} onChange={(event) => setTechName(event.target.value)} />
              </label>
              <label className="block space-y-2">
                <span className="text-sm font-medium">当前水平</span>
                <select
                  className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  value={userLevel}
                  onChange={(event) => setUserLevel(event.target.value)}
                >
                  <option value="beginner">beginner</option>
                  <option value="intermediate">intermediate</option>
                  <option value="advanced">advanced</option>
                </select>
              </label>
              <label className="block space-y-2">
                <span className="text-sm font-medium">学习目标</span>
                <Textarea value={learningGoal} onChange={(event) => setLearningGoal(event.target.value)} />
              </label>
              {mutation.error ? <ErrorText error={mutation.error} /> : null}
              <Button type="submit" disabled={mutation.isPending || !techName.trim()}>
                {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                开始学习
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
      <Card className="self-start">
        <CardHeader>
          <CardTitle>后端链路</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          {["官方资料", "技术边界", "知识点", "体感样例", "三类关卡"].map((item) => (
            <div key={item} className="flex items-center gap-2">
              <ChevronRight className="h-4 w-4 text-primary" />
              {item}
            </div>
          ))}
        </CardContent>
      </Card>
    </section>
  );
}

function ProgressPage({ sessionId, onReady }: { sessionId: number; onReady: () => void }) {
  const statusQuery = useQuery({
    queryKey: ["session-status", sessionId],
    queryFn: () => getLearningSessionStatus(sessionId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "ready" || status === "failed" || status === "levels_completed" ? false : 2000;
    },
  });
  const task = statusQuery.data?.task;
  const progress = task?.progress ?? 0;

  return (
    <section className="mx-auto max-w-4xl px-4 py-8">
      <Card>
        <CardHeader>
          <CardTitle>生成进度</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">{task?.message ?? "queued"}</span>
            <Badge>{statusQuery.data?.status ?? "loading"}</Badge>
          </div>
          <div className="h-3 overflow-hidden rounded-full bg-muted">
            <div className="h-full bg-primary transition-all" style={{ width: `${progress}%` }} />
          </div>
          <div className="text-sm text-muted-foreground">Progress {progress}%</div>
          {task?.error_message ? <ErrorText error={task.error_message} /> : null}
          <div className="flex gap-2">
            <Button onClick={onReady} disabled={statusQuery.data?.status !== "ready" && statusQuery.data?.status !== "levels_completed"}>
              <BookOpen className="h-4 w-4" />
              进入学习
            </Button>
            <Button variant="outline" onClick={() => statusQuery.refetch()}>
              刷新
            </Button>
          </div>
        </CardContent>
      </Card>
    </section>
  );
}

function LearningWorkspacePage({
  sessionId,
  openPractice,
  openCard,
}: {
  sessionId: number;
  openPractice: () => void;
  openCard: () => void;
}) {
  const queryClient = useQueryClient();
  const [selectedPointId, setSelectedPointId] = useState<number | null>(null);
  const [selectedLevelId, setSelectedLevelId] = useState<number | null>(null);
  const [answer, setAnswer] = useState("");
  const [lastFeedback, setLastFeedback] = useState<FeedbackResult | null>(null);

  const sessionQuery = useQuery({ queryKey: ["session", sessionId], queryFn: () => getLearningSession(sessionId) });
  const pointsQuery = useQuery({ queryKey: ["knowledge-points", sessionId], queryFn: () => getKnowledgePoints(sessionId) });
  const comparisonsQuery = useQuery({ queryKey: ["comparisons", sessionId], queryFn: () => getComparisons(sessionId) });

  const currentPoint = useMemo(() => {
    const points = pointsQuery.data ?? [];
    return (
      points.find((point) => point.id === selectedPointId) ??
      points.find((point) => point.id === sessionQuery.data?.current_knowledge_point_id) ??
      points.find((point) => point.category === "must_learn") ??
      points[0]
    );
  }, [pointsQuery.data, selectedPointId, sessionQuery.data?.current_knowledge_point_id]);

  const levelsQuery = useQuery({
    queryKey: ["levels", currentPoint?.id],
    queryFn: () => getLevels(currentPoint!.id),
    enabled: !!currentPoint,
  });
  const examplesQuery = useQuery({
    queryKey: ["examples", currentPoint?.id],
    queryFn: () => getExamples(currentPoint!.id),
    enabled: !!currentPoint,
  });

  const currentLevel = useMemo(() => {
    const levels = levelsQuery.data ?? [];
    return (
      levels.find((level) => level.id === selectedLevelId) ??
      levels.find((level) => level.id === sessionQuery.data?.current_level_id) ??
      levels[0]
    );
  }, [levelsQuery.data, selectedLevelId, sessionQuery.data?.current_level_id]);

  const submitMutation = useMutation({
    mutationFn: async () => {
      if (!currentLevel) throw new Error("No current level");
      const result = await submitAnswer(currentLevel.id, answer);
      return getFeedback(result.answer_id);
    },
    onSuccess: (feedback) => {
      setLastFeedback(feedback);
      setAnswer("");
      queryClient.invalidateQueries({ queryKey: ["session", sessionId] });
      queryClient.invalidateQueries({ queryKey: ["session-status", sessionId] });
    },
  });

  if (pointsQuery.isLoading || sessionQuery.isLoading) {
    return <LoadingState label="加载学习空间" />;
  }

  const points = pointsQuery.data ?? [];
  const comparison = comparisonsQuery.data?.[0];

  return (
    <section className="grid min-h-[calc(100vh-56px)] grid-cols-1 gap-4 px-4 py-4 lg:grid-cols-[280px_minmax(0,1fr)_340px]">
      <aside className="space-y-3">
        <PanelTitle icon={<Target className="h-4 w-4" />} title="知识点" />
        <div className="space-y-2">
          {points.map((point) => (
            <button
              key={point.id}
              className={`w-full rounded-md border px-3 py-2 text-left text-sm transition ${
                point.id === currentPoint?.id ? "border-primary bg-accent" : "border-border hover:bg-accent"
              }`}
              onClick={() => {
                setSelectedPointId(point.id);
                setSelectedLevelId(null);
                setLastFeedback(null);
              }}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium">{point.title}</span>
                <Badge>{point.category}</Badge>
              </div>
              <div className="mt-1 text-xs text-muted-foreground">{point.difficulty}</div>
            </button>
          ))}
        </div>
        <PanelTitle icon={<ClipboardCheck className="h-4 w-4" />} title="关卡" />
        <div className="space-y-2">
          {(levelsQuery.data ?? []).map((level) => (
            <Button
              key={level.id}
              className="w-full justify-start"
              variant={level.id === currentLevel?.id ? "subtle" : "outline"}
              onClick={() => {
                setSelectedLevelId(level.id);
                setLastFeedback(null);
              }}
            >
              {level.type}
            </Button>
          ))}
        </div>
      </aside>

      <section className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>{currentPoint?.title ?? "知识点"}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">{currentPoint?.goal}</p>
            <MarkdownBlock>{examplesMarkdown(examplesQuery.data ?? [])}</MarkdownBlock>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{currentLevel?.title ?? "当前关卡"}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <MarkdownBlock>{currentLevel?.task ?? ""}</MarkdownBlock>
            <div className="overflow-hidden rounded-md border border-border">
              <Editor
                height="180px"
                defaultLanguage="markdown"
                theme="vs-light"
                value={answer}
                onChange={(value) => setAnswer(value ?? "")}
                options={{ minimap: { enabled: false }, wordWrap: "on", fontSize: 13 }}
              />
            </div>
            {submitMutation.error ? <ErrorText error={submitMutation.error} /> : null}
            <Button disabled={!answer.trim() || submitMutation.isPending || !currentLevel} onClick={() => submitMutation.mutate()}>
              {submitMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              提交答案
            </Button>
            {lastFeedback ? <FeedbackPanel feedback={lastFeedback} /> : null}
          </CardContent>
        </Card>
      </section>

      <aside className="space-y-4">
        <SidePanel title="提示">
          <p>{currentLevel?.hint}</p>
        </SidePanel>
        <SidePanel title="验收标准">
          <List items={currentLevel?.acceptance_criteria ?? []} />
        </SidePanel>
        <SidePanel title="常见错误">
          <List items={currentLevel?.common_mistakes ?? []} />
        </SidePanel>
        <SidePanel title="技术边界">
          <p className="font-medium">同一个小任务</p>
          <p>{comparison?.comparison_task}</p>
          <p className="mt-3 font-medium">什么时候用</p>
          <List items={comparison?.when_to_use ?? []} />
          <p className="mt-3 font-medium">什么时候不用</p>
          <List items={comparison?.when_not_to_use ?? []} />
        </SidePanel>
        <div className="flex gap-2">
          <Button variant="outline" className="flex-1" onClick={openPractice}>
            Boss
          </Button>
          <Button variant="outline" className="flex-1" onClick={openCard}>
            卡片
          </Button>
        </div>
      </aside>
    </section>
  );
}

function PracticePage({ sessionId }: { sessionId: number }) {
  const queryClient = useQueryClient();
  const practiceQuery = useQuery({
    queryKey: ["practice", sessionId],
    queryFn: () => getPracticeTask(sessionId),
    retry: false,
  });
  const generateMutation = useMutation({
    mutationFn: () => generatePracticeTask(sessionId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["practice", sessionId] }),
  });
  const task = practiceQuery.data ?? generateMutation.data;

  return (
    <section className="mx-auto max-w-5xl px-4 py-6">
      <Card>
        <CardHeader>
          <CardTitle>实战 Boss</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {task ? (
            <PracticeTaskView task={task} />
          ) : (
            <>
              {practiceQuery.error ? <ErrorText error={practiceQuery.error} /> : null}
              {generateMutation.error ? <ErrorText error={generateMutation.error} /> : null}
              <Button onClick={() => generateMutation.mutate()} disabled={generateMutation.isPending}>
                {generateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Target className="h-4 w-4" />}
                生成实战题
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </section>
  );
}

function LearningCardPage({ sessionId }: { sessionId: number }) {
  const queryClient = useQueryClient();
  const cardQuery = useQuery({
    queryKey: ["card", sessionId],
    queryFn: () => getLearningCard(sessionId),
    retry: false,
  });
  const generateMutation = useMutation({
    mutationFn: () => generateLearningCard(sessionId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["card", sessionId] }),
  });
  const card = cardQuery.data ?? generateMutation.data;

  return (
    <section className="mx-auto max-w-5xl px-4 py-6">
      <Card>
        <CardHeader>
          <CardTitle>技术卡片</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {card ? (
            <MarkdownBlock>
              {card.card_markdown ??
                `# ${card.tech_name}\n\n## Pain Point\n${card.pain_point}\n\n## Minimal Example\n${card.minimal_example}`}
            </MarkdownBlock>
          ) : (
            <>
              {cardQuery.error ? <ErrorText error={cardQuery.error} /> : null}
              {generateMutation.error ? <ErrorText error={generateMutation.error} /> : null}
              <Button onClick={() => generateMutation.mutate()} disabled={generateMutation.isPending}>
                {generateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                生成技术卡片
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </section>
  );
}

function FeedbackPanel({ feedback }: { feedback: FeedbackResult }) {
  const color = feedback.result === "pass" ? "text-emerald-700" : feedback.result === "partial" ? "text-amber-700" : "text-red-700";
  return (
    <div className="rounded-md border border-border bg-muted p-3 text-sm">
      <div className={`mb-2 font-semibold ${color}`}>{feedback.result}</div>
      <p>{feedback.feedback}</p>
      <div className="mt-3 grid gap-3 md:grid-cols-3">
        <div>
          <div className="font-medium">正确点</div>
          <List items={feedback.correct_points} />
        </div>
        <div>
          <div className="font-medium">缺失点</div>
          <List items={feedback.missing_points} />
        </div>
        <div>
          <div className="font-medium">复习建议</div>
          <List items={feedback.suggested_review_points} />
        </div>
      </div>
    </div>
  );
}

function PracticeTaskView({ task }: { task: NonNullable<Awaited<ReturnType<typeof getPracticeTask>>> }) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">{task.title}</h2>
        <p className="mt-2 text-sm text-muted-foreground">{task.background}</p>
      </div>
      <SidePanel title="要求">
        <List items={task.task_requirements} />
      </SidePanel>
      <SidePanel title="普通方案 vs 目标技术方案">
        <p>{task.comparison_requirement}</p>
      </SidePanel>
      <SidePanel title="验收标准">
        <List items={task.acceptance_criteria} />
      </SidePanel>
      <SidePanel title="复盘问题">
        <List items={task.review_questions} />
      </SidePanel>
    </div>
  );
}

function examplesMarkdown(examples: { official_example: string | null; beginner_example: string | null; baseline_example: string | null; target_example: string | null }[]) {
  if (!examples.length) return "暂无样例。";
  const example = examples[0];
  return [
    "### 官方样例",
    example.official_example,
    "### 初学者样例",
    example.beginner_example,
    "### 普通写法",
    example.baseline_example,
    "### 目标技术写法",
    example.target_example,
  ]
    .filter(Boolean)
    .join("\n\n");
}

function SidePanel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm text-muted-foreground">{children}</CardContent>
    </Card>
  );
}

function PanelTitle({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <div className="flex items-center gap-2 text-sm font-semibold">
      {icon}
      {title}
    </div>
  );
}

function List({ items }: { items: string[] }) {
  if (!items.length) return <p className="text-sm text-muted-foreground">暂无</p>;
  return (
    <ul className="space-y-1">
      {items.map((item, index) => (
        <li key={`${item}-${index}`} className="text-sm text-muted-foreground">
          {item}
        </li>
      ))}
    </ul>
  );
}

function MarkdownBlock({ children }: { children: string }) {
  return (
    <div className="prose prose-sm max-w-none text-foreground prose-pre:overflow-x-auto prose-pre:rounded-md prose-pre:bg-muted prose-pre:p-3">
      <ReactMarkdown>{children}</ReactMarkdown>
    </div>
  );
}

function LoadingState({ label }: { label: string }) {
  return (
    <div className="flex min-h-[320px] items-center justify-center gap-2 text-sm text-muted-foreground">
      <Loader2 className="h-4 w-4 animate-spin" />
      {label}
    </div>
  );
}

function ErrorText({ error }: { error: unknown }) {
  return (
    <div className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
      <AlertCircle className="mt-0.5 h-4 w-4 flex-none" />
      <span>{error instanceof Error ? error.message : String(error)}</span>
    </div>
  );
}
