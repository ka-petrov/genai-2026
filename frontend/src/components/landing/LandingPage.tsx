import { useState, useRef, useCallback } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useAppStore } from "../../store";
import {
  PinIcon,
  ArrowRightIcon,
  MapIcon,
  ChatBubbleIcon,
  PersonIcon,
  FamilyIcon,
  TransitIcon,
  ShieldIcon,
  SparklesIcon,
} from "../../ds";
import AddressAutocomplete from "./AddressAutocomplete";

const SUGGESTION_CHIPS = [
  { Icon: PersonIcon, label: "How walkable is this area?" },
  { Icon: FamilyIcon, label: "Is this good for families?" },
  { Icon: TransitIcon, label: "What transit options are nearby?" },
  { Icon: ShieldIcon, label: "How safe is this neighborhood?" },
  { Icon: SparklesIcon, label: "Tell me about this area" },
] as const;

export default function LandingPage() {
  const navigate = useNavigate();
  const setLanding = useAppStore((s) => s.setLanding);

  const [question, setQuestion] = useState("");
  const [address, setAddress] = useState("");
  const [coords, setCoords] = useState<{ lat: number; lon: number } | null>(
    null,
  );
  const [submitting, setSubmitting] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const submit = useCallback(() => {
    const q = question.trim();
    if (!q || submitting) return;
    setSubmitting(true);
    setLanding({
      question: q,
      address: address.trim() || null,
      coords,
    });
    void navigate({ to: "/map" });
  }, [question, address, coords, submitting, setLanding, navigate]);

  const handleChipClick = (label: string) => {
    setQuestion(label);
    textareaRef.current?.focus();
  };

  return (
    <div className="h-full overflow-y-auto bg-surface-base text-fg flex flex-col">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 py-4 md:px-10">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center">
            <PinIcon className="w-5 h-5 text-fg" />
          </div>
          <span className="text-lg font-bold tracking-tight">GenGeo</span>
        </div>
      </nav>

      {/* Hero */}
      <header className="flex flex-col items-center text-center px-6 pt-12 pb-6 md:pt-20 md:pb-10">
        <span className="text-xs font-semibold tracking-[0.2em] uppercase text-accent-text mb-4">
          Location Intelligence
        </span>
        <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight leading-tight max-w-3xl">
          Ask anything about{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-gradient-from to-gradient-to">
            any location
          </span>
        </h1>
        <p className="mt-4 text-base md:text-lg text-fg-muted max-w-2xl leading-relaxed">
          Get AI-powered insights about walkability, transit, safety, amenities,
          and more — grounded in real geospatial data.
        </p>
      </header>

      {/* Prompt card */}
      <section className="flex-1 flex flex-col items-center px-4 md:px-6">
        <div className="w-full max-w-2xl">
          <div className="relative rounded-2xl bg-surface-raised border border-border-default shadow-2xl shadow-accent/5">
            {/* Decorative grid */}
            <div className="absolute inset-0 rounded-2xl overflow-hidden opacity-[0.07] pointer-events-none bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGRlZnM+PHBhdHRlcm4gaWQ9ImdyaWQiIHdpZHRoPSI2MCIgaGVpZ2h0PSI2MCIgcGF0dGVyblVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+PHBhdGggZD0iTSAxMCAwIEwgMCAwIDAgMTAiIGZpbGw9Im5vbmUiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMC41Ii8+PC9wYXR0ZXJuPjwvZGVmcz48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSJ1cmwoI2dyaWQpIi8+PC9zdmc+')]" />

            <div className="relative p-6 md:p-8">
              <h2 className="text-lg md:text-xl font-semibold text-center mb-6">
                What would you like to know?
              </h2>

              {/* Question textarea */}
              <div className="relative mb-3">
                <textarea
                  ref={textareaRef}
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onInput={(e) => {
                    const el = e.currentTarget;
                    el.style.height = "auto";
                    el.style.height =
                      Math.min(Math.max(el.scrollHeight, 100), 200) + "px";
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      submit();
                    }
                  }}
                  placeholder="e.g. How walkable is this neighborhood? Is it good for families?"
                  className="w-full min-h-[100px] bg-surface-overlay border border-border-subtle rounded-xl px-4 py-3 text-sm text-fg-secondary placeholder:text-fg-faint focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-transparent resize-none transition-all"
                />
                <button
                  onClick={submit}
                  disabled={!question.trim() || submitting}
                  className="absolute bottom-3 right-3 w-9 h-9 rounded-full bg-accent text-fg flex items-center justify-center hover:bg-accent-hover disabled:opacity-30 disabled:cursor-not-allowed transition-all cursor-pointer"
                >
                  {submitting ? (
                    <div className="w-4 h-4 border-2 border-fg/30 border-t-fg rounded-full animate-spin" />
                  ) : (
                    <ArrowRightIcon />
                  )}
                </button>
              </div>

              {/* Address field */}
              <AddressAutocomplete
                value={address}
                onChange={setAddress}
                onPlaceSelect={setCoords}
              />
            </div>
          </div>

          {/* Suggestion chips */}
          <div className="flex overflow-x-auto md:flex-wrap md:justify-center gap-2 mt-5 pb-2 md:pb-0 scrollbar-none">
            {SUGGESTION_CHIPS.map((chip) => (
              <button
                key={chip.label}
                onClick={() => handleChipClick(chip.label)}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-full border border-border-subtle bg-surface-raised/80 text-sm text-fg-secondary hover:bg-surface-overlay hover:border-border-strong hover:text-fg transition-all cursor-pointer whitespace-nowrap shrink-0"
              >
                <chip.Icon />
                {chip.label}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="px-6 py-16 md:py-24 md:px-10">
        <div className="max-w-5xl mx-auto">
          <h3 className="text-xs font-semibold tracking-[0.2em] uppercase text-accent-text text-center mb-3">
            Powered by real data
          </h3>
          <h2 className="text-2xl md:text-3xl font-bold text-center mb-12">
            Understand any neighborhood in seconds
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <FeatureCard
              icon={<MapIcon className="w-5 h-5 text-accent-text" />}
              title="Geospatial Analysis"
              description="Real-time data from OpenStreetMap and other sources, covering amenities, transit, land use, and more."
            />
            <FeatureCard
              icon={<ChatBubbleIcon className="w-5 h-5 text-accent-text" />}
              title="Conversational AI"
              description="Ask follow-up questions in natural language. The AI maintains context about the area you're exploring."
            />
            <FeatureCard
              icon={<PinIcon className="w-5 h-5 text-accent-text" strokeWidth={1.5} />}
              title="Interactive Map"
              description="Drop a pin anywhere, set your radius, and get a comprehensive neighborhood profile instantly."
            />
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border-default px-6 py-6 text-center">
        <p className="text-xs text-fg-faint">
          Built with OpenStreetMap data. AI responses are informational and may
          not reflect real-time conditions.
        </p>
      </footer>
    </div>
  );
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-xl border border-border-default bg-surface-raised p-6 hover:border-border-strong transition-colors">
      <div className="w-10 h-10 rounded-lg bg-accent-subtle flex items-center justify-center mb-4">
        {icon}
      </div>
      <h4 className="text-base font-semibold mb-2">{title}</h4>
      <p className="text-sm text-fg-muted leading-relaxed">{description}</p>
    </div>
  );
}
