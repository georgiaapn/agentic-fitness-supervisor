"use client";

import {
  Activity,
  AlertCircle,
  Apple,
  CalendarCheck,
  CheckCircle2,
  ClipboardCheck,
  Download,
  Dumbbell,
  Eye,
  EyeOff,
  Gauge,
  HeartPulse,
  KeyRound,
  Loader2,
  LogOut,
  Moon,
  NotebookTabs,
  Save,
  Sparkles,
  Timer,
  Trash2,
  User,
  X
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

type RecoveryStatus = "GREEN" | "YELLOW" | "RED";
type DialogMode = "none" | "profile" | "plans" | "checkin" | "briefing" | "workout" | "nutrition";
type ActiveAction = "workout" | "nutrition" | "checkin" | null;
type ToastMessage = {
  tone: "info" | "success" | "error";
  message: string;
};

type RagContext = Array<{
  source: string;
  title: string;
  snippet: string;
  score: number;
}>;

type WearableSnapshot = {
  sleep_hours: number;
  sleep_score: number;
  resting_heart_rate: number;
  blood_oxygen_level: number;
  step_count: number;
  activity_level: string;
  stress_level: number;
  soreness_quads: number;
  soreness_upper: number;
  energy_level: number;
  pain_level: number;
  available_minutes: number;
};

type DailyBriefing = {
  profile: {
    user_id?: string;
    name: string;
    age: number;
    gender?: string;
    height_cm?: number;
    weight_kg?: number;
    fitness_level: string;
    goal: string;
    dietary_restrictions?: string[];
    equipment_available?: string[];
    injury_history?: string[];
  };
  wearable: WearableSnapshot;
  current_day?: string | null;
  baseline_workout?: WeeklyDayPlan | null;
  baseline_nutrition?: {
    day: string;
    focus: string;
    meals: WeeklyNutritionMeal[];
  } | null;
  recovery: {
    status: RecoveryStatus;
    readiness_score: number;
    summary: string;
    constraints: string[];
  };
  directives: {
    selected_agents: string[];
    skipped_agents: string[];
    trainer_directive: string;
    nutritionist_directive: string;
    rationale: string;
  };
  workout: PlanResponse | null;
  nutrition: NutritionResponse | null;
  audit: Array<{
    agent: string;
    decision: string;
    evidence: string[];
  }>;
  final_message: string;
};

type PlanResponse = {
  title: string;
  duration_minutes: number;
  intensity: string;
  blocks: string[];
  notes: string[];
  rag_context?: RagContext;
};

type WeeklyWorkoutExercise = {
  name: string;
  prescription: string;
  notes?: string | null;
};

type WeeklyWorkoutDay = {
  day: string;
  title: string;
  exercises: WeeklyWorkoutExercise[];
};

type WeeklyWorkoutResponse = {
  title: string;
  duration_minutes: number;
  intensity: string;
  days: WeeklyWorkoutDay[];
  notes: string[];
  rag_context?: RagContext;
};

type NutritionResponse = {
  title: string;
  calorie_target: number;
  protein_g: number;
  meals: string[];
  notes: string[];
  rag_context?: RagContext;
};

type WeeklyNutritionMeal = {
  meal_type: string;
  name: string;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
};

type WeeklyNutritionDay = {
  day: string;
  focus: string;
  meals: WeeklyNutritionMeal[];
};

type WeeklyNutritionResponse = {
  title: string;
  daily_calorie_target: number;
  daily_protein_g: number;
  days: WeeklyNutritionDay[];
  notes: string[];
  rag_context?: RagContext;
};

type SavedGeneratedPlan = {
  id: string;
  user_id: string;
  plan_type: "weekly_workout" | "weekly_nutrition" | string;
  title: string;
  payload: Record<string, unknown>;
  updated_at: string;
};

type SavedDailyAdjustment = {
  id: string;
  user_id: string;
  adjustment_date: string;
  current_day: string;
  recovery_status: RecoveryStatus;
  readiness_score: number;
  title: string;
  payload: Record<string, unknown>;
  updated_at: string;
};

type UserProfile = Required<DailyBriefing["profile"]>;
type MorningSelfReport = {
  soreness_quads: number;
  soreness_upper: number;
  pain_level: number;
  available_minutes: number;
};

type WeeklyDayPlan = {
  day: string;
  title: string;
  details: string[];
};

const weekDays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

const fallbackProfile: UserProfile = {
  user_id: "demo-user",
  name: "George",
  age: 31,
  gender: "male",
  height_cm: 178,
  weight_kg: 82,
  fitness_level: "intermediate",
  goal: "hypertrophy",
  dietary_restrictions: ["no shellfish"],
  equipment_available: ["barbell", "dumbbells", "bands"],
  injury_history: ["occasional right knee irritation"]
};

const fallbackWearable: WearableSnapshot = {
  sleep_hours: 5,
  sleep_score: 42,
  resting_heart_rate: 72,
  blood_oxygen_level: 98,
  step_count: 5450,
  activity_level: "moderately_active",
  stress_level: 7,
  soreness_quads: 8,
  soreness_upper: 3,
  energy_level: 4,
  pain_level: 3,
  available_minutes: 35
};

const fallbackBriefing: DailyBriefing = {
  profile: fallbackProfile,
  wearable: fallbackWearable,
  current_day: "Monday",
  baseline_workout: null,
  baseline_nutrition: null,
  recovery: {
    status: "RED",
    readiness_score: 18,
    summary: "High fatigue detected from low sleep and quad soreness.",
    constraints: [
      "Avoid heavy compound lifting after low sleep readiness.",
      "Block heavy lower-body loading and quad-dominant volume."
    ]
  },
  directives: {
    selected_agents: ["trainer", "nutritionist"],
    skipped_agents: [],
    trainer_directive: "Replace planned heavy lower-body training with a 30 minute mobility session.",
    nutritionist_directive:
      "Reduce calories slightly for lower activity while keeping protein high and meals recovery-focused.",
    rationale: "User goal is hypertrophy; recovery status is RED with readiness 18."
  },
  workout: {
    title: "Lower-body recovery mobility",
    duration_minutes: 30,
    intensity: "low",
    blocks: [
      "5 min nasal-breathing walk or easy bike",
      "2 rounds: cat-cow x 8, 90/90 hip switches x 8 per side",
      "2 rounds: couch stretch 45 sec per side, ankle rocks x 12 per side",
      "3 min downshift breathing"
    ],
    notes: ["No heavy squats, lunges, leg press, or deadlifts today."]
  },
  nutrition: {
    title: "Recovery-focused nutrition day",
    calorie_target: 2602,
    protein_g: 147,
    meals: [
      "Greek yogurt bowl with berries, oats, walnuts, and cinnamon",
      "Chicken or tofu grain bowl with leafy greens, olive oil, and legumes",
      "Salmon or lentil dinner with potatoes and roasted vegetables"
    ],
    notes: ["Keep hydration steady and keep protein evenly distributed."]
  },
  audit: [
    {
      agent: "recovery",
      decision: "Classified recovery as RED.",
      evidence: ["sleep_score=42", "soreness_quads=8", "readiness_score=18"]
    },
    {
      agent: "supervisor",
      decision: "Blocked heavy lower-body work and issued specialist directives.",
      evidence: ["Low sleep readiness", "High quad soreness"]
    }
  ],
  final_message:
    "Your plan was adjusted for recovery today. Heavy lower-body work is blocked, mobility is prioritized, and nutrition stays protein-forward."
};

export default function Home() {
  const [profile, setProfile] = useState<UserProfile>(fallbackProfile);
  const [selfReport, setSelfReport] = useState<MorningSelfReport>({
    soreness_quads: fallbackWearable.soreness_quads,
    soreness_upper: fallbackWearable.soreness_upper,
    pain_level: fallbackWearable.pain_level,
    available_minutes: fallbackWearable.available_minutes
  });
  const [briefing, setBriefing] = useState<DailyBriefing>(fallbackBriefing);
  const [workoutPlan, setWorkoutPlan] = useState<WeeklyWorkoutResponse | null>(null);
  const [nutritionPlan, setNutritionPlan] = useState<WeeklyNutritionResponse | null>(null);
  const [savedPlans, setSavedPlans] = useState<SavedGeneratedPlan[]>([]);
  const [savedDailyAdjustments, setSavedDailyAdjustments] = useState<SavedDailyAdjustment[]>([]);
  const [dialogMode, setDialogMode] = useState<DialogMode>("none");
  const [runState, setRunState] = useState<"idle" | "running" | "completed" | "failed">("idle");
  const [activeAction, setActiveAction] = useState<ActiveAction>(null);
  const [dailyAdjustmentState, setDailyAdjustmentState] = useState<"idle" | "saving" | "saved" | "failed">("idle");
  const [profileState, setProfileState] = useState<"idle" | "saving" | "saved" | "failed">("idle");
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<ToastMessage | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [geminiApiKey, setGeminiApiKey] = useState("");
  const [geminiKeyDraft, setGeminiKeyDraft] = useState("");
  const [showGeminiKey, setShowGeminiKey] = useState(false);
  const [accessDialogOpen, setAccessDialogOpen] = useState(false);

  useEffect(() => {
    let ignore = false;

    async function loadProfile() {
      try {
        const response = await fetch(`${apiUrl()}/api/profile/demo-user`);
        if (!response.ok) return;

        const data = (await response.json()) as UserProfile;
        if (!ignore) setProfile(normalizeProfile(data));
      } catch {
        // The fallback profile keeps the board usable when the API is offline.
      }
    }

    async function loadSavedPlans() {
      try {
        const [plans, adjustments] = await Promise.all([
          fetchSavedPlans("demo-user"),
          fetchSavedDailyAdjustments("demo-user")
        ]);
        if (!ignore) {
          setSavedPlans(plans);
          setSavedDailyAdjustments(adjustments);
        }
      } catch {
        // Saved plans are optional in non-persistent local mode.
      }
    }

    loadProfile();
    loadSavedPlans();
    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    const savedKey = window.sessionStorage.getItem("athletiq-user-gemini-api-key") ?? "";
    const savedMode = window.sessionStorage.getItem("athletiq-access-mode");
    setGeminiApiKey(savedKey);
    setGeminiKeyDraft(savedKey);
    setAccessDialogOpen(!savedMode && !savedKey);
  }, []);

  useEffect(() => {
    if (toast === null) return;

    const timeout = window.setTimeout(() => setToast(null), 4200);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  const statusTone = useMemo(() => {
    if (briefing.recovery.status === "RED") return "border-recovery text-recovery bg-[#FFF4F0]";
    if (briefing.recovery.status === "YELLOW") return "border-[#B58B16] text-[#7A5A00] bg-[#FFF8E3]";
    return "border-[#1428FF] text-[#1428FF] bg-[#EFF5FF]";
  }, [briefing.recovery.status]);

  const hasWorkoutBaseline = workoutPlan !== null || savedPlans.some((plan) => plan.plan_type === "weekly_workout");
  const hasNutritionBaseline =
    nutritionPlan !== null || savedPlans.some((plan) => plan.plan_type === "weekly_nutrition");
  const todayDateKey = useMemo(() => localDateKey(), []);
  const todayAdjustment = savedDailyAdjustments.find((adjustment) => adjustment.adjustment_date === todayDateKey);
  const hasTodayAdjustment = todayAdjustment !== undefined;
  const canRunCheckIn = hasWorkoutBaseline && hasNutritionBaseline && !hasTodayAdjustment;
  const hasUserGeminiKey = geminiApiKey.trim().length > 0;

  function llmRequestHeaders(): Record<string, string> {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    const trimmedKey = geminiApiKey.trim();
    if (trimmedKey) headers["X-Gemini-Api-Key"] = trimmedKey;
    return headers;
  }

  function continueWithFallback() {
    setGeminiApiKey("");
    setGeminiKeyDraft("");
    window.sessionStorage.removeItem("athletiq-user-gemini-api-key");
    window.sessionStorage.setItem("athletiq-access-mode", "fallback");
    setAccessDialogOpen(false);
    setToast({ tone: "info", message: "Demo mode is active. Plans will use pre-cooked fallback responses." });
  }

  function activateUserGeminiKey() {
    const trimmedKey = geminiKeyDraft.trim();
    if (!trimmedKey) {
      setToast({ tone: "error", message: "Add a Gemini API key or continue with fallback mode." });
      return;
    }
    setGeminiApiKey(trimmedKey);
    window.sessionStorage.setItem("athletiq-user-gemini-api-key", trimmedKey);
    window.sessionStorage.setItem("athletiq-access-mode", "user-key");
    setAccessDialogOpen(false);
    setToast({ tone: "success", message: "Gemini key active for this browser session." });
  }

  function clearUserGeminiKey() {
    setGeminiApiKey("");
    setGeminiKeyDraft("");
    window.sessionStorage.removeItem("athletiq-user-gemini-api-key");
    window.sessionStorage.setItem("athletiq-access-mode", "fallback");
    setToast({ tone: "info", message: "Gemini key removed. Fallback mode is active." });
  }

  async function generateWorkoutPlan() {
    setRunState("running");
    setActiveAction("workout");
    setError(null);
    try {
      const response = await fetch(`${apiUrl()}/api/plans/workout/weekly`, {
        method: "POST",
        headers: llmRequestHeaders(),
        body: JSON.stringify(profile)
      });
      if (!response.ok) throw new Error("Workout plan could not be generated.");
      const data = (await response.json()) as WeeklyWorkoutResponse;
      setWorkoutPlan(data);
      setSavedPlans(await fetchSavedPlans(profile.user_id));
      setDialogMode("workout");
      setRunState("completed");
    } catch (requestError) {
      setRunState("failed");
      setError(errorMessage(requestError, "Unable to generate workout plan."));
    } finally {
      setActiveAction(null);
    }
  }

  async function generateNutritionPlan() {
    setRunState("running");
    setActiveAction("nutrition");
    setError(null);
    try {
      const response = await fetch(`${apiUrl()}/api/plans/nutrition/weekly`, {
        method: "POST",
        headers: llmRequestHeaders(),
        body: JSON.stringify(profile)
      });
      if (!response.ok) throw new Error("Diet plan could not be generated.");
      const data = (await response.json()) as WeeklyNutritionResponse;
      setNutritionPlan(data);
      setSavedPlans(await fetchSavedPlans(profile.user_id));
      setDialogMode("nutrition");
      setRunState("completed");
    } catch (requestError) {
      setRunState("failed");
      setError(errorMessage(requestError, "Unable to generate diet plan."));
    } finally {
      setActiveAction(null);
    }
  }

  async function simulateMorningCheckIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setRunState("running");
    setActiveAction("checkin");
    setError(null);

    try {
      const response = await fetch(`${apiUrl()}/api/check-ins/simulate`, {
        method: "POST",
        headers: llmRequestHeaders(),
        body: JSON.stringify({ profile, self_report: selfReport })
      });

      if (!response.ok) throw new Error("The coaching graph did not return a valid briefing.");

      const data = (await response.json()) as DailyBriefing;
      setBriefing(data);
      setProfile(normalizeProfile(data.profile));
      setDailyAdjustmentState("idle");
      setDialogMode("briefing");
      setRunState("completed");
    } catch (requestError) {
      setRunState("failed");
      setError(errorMessage(requestError, "Unable to run check-in."));
    } finally {
      setActiveAction(null);
    }
  }

  function openCheckIn() {
    const missingPlans = [
      hasWorkoutBaseline ? null : "workout plan",
      hasNutritionBaseline ? null : "diet plan"
    ].filter(Boolean);

    if (missingPlans.length > 0) {
      setToast({
        tone: "info",
        message: `Generate your ${missingPlans.join(" and ")} first, then run the morning check-in.`
      });
      return;
    }

    if (hasTodayAdjustment) {
      setToast({
        tone: "info",
        message: "Today's adjustment is already saved. Open Generated Plans to review or delete it before checking in again."
      });
      return;
    }

    if (canRunCheckIn) {
      setToast(null);
      setDialogMode("checkin");
      return;
    }

    setToast({
      tone: "info",
      message: "Check-in is not available right now."
    });
  }

  async function saveDailyAdjustment() {
    setDailyAdjustmentState("saving");
    setError(null);

    try {
      const response = await fetch(`${apiUrl()}/api/profile/${profile.user_id}/daily-adjustments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ briefing })
      });

      if (!response.ok) throw new Error("Daily adjustment could not be saved.");

      const saved = (await response.json()) as SavedDailyAdjustment;
      const adjustments = await fetchSavedDailyAdjustments(profile.user_id);
      setSavedDailyAdjustments(adjustments.length > 0 ? adjustments : [saved]);
      setDailyAdjustmentState("saved");
    } catch (requestError) {
      setDailyAdjustmentState("failed");
      setError(errorMessage(requestError, "Unable to save today's adjustment."));
    }
  }

  async function deleteGeneratedPlan(plan: SavedGeneratedPlan) {
    setError(null);

    try {
      const response = await fetch(`${apiUrl()}/api/profile/${profile.user_id}/generated-plans/${plan.id}`, {
        method: "DELETE"
      });

      if (!response.ok) throw new Error("Saved plan could not be deleted.");

      setSavedPlans((plans) => plans.filter((savedPlan) => savedPlan.id !== plan.id));
      if (plan.plan_type === "weekly_workout") setWorkoutPlan(null);
      if (plan.plan_type === "weekly_nutrition") setNutritionPlan(null);
      setToast({ tone: "success", message: "Saved plan deleted." });
    } catch (requestError) {
      setToast({ tone: "error", message: errorMessage(requestError, "Unable to delete saved plan.") });
    }
  }

  async function deleteDailyAdjustment(adjustment: SavedDailyAdjustment) {
    setError(null);

    try {
      const response = await fetch(`${apiUrl()}/api/profile/${profile.user_id}/daily-adjustments/${adjustment.id}`, {
        method: "DELETE"
      });

      if (!response.ok) throw new Error("Daily adjustment could not be deleted.");

      setSavedDailyAdjustments((adjustments) =>
        adjustments.filter((savedAdjustment) => savedAdjustment.id !== adjustment.id)
      );
      setToast({ tone: "success", message: "Saved adjustment deleted." });
    } catch (requestError) {
      setToast({ tone: "error", message: errorMessage(requestError, "Unable to delete saved adjustment.") });
    }
  }

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setProfileState("saving");
    setProfileError(null);

    try {
      const response = await fetch(`${apiUrl()}/api/profile/${profile.user_id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(profile)
      });

      if (!response.ok) throw new Error("Profile could not be saved.");

      const data = (await response.json()) as UserProfile;
      setProfile(normalizeProfile(data));
      setProfileState("saved");
    } catch (requestError) {
      setProfileState("failed");
      setProfileError(errorMessage(requestError, "Unable to save profile."));
    }
  }

  return (
    <main className="athletiq-stage min-h-screen overflow-x-hidden px-5 py-5 text-[#101820] sm:px-8">
      <header className="relative z-10 flex items-start justify-between gap-4">
        <button
          className="group font-display text-6xl font-semibold tracking-normal text-black drop-shadow-[0_10px_0_rgba(16,24,32,0.16)] transition duration-300 hover:-translate-y-1 hover:drop-shadow-[0_14px_0_rgba(16,24,32,0.18)] sm:text-7xl"
          onClick={() => setDialogMode("none")}
          type="button"
        >
          athlet<span className="transition group-hover:text-[#1428FF]">IQ</span>
        </button>
        <div className="flex flex-wrap justify-end gap-2">
          <button
            className="inline-flex min-h-9 items-center gap-2 rounded-control bg-white/85 px-4 py-2 text-sm font-medium text-ink shadow-[0_10px_24px_rgba(6,26,46,0.12)] backdrop-blur transition hover:-translate-y-0.5 hover:bg-white hover:shadow-[0_14px_28px_rgba(6,26,46,0.16)] active:translate-y-0"
            onClick={() => {
              setGeminiKeyDraft(geminiApiKey);
              setAccessDialogOpen(true);
            }}
            type="button"
          >
            <KeyRound size={16} aria-hidden="true" />
            {hasUserGeminiKey ? "AI unlocked" : "AI key"}
          </button>
          {savedPlans.length > 0 || savedDailyAdjustments.length > 0 ? (
            <button
              className="inline-flex min-h-9 items-center gap-2 rounded-control bg-white/85 px-4 py-2 text-sm font-medium text-ink shadow-[0_10px_24px_rgba(6,26,46,0.12)] backdrop-blur transition hover:-translate-y-0.5 hover:bg-white hover:shadow-[0_14px_28px_rgba(6,26,46,0.16)] active:translate-y-0"
              onClick={() => setDialogMode("plans")}
              type="button"
            >
              <NotebookTabs size={16} aria-hidden="true" />
              See Generated Plans
            </button>
          ) : null}
          <button
            className="inline-flex min-h-9 items-center gap-2 rounded-control bg-white/85 px-4 py-2 text-sm font-medium text-ink shadow-[0_10px_24px_rgba(6,26,46,0.12)] backdrop-blur transition hover:-translate-y-0.5 hover:bg-white hover:shadow-[0_14px_28px_rgba(6,26,46,0.16)] active:translate-y-0"
            onClick={() => {
              setDialogMode("none");
              setError("Demo logout is not connected yet.");
            }}
            type="button"
          >
            <LogOut size={16} aria-hidden="true" />
            Log out
          </button>
          <button
            className="inline-flex min-h-9 items-center gap-2 rounded-control bg-[#1428FF] px-4 py-2 text-sm font-medium text-white shadow-[0_12px_30px_rgba(20,40,255,0.28)] transition hover:-translate-y-0.5 hover:bg-[#0D1DBB] hover:shadow-[0_16px_36px_rgba(20,40,255,0.34)] active:translate-y-0"
            onClick={() => setDialogMode("profile")}
            type="button"
          >
            <User size={16} aria-hidden="true" />
            My profile
          </button>
        </div>
      </header>

      <section className="relative z-10 mx-auto mt-8 max-w-7xl sm:mt-12">
        <div className="mb-7 grid gap-3 text-[#071625] sm:grid-cols-[1fr_auto] sm:items-end">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full border border-[#17202A]/20 bg-white/35 px-3 py-1 font-data text-xs uppercase backdrop-blur">
              <Sparkles size={14} aria-hidden="true" />
              AI coaching board
            </p>
            <h1 className="mt-4 max-w-2xl font-display text-3xl font-semibold leading-tight sm:text-4xl">
              Smart Fitness & Nutrition Built Around Your Body.
            </h1>
          </div>
          <div className="rounded-control border border-[#17202A]/20 bg-white/30 px-4 py-3 text-sm shadow-[0_18px_40px_rgba(6,26,46,0.12)] backdrop-blur">
            <p className="font-data text-xs uppercase text-[#0E3B62]">Active profile</p>
            <p className="mt-1 font-medium capitalize">{profile.name} · {profile.goal.replace("_", " ")}</p>
          </div>
        </div>
        <div className="grid gap-8 lg:grid-cols-3 xl:gap-10">
          <ActionFrame
            icon={Dumbbell}
            kicker=" "
            label="Get Workout Plan"
            description="Goal-oriented 7-day training split customized to your fitness level and equipment."
            accent="from-[#78D7FF]/75 to-[#2268D8]/45"
            onClick={generateWorkoutPlan}
            busy={activeAction === "workout"}
            locked={runState === "running" && activeAction !== "workout"}
          />
          <ActionFrame
            icon={Apple}
            kicker=" "
            label="Get Diet Plan"
            description="Personalized 7-day nutrition and macro blueprint built around your metabolic targets."
            accent="from-[#A9F0E0]/80 to-[#2997D8]/45"
            onClick={generateNutritionPlan}
            busy={activeAction === "nutrition"}
            locked={runState === "running" && activeAction !== "nutrition"}
          />
          <ActionFrame
            icon={ClipboardCheck}
            kicker=" "
            label="Check in"
            description="Analyze biometrics, assess readiness, and establish today's coaching strategy."
            accent="from-[#BFF4F1]/90 to-[#2672DE]/45"
            onClick={openCheckIn}
            busy={activeAction === "checkin"}
            locked={runState === "running" && activeAction !== "checkin"}
          />
        </div>
      </section>

      {toast ? <ToastNotice toast={toast} onDismiss={() => setToast(null)} /> : null}

      {accessDialogOpen ? (
        <AccessModeDialog
          geminiKeyDraft={geminiKeyDraft}
          hasUserGeminiKey={hasUserGeminiKey}
          showGeminiKey={showGeminiKey}
          onActivateUserKey={activateUserGeminiKey}
          onChangeGeminiKey={setGeminiKeyDraft}
          onClearUserKey={clearUserGeminiKey}
          onContinueFallback={continueWithFallback}
          onShowGeminiKeyChange={setShowGeminiKey}
        />
      ) : null}

      {error ? (
        <div className="relative z-10 mx-auto mt-8 max-w-3xl rounded-control border border-recovery bg-[#FFF4F0] px-4 py-3 text-sm text-recovery shadow-[0_18px_40px_rgba(6,26,46,0.14)]">
          {error}
        </div>
      ) : null}

      {dialogMode !== "none" ? (
        <div
          aria-labelledby="dialog-title"
          aria-modal="true"
          className="fixed inset-0 z-50 grid place-items-center bg-[#061A2E]/62 px-4 py-8 backdrop-blur-md"
          role="dialog"
        >
          <div className="modal-pop max-h-[90vh] w-full max-w-5xl overflow-y-auto rounded-[28px] border-[3px] border-[#17202A] bg-gradient-to-br from-[#F5FDFF]/95 via-white/95 to-[#D7F5FF]/95 p-6 shadow-[0_34px_90px_rgba(6,26,46,0.34)]">
            <div className="mb-5 flex items-start justify-between gap-4">
              <div>
                <p className="font-data text-xs uppercase text-[#0E3B62]">{dialogEyebrow(dialogMode)}</p>
                <h2 id="dialog-title" className="mt-1 font-display text-2xl font-semibold">
                  {dialogTitle(dialogMode)}
                </h2>
              </div>
              <button
                aria-label="Close dialog"
                className="inline-flex h-10 w-10 items-center justify-center rounded-control border border-[#17202A]/30 bg-white/55 text-[#102235] shadow-[0_10px_22px_rgba(6,26,46,0.12)] backdrop-blur transition hover:-translate-y-0.5 hover:border-[#1428FF] hover:bg-[#1428FF] hover:text-white active:translate-y-0"
                onClick={() => setDialogMode("none")}
                type="button"
              >
                <X size={18} aria-hidden="true" />
              </button>
            </div>

            {dialogMode === "profile" ? (
              <ProfileForm
                profile={profile}
                profileError={profileError}
                profileState={profileState}
                onChange={setProfile}
                onSubmit={saveProfile}
              />
            ) : null}

            {dialogMode === "plans" ? (
              <SavedPlansPanel
                plans={savedPlans}
                dailyAdjustments={savedDailyAdjustments}
                onOpenPlan={(plan) => {
                  const savedWorkout = normalizeSavedWorkoutPlan(plan.payload);
                  if (plan.plan_type === "weekly_workout" && savedWorkout) {
                    setWorkoutPlan(savedWorkout);
                    setDialogMode("workout");
                  }
                  if (plan.plan_type === "weekly_nutrition" && isWeeklyNutritionPayload(plan.payload)) {
                    setNutritionPlan(plan.payload);
                    setDialogMode("nutrition");
                  }
                }}
                onDeletePlan={deleteGeneratedPlan}
                onDeleteAdjustment={deleteDailyAdjustment}
                onOpenAdjustment={(adjustment) => {
                  if (isDailyBriefingPayload(adjustment.payload)) {
                    setBriefing(adjustment.payload);
                    setDailyAdjustmentState("saved");
                    setDialogMode("briefing");
                  }
                }}
              />
            ) : null}

            {dialogMode === "checkin" ? (
              <form className="space-y-5" noValidate onSubmit={simulateMorningCheckIn}>
                <section className="rounded-[22px] border border-[#17202A]/20 bg-white/55 p-4 shadow-[0_12px_26px_rgba(6,26,46,0.08)] backdrop-blur">
                  <p className="font-data text-xs uppercase text-[#1428FF]">Daily readiness check</p>
                  <h3 className="mt-2 font-display text-lg font-semibold">
                    Help us adapt today&apos;s plan to how your body feels.
                  </h3>
                  <p className="mt-2 max-w-2xl text-sm leading-6 text-slate">
                    Add a quick self-report and we&apos;ll combine it with today&apos;s smartwatch signals to adjust
                    your workout and meals.
                  </p>
                </section>
                <div className="grid gap-4 md:grid-cols-3">
                  <SelfReportSlider
                    label="Quad soreness"
                    value={selfReport.soreness_quads}
                    onChange={(value) => setSelfReport({ ...selfReport, soreness_quads: value })}
                  />
                  <SelfReportSlider
                    label="Upper-body soreness"
                    value={selfReport.soreness_upper}
                    onChange={(value) => setSelfReport({ ...selfReport, soreness_upper: value })}
                  />
                  <SelfReportSlider
                    label="Pain level"
                    value={selfReport.pain_level}
                    onChange={(value) => setSelfReport({ ...selfReport, pain_level: value })}
                  />
                </div>
                <label className="block max-w-xs text-sm font-medium text-ink">
                  Available minutes
                  <input
                    className="mt-1 w-full rounded-control border border-[#17202A]/20 bg-white/70 px-3 py-2 text-sm text-ink shadow-[inset_0_1px_0_rgba(255,255,255,0.55)] transition focus:border-[#1428FF]"
                    max={180}
                    min={5}
                    type="number"
                    value={selfReport.available_minutes}
                    onChange={(event) =>
                      setSelfReport({ ...selfReport, available_minutes: Number(event.target.value) })
                    }
                  />
                </label>
                <button
                  className="inline-flex min-h-11 min-w-44 items-center justify-center gap-2 rounded-control bg-[#111820] px-5 py-2 text-sm font-semibold text-white shadow-[0_12px_24px_rgba(6,26,46,0.22)] transition hover:-translate-y-0.5 hover:bg-black hover:shadow-[0_16px_30px_rgba(6,26,46,0.28)] disabled:opacity-70 active:translate-y-0"
                  disabled={activeAction === "checkin"}
                  type="submit"
                >
                  {activeAction === "checkin" ? (
                    <Loader2 className="animate-spin" size={17} aria-hidden="true" />
                  ) : (
                    <CheckCircle2 size={17} aria-hidden="true" />
                  )}
                  Run evaluation
                </button>
              </form>
            ) : null}

            {dialogMode === "briefing" ? (
              <BriefingResult
                briefing={briefing}
                saveState={dailyAdjustmentState}
                statusTone={statusTone}
                onSave={saveDailyAdjustment}
              />
            ) : null}

            {dialogMode === "workout" && workoutPlan ? (
              <WeeklyWorkoutPlan plan={workoutPlan} />
            ) : null}

            {dialogMode === "nutrition" && nutritionPlan ? (
              <WeeklyNutritionPlan plan={nutritionPlan} />
            ) : null}
          </div>
        </div>
      ) : null}
    </main>
  );
}

function AccessModeDialog({
  geminiKeyDraft,
  hasUserGeminiKey,
  showGeminiKey,
  onActivateUserKey,
  onChangeGeminiKey,
  onClearUserKey,
  onContinueFallback,
  onShowGeminiKeyChange
}: {
  geminiKeyDraft: string;
  hasUserGeminiKey: boolean;
  showGeminiKey: boolean;
  onActivateUserKey: () => void;
  onChangeGeminiKey: (value: string) => void;
  onClearUserKey: () => void;
  onContinueFallback: () => void;
  onShowGeminiKeyChange: (value: boolean) => void;
}) {
  return (
    <div
      aria-labelledby="access-dialog-title"
      aria-modal="true"
      className="fixed inset-0 z-[60] grid place-items-center bg-[#061A2E]/68 px-4 py-8 backdrop-blur-md"
      role="dialog"
    >
      <section className="modal-pop w-full max-w-2xl rounded-[28px] border-[3px] border-[#17202A] bg-gradient-to-br from-[#F5FDFF]/96 via-white/96 to-[#D7F5FF]/96 p-6 shadow-[0_34px_90px_rgba(6,26,46,0.34)]">
        <div className="flex items-start gap-4">
          <span className="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-control bg-[#1428FF] text-white shadow-[0_14px_30px_rgba(20,40,255,0.26)]">
            <KeyRound size={22} aria-hidden="true" />
          </span>
          <div>
            <p className="font-data text-xs uppercase text-[#0E3B62]">LLM access</p>
            <h2 id="access-dialog-title" className="mt-1 font-display text-2xl font-semibold text-ink">
              Looks like you found my portfolio project
            </h2>
            <p className="mt-3 text-sm leading-6 text-slate">
              To keep my server bills from exploding while still letting you poke around, this app starts in
              pre-cooked, hardcoded fallback mode. 
            </p>
            <p className="mt-3 text-sm leading-6 text-slate">
              Want to unleash its full AI brain? Choose your path below.
            </p>
          </div>
        </div>

        <div className="mt-6 grid gap-3">
          <label className="block text-sm font-medium text-ink">
            Gemini API key
            <div className="mt-1 flex overflow-hidden rounded-control border border-[#17202A]/20 bg-white/70 shadow-[inset_0_1px_0_rgba(255,255,255,0.55)] transition focus-within:border-[#1428FF]">
              <input
                className="min-w-0 flex-1 bg-transparent px-3 py-2 text-sm text-ink outline-none"
                placeholder="AIza..."
                type={showGeminiKey ? "text" : "password"}
                value={geminiKeyDraft}
                onChange={(event) => onChangeGeminiKey(event.target.value)}
              />
              <button
                aria-label={showGeminiKey ? "Hide Gemini API key" : "Show Gemini API key"}
                className="inline-flex h-10 w-10 items-center justify-center border-l border-[#17202A]/10 text-slate transition hover:bg-[#EFF5FF] hover:text-[#1428FF]"
                onClick={() => onShowGeminiKeyChange(!showGeminiKey)}
                type="button"
              >
                {showGeminiKey ? <EyeOff size={17} aria-hidden="true" /> : <Eye size={17} aria-hidden="true" />}
              </button>
            </div>
          </label>
          <p className="text-xs leading-5 text-slate">
            Bring your own Gemini 3.5 Lite key to unlock live generation. Your key stays in this browser session and
            never touches my database.
          </p>
        </div>

        <div className="mt-6 flex flex-wrap justify-end gap-3">
          {hasUserGeminiKey ? (
            <button
              className="inline-flex min-h-11 items-center justify-center rounded-control border border-recovery/35 bg-white/60 px-5 py-2 text-sm font-semibold text-recovery transition hover:-translate-y-0.5 hover:bg-[#FFF4F0] active:translate-y-0"
              onClick={onClearUserKey}
              type="button"
            >
              Remove key
            </button>
          ) : null}
          <button
            className="inline-flex min-h-11 items-center justify-center rounded-control border border-[#17202A]/20 bg-white/75 px-5 py-2 text-sm font-semibold text-ink shadow-[0_10px_22px_rgba(6,26,46,0.1)] transition hover:-translate-y-0.5 hover:bg-white active:translate-y-0"
            onClick={onContinueFallback}
            type="button"
          >
            Stick to the Demo
          </button>
          <button
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-control bg-[#1428FF] px-5 py-2 text-sm font-semibold text-white shadow-[0_12px_30px_rgba(20,40,255,0.28)] transition hover:-translate-y-0.5 hover:bg-[#0D1DBB] active:translate-y-0"
            onClick={onActivateUserKey}
            type="button"
          >
            <KeyRound size={17} aria-hidden="true" />
            Bring Your Own Key
          </button>
        </div>
      </section>
    </div>
  );
}

function ActionFrame({
  icon: Icon,
  kicker,
  label,
  description,
  accent,
  onClick,
  busy,
  locked
}: {
  icon: LucideIcon;
  kicker: string;
  label: string;
  description: string;
  accent: string;
  onClick: () => void;
  busy: boolean;
  locked: boolean;
}) {
  return (
    <section className={`group relative flex min-h-[340px] overflow-hidden rounded-[28px] border-[3px] border-[#17202A] bg-gradient-to-br ${accent} px-8 py-8 shadow-[0_24px_50px_rgba(6,26,46,0.16)] backdrop-blur-[1px] transition duration-300 hover:-translate-y-2 hover:shadow-[0_34px_70px_rgba(6,26,46,0.24)] sm:min-h-[380px] xl:min-h-[430px]`}>
      <div className="absolute inset-x-8 top-7 flex items-center justify-between">
        <p className="font-data text-xs uppercase text-[#0A3357]">{kicker}</p>
        <span className="h-2 w-2 rounded-full bg-[#17202A] shadow-[0_0_0_6px_rgba(255,255,255,0.22)]" />
      </div>
      <div className="grid h-full w-full grid-rows-[1fr_auto_auto] place-items-center gap-7 pt-12 text-center">
        <div className="flex min-h-[150px] items-center justify-center sm:min-h-[180px] xl:min-h-[210px]">
          <Icon
            strokeWidth={2.5}
            className="h-32 w-32 text-[#111820] transition duration-300 group-hover:scale-110 group-hover:rotate-[-3deg] sm:h-40 sm:w-40 xl:h-48 xl:w-48"
            aria-hidden="true"
          />
        </div>
        <p className="mx-auto min-h-[56px] max-w-72 text-center text-base leading-7 text-[#102235]/85">
          {description}
        </p>
        <button
          className="inline-flex min-h-12 min-w-44 items-center justify-center rounded-control bg-[#2B2F33] px-5 py-3 text-sm font-medium text-white shadow-[0_12px_24px_rgba(6,26,46,0.22)] transition hover:-translate-y-0.5 hover:bg-[#111820] hover:shadow-[0_16px_30px_rgba(6,26,46,0.28)] disabled:opacity-70 active:translate-y-0"
          disabled={busy || locked}
          onClick={onClick}
          type="button"
        >
          {busy ? <Loader2 className="animate-spin" size={17} aria-hidden="true" /> : label}
        </button>
      </div>
    </section>
  );
}

function ToastNotice({
  toast,
  onDismiss
}: {
  toast: ToastMessage;
  onDismiss: () => void;
}) {
  return (
    <div
      className={`fixed right-5 top-24 z-[60] flex w-[min(420px,calc(100vw-2.5rem))] items-start gap-3 rounded-[18px] border-[2px] bg-white/90 p-4 text-sm shadow-[0_24px_55px_rgba(6,26,46,0.24)] backdrop-blur-md ${
        toast.tone === "error"
          ? "border-recovery text-recovery"
          : toast.tone === "success"
            ? "border-[#1428FF] text-[#102235]"
            : "border-[#1428FF] text-[#102235]"
      }`}
      role="status"
      aria-live="polite"
    >
      <div className={toast.tone === "error" ? "text-recovery" : "text-[#1428FF]"}>
        <AlertCircle size={20} aria-hidden="true" />
      </div>
      <p className="flex-1 leading-6">{toast.message}</p>
      <button
        aria-label="Dismiss notification"
        className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-control border border-[#17202A]/20 bg-white/60 text-[#102235] transition hover:-translate-y-0.5 hover:border-[#1428FF] hover:bg-[#1428FF] hover:text-white active:translate-y-0"
        onClick={onDismiss}
        type="button"
      >
        <X size={15} aria-hidden="true" />
      </button>
    </div>
  );
}

function BriefingResult({
  briefing,
  saveState,
  statusTone,
  onSave
}: {
  briefing: DailyBriefing;
  saveState: "idle" | "saving" | "saved" | "failed";
  statusTone: string;
  onSave: () => void;
}) {
  return (
    <div className="space-y-5">
      <section className="overflow-hidden rounded-[24px] border border-[#17202A]/20 bg-white/65 shadow-[0_20px_44px_rgba(6,26,46,0.12)] backdrop-blur">
        <div className="grid gap-0 lg:grid-cols-[1fr_220px]">
          <div className="p-5">
            <p className="font-data text-xs uppercase text-[#1428FF]">Recovery decision</p>
            <div className={`mt-3 inline-flex rounded-control border px-3 py-1 text-sm font-semibold ${statusTone}`}>
              {recoveryLabel(briefing.recovery.status)}
            </div>
            <h3 className="mt-4 font-display text-2xl font-semibold leading-tight">{briefing.final_message}</h3>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-slate">{briefing.recovery.summary}</p>
            <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center">
              <button
                className="inline-flex min-h-11 min-w-52 items-center justify-center gap-2 rounded-control bg-[#111820] px-5 py-2 text-sm font-semibold text-white shadow-[0_12px_24px_rgba(6,26,46,0.22)] transition hover:-translate-y-0.5 hover:bg-black hover:shadow-[0_16px_30px_rgba(6,26,46,0.28)] disabled:cursor-not-allowed disabled:opacity-70 active:translate-y-0"
                disabled={saveState === "saving"}
                onClick={onSave}
                type="button"
              >
                {saveState === "saving" ? (
                  <Loader2 className="animate-spin" size={17} aria-hidden="true" />
                ) : (
                  <Save size={17} aria-hidden="true" />
                )}
                {saveState === "saving" ? "Saving..." : "Save today's adjustment"}
              </button>
              <p className="text-xs leading-5 text-slate" role="status">
                {saveState === "saved"
                  ? "Saved. You can reopen it from Generated Plans."
                  : saveState === "failed"
                    ? "Could not save this adjustment. Try again."
                    : "Keeps this adjusted workout and meal plan for today."}
              </p>
            </div>
          </div>
          <div className="flex flex-col justify-center border-t border-[#17202A]/15 bg-gradient-to-br from-[#DFF7FF] to-[#CDEBFF] p-5 text-center lg:border-l lg:border-t-0">
            <p className="font-data text-5xl font-semibold">{briefing.recovery.readiness_score}</p>
            <p className="mt-1 text-xs font-medium uppercase text-[#0E3B62]">readiness score</p>
          </div>
        </div>
      </section>

      <section className="rounded-[22px] border border-[#17202A]/20 bg-white/55 p-4 shadow-[0_16px_32px_rgba(6,26,46,0.1)] backdrop-blur">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="font-data text-xs uppercase text-[#1428FF]">Smartwatch signals</p>
            <h3 className="mt-1 font-display text-lg font-semibold">Today&apos;s body data</h3>
          </div>
          <p className="text-xs text-slate">Synced from the demo smartwatch feed plus your self-report.</p>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Metric icon={Moon} label="Sleep" value={`${briefing.wearable.sleep_hours}h`} />
          <Metric icon={HeartPulse} label="Resting HR" value={`${briefing.wearable.resting_heart_rate}`} />
          <Metric icon={HeartPulse} label="Blood oxygen" value={`${briefing.wearable.blood_oxygen_level}%`} />
          <Metric icon={Activity} label="Steps" value={briefing.wearable.step_count.toLocaleString()} />
          <Metric icon={Activity} label="Activity" value={formatActivityLevel(briefing.wearable.activity_level)} />
          <Metric icon={Activity} label="Quad soreness" value={`${briefing.wearable.soreness_quads}/10`} />
          <Metric icon={Activity} label="Upper soreness" value={`${briefing.wearable.soreness_upper}/10`} />
          <Metric icon={Gauge} label="Pain" value={`${briefing.wearable.pain_level}/10`} />
          <Metric icon={Gauge} label="Energy" value={`${briefing.wearable.energy_level}/10`} />
        </div>
      </section>

      <TodayBaseline briefing={briefing} />

      <div className="grid gap-5 lg:grid-cols-2">
        <PlanSection
          icon={Dumbbell}
          title={briefing.workout?.title ?? "Trainer skipped"}
          eyebrow="Adjusted workout"
          items={briefing.workout?.blocks ?? ["No training session generated today."]}
          notes={userFacingNotes(briefing.workout?.notes ?? [])}
        />
        <PlanSection
          icon={Apple}
          title={briefing.nutrition?.title ?? "Nutrition skipped"}
          eyebrow="Adjusted meals"
          items={briefing.nutrition?.meals ?? ["No nutrition plan generated today."]}
          notes={
            briefing.nutrition
              ? [
                  `${briefing.nutrition.calorie_target} kcal target`,
                  `${briefing.nutrition.protein_g}g protein`,
                  ...userFacingNotes(briefing.nutrition.notes)
                ]
              : []
          }
        />
      </div>

      {briefing.recovery.constraints.length > 0 ? (
        <section className="rounded-[22px] border border-[#17202A]/20 bg-white/55 p-4 shadow-[0_16px_32px_rgba(6,26,46,0.1)] backdrop-blur">
          <p className="font-data text-xs uppercase text-[#1428FF]">Why it changed</p>
          <h3 className="mt-1 font-display text-lg font-semibold">Coach guardrails for today</h3>
          <ul className="mt-4 space-y-3">
            {briefing.recovery.constraints.map((constraint, index) => (
              <li className="rounded-control border border-[#17202A]/10 bg-white/65 px-3 py-2 text-sm text-slate" key={`${constraint}-${index}`}>
                {constraint}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}

function TodayBaseline({ briefing }: { briefing: DailyBriefing }) {
  const hasWorkout = briefing.baseline_workout !== null && briefing.baseline_workout !== undefined;
  const hasNutrition = briefing.baseline_nutrition !== null && briefing.baseline_nutrition !== undefined;

  return (
    <section className="rounded-[22px] border border-[#17202A]/20 bg-white/55 p-4 shadow-[0_16px_32px_rgba(6,26,46,0.1)] backdrop-blur">
      <p className="font-data text-xs uppercase text-[#1428FF]">
        Baseline plan{briefing.current_day ? ` · ${briefing.current_day}` : ""}
      </p>
      <h3 className="mt-1 font-display text-lg font-semibold">What was planned before the check-in</h3>
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="rounded-control border border-[#17202A]/10 bg-white/65 p-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-ink">
            <Dumbbell size={17} className="text-[#1428FF]" aria-hidden="true" />
            Planned workout
          </div>
          <p className="mt-2 text-sm font-medium text-slate">
            {hasWorkout ? briefing.baseline_workout?.title : "No saved weekly workout yet."}
          </p>
          {hasWorkout && briefing.baseline_workout?.details.length ? (
            <ul className="mt-3 space-y-1">
              {briefing.baseline_workout.details.slice(0, 4).map((detail, index) => (
                <li className="text-xs leading-5 text-slate" key={`${detail}-${index}`}>
                  {detail}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
        <div className="rounded-control border border-[#17202A]/10 bg-white/65 p-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-ink">
            <Apple size={17} className="text-[#1428FF]" aria-hidden="true" />
            Planned meals
          </div>
          <p className="mt-2 text-sm font-medium text-slate">
            {hasNutrition ? briefing.baseline_nutrition?.focus : "No saved weekly diet yet."}
          </p>
          {hasNutrition && briefing.baseline_nutrition?.meals.length ? (
            <ul className="mt-3 space-y-1">
              {briefing.baseline_nutrition.meals.slice(0, 4).map((meal, index) => (
                <li className="text-xs leading-5 text-slate" key={`${meal.meal_type}-${meal.name}-${index}`}>
                  {meal.meal_type}: {meal.name}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function WeeklyWorkoutPlan({ plan }: { plan: WeeklyWorkoutResponse }) {
  const days = normalizeWorkoutDays(plan.days);
  const notes = userFacingNotes(plan.notes);

  return (
    <section className="rounded-[22px] border border-[#17202A]/20 bg-white/55 p-4 shadow-[0_18px_36px_rgba(6,26,46,0.12)] backdrop-blur">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="flex items-start gap-3">
          <div className="mt-1 text-[#1428FF]">
            <Dumbbell size={19} aria-hidden="true" />
          </div>
          <div>
            <p className="font-data text-xs uppercase text-[#1428FF]">Trainer weekly plan</p>
            <h3 className="mt-1 font-display text-lg font-semibold">{plan.title}</h3>
            <p className="mt-2 text-sm text-slate">
              {plan.duration_minutes} min sessions · {plan.intensity} intensity
            </p>
          </div>
        </div>
        <button
          className="inline-flex min-h-11 items-center justify-center gap-2 rounded-control bg-[#111820] px-5 py-2 text-sm font-semibold text-white shadow-[0_12px_24px_rgba(6,26,46,0.22)] transition hover:-translate-y-0.5 hover:bg-black hover:shadow-[0_16px_30px_rgba(6,26,46,0.28)] active:translate-y-0"
          onClick={() => downloadWorkoutPdf(plan, days)}
          type="button"
        >
          <Download size={17} aria-hidden="true" />
          Download PDF
        </button>
      </div>

      <div className="mt-5 overflow-x-auto rounded-control border border-[#17202A]/20 bg-white/75 shadow-[inset_0_1px_0_rgba(255,255,255,0.55)]">
        <table className="min-w-[980px] table-fixed border-collapse text-left">
          <thead>
            <tr>
              {days.map((day) => (
                <th
                  className="border-b border-r border-[#17202A]/15 bg-gradient-to-br from-[#DFF7FF] to-[#CDEBFF] px-3 py-3 align-top font-data text-xs uppercase text-[#0E3B62] last:border-r-0"
                  key={day.day}
                  scope="col"
                >
                  {day.day}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              {days.map((day) => (
                <td className="border-r border-[#17202A]/15 px-3 py-4 align-top last:border-r-0" key={day.day}>
                  <p className="min-h-12 font-display text-base font-semibold leading-5 text-ink">
                    {day.title}
                  </p>
                  <ul className="mt-4 space-y-2">
                    {day.exercises.map((exercise, index) => (
                      <li
                        className="grid grid-cols-[10px_1fr] gap-2 text-xs leading-5 text-slate"
                        key={`${day.day}-${exercise.name}-${exercise.prescription}-${index}`}
                      >
                        <span className="mt-2 h-1.5 w-1.5 rounded-full bg-[#1428FF]/70" />
                        <span>
                          <span className="font-semibold text-ink">{exercise.name}</span>
                          {" "}
                          {exercise.prescription}
                          {exercise.notes ? ` (${exercise.notes})` : ""}
                        </span>
                      </li>
                    ))}
                  </ul>
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>

      {notes.length > 0 ? (
        <div className="mt-4 grid gap-2 border-t border-[#17202A]/15 pt-3 md:grid-cols-2">
          {notes.map((note, index) => (
            <p
              className="rounded-control border border-[#17202A]/10 bg-white/65 px-3 py-2 text-xs leading-5 text-slate"
              key={`${note}-${index}`}
            >
              {note}
            </p>
          ))}
        </div>
      ) : null}

    </section>
  );
}

function WeeklyNutritionPlan({ plan }: { plan: WeeklyNutritionResponse }) {
  const days = normalizeNutritionDays(plan.days);
  const notes = userFacingNotes(plan.notes);

  return (
    <section className="rounded-[22px] border border-[#17202A]/20 bg-white/55 p-4 shadow-[0_18px_36px_rgba(6,26,46,0.12)] backdrop-blur">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="flex items-start gap-3">
          <div className="mt-1 text-[#1428FF]">
            <Apple size={19} aria-hidden="true" />
          </div>
          <div>
            <p className="font-data text-xs uppercase text-[#1428FF]">Nutritionist weekly plan</p>
            <h3 className="mt-1 font-display text-lg font-semibold">{plan.title}</h3>
            <p className="mt-2 text-sm text-slate">
              {plan.daily_calorie_target} kcal/day · {plan.daily_protein_g}g protein/day
            </p>
          </div>
        </div>
        <button
          className="inline-flex min-h-11 items-center justify-center gap-2 rounded-control bg-[#111820] px-5 py-2 text-sm font-semibold text-white shadow-[0_12px_24px_rgba(6,26,46,0.22)] transition hover:-translate-y-0.5 hover:bg-black hover:shadow-[0_16px_30px_rgba(6,26,46,0.28)] active:translate-y-0"
          onClick={() => downloadNutritionPdf(plan, days)}
          type="button"
        >
          <Download size={17} aria-hidden="true" />
          Download PDF
        </button>
      </div>

      <div className="mt-5 overflow-x-auto rounded-control border border-[#17202A]/20 bg-white/75 shadow-[inset_0_1px_0_rgba(255,255,255,0.55)]">
        <table className="min-w-[1180px] table-fixed border-collapse text-left">
          <thead>
            <tr>
              {days.map((day) => (
                <th
                  className="border-b border-r border-[#17202A]/15 bg-gradient-to-br from-[#DFF7FF] to-[#CDEBFF] px-3 py-3 align-top last:border-r-0"
                  key={day.day}
                  scope="col"
                >
                  <span className="block font-data text-xs uppercase text-[#0E3B62]">{day.day}</span>
                  <span className="mt-1 block text-xs font-medium normal-case text-slate">{day.focus}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              {days.map((day) => (
                <td className="border-r border-[#17202A]/15 px-3 py-4 align-top last:border-r-0" key={day.day}>
                  <div className="space-y-3">
                    {day.meals.map((meal, index) => (
                      <article
                        className="rounded-control border border-[#17202A]/10 bg-white/65 p-3 shadow-[0_8px_20px_rgba(6,26,46,0.06)] transition hover:-translate-y-0.5 hover:bg-white"
                        key={`${day.day}-${meal.meal_type}-${meal.name}-${index}`}
                      >
                        <p className="font-data text-[11px] uppercase text-[#1428FF]">{meal.meal_type}</p>
                        <h4 className="mt-1 text-sm font-semibold leading-5 text-ink">{meal.name}</h4>
                        <div className="mt-3 grid grid-cols-2 gap-1.5 font-data text-[11px] text-slate">
                          <span className="rounded bg-[#EFF5FF] px-2 py-1">{meal.calories} kcal</span>
                          <span className="rounded bg-[#EFF5FF] px-2 py-1">{meal.protein_g}g P</span>
                          <span className="rounded bg-[#EFF5FF] px-2 py-1">{meal.carbs_g}g C</span>
                          <span className="rounded bg-[#EFF5FF] px-2 py-1">{meal.fat_g}g F</span>
                        </div>
                      </article>
                    ))}
                  </div>
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>

      {notes.length > 0 ? (
        <div className="mt-4 grid gap-2 border-t border-[#17202A]/15 pt-3 md:grid-cols-2">
          {notes.map((note, index) => (
            <p
              className="rounded-control border border-[#17202A]/10 bg-white/65 px-3 py-2 text-xs leading-5 text-slate"
              key={`${note}-${index}`}
            >
              {note}
            </p>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function SavedPlansPanel({
  plans,
  dailyAdjustments,
  onOpenPlan,
  onDeletePlan,
  onDeleteAdjustment,
  onOpenAdjustment
}: {
  plans: SavedGeneratedPlan[];
  dailyAdjustments: SavedDailyAdjustment[];
  onOpenPlan: (plan: SavedGeneratedPlan) => void;
  onDeletePlan: (plan: SavedGeneratedPlan) => Promise<void>;
  onDeleteAdjustment: (adjustment: SavedDailyAdjustment) => Promise<void>;
  onOpenAdjustment: (adjustment: SavedDailyAdjustment) => void;
}) {
  const [confirmingPlanId, setConfirmingPlanId] = useState<string | null>(null);
  const [deletingPlanId, setDeletingPlanId] = useState<string | null>(null);
  const [confirmingAdjustmentId, setConfirmingAdjustmentId] = useState<string | null>(null);
  const [deletingAdjustmentId, setDeletingAdjustmentId] = useState<string | null>(null);

  if (plans.length === 0 && dailyAdjustments.length === 0) {
    return (
      <section className="rounded-[22px] border border-[#17202A]/20 bg-white/55 p-5 text-sm text-slate shadow-[0_16px_32px_rgba(6,26,46,0.1)] backdrop-blur">
        Generate a workout or diet plan first. Saved plans will appear here.
      </section>
    );
  }

  return (
    <div className="space-y-6">
      {plans.length > 0 ? (
        <section>
          <p className="font-data text-xs uppercase text-[#1428FF]">Weekly baselines</p>
          <div className="mt-3 grid gap-4 md:grid-cols-2">
            {plans.map((plan) => (
              <article
                className="rounded-[22px] border border-[#17202A]/20 bg-white/55 p-5 shadow-[0_16px_32px_rgba(6,26,46,0.1)] backdrop-blur transition hover:-translate-y-1 hover:bg-white/70 hover:shadow-[0_22px_42px_rgba(6,26,46,0.14)]"
                key={plan.id}
              >
                <div className="flex items-start gap-3">
                  <div className="mt-1 text-[#1428FF]">
                    {plan.plan_type === "weekly_workout" ? (
                      <Dumbbell size={20} aria-hidden="true" />
                    ) : (
                      <Apple size={20} aria-hidden="true" />
                    )}
                  </div>
                  <div>
                    <p className="font-data text-xs uppercase text-[#1428FF]">{savedPlanLabel(plan.plan_type)}</p>
                    <h3 className="mt-1 font-display text-lg font-semibold">{plan.title}</h3>
                    <p className="mt-2 text-xs text-slate">Updated {formatDateTime(plan.updated_at)}</p>
                  </div>
                </div>
                {confirmingPlanId === plan.id ? (
                  <div className="mt-5 rounded-control border border-recovery/30 bg-[#FFF4F0]/75 p-3">
                    <p className="text-xs leading-5 text-recovery">
                      Delete this saved baseline? You can generate a new one later.
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button
                        className="inline-flex min-h-10 items-center justify-center gap-2 rounded-control bg-recovery px-4 py-2 text-sm font-semibold text-white shadow-[0_10px_20px_rgba(201,76,46,0.2)] transition hover:-translate-y-0.5 hover:bg-[#A83C25] disabled:cursor-not-allowed disabled:opacity-70 active:translate-y-0"
                        disabled={deletingPlanId === plan.id}
                        onClick={async () => {
                          setDeletingPlanId(plan.id);
                          await onDeletePlan(plan);
                          setDeletingPlanId(null);
                          setConfirmingPlanId(null);
                        }}
                        type="button"
                      >
                        {deletingPlanId === plan.id ? (
                          <Loader2 className="animate-spin" size={16} aria-hidden="true" />
                        ) : (
                          <Trash2 size={16} aria-hidden="true" />
                        )}
                        Delete plan
                      </button>
                      <button
                        className="inline-flex min-h-10 items-center justify-center rounded-control border border-[#17202A]/20 bg-white/70 px-4 py-2 text-sm font-semibold text-ink transition hover:-translate-y-0.5 hover:border-[#1428FF] hover:bg-white active:translate-y-0"
                        disabled={deletingPlanId === plan.id}
                        onClick={() => setConfirmingPlanId(null)}
                        type="button"
                      >
                        Keep plan
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="mt-5 flex flex-wrap gap-2">
                    <button
                      className="inline-flex min-h-11 items-center justify-center rounded-control bg-[#111820] px-5 py-2 text-sm font-semibold text-white shadow-[0_12px_24px_rgba(6,26,46,0.22)] transition hover:-translate-y-0.5 hover:bg-black hover:shadow-[0_16px_30px_rgba(6,26,46,0.28)] active:translate-y-0"
                      onClick={() => onOpenPlan(plan)}
                      type="button"
                    >
                      Open plan
                    </button>
                    <button
                      className="inline-flex min-h-11 items-center justify-center gap-2 rounded-control border border-recovery/35 bg-white/60 px-4 py-2 text-sm font-semibold text-recovery transition hover:-translate-y-0.5 hover:bg-[#FFF4F0] active:translate-y-0"
                      onClick={() => setConfirmingPlanId(plan.id)}
                      type="button"
                    >
                      <Trash2 size={16} aria-hidden="true" />
                      Delete
                    </button>
                  </div>
                )}
              </article>
            ))}
          </div>
        </section>
      ) : null}

      {dailyAdjustments.length > 0 ? (
        <section>
          <p className="font-data text-xs uppercase text-[#1428FF]">Daily adjustments</p>
          <div className="mt-3 grid gap-4 md:grid-cols-2">
            {dailyAdjustments.map((adjustment) => (
              <article
                className="rounded-[22px] border border-[#17202A]/20 bg-white/55 p-5 shadow-[0_16px_32px_rgba(6,26,46,0.1)] backdrop-blur transition hover:-translate-y-1 hover:bg-white/70 hover:shadow-[0_22px_42px_rgba(6,26,46,0.14)]"
                key={adjustment.id}
              >
                <div className="flex items-start gap-3">
                  <div className="mt-1 text-[#1428FF]">
                    <CalendarCheck size={20} aria-hidden="true" />
                  </div>
                  <div>
                    <p className="font-data text-xs uppercase text-[#1428FF]">
                      {adjustment.current_day} · {adjustment.recovery_status} · {adjustment.readiness_score}
                    </p>
                    <h3 className="mt-1 font-display text-lg font-semibold">{adjustment.title}</h3>
                    <p className="mt-2 text-xs text-slate">Saved {formatDateTime(adjustment.updated_at)}</p>
                  </div>
                </div>
                {confirmingAdjustmentId === adjustment.id ? (
                  <div className="mt-5 rounded-control border border-recovery/30 bg-[#FFF4F0]/75 p-3">
                    <p className="text-xs leading-5 text-recovery">
                      Delete this saved adjustment? Your weekly baselines will stay unchanged.
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button
                        className="inline-flex min-h-10 items-center justify-center gap-2 rounded-control bg-recovery px-4 py-2 text-sm font-semibold text-white shadow-[0_10px_20px_rgba(201,76,46,0.2)] transition hover:-translate-y-0.5 hover:bg-[#A83C25] disabled:cursor-not-allowed disabled:opacity-70 active:translate-y-0"
                        disabled={deletingAdjustmentId === adjustment.id}
                        onClick={async () => {
                          setDeletingAdjustmentId(adjustment.id);
                          await onDeleteAdjustment(adjustment);
                          setDeletingAdjustmentId(null);
                          setConfirmingAdjustmentId(null);
                        }}
                        type="button"
                      >
                        {deletingAdjustmentId === adjustment.id ? (
                          <Loader2 className="animate-spin" size={16} aria-hidden="true" />
                        ) : (
                          <Trash2 size={16} aria-hidden="true" />
                        )}
                        Delete adjustment
                      </button>
                      <button
                        className="inline-flex min-h-10 items-center justify-center rounded-control border border-[#17202A]/20 bg-white/70 px-4 py-2 text-sm font-semibold text-ink transition hover:-translate-y-0.5 hover:border-[#1428FF] hover:bg-white active:translate-y-0"
                        disabled={deletingAdjustmentId === adjustment.id}
                        onClick={() => setConfirmingAdjustmentId(null)}
                        type="button"
                      >
                        Keep adjustment
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="mt-5 flex flex-wrap gap-2">
                    <button
                      className="inline-flex min-h-11 items-center justify-center rounded-control bg-[#111820] px-5 py-2 text-sm font-semibold text-white shadow-[0_12px_24px_rgba(6,26,46,0.22)] transition hover:-translate-y-0.5 hover:bg-black hover:shadow-[0_16px_30px_rgba(6,26,46,0.28)] active:translate-y-0"
                      onClick={() => onOpenAdjustment(adjustment)}
                      type="button"
                    >
                      Open adjustment
                    </button>
                    <button
                      className="inline-flex min-h-11 items-center justify-center gap-2 rounded-control border border-recovery/35 bg-white/60 px-4 py-2 text-sm font-semibold text-recovery transition hover:-translate-y-0.5 hover:bg-[#FFF4F0] active:translate-y-0"
                      onClick={() => setConfirmingAdjustmentId(adjustment.id)}
                      type="button"
                    >
                      <Trash2 size={16} aria-hidden="true" />
                      Delete
                    </button>
                  </div>
                )}
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}

function ProfileForm({
  profile,
  profileState,
  profileError,
  onChange,
  onSubmit
}: {
  profile: UserProfile;
  profileState: string;
  profileError: string | null;
  onChange: (profile: UserProfile) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <form className="grid gap-4 md:grid-cols-2" noValidate onSubmit={onSubmit}>
      <TextInput label="Name" value={profile.name} onChange={(value) => onChange({ ...profile, name: value })} />
      <NumberInput label="Age" value={profile.age} onChange={(value) => onChange({ ...profile, age: value })} />
      <NumberInput
        label="Weight"
        value={profile.weight_kg}
        onChange={(value) => onChange({ ...profile, weight_kg: value })}
      />
      <NumberInput
        label="Height"
        value={profile.height_cm}
        onChange={(value) => onChange({ ...profile, height_cm: value })}
      />
      <label className="block text-sm font-medium text-ink">
        Gender
        <select
          className="mt-1 w-full rounded-control border border-[#17202A]/20 bg-white/70 px-3 py-2 text-sm text-ink shadow-[inset_0_1px_0_rgba(255,255,255,0.55)] transition focus:border-[#1428FF]"
          value={profile.gender}
          onChange={(event) => onChange({ ...profile, gender: event.target.value })}
        >
          <option value="male">Male</option>
          <option value="female">Female</option>
          <option value="other">Other</option>
        </select>
      </label>
      <label className="block text-sm font-medium text-ink">
        Goal
        <select
          className="mt-1 w-full rounded-control border border-[#17202A]/20 bg-white/70 px-3 py-2 text-sm text-ink shadow-[inset_0_1px_0_rgba(255,255,255,0.55)] transition focus:border-[#1428FF]"
          value={profile.goal}
          onChange={(event) => onChange({ ...profile, goal: event.target.value })}
        >
          <option value="hypertrophy">Hypertrophy</option>
          <option value="fat_loss">Fat loss</option>
          <option value="strength">Strength</option>
          <option value="general_fitness">General fitness</option>
        </select>
      </label>
      <label className="block text-sm font-medium text-ink">
        Fitness level
        <select
          className="mt-1 w-full rounded-control border border-[#17202A]/20 bg-white/70 px-3 py-2 text-sm text-ink shadow-[inset_0_1px_0_rgba(255,255,255,0.55)] transition focus:border-[#1428FF]"
          value={profile.fitness_level}
          onChange={(event) => onChange({ ...profile, fitness_level: event.target.value })}
        >
          <option value="beginner">Beginner</option>
          <option value="intermediate">Intermediate</option>
          <option value="advanced">Advanced</option>
        </select>
      </label>
      <div className="md:col-span-2">
        <CsvTextInput
          label="Dietary restrictions"
          values={profile.dietary_restrictions}
          onChange={(value) => onChange({ ...profile, dietary_restrictions: splitCsv(value) })}
        />
      </div>
      <div className="md:col-span-2">
        <CsvTextInput
          label="Available equipment"
          values={profile.equipment_available}
          onChange={(value) => onChange({ ...profile, equipment_available: splitCsv(value) })}
        />
      </div>
      <div className="md:col-span-2">
        <CsvTextInput
          label="Injury history"
          values={profile.injury_history}
          onChange={(value) => onChange({ ...profile, injury_history: splitCsv(value) })}
        />
      </div>
      {profileError ? (
        <p className="rounded-control border border-recovery bg-[#FFF4F0] px-3 py-2 text-sm text-recovery md:col-span-2">
          {profileError}
        </p>
      ) : null}
      {profileState === "saved" ? (
        <p className="rounded-control border border-[#1428FF]/25 bg-[#EFF5FF] px-3 py-2 text-sm text-[#1428FF] md:col-span-2">
          Profile saved. New plans will use these settings.
        </p>
      ) : null}
      <button
        className="inline-flex min-h-11 items-center justify-center rounded-control bg-[#111820] px-5 py-2 text-sm font-semibold text-white shadow-[0_12px_24px_rgba(6,26,46,0.22)] transition hover:-translate-y-0.5 hover:bg-black hover:shadow-[0_16px_30px_rgba(6,26,46,0.28)] disabled:opacity-70 active:translate-y-0 md:col-span-2"
        disabled={profileState === "saving"}
        type="submit"
      >
        {profileState === "saving" ? "Saving profile..." : "Save profile"}
      </button>
    </form>
  );
}

function TextInput({
  label,
  value,
  onChange
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block text-sm font-medium text-ink">
      {label}
      <input
        className="mt-1 w-full rounded-control border border-[#17202A]/20 bg-white/70 px-3 py-2 text-sm text-ink shadow-[inset_0_1px_0_rgba(255,255,255,0.55)] transition focus:border-[#1428FF]"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function CsvTextInput({
  label,
  values,
  onChange
}: {
  label: string;
  values: string[];
  onChange: (value: string) => void;
}) {
  const [draftValue, setDraftValue] = useState(values.join(", "));

  useEffect(() => {
    setDraftValue(values.join(", "));
  }, [values]);

  function commit(nextValue: string) {
    onChange(nextValue);
    setDraftValue(splitCsv(nextValue).join(", "));
  }

  return (
    <label className="block text-sm font-medium text-ink">
      {label}
      <input
        className="mt-1 w-full rounded-control border border-[#17202A]/20 bg-white/70 px-3 py-2 text-sm text-ink shadow-[inset_0_1px_0_rgba(255,255,255,0.55)] transition focus:border-[#1428FF]"
        value={draftValue}
        onBlur={() => commit(draftValue)}
        onChange={(event) => setDraftValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            commit(draftValue);
          }
        }}
      />
    </label>
  );
}

function NumberInput({
  label,
  value,
  onChange
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  const [draftValue, setDraftValue] = useState(String(value));

  useEffect(() => {
    setDraftValue(String(value));
  }, [value]);

  return (
    <label className="block text-sm font-medium text-ink">
      {label}
      <input
        className="mt-1 w-full rounded-control border border-[#17202A]/20 bg-white/70 px-3 py-2 text-sm text-ink shadow-[inset_0_1px_0_rgba(255,255,255,0.55)] transition focus:border-[#1428FF]"
        type="number"
        value={draftValue}
        onBlur={() => {
          if (draftValue.trim() === "") {
            setDraftValue(String(value));
          }
        }}
        onChange={(event) => {
          const nextValue = event.target.value;
          setDraftValue(nextValue);
          if (nextValue.trim() !== "") {
            onChange(Number(nextValue));
          }
        }}
      />
    </label>
  );
}

function SelfReportSlider({
  label,
  value,
  onChange
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="block rounded-control border border-[#17202A]/20 bg-white/55 p-4 text-sm font-medium text-ink shadow-[0_10px_24px_rgba(6,26,46,0.08)] backdrop-blur transition hover:-translate-y-0.5 hover:border-[#1428FF]/55 hover:bg-white/75">
      <span className="flex items-center justify-between gap-3">
        <span>{label}</span>
        <span className="font-data text-xs text-slate">{value}/10</span>
      </span>
      <input
        className="mt-3 w-full accent-[#1428FF]"
        max={10}
        min={0}
        type="range"
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}

function Metric({
  icon: Icon,
  label,
  value
}: {
  icon: LucideIcon;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-control border border-[#17202A]/20 bg-white/55 p-4 shadow-[0_10px_24px_rgba(6,26,46,0.08)] backdrop-blur transition hover:-translate-y-0.5 hover:border-[#1428FF]/45 hover:bg-white/75">
      <Icon size={18} className="text-[#1428FF]" aria-hidden="true" />
      <p className="mt-3 font-data text-2xl font-semibold capitalize">{value}</p>
      <p className="mt-1 text-xs text-slate">{label}</p>
    </div>
  );
}

function PlanSection({
  icon: Icon,
  eyebrow,
  title,
  items,
  notes
}: {
  icon: LucideIcon;
  eyebrow: string;
  title: string;
  items: string[];
  notes: string[];
}) {
  return (
    <section className="rounded-[22px] border border-[#17202A]/20 bg-white/55 p-4 shadow-[0_16px_32px_rgba(6,26,46,0.1)] backdrop-blur">
      <div className="flex items-start gap-3">
        <div className="mt-1 text-[#1428FF]">
          <Icon size={19} aria-hidden="true" />
        </div>
        <div>
          <p className="font-data text-xs uppercase text-[#1428FF]">{eyebrow}</p>
          <h3 className="mt-1 font-display text-lg font-semibold">{title}</h3>
        </div>
      </div>
      <ul className="mt-4 space-y-2">
        {items.map((item, index) => (
          <li className="group/item grid grid-cols-[18px_1fr] gap-2 rounded-control px-2 py-1 text-sm leading-6 text-slate transition hover:bg-white" key={`${item}-${index}`}>
            <span className="mt-2 h-2 w-2 rounded-full bg-[#1428FF]/60 transition group-hover/item:bg-[#1428FF]" />
            <span>
            {item}
            </span>
          </li>
        ))}
      </ul>
      {notes.length > 0 ? (
        <div className="mt-4 border-t border-[#17202A]/15 pt-3">
          {notes.map((note, index) => (
            <p className="rounded-control px-2 py-1 text-xs leading-5 text-slate transition hover:bg-white/70" key={`${note}-${index}`}>
              {note}
            </p>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function parseWeeklyPlan(blocks: string[]): WeeklyDayPlan[] {
  return weekDays.map((day, index) => {
    const matchingBlock =
      blocks.find((block) => block.trim().toLowerCase().startsWith(`${day.toLowerCase()}:`)) ??
      blocks[index] ??
      "";
    return parseDayBlock(day, matchingBlock);
  });
}

function normalizeWorkoutDays(days: WeeklyWorkoutDay[]): WeeklyWorkoutDay[] {
  return weekDays.map((day) => {
    const matchingDay = days.find((item) => item.day.trim().toLowerCase() === day.toLowerCase());
    return matchingDay ?? {
      day,
      title: "Rest or recovery",
      exercises: []
    };
  });
}

function normalizeNutritionDays(days: WeeklyNutritionDay[]): WeeklyNutritionDay[] {
  return weekDays.map((day) => {
    const matchingDay = days.find((item) => item.day.trim().toLowerCase() === day.toLowerCase());
    return matchingDay ?? {
      day,
      focus: "Meal planning",
      meals: []
    };
  });
}

function parseDayBlock(day: string, block: string): WeeklyDayPlan {
  const withoutDay = block.replace(new RegExp(`^${day}:\\s*`, "i"), "").trim();
  if (!withoutDay) {
    return {
      day,
      title: "Rest or recovery",
      details: ["No session details generated for this day."]
    };
  }

  const [rawTitle, ...rawDetailParts] = withoutDay.split(/\s+-\s+/);
  const title = rawTitle.trim() || "Training session";
  const detailsText = rawDetailParts.join(" - ").trim();
  const details = splitWorkoutDetails(detailsText || withoutDay);

  return {
    day,
    title,
    details: details.length > 0 ? details : [withoutDay]
  };
}

function splitWorkoutDetails(value: string): string[] {
  return value
    .split(/\s*;\s*|\.\s+(?=[A-Z0-9])/)
    .map((item) => item.replace(/\.$/, "").trim())
    .filter(Boolean)
    .slice(0, 6);
}

function weeklyWorkoutFromLegacy(plan: PlanResponse): WeeklyWorkoutResponse {
  return {
    title: plan.title,
    duration_minutes: plan.duration_minutes,
    intensity: plan.intensity,
    days: parseWeeklyPlan(plan.blocks).map((day) => ({
      day: day.day,
      title: day.title,
      exercises: day.details.map((detail) => ({
        name: detail,
        prescription: ""
      }))
    })),
    notes: plan.notes,
    rag_context: plan.rag_context
  };
}

function downloadWorkoutPdf(plan: WeeklyWorkoutResponse, days: WeeklyWorkoutDay[]) {
  const pdf = createTextPdf(workoutPdfLines(plan, days));
  const pdfBuffer = pdf.buffer.slice(pdf.byteOffset, pdf.byteOffset + pdf.byteLength) as ArrayBuffer;
  const url = URL.createObjectURL(new Blob([pdfBuffer], { type: "application/pdf" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `${slugify(plan.title)}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function downloadNutritionPdf(plan: WeeklyNutritionResponse, days: WeeklyNutritionDay[]) {
  const pdf = createTextPdf(nutritionPdfLines(plan, days));
  const pdfBuffer = pdf.buffer.slice(pdf.byteOffset, pdf.byteOffset + pdf.byteLength) as ArrayBuffer;
  const url = URL.createObjectURL(new Blob([pdfBuffer], { type: "application/pdf" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `${slugify(plan.title)}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function workoutPdfLines(plan: WeeklyWorkoutResponse, days: WeeklyWorkoutDay[]): string[] {
  const notes = userFacingNotes(plan.notes);
  return [
    plan.title,
    `${plan.duration_minutes} min sessions | ${plan.intensity} intensity`,
    "",
    ...days.flatMap((day) => [
      `${day.day}: ${day.title}`,
      ...day.exercises.map(
        (exercise) =>
          `- ${exercise.name}: ${exercise.prescription}${exercise.notes ? ` (${exercise.notes})` : ""}`
      ),
      ""
    ]),
    ...(notes.length > 0 ? ["Notes", ...notes.map((note) => `- ${note}`)] : [])
  ];
}

function nutritionPdfLines(plan: WeeklyNutritionResponse, days: WeeklyNutritionDay[]): string[] {
  const notes = userFacingNotes(plan.notes);
  return [
    plan.title,
    `${plan.daily_calorie_target} kcal/day | ${plan.daily_protein_g}g protein/day`,
    "",
    ...days.flatMap((day) => [
      `${day.day}: ${day.focus}`,
      ...day.meals.map(
        (meal) =>
          `- ${meal.meal_type}: ${meal.name} (${meal.calories} kcal, ${meal.protein_g}g protein, ${meal.carbs_g}g carbs, ${meal.fat_g}g fat)`
      ),
      ""
    ]),
    ...(notes.length > 0 ? ["Notes", ...notes.map((note) => `- ${note}`)] : [])
  ];
}

function createTextPdf(lines: string[]): Uint8Array {
  const pageWidth = 595;
  const pageHeight = 842;
  const margin = 44;
  const lineHeight = 14;
  const maxLinesPerPage = Math.floor((pageHeight - margin * 2) / lineHeight);
  const pages = chunkLines(flattenWrappedLines(lines, 88), maxLinesPerPage);
  const objects: string[] = [];

  objects.push("<< /Type /Catalog /Pages 2 0 R >>");
  objects.push(
    `<< /Type /Pages /Kids [${pages.map((_, index) => `${3 + index * 2} 0 R`).join(" ")}] /Count ${pages.length} >>`
  );

  pages.forEach((pageLines, index) => {
    const pageObjectNumber = 3 + index * 2;
    const contentObjectNumber = pageObjectNumber + 1;
    objects.push(
      `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${pageWidth} ${pageHeight}] /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> /F2 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >> >> >> /Contents ${contentObjectNumber} 0 R >>`
    );
    const content = pageLines
      .map((line, lineIndex) => {
        const y = pageHeight - margin - lineIndex * lineHeight;
        const isHeading = lineIndex === 0 && index === 0;
        const font = isHeading ? "/F2 17 Tf" : line.endsWith("Notes") ? "/F2 12 Tf" : "/F1 10 Tf";
        return `BT ${font} ${margin} ${y} Td (${escapePdfText(line)}) Tj ET`;
      })
      .join("\n");
    objects.push(`<< /Length ${byteLength(content)} >>\nstream\n${content}\nendstream`);
  });

  let body = "%PDF-1.4\n";
  const offsets: number[] = [0];
  objects.forEach((object, index) => {
    offsets.push(byteLength(body));
    body += `${index + 1} 0 obj\n${object}\nendobj\n`;
  });
  const xrefOffset = byteLength(body);
  body += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  offsets.slice(1).forEach((offset) => {
    body += `${String(offset).padStart(10, "0")} 00000 n \n`;
  });
  body += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF`;
  return new TextEncoder().encode(body);
}

function flattenWrappedLines(lines: string[], maxChars: number): string[] {
  return lines.flatMap((line) => wrapLine(line, maxChars));
}

function wrapLine(line: string, maxChars: number): string[] {
  if (!line || line.length <= maxChars) return [line];
  const words = line.split(" ");
  const wrapped: string[] = [];
  let current = "";
  words.forEach((word) => {
    const next = current ? `${current} ${word}` : word;
    if (next.length > maxChars && current) {
      wrapped.push(current);
      current = word;
    } else {
      current = next;
    }
  });
  if (current) wrapped.push(current);
  return wrapped;
}

function chunkLines(lines: string[], size: number): string[][] {
  const chunks: string[][] = [];
  for (let index = 0; index < lines.length; index += size) {
    chunks.push(lines.slice(index, index + size));
  }
  return chunks.length > 0 ? chunks : [["Workout plan"]];
}

function escapePdfText(value: string): string {
  return value
    .normalize("NFKD")
    .replace(/[^\x20-\x7E]/g, "")
    .replace(/[\\()]/g, "\\$&");
}

function byteLength(value: string): number {
  return new TextEncoder().encode(value).byteLength;
}

function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "") || "weekly-workout-plan";
}

function recoveryLabel(status: RecoveryStatus): string {
  if (status === "RED") return "Recovery RED - reduce today";
  if (status === "YELLOW") return "Recovery YELLOW - adjust today";
  return "Recovery GREEN - follow the plan";
}

function userFacingNotes(notes: string[]): string[] {
  return notes.filter((note) => {
    const lowered = note.toLowerCase();
    return (
      !lowered.includes("gemini") &&
      !lowered.includes("rag") &&
      !lowered.includes("retrieved") &&
      !lowered.includes("retrieval") &&
      !lowered.includes("llm") &&
      !lowered.includes("context")
    );
  });
}

async function fetchSavedPlans(userId: string): Promise<SavedGeneratedPlan[]> {
  try {
    const response = await fetch(`${apiUrl()}/api/profile/${userId}/generated-plans`);
    if (!response.ok) return [];
    return (await response.json()) as SavedGeneratedPlan[];
  } catch {
    return [];
  }
}

async function fetchSavedDailyAdjustments(userId: string): Promise<SavedDailyAdjustment[]> {
  try {
    const response = await fetch(`${apiUrl()}/api/profile/${userId}/daily-adjustments`);
    if (!response.ok) return [];
    return (await response.json()) as SavedDailyAdjustment[];
  } catch {
    return [];
  }
}

function normalizeSavedWorkoutPlan(payload: Record<string, unknown>): WeeklyWorkoutResponse | null {
  if (isWeeklyWorkoutPayload(payload)) return payload;
  if (isLegacyWorkoutPlanPayload(payload)) return weeklyWorkoutFromLegacy(payload);
  return null;
}

function isWeeklyWorkoutPayload(payload: Record<string, unknown>): payload is WeeklyWorkoutResponse {
  return (
    typeof payload.title === "string" &&
    typeof payload.duration_minutes === "number" &&
    typeof payload.intensity === "string" &&
    Array.isArray(payload.days) &&
    Array.isArray(payload.notes)
  );
}

function isLegacyWorkoutPlanPayload(payload: Record<string, unknown>): payload is PlanResponse {
  return (
    typeof payload.title === "string" &&
    typeof payload.duration_minutes === "number" &&
    Array.isArray(payload.blocks) &&
    Array.isArray(payload.notes)
  );
}

function isWeeklyNutritionPayload(payload: Record<string, unknown>): payload is WeeklyNutritionResponse {
  return (
    typeof payload.title === "string" &&
    typeof payload.daily_calorie_target === "number" &&
    typeof payload.daily_protein_g === "number" &&
    Array.isArray(payload.days) &&
    Array.isArray(payload.notes)
  );
}

function isDailyBriefingPayload(payload: Record<string, unknown>): payload is DailyBriefing {
  return (
    typeof payload.profile === "object" &&
    payload.profile !== null &&
    typeof payload.wearable === "object" &&
    payload.wearable !== null &&
    typeof payload.recovery === "object" &&
    payload.recovery !== null &&
    typeof payload.directives === "object" &&
    payload.directives !== null &&
    typeof payload.final_message === "string"
  );
}

function savedPlanLabel(planType: string): string {
  if (planType === "weekly_workout") return "Weekly workout";
  if (planType === "weekly_nutrition") return "Weekly nutrition";
  return "Generated plan";
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(date);
}

function localDateKey(date = new Date()): string {
  const localDate = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return localDate.toISOString().slice(0, 10);
}

function normalizeProfile(profile: DailyBriefing["profile"]): UserProfile {
  return {
    user_id: profile.user_id ?? "demo-user",
    name: profile.name,
    age: profile.age,
    gender: profile.gender ?? "male",
    height_cm: profile.height_cm ?? 178,
    weight_kg: profile.weight_kg ?? 82,
    fitness_level: profile.fitness_level,
    goal: profile.goal,
    dietary_restrictions: profile.dietary_restrictions ?? [],
    equipment_available: profile.equipment_available ?? [],
    injury_history: profile.injury_history ?? []
  };
}

function splitCsv(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function formatActivityLevel(value: string): string {
  return value.replaceAll("_", " ");
}

function dialogTitle(mode: DialogMode): string {
  if (mode === "profile") return "My profile";
  if (mode === "plans") return "Generated plans";
  if (mode === "checkin") return "Morning self-report";
  if (mode === "briefing") return "Daily evaluation";
  if (mode === "workout") return "Weekly workout plan";
  if (mode === "nutrition") return "Diet plan";
  return "";
}

function dialogEyebrow(mode: DialogMode): string {
  if (mode === "profile") return "Account settings";
  if (mode === "plans") return "Saved coaching output";
  if (mode === "checkin") return "Smartwatch sync";
  if (mode === "briefing") return "Supervisor output";
  if (mode === "workout") return "Trainer agent";
  if (mode === "nutrition") return "Nutritionist agent";
  return "";
}

function apiUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}
