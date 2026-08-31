"use client";

import {
  Activity,
  Apple,
  CheckCircle2,
  ClipboardCheck,
  Dumbbell,
  Gauge,
  HeartPulse,
  Loader2,
  LogOut,
  Moon,
  Sparkles,
  Timer,
  User,
  X
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

type RecoveryStatus = "GREEN" | "YELLOW" | "RED";
type DialogMode = "none" | "profile" | "checkin" | "briefing" | "workout" | "nutrition";

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

type NutritionResponse = {
  title: string;
  calorie_target: number;
  protein_g: number;
  meals: string[];
  notes: string[];
  rag_context?: RagContext;
};

type UserProfile = Required<DailyBriefing["profile"]>;
type MorningSelfReport = {
  soreness_quads: number;
  soreness_upper: number;
  pain_level: number;
  available_minutes: number;
};

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
  const [workoutPlan, setWorkoutPlan] = useState<PlanResponse | null>(null);
  const [nutritionPlan, setNutritionPlan] = useState<NutritionResponse | null>(null);
  const [dialogMode, setDialogMode] = useState<DialogMode>("none");
  const [runState, setRunState] = useState<"idle" | "running" | "completed" | "failed">("idle");
  const [profileState, setProfileState] = useState<"idle" | "saving" | "saved" | "failed">("idle");
  const [error, setError] = useState<string | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);

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

    loadProfile();
    return () => {
      ignore = true;
    };
  }, []);

  const statusTone = useMemo(() => {
    if (briefing.recovery.status === "RED") return "border-recovery text-recovery bg-[#FFF4F0]";
    if (briefing.recovery.status === "YELLOW") return "border-[#B58B16] text-[#7A5A00] bg-[#FFF8E3]";
    return "border-primary text-primary bg-[#EEF8F5]";
  }, [briefing.recovery.status]);

  async function generateWorkoutPlan() {
    setRunState("running");
    setError(null);
    try {
      const response = await fetch(`${apiUrl()}/api/plans/workout/weekly`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(profile)
      });
      if (!response.ok) throw new Error("Workout plan could not be generated.");
      const data = (await response.json()) as PlanResponse;
      setWorkoutPlan(data);
      setDialogMode("workout");
      setRunState("completed");
    } catch (requestError) {
      setRunState("failed");
      setError(errorMessage(requestError, "Unable to generate workout plan."));
    }
  }

  async function generateNutritionPlan() {
    setRunState("running");
    setError(null);
    try {
      const response = await fetch(`${apiUrl()}/api/plans/nutrition`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(profile)
      });
      if (!response.ok) throw new Error("Diet plan could not be generated.");
      const data = (await response.json()) as NutritionResponse;
      setNutritionPlan(data);
      setDialogMode("nutrition");
      setRunState("completed");
    } catch (requestError) {
      setRunState("failed");
      setError(errorMessage(requestError, "Unable to generate diet plan."));
    }
  }

  async function simulateMorningCheckIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setRunState("running");
    setError(null);

    try {
      const response = await fetch(`${apiUrl()}/api/check-ins/simulate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile, self_report: selfReport })
      });

      if (!response.ok) throw new Error("The coaching graph did not return a valid briefing.");

      const data = (await response.json()) as DailyBriefing;
      setBriefing(data);
      setProfile(normalizeProfile(data.profile));
      setDialogMode("briefing");
      setRunState("completed");
    } catch (requestError) {
      setRunState("failed");
      setError(errorMessage(requestError, "Unable to run check-in."));
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
            label="Get Workout Plan"
            description="Goal-oriented 7-day training split customized to your fitness level and equipment."
            accent="from-[#78D7FF]/75 to-[#2268D8]/45"
            onClick={generateWorkoutPlan}
            busy={runState === "running"}
          />
          <ActionFrame
            icon={Apple}
            label="Get Diet Plan"
            description="Personalized 7-day nutrition and macro blueprint built around your metabolic targets."
            accent="from-[#A9F0E0]/80 to-[#2997D8]/45"
            onClick={generateNutritionPlan}
            busy={runState === "running"}
          />
          <ActionFrame
            icon={ClipboardCheck}
            label="Check in"
            description="Analyze biometrics, assess readiness, and establish today's coaching strategy."
            accent="from-[#BFF4F1]/90 to-[#2672DE]/45"
            onClick={() => setDialogMode("checkin")}
            busy={runState === "running"}
          />
        </div>
      </section>

      {error ? (
        <div className="relative z-10 mx-auto mt-8 max-w-3xl rounded-control border border-recovery bg-[#FFF4F0] px-4 py-3 text-sm text-recovery shadow-[0_18px_40px_rgba(6,26,46,0.14)]">
          {error}
        </div>
      ) : null}

      {dialogMode !== "none" ? (
        <div
          aria-labelledby="dialog-title"
          aria-modal="true"
          className="fixed inset-0 z-50 grid place-items-center bg-[#061A2E]/65 px-4 py-8 backdrop-blur-sm"
          role="dialog"
        >
          <div className="modal-pop max-h-[90vh] w-full max-w-5xl overflow-y-auto rounded-briefing border border-white/70 bg-panel/95 p-5 shadow-[0_28px_90px_rgba(0,0,0,0.34)]">
            <div className="mb-5 flex items-start justify-between gap-4">
              <div>
                <p className="font-data text-xs uppercase text-primary">{dialogEyebrow(dialogMode)}</p>
                <h2 id="dialog-title" className="mt-1 font-display text-2xl font-semibold">
                  {dialogTitle(dialogMode)}
                </h2>
              </div>
              <button
                aria-label="Close dialog"
                className="inline-flex h-9 w-9 items-center justify-center rounded-control border border-border text-slate transition hover:-translate-y-0.5 hover:bg-surface hover:text-ink active:translate-y-0"
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

            {dialogMode === "checkin" ? (
              <form className="space-y-5" noValidate onSubmit={simulateMorningCheckIn}>
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
                    className="mt-1 w-full rounded-control border border-border bg-white px-3 py-2 text-sm text-ink"
                    max={180}
                    min={5}
                    type="number"
                    value={selfReport.available_minutes}
                    onChange={(event) =>
                      setSelfReport({ ...selfReport, available_minutes: Number(event.target.value) })
                    }
                  />
                </label>
                <div className="grid gap-3 rounded-control border border-border bg-surface p-4 text-sm text-slate md:grid-cols-3">
                  <p className="flex items-center gap-2">
                    <Moon size={16} className="text-primary" aria-hidden="true" />
                    Smartwatch sleep sync
                  </p>
                  <p className="flex items-center gap-2">
                    <HeartPulse size={16} className="text-primary" aria-hidden="true" />
                    HR and SpO2 sample
                  </p>
                  <p className="flex items-center gap-2">
                    <Timer size={16} className="text-primary" aria-hidden="true" />
                    Round-robin CSV row
                  </p>
                </div>
                <button
                  className="inline-flex min-h-10 items-center justify-center gap-2 rounded-control bg-primary px-4 py-2 text-sm font-semibold text-white shadow-[0_12px_26px_rgba(22,126,118,0.24)] transition hover:-translate-y-0.5 hover:bg-[#126961] hover:shadow-[0_16px_32px_rgba(22,126,118,0.28)] disabled:opacity-70 active:translate-y-0"
                  disabled={runState === "running"}
                  type="submit"
                >
                  {runState === "running" ? (
                    <Loader2 className="animate-spin" size={17} aria-hidden="true" />
                  ) : (
                    <CheckCircle2 size={17} aria-hidden="true" />
                  )}
                  Run evaluation
                </button>
              </form>
            ) : null}

            {dialogMode === "briefing" ? (
              <BriefingResult briefing={briefing} statusTone={statusTone} />
            ) : null}

            {dialogMode === "workout" && workoutPlan ? (
              <PlanSection
                icon={Dumbbell}
                title={workoutPlan.title}
                eyebrow="Trainer weekly plan"
                items={workoutPlan.blocks}
                notes={workoutPlan.notes}
                context={workoutPlan.rag_context ?? []}
              />
            ) : null}

            {dialogMode === "nutrition" && nutritionPlan ? (
              <PlanSection
                icon={Apple}
                title={nutritionPlan.title}
                eyebrow="Diet plan"
                items={nutritionPlan.meals}
                notes={[
                  `${nutritionPlan.calorie_target} kcal target`,
                  `${nutritionPlan.protein_g}g protein`,
                  ...nutritionPlan.notes
                ]}
                context={nutritionPlan.rag_context ?? []}
              />
            ) : null}
          </div>
        </div>
      ) : null}
    </main>
  );
}

function ActionFrame({
  icon: Icon,
  kicker,
  label,
  description,
  accent,
  onClick,
  busy
}: {
  icon: LucideIcon;
  kicker: string;
  label: string;
  description: string;
  accent: string;
  onClick: () => void;
  busy: boolean;
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
          disabled={busy}
          onClick={onClick}
          type="button"
        >
          {busy ? <Loader2 className="animate-spin" size={17} aria-hidden="true" /> : label}
        </button>
      </div>
    </section>
  );
}

function BriefingResult({
  briefing,
  statusTone
}: {
  briefing: DailyBriefing;
  statusTone: string;
}) {
  return (
    <div className="space-y-5">
      <section className="rounded-briefing border border-border bg-panel p-5">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <div className={`inline-flex rounded-control border px-3 py-1 text-sm ${statusTone}`}>
              Recovery {briefing.recovery.status}
            </div>
            <h3 className="mt-4 font-display text-2xl font-semibold">{briefing.final_message}</h3>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-slate">{briefing.directives.rationale}</p>
          </div>
          <div className="rounded-control bg-surface p-4 text-center">
            <p className="font-data text-4xl font-semibold">{briefing.recovery.readiness_score}</p>
            <p className="mt-1 text-xs text-slate">readiness score</p>
          </div>
        </div>

        <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Metric icon={Moon} label="Sleep" value={`${briefing.wearable.sleep_hours}h`} />
          <Metric icon={HeartPulse} label="Resting HR" value={`${briefing.wearable.resting_heart_rate}`} />
          <Metric icon={HeartPulse} label="Blood oxygen" value={`${briefing.wearable.blood_oxygen_level}%`} />
          <Metric icon={Activity} label="Steps" value={briefing.wearable.step_count.toLocaleString()} />
          <Metric icon={Activity} label="Activity" value={formatActivityLevel(briefing.wearable.activity_level)} />
          <Metric icon={Activity} label="Quad soreness" value={`${briefing.wearable.soreness_quads}/10`} />
          <Metric icon={Gauge} label="Energy" value={`${briefing.wearable.energy_level}/10`} />
        </div>
      </section>

      <div className="grid gap-5 lg:grid-cols-2">
        <PlanSection
          icon={Dumbbell}
          title={briefing.workout?.title ?? "Trainer skipped"}
          eyebrow="Trainer adjustment"
          items={briefing.workout?.blocks ?? ["No training session generated today."]}
          notes={briefing.workout?.notes ?? []}
          context={briefing.workout?.rag_context ?? []}
        />
        <PlanSection
          icon={Apple}
          title={briefing.nutrition?.title ?? "Nutrition skipped"}
          eyebrow="Nutrition plan"
          items={briefing.nutrition?.meals ?? ["No nutrition plan generated today."]}
          notes={
            briefing.nutrition
              ? [
                  `${briefing.nutrition.calorie_target} kcal target`,
                  `${briefing.nutrition.protein_g}g protein`,
                  ...briefing.nutrition.notes
                ]
              : []
          }
          context={briefing.nutrition?.rag_context ?? []}
        />
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <section className="rounded-control border border-border bg-surface p-4">
          <h3 className="font-display text-lg font-semibold">Supervisor Trace</h3>
          <div className="mt-5 space-y-4">
            {briefing.audit.map((item, index) => (
              <div className="border-l-2 border-primary pl-4" key={`${item.agent}-${index}`}>
                <p className="font-data text-xs uppercase text-primary">{item.agent}</p>
                <p className="mt-1 text-sm font-medium text-ink">{item.decision}</p>
                <p className="mt-2 text-xs leading-5 text-slate">{item.evidence.join(" - ")}</p>
              </div>
            ))}
          </div>
        </section>
        <section className="rounded-control border border-border bg-surface p-4">
          <h3 className="font-display text-lg font-semibold">Active Constraints</h3>
          <ul className="mt-4 space-y-3">
            {briefing.recovery.constraints.map((constraint, index) => (
              <li className="rounded-control bg-panel px-3 py-2 text-sm text-slate" key={`${constraint}-${index}`}>
                {constraint}
              </li>
            ))}
          </ul>
        </section>
      </div>
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
        Goal
        <select
          className="mt-1 w-full rounded-control border border-border bg-white px-3 py-2 text-sm text-ink"
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
          className="mt-1 w-full rounded-control border border-border bg-white px-3 py-2 text-sm text-ink"
          value={profile.fitness_level}
          onChange={(event) => onChange({ ...profile, fitness_level: event.target.value })}
        >
          <option value="beginner">Beginner</option>
          <option value="intermediate">Intermediate</option>
          <option value="advanced">Advanced</option>
        </select>
      </label>
      <div className="md:col-span-2">
        <TextInput
          label="Dietary restrictions"
          value={profile.dietary_restrictions.join(", ")}
          onChange={(value) => onChange({ ...profile, dietary_restrictions: splitCsv(value) })}
        />
      </div>
      {profileError ? (
        <p className="rounded-control border border-recovery bg-[#FFF4F0] px-3 py-2 text-sm text-recovery md:col-span-2">
          {profileError}
        </p>
      ) : null}
      {profileState === "saved" ? (
        <p className="rounded-control border border-primary bg-[#EEF8F5] px-3 py-2 text-sm text-primary md:col-span-2">
          Profile saved. New plans will use these settings.
        </p>
      ) : null}
      <button
        className="inline-flex min-h-10 items-center justify-center rounded-control border border-primary px-4 py-2 text-sm font-semibold text-primary transition hover:bg-[#EEF8F5] disabled:opacity-70 md:col-span-2"
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
        className="mt-1 w-full rounded-control border border-border bg-white px-3 py-2 text-sm text-ink"
        value={value}
        onChange={(event) => onChange(event.target.value)}
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
  return (
    <label className="block text-sm font-medium text-ink">
      {label}
      <input
        className="mt-1 w-full rounded-control border border-border bg-white px-3 py-2 text-sm text-ink"
        type="number"
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
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
    <label className="block rounded-control border border-border bg-surface p-4 text-sm font-medium text-ink transition hover:-translate-y-0.5 hover:border-primary/50 hover:bg-white">
      <span className="flex items-center justify-between gap-3">
        <span>{label}</span>
        <span className="font-data text-xs text-slate">{value}/10</span>
      </span>
      <input
        className="mt-3 w-full accent-primary"
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
    <div className="rounded-control border border-border bg-surface p-4 transition hover:-translate-y-0.5 hover:border-primary/40 hover:bg-white">
      <Icon size={18} className="text-primary" aria-hidden="true" />
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
  notes,
  context
}: {
  icon: LucideIcon;
  eyebrow: string;
  title: string;
  items: string[];
  notes: string[];
  context?: RagContext;
}) {
  return (
    <section className="rounded-control border border-border bg-surface p-4 shadow-[0_12px_28px_rgba(16,24,32,0.06)]">
      <div className="flex items-start gap-3">
        <div className="mt-1 text-primary">
          <Icon size={19} aria-hidden="true" />
        </div>
        <div>
          <p className="font-data text-xs uppercase text-primary">{eyebrow}</p>
          <h3 className="mt-1 font-display text-lg font-semibold">{title}</h3>
        </div>
      </div>
      <ul className="mt-4 space-y-2">
        {items.map((item, index) => (
          <li className="group/item grid grid-cols-[18px_1fr] gap-2 rounded-control px-2 py-1 text-sm leading-6 text-slate transition hover:bg-white" key={`${item}-${index}`}>
            <span className="mt-2 h-2 w-2 rounded-full bg-primary/60 transition group-hover/item:bg-primary" />
            <span>
            {item}
            </span>
          </li>
        ))}
      </ul>
      {notes.length > 0 ? (
        <div className="mt-4 border-t border-border pt-3">
          {notes.map((note, index) => (
            <p className="rounded-control px-2 py-1 text-xs leading-5 text-slate transition hover:bg-white" key={`${note}-${index}`}>
              {note}
            </p>
          ))}
        </div>
      ) : null}
      {context && context.length > 0 ? (
        <div className="mt-4 border-t border-border pt-3">
          <p className="font-data text-xs uppercase text-primary">Retrieved context</p>
          <div className="mt-3 space-y-3">
            {context.slice(0, 3).map((hit, index) => (
              <div className="rounded-control border-l-2 border-primary/40 px-3 py-2 transition hover:border-primary hover:bg-white" key={`${hit.source}-${hit.title}-${index}`}>
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm font-medium text-ink">{hit.title}</p>
                  <span className="font-data text-xs text-slate">{Math.round(hit.score * 100)}%</span>
                </div>
                <p className="mt-1 line-clamp-2 text-xs leading-5 text-slate">{hit.snippet}</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
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
  if (mode === "checkin") return "Morning self-report";
  if (mode === "briefing") return "Daily evaluation";
  if (mode === "workout") return "Weekly workout plan";
  if (mode === "nutrition") return "Diet plan";
  return "";
}

function dialogEyebrow(mode: DialogMode): string {
  if (mode === "profile") return "Account settings";
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
