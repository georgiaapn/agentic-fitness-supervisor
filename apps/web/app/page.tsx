"use client";

import {
  Activity,
  Apple,
  BrainCircuit,
  Dumbbell,
  Gauge,
  HeartPulse,
  Loader2,
  Moon,
  ShieldCheck,
  User
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

type RecoveryStatus = "GREEN" | "YELLOW" | "RED";

type RagContext = Array<{
  source: string;
  title: string;
  snippet: string;
  score: number;
}>;

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
  wearable: {
    sleep_hours: number;
    sleep_score: number;
    resting_heart_rate: number;
    stress_level: number;
    soreness_quads: number;
    energy_level: number;
    available_minutes: number;
  };
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
  workout: {
    title: string;
    duration_minutes: number;
    intensity: string;
    blocks: string[];
    notes: string[];
    rag_context?: RagContext;
  } | null;
  nutrition: {
    title: string;
    calorie_target: number;
    protein_g: number;
    meals: string[];
    notes: string[];
    rag_context?: RagContext;
  } | null;
  audit: Array<{
    agent: string;
    decision: string;
    evidence: string[];
  }>;
  final_message: string;
};

type UserProfile = Required<DailyBriefing["profile"]>;

const navItems: Array<{ label: string; icon: LucideIcon }> = [
  { label: "Daily briefing", icon: Gauge },
  { label: "Workout plan", icon: Dumbbell },
  { label: "Nutrition", icon: Apple },
  { label: "Recovery", icon: HeartPulse },
  { label: "Profile", icon: User }
];

const fallbackBriefing: DailyBriefing = {
  profile: {
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
  },
  wearable: {
    sleep_hours: 5,
    sleep_score: 42,
    resting_heart_rate: 72,
    stress_level: 7,
    soreness_quads: 8,
    energy_level: 4,
    available_minutes: 35
  },
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
      "3 rounds: Spanish squat isometric 20 sec, band pull-aparts x 15",
      "3 min downshift breathing"
    ],
    notes: ["No heavy squats, lunges, leg press, or deadlifts today."],
    rag_context: [
      {
        source: "exercise_knowledge_base",
        title: "Lower-body mobility reset",
        snippet: "Cat-cow, 90/90 hip switches, couch stretch, and ankle rocks are low-load options.",
        score: 0.88
      }
    ]
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
  const [briefing, setBriefing] = useState<DailyBriefing>(fallbackBriefing);
  const [profile, setProfile] = useState<UserProfile>(normalizeProfile(fallbackBriefing.profile));
  const [runState, setRunState] = useState<"idle" | "running" | "completed" | "failed">("idle");
  const [profileState, setProfileState] = useState<"idle" | "saving" | "saved" | "failed">("idle");
  const [error, setError] = useState<string | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;

    async function loadProfile() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
        const response = await fetch(`${apiUrl}/api/profile/demo-user`);
        if (!response.ok) return;

        const data = (await response.json()) as UserProfile;
        if (!ignore) {
          setProfile(normalizeProfile(data));
        }
      } catch {
        // The fallback profile keeps the dashboard usable when the API is offline.
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

  async function simulateMorningCheckIn() {
    setRunState("running");
    setError(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const response = await fetch(`${apiUrl}/api/check-ins/simulate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile })
      });

      if (!response.ok) {
        throw new Error("The coaching graph did not return a valid briefing.");
      }

      const data = (await response.json()) as DailyBriefing;
      setBriefing(data);
      setProfile(normalizeProfile(data.profile));
      setRunState("completed");
    } catch (requestError) {
      setRunState("failed");
      setError(requestError instanceof Error ? requestError.message : "Unable to run check-in.");
    }
  }

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setProfileState("saving");
    setProfileError(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const response = await fetch(`${apiUrl}/api/profile/${profile.user_id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(profile)
      });

      if (!response.ok) {
        throw new Error("Profile could not be saved.");
      }

      const data = (await response.json()) as UserProfile;
      setProfile(normalizeProfile(data));
      setProfileState("saved");
    } catch (requestError) {
      setProfileState("failed");
      setProfileError(requestError instanceof Error ? requestError.message : "Unable to save profile.");
    }
  }

  return (
    <main className="min-h-screen">
      <div className="grid min-h-screen grid-cols-1 lg:grid-cols-[260px_1fr]">
        <aside className="border-b border-border bg-panel/80 px-5 py-5 lg:border-b-0 lg:border-r">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-control bg-primary text-white">
              <BrainCircuit size={21} aria-hidden="true" />
            </div>
            <div>
              <p className="font-display text-sm font-semibold">Agentic Fitness</p>
              <p className="text-xs text-slate">Supervisor board</p>
            </div>
          </div>

          <nav className="mt-8 grid gap-2" aria-label="Primary">
            {navItems.map(({ label, icon: Icon }) => (
              <a
                className="flex items-center gap-3 rounded-control px-3 py-2 text-sm text-slate transition hover:bg-surface hover:text-ink"
                href="#daily-briefing"
                key={label}
              >
                <Icon size={18} aria-hidden="true" />
                {label}
              </a>
            ))}
          </nav>
        </aside>

        <section className="px-4 py-5 sm:px-6 lg:px-8">
          <header className="flex flex-col gap-4 border-b border-border pb-5 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="font-data text-xs uppercase text-primary">Morning coaching graph</p>
              <h1 className="mt-2 font-display text-3xl font-semibold tracking-normal text-ink">
                Daily Briefing
              </h1>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <div className="rounded-control border border-border bg-panel px-3 py-2 text-sm text-slate">
                {profile.name} · {profile.fitness_level} · {profile.goal.replace("_", " ")}
              </div>
              <button
                className="inline-flex min-h-10 items-center justify-center gap-2 rounded-control bg-primary px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#126961] disabled:opacity-70"
                disabled={runState === "running"}
                onClick={simulateMorningCheckIn}
                type="button"
              >
                {runState === "running" ? (
                  <Loader2 className="animate-spin" size={17} aria-hidden="true" />
                ) : (
                  <Activity size={17} aria-hidden="true" />
                )}
                Simulate Morning Check-in
              </button>
            </div>
          </header>

          {error ? (
            <div className="mt-5 rounded-control border border-recovery bg-[#FFF4F0] px-4 py-3 text-sm text-recovery">
              {error} The fallback briefing is still visible so the UI can be reviewed offline.
            </div>
          ) : null}

          <div
            id="daily-briefing"
            className="grid gap-5 py-6 xl:grid-cols-[minmax(0,1fr)_360px]"
          >
            <section className="rounded-briefing border border-border bg-panel p-5">
              <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div>
                  <div className={`inline-flex rounded-control border px-3 py-1 text-sm ${statusTone}`}>
                    Recovery {briefing.recovery.status}
                  </div>
                  <h2 className="mt-4 font-display text-2xl font-semibold">{briefing.final_message}</h2>
                  <p className="mt-3 max-w-3xl text-sm leading-6 text-slate">
                    {briefing.directives.rationale}
                  </p>
                </div>
                <div className="rounded-control bg-surface p-4 text-center">
                  <p className="font-data text-4xl font-semibold">{briefing.recovery.readiness_score}</p>
                  <p className="mt-1 text-xs text-slate">readiness score</p>
                </div>
              </div>

              <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <Metric icon={Moon} label="Sleep" value={`${briefing.wearable.sleep_hours}h`} />
                <Metric icon={HeartPulse} label="Resting HR" value={`${briefing.wearable.resting_heart_rate}`} />
                <Metric icon={Activity} label="Quad soreness" value={`${briefing.wearable.soreness_quads}/10`} />
                <Metric icon={Gauge} label="Energy" value={`${briefing.wearable.energy_level}/10`} />
              </div>

              <div className="mt-7 grid gap-5 lg:grid-cols-2">
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
                          `${briefing.nutrition.protein_g}g protein`
                        ]
                      : []
                  }
                />
              </div>
            </section>

            <aside className="space-y-5">
              <section className="rounded-briefing border border-border bg-panel p-5">
                <div className="flex items-center gap-2">
                  <User size={19} className="text-primary" aria-hidden="true" />
                  <h2 className="font-display text-lg font-semibold">Profile Settings</h2>
                </div>
                <form className="mt-4 space-y-3" noValidate onSubmit={saveProfile}>
                  <label className="block text-sm font-medium text-ink">
                    Name
                    <input
                      className="mt-1 w-full rounded-control border border-border bg-white px-3 py-2 text-sm text-ink"
                      value={profile.name}
                      onChange={(event) => setProfile({ ...profile, name: event.target.value })}
                    />
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    <label className="block text-sm font-medium text-ink">
                      Age
                      <input
                        className="mt-1 w-full rounded-control border border-border bg-white px-3 py-2 text-sm text-ink"
                        type="number"
                        value={profile.age}
                        onChange={(event) =>
                          setProfile({ ...profile, age: Number(event.target.value) })
                        }
                      />
                    </label>
                    <label className="block text-sm font-medium text-ink">
                      Weight
                      <input
                        className="mt-1 w-full rounded-control border border-border bg-white px-3 py-2 text-sm text-ink"
                        type="number"
                        value={profile.weight_kg}
                        onChange={(event) =>
                          setProfile({ ...profile, weight_kg: Number(event.target.value) })
                        }
                      />
                    </label>
                  </div>
                  <label className="block text-sm font-medium text-ink">
                    Goal
                    <select
                      className="mt-1 w-full rounded-control border border-border bg-white px-3 py-2 text-sm text-ink"
                      value={profile.goal}
                      onChange={(event) => setProfile({ ...profile, goal: event.target.value })}
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
                      onChange={(event) =>
                        setProfile({ ...profile, fitness_level: event.target.value })
                      }
                    >
                      <option value="beginner">Beginner</option>
                      <option value="intermediate">Intermediate</option>
                      <option value="advanced">Advanced</option>
                    </select>
                  </label>
                  <label className="block text-sm font-medium text-ink">
                    Dietary restrictions
                    <input
                      className="mt-1 w-full rounded-control border border-border bg-white px-3 py-2 text-sm text-ink"
                      value={profile.dietary_restrictions.join(", ")}
                      onChange={(event) =>
                        setProfile({
                          ...profile,
                          dietary_restrictions: splitCsv(event.target.value)
                        })
                      }
                    />
                  </label>
                  {profileError ? (
                    <p className="rounded-control border border-recovery bg-[#FFF4F0] px-3 py-2 text-sm text-recovery">
                      {profileError}
                    </p>
                  ) : null}
                  {profileState === "saved" ? (
                    <p className="rounded-control border border-primary bg-[#EEF8F5] px-3 py-2 text-sm text-primary">
                      Profile saved. The next check-in will use these settings.
                    </p>
                  ) : null}
                  <button
                    className="inline-flex min-h-10 w-full items-center justify-center rounded-control border border-primary px-4 py-2 text-sm font-semibold text-primary transition hover:bg-[#EEF8F5] disabled:opacity-70"
                    disabled={profileState === "saving"}
                    type="submit"
                  >
                    {profileState === "saving" ? "Saving profile..." : "Save profile"}
                  </button>
                </form>
              </section>

              <section className="rounded-briefing border border-border bg-panel p-5">
                <div className="flex items-center gap-2">
                  <ShieldCheck size={19} className="text-primary" aria-hidden="true" />
                  <h2 className="font-display text-lg font-semibold">Supervisor Trace</h2>
                </div>
                <div className="mt-5 space-y-4">
                  {briefing.audit.map((item) => (
                    <div className="border-l-2 border-primary pl-4" key={`${item.agent}-${item.decision}`}>
                      <p className="font-data text-xs uppercase text-primary">{item.agent}</p>
                      <p className="mt-1 text-sm font-medium text-ink">{item.decision}</p>
                      <p className="mt-2 text-xs leading-5 text-slate">{item.evidence.join(" · ")}</p>
                    </div>
                  ))}
                </div>
              </section>

              <section className="rounded-briefing border border-border bg-panel p-5">
                <h2 className="font-display text-lg font-semibold">Active Constraints</h2>
                <ul className="mt-4 space-y-3">
                  {briefing.recovery.constraints.map((constraint) => (
                    <li className="rounded-control bg-surface px-3 py-2 text-sm text-slate" key={constraint}>
                      {constraint}
                    </li>
                  ))}
                </ul>
              </section>
            </aside>
          </div>
        </section>
      </div>
    </main>
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
    <div className="rounded-control border border-border bg-surface p-4">
      <Icon size={18} className="text-primary" aria-hidden="true" />
      <p className="mt-3 font-data text-2xl font-semibold">{value}</p>
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
    <section className="rounded-control border border-border bg-surface p-4">
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
        {items.map((item) => (
          <li className="text-sm leading-6 text-slate" key={item}>
            {item}
          </li>
        ))}
      </ul>
      {notes.length > 0 ? (
        <div className="mt-4 border-t border-border pt-3">
          {notes.map((note) => (
            <p className="text-xs leading-5 text-slate" key={note}>
              {note}
            </p>
          ))}
        </div>
      ) : null}
      {context && context.length > 0 ? (
        <div className="mt-4 border-t border-border pt-3">
          <p className="font-data text-xs uppercase text-primary">Retrieved context</p>
          <div className="mt-3 space-y-3">
            {context.slice(0, 3).map((hit) => (
              <div className="border-l-2 border-primary/40 pl-3" key={`${hit.source}-${hit.title}`}>
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
