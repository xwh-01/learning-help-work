import { type ReactNode, useMemo, useState } from "react";
import Editor from "@monaco-editor/react";
import ReactMarkdown from "react-markdown";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  ChevronRight,
  Circle,
  ClipboardCheck,
  FileText,
  Layers,
  Loader2,
  Play,
  RotateCw,
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
  listLearningSessions,
  submitAnswer,
} from "./api/learning";
import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./components/ui/card";
import { Input } from "./components/ui/input";
import { Textarea } from "./components/ui/textarea";
import type { FeedbackResult, LearningExample, LearningLevel, PracticeTask } from "./types/api";

type View = "create" | "progress" | "learn" | "practice" | "card";

type LastSubmission = {
  result: "pass" | "partial" | "fail";
  message: string;
  nextLevelId: number | null;
};

const SESSION_KEY = "techleveler.session_id";
const savedSessionId = Number(localStorage.getItem(SESSION_KEY) ?? 0) || null;
const readyStatuses = new Set(["ready", "levels_completed", "completed"]);

const generationSteps = [
  { title: "官方资料", detail: "抓取官方来源并提取正文", start: 0, end: 20 },
  { title: "技术边界", detail: "生成普通方案 vs 目标技术对比", start: 20, end: 40 },
  { title: "知识点拆解", detail: "规划 must_learn / advanced_later / skip_now", start: 40, end: 60 },
  { title: "体感样例", detail: "为每个必学知识点生成短样例", start: 60, end: 80 },
  { title: "三类关卡", detail: "生成观察、动手、总结关", start: 80, end: 100 },
];

export default function App() {
  const [sessionId, setSessionId] = useState<number | null>(savedSessionId);
  const [view, setView] = useState<View>(savedSessionId ? "progress" : "create");

  const openSession = (nextSessionId: number, nextView: View) => {
    localStorage.setItem(SESSION_KEY, String(nextSessionId));
    setSessionId(nextSessionId);
    setView(nextView);
  };

  const resetSession = () => {
    localStorage.removeItem(SESSION_KEY);
    setSessionId(null);
    setView("create");
  };

  return (
    <main className="min-h-screen bg-background text-foreground">
      <TopBar sessionId={sessionId} view={view} setView={setView} reset={resetSession} />
      {!sessionId || view === "create" ? (
        <CreateSessionPage onCreated={(id) => openSession(id, "progress")} onOpened={(id) => openSession(id, "progress")} />
      ) : view === "progress" ? (
        <ProgressPage sessionId={sessionId} onReady={() => setView("learn")} />
      ) : view === "learn" ? (
        <LearningWorkspacePage
          sessionId={sessionId}
          openProgress={() => setView("progress")}
          openPractice={() => setView("practice")}
          openCard={() => setView("card")}
        />
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
    <header className="sticky top-0 z-20 border-b border-border bg-background/95 backdrop-blur">
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

function CreateSessionPage({
  onCreated,
  onOpened,
}: {
  onCreated: (sessionId: number) => void;
  onOpened: (sessionId: number) => void;
}) {
  const [techName, setTechName] = useState("LangGraph");
  const [userLevel, setUserLevel] = useState("beginner");
  const [learningGoal, setLearningGoal] = useState("理解什么时候应该使用目标技术，而不是普通写法。");
  const [existingSessionId, setExistingSessionId] = useState("");

  const createMutation = useMutation({
    mutationFn: createLearningSession,
    onSuccess: (data) => onCreated(data.session_id),
  });
  const openMutation = useMutation({
    mutationFn: async (id: number) => getLearningSession(id),
    onSuccess: (session) => onOpened(session.id),
  });
  const sessionsQuery = useQuery({ queryKey: ["learning-sessions"], queryFn: () => listLearningSessions(20) });

  return (
    <section className="mx-auto grid max-w-6xl gap-5 px-4 py-6 lg:grid-cols-[minmax(0,1fr)_360px]">
      <div className="space-y-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold">开始一条真实学习链路</h1>
          <p className="text-sm text-muted-foreground">创建后后端会立即返回 session_id，LLM 生成会在 Celery worker 里异步执行。</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>新建 Session</CardTitle>
          </CardHeader>
          <CardContent>
            <form
              className="space-y-4"
              onSubmit={(event) => {
                event.preventDefault();
                createMutation.mutate({ tech_name: techName.trim(), user_level: userLevel, learning_goal: learningGoal.trim() });
              }}
            >
              <label className="block space-y-2">
                <span className="text-sm font-medium">技术名</span>
                <Input value={techName} onChange={(event) => setTechName(event.target.value)} placeholder="例如 LangGraph / Redis" />
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
                <Textarea value={learningGoal} onChange={(event) => setLearningGoal(event.target.value)} rows={4} />
              </label>
              {createMutation.error ? <ErrorText error={createMutation.error} /> : null}
              <Button type="submit" disabled={createMutation.isPending || !techName.trim() || !learningGoal.trim()}>
                {createMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                开始生成
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>

      <aside className="space-y-4">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-2">
              <CardTitle>已有 Session</CardTitle>
              <Button variant="ghost" size="sm" onClick={() => sessionsQuery.refetch()} disabled={sessionsQuery.isFetching}>
                <RotateCw className={`h-4 w-4 ${sessionsQuery.isFetching ? "animate-spin" : ""}`} />
                刷新
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">从数据库读取最近的学习记录，点一条就能打开。</p>
            <div className="max-h-72 space-y-2 overflow-y-auto pr-1">
              {sessionsQuery.isLoading ? (
                <LoadingState label="正在读取 Session" />
              ) : sessionsQuery.error ? (
                <ErrorText error={sessionsQuery.error} />
              ) : sessionsQuery.data?.length ? (
                sessionsQuery.data.map((session) => (
                  <button
                    key={session.id}
                    className="w-full rounded-md border border-border px-3 py-2 text-left text-sm transition hover:bg-accent"
                    onClick={() => onOpened(session.id)}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium">#{session.id} {session.tech_name}</span>
                      <Badge>{session.status}</Badge>
                    </div>
                    <div className="mt-1 line-clamp-1 text-xs text-muted-foreground">{session.learning_goal ?? "无学习目标"}</div>
                    <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted">
                      <div className="h-full bg-primary" style={{ width: `${session.task?.progress ?? 0}%` }} />
                    </div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      {session.task?.message ?? "无任务信息"} · {new Date(session.updated_at).toLocaleString()}
                    </div>
                  </button>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">数据库里暂时没有 Session。</p>
              )}
            </div>
            <div className="border-t border-border pt-3">
              <p className="mb-2 text-sm text-muted-foreground">也可以手动输入 session_id。</p>
              <div className="flex gap-2">
                <Input
                  inputMode="numeric"
                  value={existingSessionId}
                  onChange={(event) => setExistingSessionId(event.target.value)}
                  placeholder="例如 3"
                />
                <Button
                  variant="outline"
                  disabled={openMutation.isPending || !Number(existingSessionId)}
                  onClick={() => openMutation.mutate(Number(existingSessionId))}
                >
                  {openMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <ChevronRight className="h-4 w-4" />}
                  打开
                </Button>
              </div>
            </div>
            {openMutation.error ? <ErrorText error={openMutation.error} /> : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>生成链路</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            {generationSteps.map((step) => (
              <div key={step.title} className="flex items-start gap-2">
                <Circle className="mt-0.5 h-4 w-4 text-primary" />
                <div>
                  <div className="font-medium text-foreground">{step.title}</div>
                  <div>{step.detail}</div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </aside>
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
  const progress = task?.progress ?? 0;
  const status = statusQuery.data?.status ?? "loading";
  const isReady = readyStatuses.has(status);

  return (
    <section className="mx-auto max-w-5xl px-4 py-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Session {sessionId} 生成进度</h1>
          <p className="text-sm text-muted-foreground">{task?.message ?? "等待 worker 更新任务状态"}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => statusQuery.refetch()} disabled={statusQuery.isFetching}>
            <RotateCw className={`h-4 w-4 ${statusQuery.isFetching ? "animate-spin" : ""}`} />
            刷新
          </Button>
          <Button onClick={onReady} disabled={!isReady}>
            <BookOpen className="h-4 w-4" />
            进入学习
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="space-y-5">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">当前状态</span>
            <Badge>{status}</Badge>
          </div>
          <div className="h-3 overflow-hidden rounded-full bg-muted">
            <div className="h-full bg-primary transition-all" style={{ width: `${Math.max(0, Math.min(progress, 100))}%` }} />
          </div>
          <div className="grid gap-3 md:grid-cols-5">
            {generationSteps.map((step) => (
              <ProgressStep key={step.title} title={step.title} detail={step.detail} state={stepState(progress, step.start, step.end, status)} />
            ))}
          </div>
          {task ? (
            <div className="rounded-md border border-border bg-muted/60 p-3 text-xs text-muted-foreground">
              <div>task_id: {task.task_id}</div>
              <div>task_status: {task.status}</div>
              <div>progress: {task.progress}%</div>
              {task.error_message ? <div className="mt-2 text-red-700">error: {task.error_message}</div> : null}
            </div>
          ) : null}
          {status === "failed" ? <ErrorText error={task?.error_message ?? "生成任务失败，请查看 backend / celery 日志"} /> : null}
        </CardContent>
      </Card>
    </section>
  );
}

function LearningWorkspacePage({
  sessionId,
  openProgress,
  openPractice,
  openCard,
}: {
  sessionId: number;
  openProgress: () => void;
  openPractice: () => void;
  openCard: () => void;
}) {
  const queryClient = useQueryClient();
  const [selectedPointId, setSelectedPointId] = useState<number | null>(null);
  const [selectedLevelId, setSelectedLevelId] = useState<number | null>(null);
  const [answer, setAnswer] = useState("");
  const [lastFeedback, setLastFeedback] = useState<FeedbackResult | null>(null);
  const [lastSubmission, setLastSubmission] = useState<LastSubmission | null>(null);

  const sessionQuery = useQuery({ queryKey: ["session", sessionId], queryFn: () => getLearningSession(sessionId) });
  const statusQuery = useQuery({ queryKey: ["session-status", sessionId], queryFn: () => getLearningSessionStatus(sessionId), refetchInterval: 5000 });
  const pointsQuery = useQuery({ queryKey: ["knowledge-points", sessionId], queryFn: () => getKnowledgePoints(sessionId) });
  const comparisonsQuery = useQuery({ queryKey: ["comparisons", sessionId], queryFn: () => getComparisons(sessionId), retry: false });

  const points = pointsQuery.data ?? [];
  const mustLearnPoints = points.filter((point) => point.category === "must_learn");
  const currentPoint = useMemo(() => {
    return (
      points.find((point) => point.id === selectedPointId) ??
      points.find((point) => point.id === sessionQuery.data?.current_knowledge_point_id) ??
      points.find((point) => point.category === "must_learn") ??
      points[0]
    );
  }, [points, selectedPointId, sessionQuery.data?.current_knowledge_point_id]);

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

  const levels = levelsQuery.data ?? [];
  const currentLevel = useMemo(() => {
    return (
      levels.find((level) => level.id === selectedLevelId) ??
      levels.find((level) => level.id === sessionQuery.data?.current_level_id) ??
      levels[0]
    );
  }, [levels, selectedLevelId, sessionQuery.data?.current_level_id]);

  const submitMutation = useMutation({
    mutationFn: async () => {
      if (!currentLevel) throw new Error("当前没有可提交的关卡");
      const submission = await submitAnswer(currentLevel.id, answer);
      const feedback = await getFeedback(submission.answer_id);
      const nextLevel = submission.next_level_id ? await getLevel(submission.next_level_id) : null;
      return { submission, feedback, nextLevel };
    },
    onSuccess: ({ submission, feedback, nextLevel }) => {
      setLastFeedback(feedback);
      setLastSubmission({ result: submission.result, message: submission.message, nextLevelId: submission.next_level_id });
      if (submission.result === "pass") {
        setAnswer("");
        if (nextLevel) {
          setSelectedPointId(nextLevel.knowledge_point_id);
          setSelectedLevelId(nextLevel.id);
        }
      }
      queryClient.invalidateQueries({ queryKey: ["session", sessionId] });
      queryClient.invalidateQueries({ queryKey: ["session-status", sessionId] });
      queryClient.invalidateQueries({ queryKey: ["knowledge-points", sessionId] });
    },
  });

  if (pointsQuery.isLoading || sessionQuery.isLoading) {
    return <LoadingState label="正在加载学习工作台" />;
  }

  if (!points.length) {
    return (
      <EmptyPage
        title="还没有知识点"
        description="这个 Session 可能仍在生成中。请先回到进度页观察 Celery 任务状态。"
        actionLabel="查看进度"
        onAction={openProgress}
      />
    );
  }

  const status = statusQuery.data?.status ?? sessionQuery.data?.status ?? "unknown";
  const comparison = comparisonsQuery.data?.[0];

  return (
    <section className="grid min-h-[calc(100vh-56px)] grid-cols-1 gap-4 px-4 py-4 lg:grid-cols-[300px_minmax(0,1fr)_360px]">
      <aside className="space-y-3">
        <StatusStrip status={status} message={statusQuery.data?.task?.message ?? null} />
        <PanelTitle icon={<Target className="h-4 w-4" />} title={`知识点 ${mustLearnPoints.length || points.length} 个`} />
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
                setLastSubmission(null);
              }}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium">{point.sort_order}. {point.title}</span>
                <Badge>{point.category ?? "unknown"}</Badge>
              </div>
              <div className="mt-1 line-clamp-2 text-xs text-muted-foreground">{point.reason ?? point.goal}</div>
            </button>
          ))}
        </div>
        <PanelTitle icon={<ClipboardCheck className="h-4 w-4" />} title="当前知识点关卡" />
        <div className="grid gap-2">
          {levels.map((level) => (
            <Button
              key={level.id}
              className="justify-start"
              variant={level.id === currentLevel?.id ? "subtle" : "outline"}
              onClick={() => {
                setSelectedLevelId(level.id);
                setLastFeedback(null);
                setLastSubmission(null);
              }}
            >
              <LevelTypeLabel type={level.type} />
              {level.title}
            </Button>
          ))}
        </div>
      </aside>

      <section className="space-y-4">
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <CardTitle className="text-base">{currentPoint?.title ?? "知识点"}</CardTitle>
              <Badge>{currentPoint?.difficulty ?? "difficulty"}</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">{currentPoint?.goal}</p>
            {currentPoint?.depends_on?.length ? (
              <div className="text-xs text-muted-foreground">依赖：{currentPoint.depends_on.join(" / ")}</div>
            ) : null}
            <MarkdownBlock>{examplesMarkdown(examplesQuery.data ?? [])}</MarkdownBlock>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <CardTitle className="text-base">{currentLevel?.title ?? "当前关卡"}</CardTitle>
              {currentLevel ? <Badge><LevelTypeLabel type={currentLevel.type} /></Badge> : null}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <MarkdownBlock>{currentLevel?.task ?? "暂无关卡任务"}</MarkdownBlock>
            <div>
              <div className="mb-2 flex items-center justify-between">
                <label className="text-sm font-medium">答题区</label>
                <span className="text-xs text-muted-foreground">支持文字、代码和 Markdown</span>
              </div>
              <div className="overflow-hidden rounded-md border border-border">
                <Editor
                  height="260px"
                  defaultLanguage="markdown"
                  theme="vs-light"
                  value={answer}
                  onChange={(value) => setAnswer(value ?? "")}
                  options={{ minimap: { enabled: false }, wordWrap: "on", fontSize: 14, scrollBeyondLastLine: false }}
                />
              </div>
            </div>
            {submitMutation.error ? <ErrorText error={submitMutation.error} /> : null}
            <div className="flex flex-wrap gap-2">
              <Button disabled={!answer.trim() || submitMutation.isPending || !currentLevel} onClick={() => submitMutation.mutate()}>
                {submitMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                提交答案
              </Button>
              <Button variant="outline" onClick={() => setAnswer("")} disabled={!answer}>
                清空
              </Button>
            </div>
            {lastSubmission ? <SubmissionMessage submission={lastSubmission} /> : null}
            {lastFeedback ? <FeedbackPanel feedback={lastFeedback} /> : null}
          </CardContent>
        </Card>
      </section>

      <aside className="space-y-4">
        <SidePanel title="提示">
          <p>{currentLevel?.hint ?? "暂无提示"}</p>
        </SidePanel>
        <SidePanel title="验收标准">
          <List items={currentLevel?.acceptance_criteria ?? []} />
        </SidePanel>
        <SidePanel title="常见错误">
          <List items={currentLevel?.common_mistakes ?? []} />
        </SidePanel>
        <SidePanel title="技术边界">
          <p className="font-medium text-foreground">同一个小任务</p>
          <p>{comparison?.comparison_task ?? "暂无对比结果"}</p>
          <p className="mt-3 font-medium text-foreground">什么时候用</p>
          <List items={comparison?.when_to_use ?? []} />
          <p className="mt-3 font-medium text-foreground">什么时候不用</p>
          <List items={comparison?.when_not_to_use ?? []} />
        </SidePanel>
        <div className="grid grid-cols-2 gap-2">
          <Button variant="outline" onClick={openPractice}>
            <Target className="h-4 w-4" />
            Boss 题
          </Button>
          <Button variant="outline" onClick={openCard}>
            <FileText className="h-4 w-4" />
            卡片
          </Button>
        </div>
      </aside>
    </section>
  );
}

function PracticePage({ sessionId }: { sessionId: number }) {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState(localStorage.getItem(`techleveler.practice_draft.${sessionId}`) ?? "");
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

  const saveDraft = (value: string) => {
    setDraft(value);
    localStorage.setItem(`techleveler.practice_draft.${sessionId}`, value);
  };

  return (
    <section className="mx-auto grid max-w-6xl gap-4 px-4 py-6 lg:grid-cols-[minmax(0,1fr)_420px]">
      <Card>
        <CardHeader>
          <CardTitle>实战 Boss 题</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {task ? (
            <PracticeTaskView task={task} />
          ) : (
            <>
              <p className="text-sm text-muted-foreground">当 must_learn 关卡全部通过后，可以生成实战题。</p>
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

      <Card>
        <CardHeader>
          <CardTitle>实战草稿区</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">这里先作为本地草稿保存，后端目前没有实战题提交接口。</p>
          <div className="overflow-hidden rounded-md border border-border">
            <Editor
              height="520px"
              defaultLanguage="markdown"
              theme="vs-light"
              value={draft}
              onChange={(value) => saveDraft(value ?? "")}
              options={{ minimap: { enabled: false }, wordWrap: "on", fontSize: 14, scrollBeyondLastLine: false }}
            />
          </div>
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
                `# ${card.tech_name}\n\n## 痛点\n${card.pain_point}\n\n## 普通方案\n${card.baseline_solution}\n\n## 目标技术优势\n${card.target_advantage}\n\n## 最小样例\n${card.minimal_example}\n\n## 我的理解\n${card.my_understanding}`}
            </MarkdownBlock>
          ) : (
            <>
              <p className="text-sm text-muted-foreground">完成学习和实战后，可以生成个人技术卡片。</p>
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

function ProgressStep({ title, detail, state }: { title: string; detail: string; state: "done" | "active" | "pending" | "failed" }) {
  const icon =
    state === "done" ? (
      <CheckCircle2 className="h-4 w-4 text-emerald-700" />
    ) : state === "active" ? (
      <Loader2 className="h-4 w-4 animate-spin text-primary" />
    ) : state === "failed" ? (
      <AlertCircle className="h-4 w-4 text-red-700" />
    ) : (
      <Circle className="h-4 w-4 text-muted-foreground" />
    );
  return (
    <div className="rounded-md border border-border p-3">
      <div className="mb-2 flex items-center gap-2 text-sm font-medium">
        {icon}
        {title}
      </div>
      <p className="text-xs text-muted-foreground">{detail}</p>
    </div>
  );
}

function stepState(progress: number, start: number, end: number, status: string): "done" | "active" | "pending" | "failed" {
  if (status === "failed") return progress >= start && progress < end ? "failed" : progress >= end ? "done" : "pending";
  if (progress >= end) return "done";
  if (progress >= start) return "active";
  return "pending";
}

function StatusStrip({ status, message }: { status: string; message: string | null }) {
  return (
    <div className="rounded-md border border-border bg-muted/50 px-3 py-2 text-sm">
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium">状态</span>
        <Badge>{status}</Badge>
      </div>
      {message ? <p className="mt-1 text-xs text-muted-foreground">{message}</p> : null}
    </div>
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

function SubmissionMessage({ submission }: { submission: LastSubmission }) {
  return (
    <div className="rounded-md border border-border px-3 py-2 text-sm">
      <div className="font-medium">提交结果：{submission.result}</div>
      <div className="mt-1 text-muted-foreground">{submission.message}</div>
      {submission.result === "pass" && submission.nextLevelId ? (
        <div className="mt-1 text-xs text-muted-foreground">已进入下一关：Level {submission.nextLevelId}</div>
      ) : null}
    </div>
  );
}

function PracticeTaskView({ task }: { task: PracticeTask }) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">{task.title}</h2>
        <p className="mt-2 text-sm text-muted-foreground">{task.background}</p>
      </div>
      <SidePanel title="必须覆盖的知识点">
        <List items={task.required_points} />
      </SidePanel>
      <SidePanel title="任务要求">
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

function examplesMarkdown(examples: LearningExample[]) {
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
    example.observe_questions?.length ? `### 观察问题\n${example.observe_questions.map((question) => `- ${question}`).join("\n")}` : null,
  ]
    .filter(Boolean)
    .join("\n\n");
}

function SidePanel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm text-muted-foreground">{children}</CardContent>
    </Card>
  );
}

function PanelTitle({ icon, title }: { icon: ReactNode; title: string }) {
  return (
    <div className="flex items-center gap-2 text-sm font-semibold">
      {icon}
      {title}
    </div>
  );
}

function LevelTypeLabel({ type }: { type: string }) {
  const labels: Record<string, string> = {
    observe: "体感关",
    hands_on: "动手关",
    summary: "总结关",
  };
  return <span>{labels[type] ?? type}</span>;
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
    <div className="markdown max-w-none text-foreground">
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
    <section className="mx-auto max-w-xl px-4 py-12">
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">{description}</p>
          <Button onClick={onAction}>{actionLabel}</Button>
        </CardContent>
      </Card>
    </section>
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
