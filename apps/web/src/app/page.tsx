"use client";

import {
  Activity,
  AlertCircle,
  ArrowDownUp,
  ArrowRight,
  BadgeCheck,
  Building2,
  CalendarDays,
  CarFront,
  Check,
  ChevronDown,
  Clock3,
  Filter,
  History,
  LocateFixed,
  LogOut,
  MapPin,
  Moon,
  Navigation,
  ParkingCircle,
  Plus,
  QrCode,
  Search,
  ShieldCheck,
  Smartphone,
  Sparkles,
  Ticket,
  Trash2,
  TrendingUp,
  Users,
  Wallet,
  X,
  Zap,
  Sun,
} from "lucide-react";
import Image from "next/image";
import { useCallback, useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import { QRCodeSVG } from "qrcode.react";
import { ParkingMap } from "@/components/parking-map";
import { Button } from "@/components/ui/button";
import {
  api,
  parkEnApi,
  type Booking,
  type CorporatePass,
  type ParkingLot,
  type ParkingSession,
  type ParkingSlot,
  type User,
  type Vehicle,
  ApiError,
} from "@/lib/api";

type PageKey = "discover" | "reservations" | "vehicles" | "operations" | "insights";

const parkingTypes = ["All spaces", "Mall", "Hospital", "Airport", "Hotel", "Restaurant", "Valet", "Corporate", "Event"];
const parkingModes = ["Any price", "Free", "Paid", "Valet", "Hybrid"];
const phonePattern = /^\+[1-9]\d{7,14}$/;
const OFFLINE_EXITS_KEY = "parken_offline_exits";

function readOfflineExits(): string[] {
  const raw = window.localStorage.getItem(OFFLINE_EXITS_KEY);
  if (!raw) return [];
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new Error("The saved offline-exit queue is unreadable. Do not clear browser storage until it is recovered.");
  }
  if (!Array.isArray(parsed) || parsed.some((item) => typeof item !== "string")) {
    throw new Error("The saved offline-exit queue has an invalid format.");
  }
  return parsed;
}

function localDateTime(value: Date) {
  const offset = value.getTimezoneOffset() * 60_000;
  return new Date(value.getTime() - offset).toISOString().slice(0, 16);
}

function money(value: number | string) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(Number(value || 0));
}

function readableDate(value: string) {
  return new Intl.DateTimeFormat("en-IN", { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }).format(new Date(value));
}

function titleCase(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function iconFor(type: string) {
  if (type === "hospital") return <Activity size={22} />;
  if (type === "airport") return <Navigation size={22} />;
  if (type === "hotel") return <Building2 size={22} />;
  if (type === "restaurant") return <Sparkles size={22} />;
  if (type === "valet") return <CarFront size={22} />;
  if (type === "corporate") return <Users size={22} />;
  if (type === "event") return <Ticket size={22} />;
  return <ParkingCircle size={22} />;
}

function Brand() {
  return <div className="ort-logo" aria-label="ORT"><Image src="/ort-mark.png" alt="" width={36} height={38} priority /><Image className="ort-wordmark" src="/ort-wordmark.png" alt="ORT" width={88} height={33} priority /></div>;
}

function BrandMark({ size = 34 }: { size?: number }) {
  return <Image src="/ort-mark.png" alt="" width={size} height={size} style={{ width: size, height: size, objectFit: "contain" }} />;
}

function ThemeToggle({ theme, onToggle }: { theme: "light" | "dark"; onToggle: () => void }) {
  const nextTheme = theme === "dark" ? "light" : "dark";
  return <button type="button" className="theme-toggle" onClick={onToggle} aria-label={`Switch to ${nextTheme} mode`} aria-pressed={theme === "dark"} title={`Switch to ${nextTheme} mode`}>{theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}<span>{theme === "dark" ? "Light" : "Dark"} mode</span></button>;
}

function StatCard({ label, value, footnote, icon }: { label: string; value: string | number; footnote: string; icon: ReactNode }) {
  return <article className="stat-card"><div className="stat-top"><span>{label}</span><span className="stat-icon">{icon}</span></div><div className="stat-value">{value}</div><div className="stat-sub">{footnote}</div></article>;
}

function SectionHeading({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) {
  return <div className="page-heading"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p>{description}</p></div>{action && <div className="heading-actions">{action}</div>}</div>;
}

function OtpDialog({
  onClose,
  onVerified,
  initialPhone = "",
}: {
  onClose: () => void;
  onVerified: (user: User) => void;
  initialPhone?: string;
}) {
  const [phone, setPhone] = useState(initialPhone);
  const [fullName, setFullName] = useState("");
  const [code, setCode] = useState("");
  const [sent, setSent] = useState(false);
  const [devCode, setDevCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [resendSeconds, setResendSeconds] = useState(0);

  useEffect(() => {
    if (resendSeconds <= 0) return;
    const timer = window.setTimeout(() => setResendSeconds((seconds) => seconds - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [resendSeconds]);

  const requestCode = async () => {
    if (!phonePattern.test(phone)) {
      setError("Use your full mobile number in international format, e.g. +919876543210.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const result = await parkEnApi.requestOtp(phone, fullName.trim() || undefined);
      setDevCode(result.dev_code ?? "");
      setSent(true);
      setCode("");
      setResendSeconds(60);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not send the verification code.");
    } finally {
      setBusy(false);
    }
  };

  const send = async (event: FormEvent) => {
    event.preventDefault();
    await requestCode();
  };

  const verify = async (event: FormEvent) => {
    event.preventDefault();
    if (!/^\d{6}$/.test(code)) {
      setError("Enter the 6-digit code.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const token = await parkEnApi.verifyOtp(phone, code);
      window.localStorage.setItem("parken_access_token", token.access_token);
      const user = await parkEnApi.me();
      onVerified(user);
      onClose();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The code could not be verified.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="modal" role="dialog" aria-modal="true" aria-labelledby="otp-title">
        <div className="modal-head">
          <div><h2 id="otp-title">{sent ? "Check your messages" : "Welcome to ORT"}</h2><p>{sent ? `Enter the verification code sent to ${phone}.` : "Sign in securely with your mobile number. No password to remember."}</p></div>
          <button className="modal-close" type="button" onClick={onClose} aria-label="Close"><X size={16} /></button>
        </div>
        <form className="form-grid" onSubmit={sent ? verify : send}>
          {!sent ? <>
            <label className="field">Mobile number<input autoComplete="tel" inputMode="tel" placeholder="+91 98765 43210" value={phone} onChange={(event) => setPhone(event.target.value.replaceAll(" ", ""))} required /></label>
            <label className="field">Your name <span style={{ color: "#89958f", fontWeight: 400 }}>(for a new account)</span><input autoComplete="name" minLength={2} maxLength={150} placeholder="e.g. Ananya Rao" value={fullName} onChange={(event) => setFullName(event.target.value)} /></label>
            <Button className="w-full" type="submit" disabled={busy}>{busy ? "Sending code…" : <>Send verification code <ArrowRight size={15} /></>}</Button>
          </> : <>
            <label className="field">6-digit verification code<input autoComplete="one-time-code" inputMode="numeric" maxLength={6} placeholder="000000" value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))} required /></label>
            {devCode && <div className="alert" role="status">Local development OTP: <strong>{devCode}</strong></div>}
            <Button className="w-full" type="submit" disabled={busy}>{busy ? "Verifying…" : <>Verify and continue <Check size={15} /></>}</Button>
            <button className="text-xs font-semibold text-slate-500 underline disabled:cursor-not-allowed disabled:opacity-50" type="button" disabled={busy || resendSeconds > 0} onClick={() => { void requestCode(); }}>{resendSeconds > 0 ? `Resend code in ${resendSeconds}s` : "Resend verification code"}</button>
            <button className="text-xs font-semibold text-slate-500 underline" type="button" onClick={() => { setSent(false); setCode(""); setDevCode(""); setError(""); }}>Use a different number</button>
          </>}
          {error && <p className="alert" role="alert">{error}</p>}
        </form>
        <p className="mt-1 text-[10px] leading-5 text-slate-400">By continuing, you agree to ORT’s terms and privacy policy.</p>
      </section>
    </div>
  );
}

function ParkingLotCard({ lot, selected, onSelect, onReserve }: { lot: ParkingLot; selected: boolean; onSelect: () => void; onReserve: () => void }) {
  return (
    <article className="lot-card" onMouseEnter={onSelect}>
      <div className="lot-thumb">{iconFor(lot.parking_type)}</div>
      <div className="min-w-0">
        <div className="lot-title-row"><span className="lot-title">{lot.name}</span><span className="tag">{titleCase(lot.parking_type)}</span></div>
        <p className="lot-address"><MapPin size={11} />{lot.address}, {lot.city}</p>
        <div className="lot-meta">
          <span><BadgeCheck size={12} />{lot.available_slots} open</span>
          <span><Clock3 size={12} />{titleCase(lot.parking_mode)}</span>
          {lot.parking_type === "hospital" && <span><Activity size={12} />Emergency priority</span>}
        </div>
      </div>
      <div className="lot-price"><strong>{lot.starting_hourly_rate === null || Number(lot.starting_hourly_rate) === 0 ? "Free" : money(lot.starting_hourly_rate)}</strong><span>{lot.starting_hourly_rate === null || Number(lot.starting_hourly_rate) === 0 ? "no charge" : "per hour"}</span><Button size="sm" onClick={onReserve} aria-label={`Reserve at ${lot.name}`}>{selected ? "Reserve" : "Choose"}</Button></div>
    </article>
  );
}

function AuthRequired({ onSignIn }: { onSignIn: () => void }) {
  return <div className="empty"><Smartphone size={24} className="mx-auto mb-3 text-emerald-600" /><p>Sign in to see your ORT account.</p><Button className="mt-3" size="sm" onClick={onSignIn}>Sign in with mobile</Button></div>;
}

function LandingPage({
  onFindParking,
  onOpenApp,
  onSignIn,
  theme,
  onToggleTheme,
}: {
  onFindParking: (type?: string) => void;
  onOpenApp: (destination: PageKey) => void;
  onSignIn: () => void;
  theme: "light" | "dark";
  onToggleTheme: () => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [demoOpen, setDemoOpen] = useState(false);
  const [demoStep, setDemoStep] = useState(0);
  const demoSteps = [
    { title: "Find a spot that fits your trip.", detail: "Compare live availability, parking types, distance, and clear hourly prices before you set off.", icon: <Search size={20} /> },
    { title: "Reserve or walk straight in.", detail: "Choose a vehicle and slot for a reservation, or start a walk-in session with a digital ticket.", icon: <CalendarDays size={20} /> },
    { title: "Arrive, park, and carry on.", detail: "Keep your session ID and QR pass handy, find your vehicle later, and close the session when you leave.", icon: <QrCode size={20} /> },
  ];
  const closeMenu = () => setMenuOpen(false);

  return (
    <div className="site-landing min-h-screen overflow-hidden bg-[#f6faf8] text-slate-950">
      <header className="landing-nav sticky top-0 z-40 border-b border-emerald-950/5 bg-white/90 backdrop-blur-xl">
        <div className="mx-auto flex h-[72px] max-w-7xl items-center justify-between px-5 sm:px-8">
          <a href="#" className="flex items-center" aria-label="ORT home" onClick={closeMenu}><Brand /></a>
          <nav className="hidden items-center gap-8 text-sm font-medium text-slate-600 md:flex" aria-label="Main navigation">
            <a className="transition hover:text-emerald-800" href="#">Home</a>
            <a className="transition hover:text-emerald-800" href="#how-it-works">How it works</a>
            <a className="transition hover:text-emerald-800" href="#features">Features</a>
            <a className="transition hover:text-emerald-800" href="#business">For business</a>
            <a className="transition hover:text-emerald-800" href="#contact">Contact</a>
          </nav>
          <div className="hidden items-center gap-3 md:flex">
            <ThemeToggle theme={theme} onToggle={onToggleTheme} />
            <Button variant="ghost" onClick={onSignIn}>Sign in</Button>
            <Button onClick={() => onFindParking()}>Get started <ArrowRight size={15} /></Button>
          </div>
          <div className="flex items-center gap-2 md:hidden"><ThemeToggle theme={theme} onToggle={onToggleTheme} /><button type="button" aria-label={menuOpen ? "Close menu" : "Open menu"} aria-expanded={menuOpen} onClick={() => setMenuOpen((open) => !open)} className="grid h-10 w-10 place-items-center rounded-xl border border-slate-200 text-slate-700">
            {menuOpen ? <X size={18} /> : <ChevronDown size={18} />}
          </button></div>
        </div>
        {menuOpen && <nav className="grid gap-1 border-t border-slate-100 bg-white px-5 py-3 text-sm font-medium md:hidden" aria-label="Mobile navigation">
          {[["Home", "#"], ["How it works", "#how-it-works"], ["Features", "#features"], ["For business", "#business"], ["Contact", "#contact"]].map(([label, href]) => <a key={label} href={href} onClick={closeMenu} className="rounded-lg px-3 py-2.5 text-slate-700 hover:bg-emerald-50">{label}</a>)}
          <div className="flex gap-2 px-3 pb-2 pt-1"><Button variant="outline" onClick={() => { closeMenu(); onSignIn(); }}>Sign in</Button><Button onClick={() => { closeMenu(); onFindParking(); }}>Get started</Button></div>
        </nav>}
      </header>

      <main>
        <section className="ort-hero relative isolate">
          <div className="hero-backdrop pointer-events-none absolute inset-0 -z-10" />
          <div className="mx-auto grid min-h-[590px] max-w-7xl items-center gap-10 px-5 py-12 sm:px-8 lg:grid-cols-[.88fr_1.12fr] lg:py-16">
            <div className="relative z-10 max-w-xl">
              <div className="hero-eyebrow mb-6 inline-flex items-center gap-2 rounded-full border border-emerald-700/10 bg-white/80 px-3.5 py-2 text-xs font-medium text-emerald-950 shadow-sm"><span className="live-dot" /> Smart parking ecosystem</div>
              <h1 className="hero-title text-5xl font-bold leading-[1.04] tracking-[-.055em] sm:text-6xl lg:text-[68px]">Know where<br />you’ll park<br /><span>before you arrive.</span></h1>
              <p className="mt-6 max-w-lg text-base leading-7 text-slate-600 sm:text-lg">A unified parking platform for malls, hospitals, airports, corporate campuses, hotels, restaurants and event venues.</p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Button size="lg" onClick={() => onFindParking()}><MapPin size={16} /> Find parking</Button>
                <Button size="lg" variant="outline" onClick={() => { setDemoStep(0); setDemoOpen(true); }}><span className="grid h-5 w-5 place-items-center rounded-full border border-current"><span className="ml-0.5 text-[9px]">▶</span></span> Watch demo</Button>
              </div>
              <div className="hero-stats mt-8 grid max-w-lg grid-cols-3 gap-4 text-xs text-slate-500"><span className="inline-flex items-center gap-2"><CarFront size={17} className="text-emerald-700" /><span><strong className="block text-sm text-slate-900">Live</strong>spaces</span></span><span className="inline-flex items-center gap-2"><ShieldCheck size={17} className="text-emerald-700" /><span><strong className="block text-sm text-slate-900">Secure</strong>OTP access</span></span><span className="inline-flex items-center gap-2"><Clock3 size={17} className="text-emerald-700" /><span><strong className="block text-sm text-slate-900">Fast</strong>reservations</span></span></div>
            </div>
            <div className="hero-cityscape">
              <div className="city-grid" />
              <svg className="city-route" viewBox="0 0 720 520" preserveAspectRatio="none" aria-hidden="true"><path className="route-glow" d="M70 490 C185 415 102 340 252 300 S390 256 410 185 S562 142 710 18" /><path className="route-line" d="M70 490 C185 415 102 340 252 300 S390 256 410 185 S562 142 710 18" /></svg>
              <div className="city-building building-one"><span /></div>
              <div className="city-building building-two"><span /></div>
              <div className="city-building building-three"><span /></div>
              <div className="city-building building-four"><span /></div>
              <div className="city-building building-five"><span /></div>
              <div className="city-marker marker-mall"><MapPin size={14} /><span><strong>Mall parking</strong><small>32 spaces nearby</small></span></div>
              <div className="city-marker marker-hospital"><Activity size={14} /><span><strong>Hospital</strong><small>Priority access</small></span></div>
              <div className="city-marker marker-airport"><Navigation size={14} /><span><strong>Airport</strong><small>Plan ahead</small></span></div>
              <div className="city-center-pin"><LocateFixed size={19} /></div>
              <div className="city-caption"><span className="live-dot" /> A better arrival starts here <span className="caption-divider" /> Bengaluru, India</div>
              <button type="button" onClick={() => onFindParking()} className="floating-search-card"><span className="floating-search-icon"><Search size={16} /></span><span><strong>Park closer to where you’re going.</strong><small>Find your next space in seconds.</small></span><ArrowRight size={15} /></button>
              <button type="button" aria-label="Explore nearby parking" onClick={() => onFindParking()} className="city-compass"><LocateFixed size={17} /></button>
            </div>
          </div>
        </section>

        <section className="mx-auto grid max-w-7xl grid-cols-2 gap-3 px-5 pb-14 sm:px-8 md:grid-cols-3 lg:grid-cols-6">
          {[
            { title: "Real-time availability", text: "Find parking near you", icon: <ParkingCircle size={19} />, action: () => onFindParking() },
            { title: "Easy reservations", text: "Book in seconds", icon: <CalendarDays size={19} />, action: () => onOpenApp("reservations") },
            { title: "Valet support", text: "Seamless valet service", icon: <CarFront size={19} />, action: () => onFindParking("Valet") },
            { title: "Corporate parking", text: "Employee & visitor access", icon: <Building2 size={19} />, action: () => onOpenApp("insights") },
            { title: "Hospital priority", text: "Emergency & staff support", icon: <Activity size={19} />, action: () => onFindParking("Hospital") },
            { title: "Detailed analytics", text: "For operators & owners", icon: <TrendingUp size={19} />, action: () => onOpenApp("insights") },
          ].map((feature) => <button key={feature.title} type="button" onClick={feature.action} className="group flex min-h-28 flex-col items-start rounded-2xl border border-emerald-950/5 bg-white p-4 text-left shadow-[0_8px_30px_-25px_rgba(15,50,40,.4)] transition hover:-translate-y-1 hover:border-emerald-700/20 hover:shadow-lg">
            <span className="mb-3 grid h-9 w-9 place-items-center rounded-xl bg-emerald-50 text-emerald-800 transition group-hover:bg-emerald-700 group-hover:text-white">{feature.icon}</span><strong className="text-[11px]">{feature.title}</strong><span className="mt-1 text-[10px] text-slate-500">{feature.text}</span>
          </button>)}
        </section>

        <section id="how-it-works" className="scroll-mt-24 bg-white py-16 sm:py-20">
          <div className="mx-auto max-w-7xl px-5 sm:px-8">
            <div className="mx-auto max-w-2xl text-center"><p className="text-xs font-bold uppercase tracking-[.2em] text-emerald-700">A smoother arrival</p><h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">Parking, in three simple steps.</h2><p className="mt-3 text-sm leading-6 text-slate-500">Less circling. No paper ticket to lose. Just a better way to get where you’re going.</p></div>
            <div className="mt-10 grid gap-4 md:grid-cols-3">
              {[
                { n: "01", title: "Find your space", body: "Search by destination, compare live availability and choose a spot that suits your vehicle.", icon: <Search size={21} />, action: () => onFindParking() },
                { n: "02", title: "Reserve or walk in", body: "Book ahead when plans are set or check in instantly when you arrive.", icon: <Ticket size={21} />, action: () => onOpenApp("discover") },
                { n: "03", title: "Park with confidence", body: "Keep a digital pass, know where you parked and leave with a simple session close.", icon: <Navigation size={21} />, action: () => onOpenApp("reservations") },
              ].map((step) => <button key={step.n} type="button" onClick={step.action} className="group relative rounded-3xl border border-slate-100 bg-[#f8fbf9] p-6 text-left transition hover:-translate-y-1 hover:border-emerald-200 hover:bg-emerald-50/50">
                <span className="absolute right-5 top-5 text-xs font-bold tracking-widest text-emerald-700/50">{step.n}</span><span className="grid h-12 w-12 place-items-center rounded-2xl bg-white text-emerald-800 shadow-sm">{step.icon}</span><h3 className="mt-6 text-base font-bold">{step.title}</h3><p className="mt-2 text-sm leading-6 text-slate-500">{step.body}</p><span className="mt-5 inline-flex items-center gap-1 text-xs font-semibold text-emerald-800">Get started <ArrowRight size={13} className="transition group-hover:translate-x-1" /></span>
              </button>)}
            </div>
          </div>
        </section>

        <section id="features" className="scroll-mt-24 px-5 py-16 sm:px-8 sm:py-20">
          <div className="mx-auto max-w-7xl">
            <div className="flex flex-wrap items-end justify-between gap-5"><div><p className="text-xs font-bold uppercase tracking-[.2em] text-emerald-700">One connected platform</p><h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">Built around your whole journey.</h2><p className="mt-3 max-w-xl text-sm leading-6 text-slate-500">From finding a space to managing a multi-level facility, ORT connects drivers and parking teams.</p></div><Button variant="outline" onClick={() => onFindParking()}>Explore parking <ArrowRight size={14} /></Button></div>
            <div className="mt-9 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {[
                { title: "For drivers", body: "Multi-vehicle garage, reservations, walk-ins, history and find-my-vehicle.", icon: <CarFront size={20} />, action: () => onOpenApp("vehicles") },
                { title: "For parking teams", body: "Session lookup by QR, session ID or plate, slot assignment and incident reports.", icon: <QrCode size={20} />, action: () => onOpenApp("operations") },
                { title: "For valet", body: "Record vehicle handover, accept retrieval requests and close completed sessions.", icon: <Ticket size={20} />, action: () => onFindParking("Valet") },
                { title: "For hospitals", body: "Emergency priority, auditable overrides and dedicated parking categories.", icon: <Activity size={20} />, action: () => onFindParking("Hospital") },
              ].map((feature) => <button key={feature.title} type="button" onClick={feature.action} className="rounded-2xl border border-slate-200 bg-white p-5 text-left transition hover:border-emerald-300 hover:shadow-lg">
                <span className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-50 text-emerald-800">{feature.icon}</span><h3 className="mt-4 text-sm font-bold">{feature.title}</h3><p className="mt-2 text-xs leading-5 text-slate-500">{feature.body}</p>
              </button>)}
            </div>
            <div className="mt-12 grid gap-5 rounded-[28px] bg-slate-950 p-6 text-white sm:p-8 lg:grid-cols-[.7fr_1.3fr]">
              <div className="flex flex-col justify-center"><p className="text-xs font-bold uppercase tracking-[.2em] text-emerald-300">The ORT app</p><h3 className="mt-3 text-2xl font-bold">Your next parking spot is closer than you think.</h3><p className="mt-3 text-sm leading-6 text-slate-300">Browse a live parking map, save your vehicles and keep every trip in one place.</p><Button className="mt-6 w-fit" onClick={() => onFindParking()}>Find parking <ArrowRight size={14} /></Button></div>
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-2xl border border-white/10 bg-white/[.06] p-4 text-left"><div className="flex items-center justify-between text-slate-200"><span className="text-[10px]">9:41</span><span className="text-[10px]">•••</span></div><div className="mt-6 flex items-center gap-2"><BrandMark size={23} /><strong className="text-sm">ORT</strong></div><p className="mt-7 text-sm font-bold">Welcome to ORT</p><p className="mt-1 text-[10px] text-slate-300">Find. Reserve. Park.</p><Button className="mt-6 w-full !h-auto !min-h-0 !px-3 !py-2 !text-[10px]" onClick={onSignIn}>Send OTP</Button><p className="mt-5 text-center text-[9px] text-slate-400">Secure mobile sign-in</p></div>
                <button type="button" onClick={() => onFindParking()} className="rounded-2xl border border-white/10 bg-white/[.06] p-4 text-left transition hover:bg-white/10"><div className="flex items-center justify-between text-slate-200"><span className="text-[10px]">9:41 · Bengaluru</span><MapPin size={12} /></div><div className="mt-5 flex items-center gap-2 rounded-lg bg-white px-2 py-2 text-[9px] text-slate-500"><Search size={12} /> Search for parking near you…</div><div className="mt-4 grid grid-cols-4 gap-1.5">{["Mall", "Hospital", "Airport", "Hotel"].map((type) => <span key={type} className="rounded-lg bg-white/10 px-1 py-2 text-center text-[8px]">{type}</span>)}</div><div className="mt-4 rounded-xl bg-white p-2.5 text-slate-900"><div className="flex justify-between"><strong className="text-[9px]">Orchard Central</strong><span className="text-[8px] text-emerald-700">4.8 ★</span></div><p className="mt-1 text-[8px] text-slate-500">12 min · 120 spaces open</p></div><p className="mt-4 text-center text-[9px] text-emerald-200">Tap to browse live spaces</p></button>
                <button type="button" onClick={() => onOpenApp("reservations")} className="rounded-2xl border border-white/10 bg-white/[.06] p-4 text-left transition hover:bg-white/10"><div className="flex items-center justify-between text-slate-200"><span className="text-[10px]">My bookings</span><CalendarDays size={13} /></div><div className="mt-5 rounded-xl bg-white p-3 text-slate-900"><span className="rounded-full bg-emerald-100 px-2 py-1 text-[8px] font-semibold text-emerald-800">Confirmed</span><p className="mt-3 text-[10px] font-bold">Orchard Central</p><p className="mt-1 text-[8px] text-slate-500">Today · 10:00 AM</p><div className="mx-auto mt-3 grid h-16 w-16 place-items-center border border-slate-100"><QrCode size={35} /></div></div><p className="mt-3 text-center text-[9px] text-emerald-200">Tap to see your trips</p></button>
              </div>
            </div>
          </div>
        </section>

        <section id="business" className="scroll-mt-24 bg-[#eaf4ef] px-5 py-16 sm:px-8 sm:py-20">
          <div className="mx-auto grid max-w-7xl items-center gap-9 lg:grid-cols-[.8fr_1.2fr]">
            <div><p className="text-xs font-bold uppercase tracking-[.2em] text-emerald-800">For business</p><h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">Make every space work smarter.</h2><p className="mt-4 text-sm leading-6 text-slate-600">One operations dashboard for owners and teams: occupancy, revenue, booking patterns, staff assignments and digital visitor passes.</p><ul className="mt-5 grid gap-2 text-sm text-slate-700"><li className="flex items-center gap-2"><Check size={15} className="text-emerald-700" /> Multi-level inventory with zones and slot categories</li><li className="flex items-center gap-2"><Check size={15} className="text-emerald-700" /> Live occupancy and booking revenue</li><li className="flex items-center gap-2"><Check size={15} className="text-emerald-700" /> Staff, valet and incident workflows</li></ul><Button className="mt-7" onClick={() => onOpenApp("insights")}>Explore the owner dashboard <ArrowRight size={14} /></Button></div>
            <button type="button" onClick={() => onOpenApp("insights")} aria-label="Open owner analytics dashboard" className="group overflow-hidden rounded-[26px] border border-white bg-white p-4 text-left shadow-[0_24px_70px_-36px_rgba(15,55,40,.4)] transition hover:-translate-y-1 sm:p-6">
              <div className="flex items-center justify-between"><div className="flex items-center gap-2"><BrandMark size={25} /><strong className="text-xs">ORT <span className="font-normal text-slate-400">/ Owner dashboard</span></strong></div><span className="rounded-lg bg-slate-50 px-2.5 py-1.5 text-[9px] text-slate-500">Illustrative preview · sample metrics</span></div>
              <div className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-4">{[["Total bookings", "12,458", "+12%"], ["Current occupancy", "72%", "+5%"], ["Revenue", "₹3,24,500", "+18%"], ["Available slots", "168", "of 600"]].map(([label, value, delta]) => <div key={label} className="rounded-xl bg-slate-50 p-3"><p className="text-[8px] text-slate-500">{label}</p><p className="mt-1 text-base font-bold tracking-tight">{value}</p><p className="mt-1 text-[8px] font-semibold text-emerald-700">{delta}</p></div>)}</div>
              <div className="mt-3 grid gap-3 sm:grid-cols-[1.35fr_.65fr]"><div className="rounded-xl border border-slate-100 p-3"><div className="flex items-center justify-between"><strong className="text-[9px]">Parking occupancy</strong><span className="text-[8px] text-emerald-700">Peak 92%</span></div><svg viewBox="0 0 480 125" className="mt-2 h-28 w-full" role="img" aria-label="Occupancy trend chart"><path d="M0 105 C45 90 60 85 95 94 S155 55 190 69 S250 28 285 50 S345 12 375 40 S430 32 480 20" fill="none" stroke="#07875c" strokeWidth="4" /><path d="M0 105 C45 90 60 85 95 94 S155 55 190 69 S250 28 285 50 S345 12 375 40 S430 32 480 20 L480 125 L0 125Z" fill="url(#parkArea)" opacity=".18" /><defs><linearGradient id="parkArea" x1="0" x2="0" y1="0" y2="1"><stop stopColor="#07875c" /><stop offset="1" stopColor="#fff" /></linearGradient></defs><path d="M0 120H480M0 80H480M0 40H480" stroke="#e9efec" strokeDasharray="3 5" /></svg><div className="flex justify-between text-[8px] text-slate-400"><span>6 AM</span><span>9 AM</span><span>12 PM</span><span>3 PM</span><span>6 PM</span></div></div><div className="rounded-xl border border-slate-100 p-3"><strong className="text-[9px]">Space mix</strong><div className="mx-auto mt-4 grid h-24 w-24 place-items-center rounded-full" style={{ background: "conic-gradient(#07875c 0 60%,#48b893 60% 75%,#f1b45b 75% 90%,#ea7777 90% 100%)" }}><div className="grid h-14 w-14 place-items-center rounded-full bg-white text-[8px] font-semibold">600 total</div></div><div className="mt-3 space-y-1 text-[8px] text-slate-500"><p>● Regular <span className="float-right">60%</span></p><p>● EV <span className="float-right">15%</span></p><p>● Visitor <span className="float-right">15%</span></p></div></div></div>
              <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-3"><span className="text-[9px] text-slate-500">Occupancy and revenue, together.</span><span className="inline-flex items-center gap-1 text-[9px] font-semibold text-emerald-800 group-hover:gap-2">Open dashboard <ArrowRight size={12} /></span></div>
            </button>
          </div>
        </section>

        <section className="px-5 py-16 sm:px-8 sm:py-20">
          <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-7 rounded-[28px] bg-emerald-800 px-6 py-9 text-white sm:flex-row sm:items-center sm:px-10 sm:py-11">
            <div><p className="text-xs font-bold uppercase tracking-[.2em] text-emerald-200">Ready when you are</p><h2 className="mt-2 text-2xl font-bold sm:text-3xl">Take the stress out of parking.</h2><p className="mt-2 text-sm text-emerald-100">Find your next space with ORT.</p></div><Button variant="secondary" size="lg" onClick={() => onFindParking()}>Find parking <ArrowRight size={15} /></Button>
          </div>
        </section>
      </main>
      <footer id="contact" className="scroll-mt-20 border-t border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-5 px-5 py-8 sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <a href="#" className="flex items-center gap-2" aria-label="ORT home"><BrandMark size={29} /><span className="text-lg font-extrabold tracking-[-1px] text-slate-900">ORT</span></a><p className="text-xs text-slate-500">Find. Reserve. Park. · Smarter parking for every journey.</p><a href="mailto:hello@ort.in?subject=ORT%20enquiry" className="inline-flex items-center gap-2 text-sm font-semibold text-emerald-800 hover:text-emerald-950">Contact ORT <ArrowRight size={14} /></a>
        </div>
      </footer>
      {demoOpen && <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setDemoOpen(false); }}><section className="modal" role="dialog" aria-modal="true" aria-labelledby="demo-title"><div className="modal-head"><div><p className="eyebrow">ORT in a minute</p><h2 id="demo-title">{demoSteps[demoStep].title}</h2><p>{demoSteps[demoStep].detail}</p></div><button type="button" className="modal-close" aria-label="Close demo" onClick={() => setDemoOpen(false)}><X size={16} /></button></div><div className="my-5 flex items-center gap-3 rounded-2xl bg-emerald-50 p-4"><span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-white text-emerald-800">{demoSteps[demoStep].icon}</span><div className="flex gap-1.5">{demoSteps.map((step, index) => <button type="button" key={step.title} aria-label={`Show demo step ${index + 1}`} onClick={() => setDemoStep(index)} className={`h-1.5 w-12 rounded-full ${index === demoStep ? "bg-emerald-700" : "bg-emerald-200"}`} />)}</div><span className="ml-auto text-xs font-semibold text-slate-500">{demoStep + 1} / {demoSteps.length}</span></div><div className="flex justify-between gap-3"><Button variant="outline" disabled={demoStep === 0} onClick={() => setDemoStep((step) => Math.max(0, step - 1))}>Back</Button>{demoStep < demoSteps.length - 1 ? <Button onClick={() => setDemoStep((step) => Math.min(demoSteps.length - 1, step + 1))}>Next <ArrowRight size={14} /></Button> : <Button onClick={() => onFindParking()}>Explore parking <ArrowRight size={14} /></Button>}</div></section></div>}
    </div>
  );
}

export default function HomePage() {
  const [appMode, setAppMode] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark">("dark");
  const [themeReady, setThemeReady] = useState(false);
  const [page, setPage] = useState<PageKey>("discover");
  const [user, setUser] = useState<User | null>(null);
  const [lots, setLots] = useState<ParkingLot[]>([]);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [sessions, setSessions] = useState<ParkingSession[]>([]);
  const [corporatePasses, setCorporatePasses] = useState<CorporatePass[]>([]);
  const [managedLots, setManagedLots] = useState<ParkingLot[]>([]);
  const [visitorName, setVisitorName] = useState("");
  const [visitorPhone, setVisitorPhone] = useState("");
  const [visitorLotId, setVisitorLotId] = useState("");
  const [visitorPassExpiry, setVisitorPassExpiry] = useState(() => localDateTime(new Date(Date.now() + 24 * 60 * 60_000)));
  const [sessionSlots, setSessionSlots] = useState<ParkingSlot[]>([]);
  const [sessionSlotId, setSessionSlotId] = useState("");
  const [sessionVehicleId, setSessionVehicleId] = useState("");
  const [analytics, setAnalytics] = useState<{ locations: number; capacity: number; occupied: number; occupancy_rate: number; revenue: string; bookings: number; peak_entry_hour: number | null; overstay_sessions: number } | null>(null);
  const [loadingLots, setLoadingLots] = useState(true);
  const [searchError, setSearchError] = useState("");
  const [query, setQuery] = useState("");
  const [parkingType, setParkingType] = useState("All spaces");
  const [parkingMode, setParkingMode] = useState("Any price");
  const [coordinates, setCoordinates] = useState<{ latitude: number; longitude: number } | null>(null);
  const [selectedLot, setSelectedLot] = useState<string>();
  const [loginOpen, setLoginOpen] = useState(false);
  const [pendingReservation, setPendingReservation] = useState<ParkingLot | null>(null);
  const [bookingLot, setBookingLot] = useState<ParkingLot | null>(null);
  const [bookingSlots, setBookingSlots] = useState<ParkingSlot[]>([]);
  const [bookingSlot, setBookingSlot] = useState("");
  const [bookingStart, setBookingStart] = useState(() => localDateTime(new Date(Date.now() + 60 * 60_000)));
  const [bookingHours, setBookingHours] = useState(2);
  const [vehiclePlate, setVehiclePlate] = useState("");
  const [vehicleLabel, setVehicleLabel] = useState("");
  const [vehicleType, setVehicleType] = useState("car");
  const [sessionLot, setSessionLot] = useState("");
  const [staffMethod, setStaffMethod] = useState("session_id");
  const [staffValue, setStaffValue] = useState("");
  const [staffSession, setStaffSession] = useState<ParkingSession | null>(null);
  const [staffSlots, setStaffSlots] = useState<ParkingSlot[]>([]);
  const [staffSlotId, setStaffSlotId] = useState("");
  const [overrideReason, setOverrideReason] = useState("");
  const [corporatePassCode, setCorporatePassCode] = useState("");
  const [lookedUpPass, setLookedUpPass] = useState<CorporatePass | null>(null);
  const [qrSession, setQrSession] = useState<{ session: ParkingSession; token: string } | null>(null);
  const [incidentCategory, setIncidentCategory] = useState("facility");
  const [incidentDescription, setIncidentDescription] = useState("");
  const [toast, setToast] = useState("");
  const [actionBusy, setActionBusy] = useState(false);
  const [online, setOnline] = useState(true);
  const [offlineExitCount, setOfflineExitCount] = useState(0);

  useEffect(() => {
    const storedTheme = window.localStorage.getItem("ort_theme");
    const initialTheme = storedTheme === "light" || storedTheme === "dark" ? storedTheme : "dark";
    setTheme(initialTheme);
    document.documentElement.dataset.theme = initialTheme;
    setThemeReady(true);
  }, []);

  useEffect(() => {
    if (!themeReady) return;
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("ort_theme", theme);
  }, [theme, themeReady]);

  const openApp = useCallback((destination: PageKey = "discover", signIn = false) => {
    setPage(destination);
    setAppMode(true);
    window.history.pushState({ parkenApp: true }, "", `/?app=${destination}`);
    if (signIn) setLoginOpen(true);
  }, []);

  const returnHome = useCallback(() => {
    setAppMode(false);
    setLoginOpen(false);
    window.history.pushState({ parkenApp: false }, "", "/");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  useEffect(() => {
    const applyRoute = () => {
      const params = new URLSearchParams(window.location.search);
      const destination = params.get("app") as PageKey | null;
      if (destination && ["discover", "reservations", "vehicles", "operations", "insights"].includes(destination)) {
        setPage(destination);
        setAppMode(true);
      } else {
        setAppMode(false);
      }
    };
    applyRoute();
    window.addEventListener("popstate", applyRoute);
    return () => window.removeEventListener("popstate", applyRoute);
  }, []);

  useEffect(() => {
    if (!managedLots.some((lot) => lot.id === visitorLotId)) {
      setVisitorLotId(managedLots[0]?.id ?? "");
    }
  }, [managedLots, visitorLotId]);

  const notify = useCallback((message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 4200);
  }, []);

  const selectLot = useCallback((lot: ParkingLot) => setSelectedLot(lot.id), []);

  const refreshAccount = useCallback(async (currentUser: User) => {
    const [nextBookings, nextVehicles, nextSessions, nextPasses, nextManagedLots] = await Promise.all([
      parkEnApi.bookings(),
      parkEnApi.vehicles(),
      parkEnApi.sessions(),
      parkEnApi.corporatePasses(),
      parkEnApi.managedLots(),
    ]);
    setUser(currentUser);
    setBookings(nextBookings);
    setVehicles(nextVehicles);
    setSessions(nextSessions);
    setCorporatePasses(nextPasses);
    setManagedLots(nextManagedLots);
    if (currentUser.role === "owner" || currentUser.role === "admin") {
      const report = await parkEnApi.analytics();
      setAnalytics(report);
    }
  }, []);

  useEffect(() => {
    const token = window.localStorage.getItem("parken_access_token");
    if (token) {
      setAppMode(true);
      void parkEnApi.me().then(refreshAccount).catch((reason: unknown) => {
        if (reason instanceof ApiError && reason.status === 401) {
          window.localStorage.removeItem("parken_access_token");
          setUser(null);
        } else {
          notify(reason instanceof Error ? reason.message : "Could not load your account.");
        }
      });
    }
    const updateOnline = () => setOnline(navigator.onLine);
    updateOnline();
    try {
      setOfflineExitCount(readOfflineExits().length);
    } catch (reason) {
      notify(reason instanceof Error ? reason.message : "Could not read the offline-exit queue.");
    }
    window.addEventListener("online", updateOnline);
    window.addEventListener("offline", updateOnline);
    return () => {
      window.removeEventListener("online", updateOnline);
      window.removeEventListener("offline", updateOnline);
    };
  }, [refreshAccount, notify]);

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      const params = new URLSearchParams();
      if (query.trim()) params.set("q", query.trim());
      if (parkingType !== "All spaces") params.set("parking_type", parkingType.toLowerCase());
      if (parkingMode !== "Any price") params.set("parking_mode", parkingMode.toLowerCase());
      if (coordinates) {
        params.set("latitude", String(coordinates.latitude));
        params.set("longitude", String(coordinates.longitude));
      } else {
        params.set("city", "Bengaluru");
      }
      setLoadingLots(true);
      setSearchError("");
      void parkEnApi.search(params, controller.signal)
        .then((nextLots) => {
          setLots(nextLots);
          setSelectedLot((current) => current && nextLots.some((lot) => lot.id === current) ? current : nextLots[0]?.id);
        })
        .catch((reason: unknown) => {
          if (reason instanceof DOMException && reason.name === "AbortError") return;
          setSearchError(reason instanceof Error ? reason.message : "Parking search is unavailable.");
        })
        .finally(() => { if (!controller.signal.aborted) setLoadingLots(false); });
    }, 180);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [query, parkingType, parkingMode, coordinates]);

  useEffect(() => {
    const defaultVehicle = vehicles.find((vehicle) => vehicle.is_default) ?? vehicles[0];
    if (defaultVehicle && !vehicles.some((vehicle) => vehicle.id === sessionVehicleId)) {
      setSessionVehicleId(defaultVehicle.id);
    }
  }, [vehicles, sessionVehicleId]);

  useEffect(() => {
    if (!sessionLot || !user || user.role !== "customer") {
      setSessionSlots([]);
      setSessionSlotId("");
      return;
    }
    let cancelled = false;
    void parkEnApi.slots(sessionLot)
      .then((slots) => {
        if (cancelled) return;
        const available = slots.filter((slot) => slot.status === "available");
        setSessionSlots(available);
        setSessionSlotId(available[0]?.id ?? "");
      })
      .catch((reason: unknown) => {
        if (!cancelled) notify(reason instanceof Error ? reason.message : "Could not load available parking slots.");
      });
    return () => { cancelled = true; };
  }, [sessionLot, user, notify]);

  const visibleLots = useMemo(() => lots.filter((lot) => lot.available_slots > 0), [lots]);
  const selected = visibleLots.find((lot) => lot.id === selectedLot);
  const activeSessions = sessions.filter((session) => session.status === "active");
  const activeBookings = bookings.filter((booking) => booking.status === "confirmed" || booking.status === "pending");

  const startReservation = async (lot: ParkingLot) => {
    if (!user) {
      setPendingReservation(lot);
      setLoginOpen(true);
      return;
    }
    setActionBusy(true);
    try {
      const available = (await parkEnApi.slots(lot.id)).filter((slot) => slot.status === "available");
      if (!available.length) {
        notify("That location just filled up. Refresh the search to see current availability.");
        return;
      }
      setBookingSlots(available);
      setBookingSlot(available[0].id);
      setBookingLot(lot);
      setBookingStart(localDateTime(new Date(Date.now() + 60 * 60_000)));
    } catch (reason) {
      notify(reason instanceof Error ? reason.message : "Could not load available slots.");
    } finally {
      setActionBusy(false);
    }
  };

  const confirmBooking = async (event: FormEvent) => {
    event.preventDefault();
    if (!user || !bookingLot || !bookingSlot) return;
    const start = new Date(bookingStart);
    if (Number.isNaN(start.getTime()) || start.getTime() < Date.now()) {
      notify("Choose a future arrival time.");
      return;
    }
    const slot = bookingSlots.find((candidate) => candidate.id === bookingSlot);
    if (!slot) return;
    setActionBusy(true);
    try {
      const result = await parkEnApi.createBooking({
        customer_id: user.id,
        parking_slot_id: slot.id,
        starts_at: start.toISOString(),
        ends_at: new Date(start.getTime() + bookingHours * 60 * 60_000).toISOString(),
        total_amount: Number(slot.hourly_rate) * bookingHours,
        status: "pending",
      });
      setBookings((current) => [result, ...current]);
      setBookingLot(null);
      setPage("reservations");
      notify("Reserved! Your parking space is waiting for you.");
    } catch (reason) {
      notify(reason instanceof Error ? reason.message : "Reservation could not be completed.");
    } finally {
      setActionBusy(false);
    }
  };

  const addVehicle = async (event: FormEvent) => {
    event.preventDefault();
    setActionBusy(true);
    try {
      const created = await parkEnApi.createVehicle({
        plate_number: vehiclePlate,
        label: vehicleLabel || "My vehicle",
        vehicle_type: vehicleType,
        is_default: vehicles.length === 0,
      });
      setVehicles((current) => [...current, created]);
      setVehiclePlate("");
      setVehicleLabel("");
      notify("Vehicle added to your garage.");
    } catch (reason) {
      notify(reason instanceof Error ? reason.message : "Vehicle could not be added.");
    } finally {
      setActionBusy(false);
    }
  };

  const createVisitorPass = async (event: FormEvent) => {
    event.preventDefault();
    const expiresAt = new Date(visitorPassExpiry);
    if (Number.isNaN(expiresAt.getTime()) || expiresAt.getTime() <= Date.now()) {
      notify("Choose a visitor pass expiry time in the future.");
      return;
    }
    const parkingLotId = visitorLotId;
    if (!parkingLotId) {
      notify("No managed parking location is available for visitor passes.");
      return;
    }
    setActionBusy(true);
    try {
      const created = await parkEnApi.createVisitorPass({
        parking_lot_id: parkingLotId,
        pass_type: "visitor",
        visitor_name: visitorName.trim(),
        visitor_phone: visitorPhone || undefined,
        starts_at: new Date().toISOString(),
        expires_at: expiresAt.toISOString(),
      });
      setCorporatePasses((current) => [created, ...current]);
      setVisitorName("");
      setVisitorPhone("");
      notify(`Visitor pass ${created.pass_code} created.`);
    } catch (reason) {
      notify(reason instanceof Error ? reason.message : "Visitor pass could not be created.");
    } finally {
      setActionBusy(false);
    }
  };

  const revokePass = async (pass: CorporatePass) => {
    setActionBusy(true);
    try {
      const updated = await parkEnApi.revokeCorporatePass(pass.id);
      setCorporatePasses((current) => current.map((item) => item.id === updated.id ? updated : item));
      notify("Corporate pass revoked.");
    } catch (reason) {
      notify(reason instanceof Error ? reason.message : "Corporate pass could not be revoked.");
    } finally {
      setActionBusy(false);
    }
  };

  const startWalkIn = async (event: FormEvent) => {
    event.preventDefault();
    if (!sessionLot || !sessionVehicleId || !sessionSlotId) {
      notify("Choose a vehicle, parking location, and available slot first.");
      return;
    }
    setActionBusy(true);
    try {
      const session = await parkEnApi.createSession({ parking_lot_id: sessionLot, vehicle_id: sessionVehicleId, parking_slot_id: sessionSlotId, entry_method: "walk_in" });
      setSessions((current) => [session, ...current]);
      setQrSession({ session, token: session.qr_token });
    } catch (reason) {
      notify(reason instanceof Error ? reason.message : "Could not start a parking session.");
    } finally {
      setActionBusy(false);
    }
  };

  const lookupStaffSession = async (event: FormEvent) => {
    event.preventDefault();
    if (!sessionLot || !staffValue.trim()) return;
    setActionBusy(true);
    try {
      const found = await parkEnApi.lookupSession(sessionLot, staffMethod, staffValue.trim());
      setStaffSession(found);
      const slots = await parkEnApi.slots(sessionLot);
      const freeSlots = slots.filter((slot) => slot.status === "available" || (found.emergency_priority && slot.status === "maintenance"));
      setStaffSlots(freeSlots);
      setStaffSlotId(freeSlots[0]?.id ?? "");
    } catch (reason) {
      setStaffSession(null);
      notify(reason instanceof Error ? reason.message : "No active session matched that identifier.");
    } finally {
      setActionBusy(false);
    }
  };

  const lookupStaffPass = async (event: FormEvent) => {
    event.preventDefault();
    if (!sessionLot || !corporatePassCode.trim()) return;
    setActionBusy(true);
    try {
      const found = await parkEnApi.lookupCorporatePass(sessionLot, corporatePassCode.trim());
      setLookedUpPass(found);
      notify("Active parking pass verified.");
    } catch (reason) {
      setLookedUpPass(null);
      notify(reason instanceof Error ? reason.message : "No active pass matched that code.");
    } finally {
      setActionBusy(false);
    }
  };

  const assignStaffSlot = async () => {
    if (!staffSession || !staffSlotId) return;
    setActionBusy(true);
    try {
      const updated = await parkEnApi.assignSessionSlot(staffSession.id, staffSlotId, overrideReason || undefined);
      setStaffSession(updated);
      setSessions((current) => current.map((session) => session.id === updated.id ? updated : session));
      notify("Parking slot assigned.");
    } catch (reason) {
      notify(reason instanceof Error ? reason.message : "Slot could not be assigned.");
    } finally {
      setActionBusy(false);
    }
  };

  const updateValetSession = async (session: ParkingSession, action: "handover" | "request" | "retrieve") => {
    setActionBusy(true);
    try {
      const updated = action === "handover"
        ? await parkEnApi.recordValetHandover(session.id)
        : action === "request"
          ? await parkEnApi.requestValetRetrieval(session.id)
          : await parkEnApi.completeValetRetrieval(session.id);
      setSessions((current) => current.map((item) => item.id === updated.id ? updated : item));
      setStaffSession((current) => current?.id === updated.id ? updated : current);
      notify(action === "handover" ? "Vehicle handover recorded." : action === "request" ? "Your valet retrieval has been requested." : "Vehicle retrieval completed.");
    } catch (reason) {
      notify(reason instanceof Error ? reason.message : "Valet update could not be completed.");
    } finally {
      setActionBusy(false);
    }
  };

  const updateEmergencyPriority = async () => {
    if (!staffSession) return;
    setActionBusy(true);
    try {
      const updated = await parkEnApi.setEmergencyPriority(
        staffSession.id,
        !staffSession.emergency_priority,
        staffSession.emergency_priority ? null : overrideReason,
      );
      setStaffSession(updated);
      setSessions((current) => current.map((item) => item.id === updated.id ? updated : item));
      if (!updated.emergency_priority) setOverrideReason("");
      notify(updated.emergency_priority ? "Hospital emergency priority enabled." : "Hospital emergency priority cleared.");
      try {
        const slots = await parkEnApi.slots(updated.parking_lot_id);
        setStaffSlots(slots.filter((slot) => slot.status === "available" || (updated.emergency_priority && slot.status === "maintenance")));
        setStaffSlotId("");
      } catch (reason) {
        notify(reason instanceof Error ? `Priority updated, but slots could not be refreshed: ${reason.message}` : "Priority updated, but slots could not be refreshed.");
      }
    } catch (reason) {
      notify(reason instanceof Error ? reason.message : "Emergency priority could not be updated.");
    } finally {
      setActionBusy(false);
    }
  };

  const closeSession = async (session: ParkingSession) => {
    if (!online) {
      try {
        const queue = readOfflineExits();
        if (!queue.includes(session.id)) queue.push(session.id);
        window.localStorage.setItem(OFFLINE_EXITS_KEY, JSON.stringify(queue));
        setOfflineExitCount(queue.length);
      } catch (reason) {
        notify(reason instanceof Error ? reason.message : "Could not queue this offline exit.");
        return;
      }
      setSessions((current) => current.map((item) => item.id === session.id ? { ...item, synced_at: null } : item));
      notify("Exit saved on this device. It will sync when you’re back online.");
      return;
    }
    setActionBusy(true);
    try {
      const closed = await parkEnApi.closeSession(session.id);
      setSessions((current) => current.map((item) => item.id === closed.id ? closed : item));
      try {
        const queue = readOfflineExits().filter((id) => id !== session.id);
        window.localStorage.setItem(OFFLINE_EXITS_KEY, JSON.stringify(queue));
        setOfflineExitCount(queue.length);
      } catch (queueError) {
        notify(queueError instanceof Error ? queueError.message : "Parking closed, but the local sync queue could not be updated.");
      }
      notify("Parking session closed.");
    } catch (reason) {
      if (!navigator.onLine) {
        try {
          const queue = readOfflineExits();
          if (!queue.includes(session.id)) queue.push(session.id);
          window.localStorage.setItem(OFFLINE_EXITS_KEY, JSON.stringify(queue));
          setOfflineExitCount(queue.length);
          notify("Exit saved on this device. It will sync when you’re back online.");
        } catch (queueError) {
          notify(queueError instanceof Error ? queueError.message : "Could not queue this offline exit.");
        }
      } else {
        notify(reason instanceof Error ? reason.message : "Could not close this session.");
      }
    } finally {
      setActionBusy(false);
    }
  };

  useEffect(() => {
    const syncOfflineExits = async () => {
      if (!navigator.onLine || !user) return;
      let queued: string[];
      try {
        queued = readOfflineExits();
      } catch (reason) {
        notify(reason instanceof Error ? reason.message : "Could not read the offline-exit queue.");
        return;
      }
      if (!queued.length) return;
      const failed: string[] = [];
      let syncError = "";
      for (const sessionId of queued) {
        try {
          await parkEnApi.closeSession(sessionId);
        } catch (closeError) {
          try {
            const refreshed = await parkEnApi.sessions();
            setSessions(refreshed);
            if (!refreshed.some((session) => session.id === sessionId && session.status === "closed")) {
              failed.push(sessionId);
              syncError = closeError instanceof Error ? closeError.message : "A queued exit could not be synced.";
            }
          } catch (refreshError) {
            failed.push(sessionId);
            syncError = refreshError instanceof Error ? refreshError.message : "Could not verify a queued exit.";
          }
        }
      }
      window.localStorage.setItem(OFFLINE_EXITS_KEY, JSON.stringify(failed));
      setOfflineExitCount(failed.length);
      if (failed.length < queued.length) {
        try {
          setSessions(await parkEnApi.sessions());
        } catch (reason) {
          notify(reason instanceof Error ? reason.message : "Offline exits synced, but session history could not refresh.");
          return;
        }
        notify("Your offline parking exits are synced.");
      }
      if (failed.length) notify(`Could not sync ${failed.length} offline exit${failed.length === 1 ? "" : "s"}: ${syncError}`);
    };
    window.addEventListener("online", syncOfflineExits);
    void syncOfflineExits();
    return () => window.removeEventListener("online", syncOfflineExits);
  }, [user, notify]);

  const submitIncident = async (event: FormEvent) => {
    event.preventDefault();
    if (!sessionLot) return;
    setActionBusy(true);
    try {
      await parkEnApi.reportIncident({ parking_lot_id: sessionLot, category: incidentCategory, description: incidentDescription });
      setIncidentDescription("");
      notify("Incident report sent to the parking team.");
    } catch (reason) {
      notify(reason instanceof Error ? reason.message : "Incident could not be reported.");
    } finally {
      setActionBusy(false);
    }
  };

  const cancelBooking = async (booking: Booking) => {
    setActionBusy(true);
    try {
      const updated = await parkEnApi.updateBooking(booking.id, "cancelled");
      setBookings((current) => current.map((item) => item.id === updated.id ? updated : item));
      notify("Reservation cancelled.");
    } catch (reason) {
      notify(reason instanceof Error ? reason.message : "Reservation could not be cancelled.");
    } finally {
      setActionBusy(false);
    }
  };

  const signOut = () => {
    window.localStorage.removeItem("parken_access_token");
    setUser(null);
    setBookings([]);
    setVehicles([]);
    setSessions([]);
    setCorporatePasses([]);
    setManagedLots([]);
    setAnalytics(null);
    setPage("discover");
    notify("You’ve been signed out.");
  };

  const visibleNavigation = [
    { id: "discover" as const, label: "Find parking", icon: <Search size={17} /> },
    { id: "reservations" as const, label: "My reservations", icon: <CalendarDays size={17} /> },
    { id: "vehicles" as const, label: "My vehicles", icon: <CarFront size={17} /> },
    ...(user && ["owner", "staff", "admin"].includes(user.role) ? [{ id: "operations" as const, label: "Parking operations", icon: <QrCode size={17} /> }] : []),
    ...(user && ["owner", "admin"].includes(user.role) ? [{ id: "insights" as const, label: "Owner insights", icon: <TrendingUp size={17} /> }] : []),
  ];

  const onVerified = async (verified: User) => {
    try {
      await refreshAccount(verified);
      notify(`Welcome${verified.full_name ? `, ${verified.full_name.split(" ")[0]}` : ""}.`);
      if (pendingReservation) {
        const lot = pendingReservation;
        setPendingReservation(null);
        void startReservation(lot);
      }
    } catch (reason) {
      setUser(verified);
      notify(reason instanceof Error ? reason.message : "Signed in, but account details could not be loaded.");
    }
  };

  return !appMode ? (
    <LandingPage
      onFindParking={(type) => {
        if (type) setParkingType(type);
        else setParkingType("All spaces");
        openApp("discover");
      }}
      onOpenApp={(destination) => openApp(destination)}
      onSignIn={() => openApp("discover", true)}
      theme={theme}
      onToggleTheme={() => setTheme((current) => current === "dark" ? "light" : "dark")}
    />
  ) : (
    <div className="app-shell">
      <header className="topbar">
        <button type="button" onClick={returnHome} aria-label="Return to ORT home"><Brand /></button>
        <div className="topbar-right">
          <ThemeToggle theme={theme} onToggle={() => setTheme((current) => current === "dark" ? "light" : "dark")} />
          <button className="location-chip" type="button" onClick={() => { if (page !== "discover") setPage("discover"); window.setTimeout(() => document.getElementById("parking-search")?.focus(), 0); }}><MapPin size={14} className="text-emerald-600" /> {coordinates ? "Near me" : "Bengaluru, India"} <ChevronDown size={13} /></button>
          {!online && <span className="offline-banner"><AlertCircle size={14} /> Offline</span>}
          {user ? <><button className="topbar-action" type="button" onClick={() => setPage("reservations")}><CalendarDays size={14} /> My trips</button><button className="avatar" type="button" title={`${user.full_name} · Sign out`} onClick={signOut}>{user.full_name.slice(0, 1).toUpperCase()}<span className="sr-only">Sign out</span></button></> : <Button size="sm" onClick={() => setLoginOpen(true)}>Sign in</Button>}
        </div>
      </header>
      <div className="layout">
        <aside className="sidebar">
          <nav aria-label="Main navigation">
            <p className="nav-label">Your ORT</p>
            <div className="nav-list">
              {visibleNavigation.map((item) => <button key={item.id} type="button" className={`nav-item${page === item.id ? " active" : ""}`} onClick={() => setPage(item.id)}>{item.icon}<span>{item.label}</span></button>)}
            </div>
          </nav>
          <div>
            <p className="nav-label">Your account</p>
            <div className="nav-list">
              <button type="button" className="nav-item" onClick={() => setLoginOpen(true)}><ShieldCheck size={17} /><span>Account & security</span></button>
              {user && <button type="button" className="nav-item" onClick={signOut}><LogOut size={17} /><span>Sign out</span></button>}
            </div>
          </div>
          <div className="sidebar-note"><span className="stat-icon"><Sparkles size={15} /></span><strong>Parking, without the guesswork.</strong><p>Real-time spaces. Clear prices. A better arrival.</p></div>
          <div className="mt-auto px-3 text-[10px] text-slate-400">Find. Reserve. Park.</div>
        </aside>

        <main className="main">
          {!online && <div className="alert" role="status">You’re offline. Details already loaded in this session remain available. Exit actions will sync when you reconnect.</div>}
          {page === "discover" && <>
            <SectionHeading eyebrow="Your city, closer" title={user ? `Good to see you, ${user.full_name.split(" ")[0]}.` : "Find a better place to park."} description="See what’s open near your next stop — before you get there." action={<Button variant="outline" onClick={() => { if (!navigator.geolocation) { notify("Location services are not available in this browser."); return; } navigator.geolocation.getCurrentPosition((position) => setCoordinates({ latitude: position.coords.latitude, longitude: position.coords.longitude }), () => notify("Location permission was not granted."), { timeout: 8000, maximumAge: 60000 }); }}><LocateFixed size={15} /> Near me</Button>} />
            {user && <div className="stats-grid">
              <StatCard label="Available nearby" value={visibleLots.reduce((sum, lot) => sum + lot.available_slots, 0)} footnote={`${visibleLots.length} locations in your search`} icon={<ParkingCircle size={16} />} />
              <StatCard label="Upcoming reservations" value={activeBookings.length} footnote="Ready when you are" icon={<CalendarDays size={16} />} />
              <StatCard label="Your vehicles" value={vehicles.length} footnote="All your cars, one account" icon={<CarFront size={16} />} />
              <StatCard label="Parking sessions" value={activeSessions.length} footnote={activeSessions.length ? "Currently parked" : "No active sessions"} icon={<Clock3 size={16} />} />
            </div>}
            {searchError && <div className="alert" role="alert">Parking search is unavailable: {searchError}</div>}
            <div className="search-layout">
              <section className="panel search-panel" aria-label="Parking search results">
                <div className="panel-head"><div><h2>Parking around you</h2><p>Live availability · {visibleLots.length} places to park</p></div>                <Button variant="ghost" size="icon" aria-label="Reset filters" onClick={() => { setParkingType("All spaces"); setParkingMode("Any price"); setCoordinates(null); }}><Filter size={16} /></Button></div>
                <label className="search-box"><Search size={16} /><input id="parking-search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search a place, area or destination" /><button type="button" onClick={() => setQuery("")} aria-label="Clear search">{query && <X size={14} />}</button></label>
                <div className="search-tools">{parkingTypes.map((item) => <button key={item} type="button" className={`filter-chip${parkingType === item ? " selected" : ""}`} onClick={() => setParkingType(item)}>{item}</button>)}</div>
                <div className="search-tools !pt-0">{parkingModes.map((item) => <button key={item} type="button" className={`filter-chip${parkingMode === item ? " selected" : ""}`} onClick={() => setParkingMode(item)}>{item}</button>)}</div>
                <div className="results-meta">{loadingLots ? "Updating live availability…" : `Showing ${visibleLots.length} parking ${visibleLots.length === 1 ? "location" : "locations"}`}</div>
                <div className="lot-list">
                  {loadingLots && !lots.length ? <div className="empty">Loading parking near you…</div>
                    : visibleLots.length ? visibleLots.map((lot) => <ParkingLotCard key={lot.id} lot={lot} selected={lot.id === selectedLot} onSelect={() => selectLot(lot)} onReserve={() => void startReservation(lot)} />)
                      : <div className="empty">{searchError ? "Try again once the service is available." : "No spaces match these filters. Try another parking type or nearby area."}</div>}
                </div>
              </section>
              <ParkingMap lots={visibleLots} selectedId={selectedLot} theme={theme} onSelect={selectLot} onLocate={setCoordinates} />
            </div>
            {selected && <section className="panel mt-4 flex flex-wrap items-center justify-between gap-4 p-4"><div className="flex items-center gap-3"><span className="stat-icon"><MapPin size={16} /></span><div><strong className="text-xs">{selected.name}</strong><p className="mt-1 text-[10px] text-slate-500">{selected.address} · {selected.available_slots} spaces open</p></div></div><Button size="sm" onClick={() => void startReservation(selected)}>Reserve a space <ArrowRight size={14} /></Button></section>}
            {user && <section className="panel mt-4 p-4"><div className="flex flex-wrap items-center justify-between gap-3"><div><strong className="text-xs">Just arrived? Start a walk-in session</strong><p className="mt-1 text-[10px] text-slate-500">Your digital ticket is ready in seconds. Keep your phone handy at exit.</p></div><Button variant="outline" size="sm" onClick={() => setPage("operations")}><QrCode size={14} /> Start parking</Button></div></section>}
          </>}

          {page === "reservations" && <>
            <SectionHeading eyebrow="Your parking plans" title="Reservations & history" description="Your upcoming bookings and every trip, together." action={<Button onClick={() => setPage("discover")}><Plus size={15} /> Find parking</Button>} />
            {!user ? <section className="panel"><AuthRequired onSignIn={() => setLoginOpen(true)} /></section> : <>
              <div className="stats-grid"><StatCard label="Upcoming" value={activeBookings.length} footnote="Confirmed and awaiting arrival" icon={<CalendarDays size={16} />} /><StatCard label="Completed trips" value={bookings.filter((booking) => booking.status === "completed").length} footnote="Your parking history" icon={<History size={16} />} /><StatCard label="Active now" value={activeSessions.length} footnote="Live parking sessions" icon={<Clock3 size={16} />} /><StatCard label="Payment method" value="On arrival" footnote="Pay at the parking location" icon={<Wallet size={16} />} /></div>
              <section className="panel"><div className="panel-head"><div><h2>All reservations</h2><p>Manage upcoming plans or find a completed trip.</p></div><ArrowDownUp size={15} className="text-slate-400" /></div>
                {bookings.length ? bookings.map((booking) => {
                  const lot = lots.find((item) => item.id === booking.parking_slot_id);
                  return <div className="table-row" key={booking.id}><div><strong>{lot?.name ?? "ORT reservation"}</strong><p className="mt-1 text-[10px] text-slate-500">{readableDate(booking.starts_at)}</p></div><div>{money(booking.total_amount)}</div><span className={`status-pill${booking.status === "cancelled" ? " closed" : ""}`}>{booking.status}</span>{(booking.status === "pending" || booking.status === "confirmed") ? <Button variant="ghost" size="sm" disabled={actionBusy} onClick={() => void cancelBooking(booking)}>Cancel</Button> : <span />}</div>;
                }) : <div className="empty">No reservations yet. Find a space for your next trip.</div>}
              </section>
              <section className="panel mt-4"><div className="panel-head"><div><h2>Live parking sessions</h2><p>Find your vehicle and close your session when you leave.</p></div></div>
                {sessions.length ? sessions.map((session) => <SessionRow key={session.id} session={session} lot={lots.find((item) => item.id === session.parking_lot_id)} vehicle={vehicles.find((item) => item.id === session.vehicle_id)} role={user.role} onClose={() => void closeSession(session)} onValetAction={(action) => void updateValetSession(session, action)} busy={actionBusy} />) : <div className="empty">No parking sessions yet.</div>}
              </section>
              {corporatePasses.length > 0 && <section className="panel mt-4"><div className="panel-head"><div><h2>Digital parking passes</h2><p>Show your QR code to parking staff at arrival.</p></div><Ticket size={16} className="text-emerald-600" /></div>
                {corporatePasses.map((pass) => <div className="table-row !grid-cols-[auto_1fr_auto_auto]" key={pass.id}><QRCodeSVG value={pass.pass_code} size={44} title={`Pass ${pass.pass_code}`} /><div><strong>{pass.visitor_name || titleCase(pass.pass_type)} · {pass.pass_code}</strong><p className="mt-1 text-[10px] text-slate-500">{titleCase(pass.status)}{pass.expires_at ? ` · Expires ${readableDate(pass.expires_at)}` : " · No expiry"}</p></div><span className="status-pill">{titleCase(pass.pass_type)}</span>{pass.status === "active" && <Button variant="outline" size="sm" disabled={actionBusy} onClick={() => void revokePass(pass)}>Revoke</Button>}</div>)}
              </section>}
            </>}
          </>}

          {page === "vehicles" && <>
            <SectionHeading eyebrow="Your garage" title="Your vehicles" description="Save your plate once. Check in and get on your way." />
            {!user ? <section className="panel"><AuthRequired onSignIn={() => setLoginOpen(true)} /></section> : <div className="section-grid">
              <section className="panel"><div className="panel-head"><div><h2>Saved vehicles</h2><p>{vehicles.length} of your vehicles</p></div><CarFront size={16} className="text-emerald-600" /></div>
                {vehicles.length ? vehicles.map((vehicle) => <div className="table-row !grid-cols-[1fr_auto]" key={vehicle.id}><div><strong>{vehicle.label}</strong><p className="mt-1 text-[10px] uppercase tracking-widest text-slate-500">{vehicle.plate_number} · {titleCase(vehicle.vehicle_type)}</p></div><div className="flex items-center gap-2">{vehicle.is_default && <span className="status-pill">Default</span>}<button className="text-slate-400 hover:text-rose-600" type="button" aria-label={`Remove ${vehicle.plate_number}`} onClick={async () => { try { await parkEnApi.deleteVehicle(vehicle.id); setVehicles((current) => current.filter((item) => item.id !== vehicle.id)); notify("Vehicle removed."); } catch (reason) { notify(reason instanceof Error ? reason.message : "Vehicle could not be removed."); } }}><Trash2 size={15} /></button></div></div>) : <div className="empty">Add your first vehicle to reserve and start parking.</div>}
              </section>
              <section className="panel"><div className="panel-head"><div><h2>Add a vehicle</h2><p>Vehicle details stay private to your account.</p></div><Plus size={16} className="text-emerald-600" /></div>
                <form className="form-grid" onSubmit={addVehicle}>
                  <label className="field">Number plate<input required minLength={2} maxLength={20} placeholder="KA 03 MN 2486" value={vehiclePlate} onChange={(event) => setVehiclePlate(event.target.value)} /></label>
                  <label className="field">Vehicle nickname<input maxLength={60} placeholder="Blue hatchback" value={vehicleLabel} onChange={(event) => setVehicleLabel(event.target.value)} /></label>
                  <label className="field">Vehicle type<select value={vehicleType} onChange={(event) => setVehicleType(event.target.value)}><option value="car">Car</option><option value="motorcycle">Motorcycle</option><option value="suv">SUV</option><option value="van">Van</option><option value="truck">Truck</option></select></label>
                  <Button type="submit" disabled={actionBusy}>Save vehicle <ArrowRight size={14} /></Button>
                </form>
              </section>
            </div>}
          </>}

          {page === "operations" && <>
            <SectionHeading eyebrow={user?.role === "customer" ? "Arrive & go" : "Parking team"} title={user?.role === "customer" ? "Your parking sessions" : "Parking operations"} description={user?.role === "customer" ? "Start a walk-in, see where you parked, and find your car." : "Session control, staff workflows, and incident reporting."} action={user && <span className="status-pill">{titleCase(user.role)} access</span>} />
            {!user ? <section className="panel"><AuthRequired onSignIn={() => setLoginOpen(true)} /></section> : <>
              <div className="stats-grid"><StatCard label="Active sessions" value={activeSessions.length} footnote="Vehicles currently parked" icon={<CarFront size={16} />} /><StatCard label="Current locations" value={visibleLots.length} footnote="Open parking facilities" icon={<Building2 size={16} />} />              <StatCard label="Offline queue" value={offlineExitCount} footnote="Exit actions pending sync" icon={<Zap size={16} />} /><StatCard label="Identification" value="QR · ID · Plate" footnote="Find a session three ways" icon={<QrCode size={16} />} /></div>
              {user.role === "customer" && <section className="panel mb-4"><div className="panel-head"><div><h2>Start a walk-in session</h2><p>Instant digital ticket and a session ID for your visit.</p></div><QrCode size={16} className="text-emerald-600" /></div>
                {!vehicles.length ? <div className="empty">Add a vehicle before starting a parking session. <Button size="sm" variant="outline" onClick={() => setPage("vehicles")}>Add vehicle</Button></div> : <form className="form-grid !grid-cols-1 md:!grid-cols-[1fr_1fr_1fr_auto] md:!items-end" onSubmit={startWalkIn}><label className="field">Vehicle<select required value={sessionVehicleId} onChange={(event) => setSessionVehicleId(event.target.value)}>{vehicles.map((vehicle) => <option value={vehicle.id} key={vehicle.id}>{vehicle.plate_number} · {vehicle.label}</option>)}</select></label><label className="field">Parking location<select required value={sessionLot} onChange={(event) => setSessionLot(event.target.value)}><option value="">Choose an open location</option>{visibleLots.map((lot) => <option value={lot.id} key={lot.id}>{lot.name} · {lot.available_slots} spaces open</option>)}</select></label><label className="field">Parking slot<select required value={sessionSlotId} onChange={(event) => setSessionSlotId(event.target.value)}><option value="">Choose an available slot</option>{sessionSlots.map((slot) => <option value={slot.id} key={slot.id}>{slot.slot_number} · {titleCase(slot.category)} · {slot.level_name ?? "Ground floor"}</option>)}</select></label><Button type="submit" disabled={actionBusy || !online || !sessionSlotId}><QrCode size={14} /> Start parking</Button></form>}
              </section>}
              {user.role !== "customer" && <section className="panel mb-4"><div className="panel-head"><div><h2>Verify a digital parking pass</h2><p>Validate an active visitor or corporate QR pass.</p></div><BadgeCheck size={16} className="text-emerald-600" /></div>
                <form className="form-grid !grid-cols-1 md:!grid-cols-[1fr_1fr_auto] md:!items-end" onSubmit={lookupStaffPass}>
                  <label className="field">Assigned location<select required value={sessionLot} onChange={(event) => { setSessionLot(event.target.value); setLookedUpPass(null); }}><option value="">Choose a location</option>{managedLots.map((lot) => <option key={lot.id} value={lot.id}>{lot.name}</option>)}</select></label>
                  <label className="field">Visitor / corporate pass code<input required minLength={8} maxLength={24} value={corporatePassCode} onChange={(event) => { setCorporatePassCode(event.target.value.toUpperCase()); setLookedUpPass(null); }} placeholder="Paste code from QR pass" /></label>
                  <Button type="submit" disabled={actionBusy || !sessionLot}>Verify pass</Button>
                </form>
                {lookedUpPass && <div className="mt-3 flex items-center gap-3 rounded-lg bg-emerald-50 p-3"><BadgeCheck size={18} className="text-emerald-700" /><div><strong className="text-xs">{lookedUpPass.visitor_name || titleCase(lookedUpPass.pass_type)} · {lookedUpPass.pass_code}</strong><p className="mt-1 text-[10px] text-slate-500">Active {titleCase(lookedUpPass.pass_type)} pass{lookedUpPass.expires_at ? ` · Expires ${readableDate(lookedUpPass.expires_at)}` : ""}</p></div></div>}
              </section>}
              {user.role !== "customer" && <section className="panel mb-4"><div className="panel-head"><div><h2>Find a parking session</h2><p>Identify by QR token, session ID, or vehicle plate.</p></div><Search size={16} className="text-emerald-600" /></div>
                <form className="form-grid !grid-cols-1 md:!grid-cols-[1fr_1fr_1.3fr_auto] md:!items-end" onSubmit={lookupStaffSession}>
                  <label className="field">Assigned location<select required value={sessionLot} onChange={(event) => setSessionLot(event.target.value)}><option value="">Choose a location</option>{managedLots.map((lot) => <option key={lot.id} value={lot.id}>{lot.name}</option>)}</select></label>
                  <label className="field">Identify with<select value={staffMethod} onChange={(event) => setStaffMethod(event.target.value)}><option value="session_id">Session ID</option><option value="vehicle_number">Vehicle plate</option><option value="qr_code">QR token</option></select></label>
                  <label className="field">Scan result or identifier<input required value={staffValue} onChange={(event) => setStaffValue(event.target.value)} placeholder="Enter or paste the identifier" /></label>
                  <Button type="submit" disabled={actionBusy}>Find session</Button>
                </form>
                {staffSession && <div className="border-t border-slate-100 p-4"><div className="flex flex-wrap items-center justify-between gap-3"><div><strong className="text-xs">Session {staffSession.public_id}</strong><p className="mt-1 text-[10px] text-slate-500">Vehicle session · entered {readableDate(staffSession.entry_at)}</p></div><span className="status-pill">{staffSession.status}</span></div>{staffSession.status === "active" && <div className="mt-3 flex flex-wrap items-end gap-2"><select className="h-9 rounded-lg border border-slate-200 bg-white px-3 text-xs" value={staffSlotId} onChange={(event) => setStaffSlotId(event.target.value)}><option value="">Assign a slot</option>{staffSlots.map((slot) => <option key={slot.id} value={slot.id}>{slot.slot_number} · {slot.category} · {slot.level_name ?? "Ground"}{slot.status === "maintenance" ? " · maintenance override" : ""}</option>)}</select>{staffSlotId && staffSlots.find((slot) => slot.id === staffSlotId)?.status === "maintenance" && <label className="field !min-w-48">Override reason<input minLength={8} value={overrideReason} onChange={(event) => setOverrideReason(event.target.value)} placeholder="Hospital emergency reason" /></label>}<Button size="sm" variant="outline" disabled={actionBusy || !staffSlotId || (staffSlots.find((slot) => slot.id === staffSlotId)?.status === "maintenance" && overrideReason.trim().length < 8)} onClick={() => void assignStaffSlot()}>Assign slot</Button>{staffSession.valet_status === "awaiting_handover" && <Button size="sm" variant="outline" disabled={actionBusy} onClick={() => void updateValetSession(staffSession, "handover")}>Record handover</Button>}{staffSession.valet_status === "retrieval_requested" && <Button size="sm" variant="outline" disabled={actionBusy} onClick={() => void updateValetSession(staffSession, "retrieve")}>Complete retrieval</Button>}{(staffSession.valet_status === "standard" || staffSession.valet_status === "retrieved") && <Button size="sm" variant="outline" disabled={actionBusy} onClick={() => { const target = sessions.find((session) => session.id === staffSession.id) ?? staffSession; void closeSession(target); }}>Close session</Button>}</div>}{staffSession.status === "active" && managedLots.find((lot) => lot.id === staffSession.parking_lot_id)?.parking_type === "hospital" && <div className="mt-3 flex flex-wrap items-end gap-2 rounded-lg bg-rose-50 p-3"><div className="mr-auto"><strong className="text-xs">Hospital emergency priority</strong><p className="mt-1 text-[10px] text-slate-500">Allows staff to assign a maintenance slot with an audit reason.</p></div>{!staffSession.emergency_priority && <label className="field !min-w-56">Reason<input minLength={8} value={overrideReason} onChange={(event) => setOverrideReason(event.target.value)} placeholder="Describe the emergency" /></label>}<Button size="sm" variant="outline" disabled={actionBusy || (!staffSession.emergency_priority && overrideReason.trim().length < 8)} onClick={() => void updateEmergencyPriority()}>{staffSession.emergency_priority ? "Clear priority" : "Grant priority"}</Button></div>}</div>}
              </section>}
              <section className="panel mb-4"><div className="panel-head"><div><h2>Active sessions</h2><p>Live arrivals, check-ins, and retrievals.</p></div><span className="status-pill">{activeSessions.length} active</span></div>
                {activeSessions.length ? activeSessions.map((session) => <SessionRow key={session.id} session={session} lot={managedLots.find((item) => item.id === session.parking_lot_id) ?? lots.find((item) => item.id === session.parking_lot_id)} vehicle={vehicles.find((item) => item.id === session.vehicle_id)} role={user.role} onClose={() => void closeSession(session)} onValetAction={(action) => void updateValetSession(session, action)} busy={actionBusy} />) : <div className="empty">No active sessions. A walk-in session appears here after check-in.</div>}
              </section>
              <section className="panel"><div className="panel-head"><div><h2>Report an incident</h2><p>Let the parking team know about safety or facility issues.</p></div><AlertCircle size={16} className="text-amber-500" /></div>
                <form className="form-grid" onSubmit={submitIncident}><label className="field">Parking location<select required value={sessionLot} onChange={(event) => setSessionLot(event.target.value)}><option value="">Choose a location</option>{visibleLots.map((lot) => <option key={lot.id} value={lot.id}>{lot.name}</option>)}</select></label><label className="field">Category<select value={incidentCategory} onChange={(event) => setIncidentCategory(event.target.value)}><option value="facility">Facility</option><option value="safety">Safety</option><option value="payment">Payment</option><option value="vehicle">Vehicle</option><option value="staff">Staff</option><option value="other">Other</option></select></label><label className="field">What happened?<textarea required minLength={8} maxLength={4000} value={incidentDescription} onChange={(event) => setIncidentDescription(event.target.value)} placeholder="Share enough detail for the team to help." /></label><Button type="submit" disabled={actionBusy}>Send incident report</Button></form>
              </section>
            </>}
          </>}

          {page === "insights" && <>
            <SectionHeading eyebrow="Your locations" title="Parking insights" description="A live view of capacity, occupancy, and booking performance." action={<Button variant="outline" onClick={() => { void parkEnApi.analytics().then(setAnalytics).catch((reason) => notify(reason instanceof Error ? reason.message : "Analytics could not be loaded.")); }}><Activity size={14} /> Refresh</Button>} />
            {!user ? <section className="panel"><AuthRequired onSignIn={() => setLoginOpen(true)} /></section> : !["owner", "admin"].includes(user.role) ? <section className="panel"><div className="empty">Owner analytics are available to verified parking owners and administrators.</div></section> : analytics ? <>
              <div className="stats-grid"><StatCard label="Locations" value={analytics.locations} footnote="Managed parking facilities" icon={<Building2 size={16} />} /><StatCard label="Occupancy" value={`${analytics.occupancy_rate}%`} footnote={`${analytics.occupied} occupied · ${analytics.capacity} total slots`} icon={<Activity size={16} />} /><StatCard label="Booking revenue" value={money(analytics.revenue)} footnote="Confirmed and completed reservations" icon={<Wallet size={16} />} /><StatCard label="Bookings" value={analytics.bookings} footnote="Total reservations" icon={<TrendingUp size={16} />} /></div>
              <div className="section-grid"><section className="panel"><div className="panel-head"><div><h2>Utilization at a glance</h2><p>Current live occupancy across your locations</p></div><span className="stat-icon"><Activity size={15} /></span></div><div className="p-5"><div className="mb-2 flex justify-between text-xs"><span>Occupied spaces</span><strong>{analytics.occupancy_rate}%</strong></div><div className="h-3 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-emerald-600 transition-all" style={{ width: `${analytics.occupancy_rate}%` }} /></div><div className="mt-4 flex justify-between text-[10px] text-slate-500"><span>{analytics.occupied} occupied</span><span>{Math.max(0, analytics.capacity - analytics.occupied)} available</span></div></div></section>
                <section className="panel"><div className="panel-head"><div><h2>Smart parking insights</h2><p>Operational signals, updated from live inventory</p></div><Sparkles size={16} className="text-emerald-600" /></div><div className="form-grid"><InsightRow icon={<BadgeCheck size={15} />} title="Availability right now" text={`${visibleLots.reduce((sum, lot) => sum + lot.available_slots, 0)} spaces are available across the current search.`} /><InsightRow icon={<Clock3 size={15} />} title="Busiest arrival hour" text={analytics.peak_entry_hour === null ? "No parking-session arrival pattern is available yet." : `Most arrivals have started around ${String(analytics.peak_entry_hour).padStart(2, "0")}:00 local database time.`} /><InsightRow icon={<AlertCircle size={15} />} title="Overstay watch" text={`${analytics.overstay_sessions} active session${analytics.overstay_sessions === 1 ? "" : "s"} have been open for more than 12 hours.`} /><InsightRow icon={<TrendingUp size={15} />} title="Reservations to date" text={`${analytics.bookings} reservations recorded across your managed locations.`} /></div></section>
              </div>
              <section className="panel mt-4"><div className="panel-head"><div><h2>Corporate & visitor passes</h2><p>Create time-limited digital access for visitors at a managed parking location.</p></div><Ticket size={16} className="text-emerald-600" /></div>
                {!managedLots.length ? <div className="empty">No active managed parking locations are available.</div> : <form className="form-grid md:!grid-cols-2" onSubmit={createVisitorPass}>
                  <label className="field">Parking location<select value={visitorLotId} onChange={(event) => setVisitorLotId(event.target.value)}>{managedLots.map((lot) => <option key={lot.id} value={lot.id}>{lot.name}</option>)}</select></label>
                  <label className="field">Visitor name<input minLength={2} maxLength={150} required value={visitorName} onChange={(event) => setVisitorName(event.target.value)} placeholder="Visitor's full name" /></label>
                  <label className="field">Visitor mobile number<input type="tel" value={visitorPhone} onChange={(event) => setVisitorPhone(event.target.value.replaceAll(" ", ""))} placeholder="+919876543210" /></label>
                  <label className="field">Pass expires<input type="datetime-local" required min={localDateTime(new Date())} value={visitorPassExpiry} onChange={(event) => setVisitorPassExpiry(event.target.value)} /></label>
                  <Button type="submit" disabled={actionBusy || !visitorLotId}>Create visitor pass <ArrowRight size={14} /></Button>
                </form>}
              </section>
              {corporatePasses.length > 0 && <section className="panel mt-4"><div className="panel-head"><div><h2>Issued passes</h2><p>Revoke passes that should no longer grant access.</p></div><Users size={16} className="text-emerald-600" /></div>
                {corporatePasses.map((pass) => <div className="table-row !grid-cols-[1fr_auto_auto]" key={pass.id}><div><strong>{pass.visitor_name || titleCase(pass.pass_type)} · {pass.pass_code}</strong><p className="mt-1 text-[10px] text-slate-500">{titleCase(pass.status)}{pass.expires_at ? ` · Expires ${readableDate(pass.expires_at)}` : " · No expiry"}</p></div><span className="status-pill">{titleCase(pass.pass_type)}</span>{pass.status === "active" && <Button size="sm" variant="outline" disabled={actionBusy} onClick={() => void revokePass(pass)}>Revoke</Button>}</div>)}
              </section>}
            </> : <section className="panel"><div className="empty">Loading owner analytics…</div></section>}
          </>}
        </main>
      </div>

      <nav className="mobile-bottom" aria-label="Mobile navigation">
        {visibleNavigation.slice(0, 4).map((item) => <button type="button" aria-label={item.label} className={`mobile-nav${page === item.id ? " active" : ""}`} key={item.id} onClick={() => setPage(item.id)}>{item.icon}{item.label.split(" ")[0]}</button>)}
      </nav>

      {loginOpen && <OtpDialog onClose={() => setLoginOpen(false)} onVerified={(verified) => { void onVerified(verified); }} />}
      {bookingLot && <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setBookingLot(null); }}><section className="modal" role="dialog" aria-modal="true" aria-labelledby="reserve-title"><div className="modal-head"><div><h2 id="reserve-title">Reserve your space</h2><p>{bookingLot.name} · {bookingLot.address}</p></div><button className="modal-close" type="button" onClick={() => setBookingLot(null)} aria-label="Close"><X size={16} /></button></div><form className="form-grid" onSubmit={confirmBooking}><label className="field">Arrival time<input type="datetime-local" required min={localDateTime(new Date())} value={bookingStart} onChange={(event) => setBookingStart(event.target.value)} /></label><label className="field">Available slot<select value={bookingSlot} onChange={(event) => setBookingSlot(event.target.value)}>{bookingSlots.map((slot) => <option key={slot.id} value={slot.id}>{slot.slot_number} · {titleCase(slot.category)} · {slot.level_name ?? "Ground floor"} · {money(slot.hourly_rate)}/hour</option>)}</select></label><label className="field">Parking duration<select value={bookingHours} onChange={(event) => setBookingHours(Number(event.target.value))}><option value={1}>1 hour</option><option value={2}>2 hours</option><option value={3}>3 hours</option><option value={4}>4 hours</option><option value={8}>8 hours</option></select></label><div className="flex items-center justify-between rounded-xl bg-emerald-50 p-3 text-xs"><span>Estimated total</span><strong>{money(Number(bookingSlots.find((slot) => slot.id === bookingSlot)?.hourly_rate ?? 0) * bookingHours)}</strong></div><Button type="submit" disabled={actionBusy || !bookingSlot}>{actionBusy ? "Confirming…" : <>Confirm reservation <ArrowRight size={15} /></>}</Button><p className="text-[10px] text-slate-400">Your space is secured when the reservation is confirmed. Payment is handled at the parking location.</p></form></section></div>}
      {qrSession && <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setQrSession(null); }}><section className="modal text-center" role="dialog" aria-modal="true" aria-labelledby="qr-title"><div className="modal-head text-left"><div><h2 id="qr-title">Your digital parking pass</h2><p>Show this code to the parking team when you arrive or leave.</p></div><button className="modal-close" type="button" onClick={() => setQrSession(null)} aria-label="Close"><X size={16} /></button></div><div className="mx-auto my-6 inline-flex rounded-2xl border border-slate-100 bg-white p-4"><QRCodeSVG value={qrSession.token} size={190} level="M" includeMargin /></div><p className="text-xs text-slate-500">Session ID</p><p className="mt-1 text-xl font-bold tracking-[.16em]">{qrSession.session.public_id}</p><Button className="mt-5 w-full" onClick={() => { setQrSession(null); setPage("reservations"); }}>Done</Button></section></div>}
      {toast && <div className="toast" role="status">{toast}</div>}
    </div>
  );
}

function SessionRow({ session, lot, vehicle, role, onClose, onValetAction, busy }: { session: ParkingSession; lot?: ParkingLot; vehicle?: Vehicle; role: User["role"]; onClose: () => void; onValetAction: (action: "handover" | "request" | "retrieve") => void; busy: boolean }) {
  const staff = role !== "customer";
  const valet = session.valet_status !== "standard";
  let action: ReactNode = <span />;
  if (session.status === "active" && !valet) {
    action = <Button variant="outline" size="sm" disabled={busy} onClick={onClose}>Exit</Button>;
  } else if (session.status === "active" && valet && session.valet_status === "awaiting_handover" && staff) {
    action = <Button variant="outline" size="sm" disabled={busy} onClick={() => onValetAction("handover")}>Record handover</Button>;
  } else if (session.status === "active" && valet && session.valet_status === "parked" && !staff) {
    action = <Button variant="outline" size="sm" disabled={busy} onClick={() => onValetAction("request")}>Request my vehicle</Button>;
  } else if (session.status === "active" && valet && session.valet_status === "retrieval_requested" && staff) {
    action = <Button variant="outline" size="sm" disabled={busy} onClick={() => onValetAction("retrieve")}>Complete retrieval</Button>;
  } else if (session.status === "active" && valet && session.valet_status === "retrieved") {
    action = <Button variant="outline" size="sm" disabled={busy} onClick={onClose}>Close session</Button>;
  }
  return <div className="table-row"><div className="flex items-center gap-3"><span className="stat-icon"><CarFront size={15} /></span><div><strong>{vehicle?.label ?? "Vehicle"}{vehicle?.plate_number ? ` · ${vehicle.plate_number}` : ""}</strong><p className="mt-1 text-[10px] text-slate-500">{lot?.name ?? "Parking location"} · {readableDate(session.entry_at)}</p></div></div><div><strong>{session.public_id}</strong><p className="mt-1 text-[10px] text-slate-500">{valet ? `Valet · ${titleCase(session.valet_status)}` : session.parking_slot_id ? "Slot assigned" : "Find my vehicle · open slot"}</p></div><span className={`status-pill${session.status === "closed" ? " closed" : ""}`}>{session.status === "active" && !session.synced_at && session.entry_method === "offline" ? "offline" : session.status}</span>{action}</div>;
}

function InsightRow({ icon, title, text }: { icon: ReactNode; title: string; text: string }) {
  return <div className="flex items-start gap-3"><span className="stat-icon shrink-0">{icon}</span><div><strong className="text-xs">{title}</strong><p className="mt-1 text-[10px] leading-5 text-slate-500">{text}</p></div></div>;
}
