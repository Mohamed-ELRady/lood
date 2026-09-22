"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  ArrowDownToLine,
  Check,
  Clipboard,
  Download,
  FileAudio,
  Film,
  LoaderCircle,
  Moon,
  RotateCcw,
  Sparkles,
  Sun,
  X,
  Zap
} from "lucide-react";
import { analyzeMedia, cancelJob, createDownload, getJob, retryJob, saveJobFile } from "@/lib/api";
import type { DownloadJob, MediaFormat, MediaInfo } from "@/lib/types";

type Lang = "ar" | "en";
type Mode = "video" | "audio";

const copy = {
  ar: {
    eyebrow: "تنزيل الوسائط، بلا ضوضاء",
    titleA: "الرابط يدخل.",
    titleB: "ملفك يخرج.",
    lead: "الصق رابطًا عامًا، واختر الجودة المتاحة فعلًا، واترك الباقي لـ LOOD.",
    placeholder: "الصق رابط YouTube أو TikTok أو Instagram…",
    paste: "لصق",
    analyze: "حلّل الرابط",
    analyzing: "جارٍ التحليل",
    secure: "لا نطلب تسجيل الدخول أو ملفات تعريف الارتباط",
    supports: "YouTube · TikTok · Instagram · Facebook · X · Vimeo · SoundCloud",
    video: "فيديو",
    audio: "صوت فقط",
    quality: "الجودة والصيغة",
    audioFormat: "صيغة الصوت",
    rights: "أؤكد أنني أملك حق تنزيل هذا المحتوى أو لدي تصريح بذلك.",
    start: "ابدأ التنزيل",
    duration: "المدة",
    source: "المصدر",
    size: "الحجم التقريبي",
    unknown: "غير محدد",
    job: "عملية التنزيل",
    preparing: "تجهيز",
    processing: "معالجة",
    downloading: "تنزيل",
    completed: "اكتمل",
    failed: "تعذّر",
    cancelled: "أُلغي",
    cancel: "إلغاء",
    save: "حفظ الملف",
    retry: "إعادة المحاولة",
    again: "رابط جديد",
    install: "تثبيت التطبيق",
    offline: "أنت دون اتصال. يمكنك فتح LOOD، لكن التحليل والتنزيل يحتاجان إلى الإنترنت.",
    noFormats: "لم يُرجع المصدر صيغًا قابلة للتنزيل.",
    validUrl: "أدخل رابطًا صحيحًا من مصدر مدعوم.",
    original: "لا يرفع LOOD جودة الملف الأصلية عند التحويل.",
    footer: "حمّل فقط المحتوى العام المسموح لك بحفظه. لا يتجاوز LOOD حماية DRM أو قيود الوصول."
  },
  en: {
    eyebrow: "Media downloads, without the noise",
    titleA: "Link goes in.",
    titleB: "Your file comes out.",
    lead: "Paste a public link, choose a quality that actually exists, and leave the rest to LOOD.",
    placeholder: "Paste a YouTube, TikTok, or Instagram link…",
    paste: "Paste",
    analyze: "Analyze link",
    analyzing: "Analyzing",
    secure: "No sign-in or account cookies requested",
    supports: "YouTube · TikTok · Instagram · Facebook · X · Vimeo · SoundCloud",
    video: "Video",
    audio: "Audio only",
    quality: "Quality & format",
    audioFormat: "Audio format",
    rights: "I confirm I own this media or have permission to download it.",
    start: "Start download",
    duration: "Duration",
    source: "Source",
    size: "Approx. size",
    unknown: "Unknown",
    job: "Download job",
    preparing: "Preparing",
    processing: "Processing",
    downloading: "Downloading",
    completed: "Completed",
    failed: "Failed",
    cancelled: "Cancelled",
    cancel: "Cancel",
    save: "Save file",
    retry: "Retry",
    again: "New link",
    install: "Install app",
    offline: "You are offline. LOOD can open, but analysis and new downloads need a connection.",
    noFormats: "The source returned no downloadable formats.",
    validUrl: "Enter a valid link from a supported source.",
    original: "LOOD never claims a conversion improves the original quality.",
    footer: "Only download public media you have permission to save. LOOD does not bypass DRM or access restrictions."
  }
} as const;

function formatTime(seconds?: number) {
  if (!seconds) return "—";
  const minutes = Math.floor(seconds / 60);
  const rest = Math.floor(seconds % 60);
  return `${minutes}:${String(rest).padStart(2, "0")}`;
}

function formatBytes(bytes?: number) {
  if (!bytes) return "—";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit++;
  }
  return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[unit]}`;
}

function isLikelyUrl(value: string) {
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol);
  } catch {
    return false;
  }
}

export function DownloadWorkbench() {
  const [lang, setLang] = useState<Lang>("ar");
  const [dark, setDark] = useState(false);
  const [online, setOnline] = useState(true);
  const [url, setUrl] = useState("");
  const [media, setMedia] = useState<MediaInfo | null>(null);
  const [mode, setMode] = useState<Mode>("video");
  const [formatId, setFormatId] = useState("");
  const [audioFormat, setAudioFormat] = useState<"mp3" | "m4a" | "webm">("mp3");
  const [authorized, setAuthorized] = useState(false);
  const [job, setJob] = useState<DownloadJob | null>(null);
  const [installPrompt, setInstallPrompt] = useState<Event | null>(null);
  const t = copy[lang];

  useEffect(() => {
    const stored = localStorage.getItem("lood-theme");
    const initialDark = stored ? stored === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    setDark(initialDark);
    document.documentElement.classList.toggle("dark", initialDark);
    const updateOnline = () => setOnline(navigator.onLine);
    updateOnline();
    addEventListener("online", updateOnline);
    addEventListener("offline", updateOnline);
    const capture = (event: Event) => {
      event.preventDefault();
      setInstallPrompt(event);
    };
    addEventListener("beforeinstallprompt", capture);
    return () => {
      removeEventListener("online", updateOnline);
      removeEventListener("offline", updateOnline);
      removeEventListener("beforeinstallprompt", capture);
    };
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  }, [lang]);

  const formats = useMemo(
    () => media?.formats.filter((item) => mode === "video" ? item.kind === "video" : item.kind === "audio" || item.has_audio) ?? [],
    [media, mode]
  );

  useEffect(() => {
    setFormatId(formats[0]?.id ?? "");
  }, [formats]);

  const analyze = useMutation({
    mutationFn: analyzeMedia,
    onSuccess: (result) => {
      setMedia(result);
      setJob(null);
      const preferredMode = result.formats.some((item) => item.kind === "video") ? "video" : "audio";
      setMode(preferredMode);
    }
  });

  const create = useMutation({
    mutationFn: createDownload,
    onSuccess: setJob
  });

  const polling = useQuery({
    queryKey: ["job", job?.id],
    queryFn: () => getJob(job!.id),
    enabled: Boolean(job && !["completed", "failed", "cancelled"].includes(job.status)),
    refetchInterval: 1200
  });

  useEffect(() => {
    if (polling.data) setJob(polling.data);
  }, [polling.data]);

  const chosen = formats.find((item) => item.id === formatId);
  const error = (analyze.error || create.error || polling.error) as Error | null;
  const busy = analyze.isPending || create.isPending;

  function toggleTheme() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("lood-theme", next ? "dark" : "light");
  }

  async function paste() {
    try {
      setUrl(await navigator.clipboard.readText());
    } catch {
      document.getElementById("media-url")?.focus();
    }
  }

  function submitAnalyze(event: React.FormEvent) {
    event.preventDefault();
    if (!isLikelyUrl(url)) return;
    analyze.mutate(url.trim());
  }

  function startDownload() {
    if (!media || !formatId || !authorized) return;
    create.mutate({
      url: media.webpage_url,
      format_id: formatId,
      output_type: mode,
      ...(mode === "audio" ? { audio_format: audioFormat } : {}),
      authorized
    });
  }

  function reset() {
    setUrl("");
    setMedia(null);
    setJob(null);
    setAuthorized(false);
    analyze.reset();
    create.reset();
  }

  const statusLabel = job ? t[job.status] : "";

  return (
    <main className="min-h-screen overflow-hidden bg-paper text-ink transition-colors">
      <div className="noise" aria-hidden="true" />
      <header className="relative z-20 mx-auto flex max-w-7xl items-center justify-between px-5 py-5 sm:px-8 lg:px-12">
        <button onClick={reset} className="group flex items-center gap-3" aria-label="LOOD home">
          <span className="logo-mark"><ArrowDownToLine size={21} strokeWidth={2.5} /></span>
          <span className="font-display text-xl font-black tracking-[-0.06em]">LOOD</span>
        </button>
        <div className="flex items-center gap-2">
          {installPrompt && (
            <button
              className="hidden items-center gap-2 rounded-full border border-line px-4 py-2 text-xs font-bold sm:flex"
              onClick={() => (installPrompt as Event & { prompt: () => void }).prompt()}
            >
              <Download size={14} /> {t.install}
            </button>
          )}
          <button className="icon-button" onClick={() => setLang(lang === "ar" ? "en" : "ar")} aria-label="Switch language">
            <span className="text-[11px] font-black">{lang === "ar" ? "EN" : "عر"}</span>
          </button>
          <button className="icon-button" onClick={toggleTheme} aria-label="Toggle theme">
            {dark ? <Sun size={17} /> : <Moon size={17} />}
          </button>
        </div>
      </header>

      {!online && (
        <div className="relative z-20 mx-auto mb-4 max-w-3xl px-5">
          <div className="flex items-center gap-2 rounded-2xl border border-coral/25 bg-coral/10 px-4 py-3 text-sm">
            <AlertCircle size={17} className="shrink-0 text-coral" /> {t.offline}
          </div>
        </div>
      )}

      <section className="relative z-10 mx-auto max-w-7xl px-5 pb-20 pt-10 sm:px-8 sm:pt-16 lg:px-12 lg:pt-20">
        <div className="hero-orbit" aria-hidden="true"><span /><span /><span /></div>
        <div className="mx-auto max-w-4xl text-center">
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-signal/20 bg-signal/10 px-4 py-2 text-xs font-bold text-signal">
            <Zap size={14} fill="currentColor" /> {t.eyebrow}
          </div>
          <h1 className="font-display text-[clamp(2.7rem,8vw,6.6rem)] font-black leading-[0.9] tracking-[-0.075em]">
            {t.titleA}<br /><span className="signal-text">{t.titleB}</span>
          </h1>
          <p className="mx-auto mt-7 max-w-2xl text-base leading-8 text-muted sm:text-lg">{t.lead}</p>
        </div>

        <div className="relative mx-auto mt-10 max-w-4xl sm:mt-14">
          <form onSubmit={submitAnalyze} className="input-shell">
            <div className="flex min-w-0 flex-1 items-center gap-3">
              <span className="hidden h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-signal/10 text-signal sm:flex"><Sparkles size={18} /></span>
              <input
                id="media-url"
                value={url}
                onChange={(event) => setUrl(event.target.value)}
                placeholder={t.placeholder}
                autoComplete="url"
                inputMode="url"
                dir="ltr"
                className="min-w-0 flex-1 bg-transparent py-4 text-left text-sm font-medium outline-none placeholder:text-muted/70 sm:text-base"
                aria-label={t.placeholder}
              />
              <button type="button" onClick={paste} className="paste-button"><Clipboard size={15} /><span className="hidden sm:inline">{t.paste}</span></button>
            </div>
            <button disabled={busy || !online || !isLikelyUrl(url)} className="primary-button min-w-[150px]">
              {analyze.isPending ? <><LoaderCircle className="animate-spin" size={18} />{t.analyzing}</> : <><Zap size={18} fill="currentColor" />{t.analyze}</>}
            </button>
          </form>
          <div className="mt-4 flex flex-col items-center justify-between gap-2 px-2 text-[11px] font-semibold text-muted sm:flex-row">
            <span className="flex items-center gap-2"><span className="status-dot" />{t.secure}</span>
            <span dir="ltr">{t.supports}</span>
          </div>
        </div>

        {error && (
          <div className="mx-auto mt-7 flex max-w-4xl items-start gap-3 rounded-2xl border border-coral/25 bg-coral/10 p-4 text-sm">
            <AlertCircle size={19} className="mt-0.5 shrink-0 text-coral" />
            <span>{error.message}</span>
          </div>
        )}

        {analyze.isPending && <AnalysisSkeleton />}

        {media && !analyze.isPending && (
          <section className="result-card" aria-live="polite">
            <div className="relative min-h-[240px] overflow-hidden bg-[#131827] md:min-h-full">
              {media.thumbnail ? <img src={media.thumbnail} alt="" className="absolute inset-0 h-full w-full object-cover opacity-85" /> : <div className="absolute inset-0 grid place-items-center text-white/40"><Film size={60} /></div>}
              <div className="absolute inset-0 bg-gradient-to-t from-[#080b17] via-transparent to-transparent" />
              <div className="absolute bottom-5 left-5 right-5 flex items-end justify-between text-white">
                <span className="rounded-full bg-black/50 px-3 py-1.5 font-mono text-xs backdrop-blur-md">{formatTime(media.duration)}</span>
                <span className="rounded-full bg-white/15 px-3 py-1.5 text-xs font-bold uppercase backdrop-blur-md">{media.platform}</span>
              </div>
            </div>

            <div className="p-5 sm:p-7 lg:p-9">
              <p className="mb-2 text-xs font-bold uppercase tracking-[0.14em] text-signal">{media.author || media.platform}</p>
              <h2 className="line-clamp-2 font-display text-2xl font-black leading-tight tracking-[-0.035em] sm:text-3xl">{media.title}</h2>

              {!job ? (
                <>
                  <div className="mt-7 grid grid-cols-2 gap-2 rounded-2xl bg-paper p-1.5">
                    <button className={`mode-button ${mode === "video" ? "active" : ""}`} onClick={() => setMode("video")} disabled={!media.formats.some((f) => f.kind === "video")}><Film size={17} />{t.video}</button>
                    <button className={`mode-button ${mode === "audio" ? "active" : ""}`} onClick={() => setMode("audio")} disabled={!media.formats.some((f) => f.kind === "audio" || f.has_audio)}><FileAudio size={17} />{t.audio}</button>
                  </div>

                  <div className="mt-5 grid gap-5 sm:grid-cols-2">
                    <label className="field-label">
                      <span>{t.quality}</span>
                      <select value={formatId} onChange={(event) => setFormatId(event.target.value)} className="select-field">
                        {formats.map((item) => <option key={item.id} value={item.id}>{item.label} · {item.extension.toUpperCase()}{item.has_audio ? " · A/V" : ""}</option>)}
                      </select>
                    </label>
                    {mode === "audio" ? (
                      <label className="field-label">
                        <span>{t.audioFormat}</span>
                        <select value={audioFormat} onChange={(event) => setAudioFormat(event.target.value as typeof audioFormat)} className="select-field">
                          <option value="mp3">MP3</option><option value="m4a">M4A</option><option value="webm">WebM</option>
                        </select>
                      </label>
                    ) : (
                      <div className="field-label"><span>{t.size}</span><div className="select-field flex items-center font-mono">{formatBytes(chosen?.filesize)}</div></div>
                    )}
                  </div>
                  {mode === "audio" && <p className="mt-3 text-xs leading-5 text-muted">{t.original}</p>}
                  {!formats.length && <p className="mt-4 text-sm text-coral">{t.noFormats}</p>}

                  <label className="mt-6 flex cursor-pointer items-start gap-3 text-xs leading-6 text-muted">
                    <input type="checkbox" checked={authorized} onChange={(event) => setAuthorized(event.target.checked)} className="rights-check mt-1" />
                    <span>{t.rights}</span>
                  </label>
                  <button onClick={startDownload} disabled={!formatId || !authorized || create.isPending} className="primary-button mt-6 w-full py-4">
                    {create.isPending ? <LoaderCircle className="animate-spin" size={18} /> : <Download size={18} />} {t.start}
                  </button>
                </>
              ) : (
                <JobPanel
                  job={job}
                  label={statusLabel}
                  t={t}
                  onCancel={async () => setJob(await cancelJob(job.id))}
                  onSave={() => saveJobFile(job)}
                  onRetry={async () => setJob(await retryJob(job.id))}
                  onReset={reset}
                />
              )}
            </div>
          </section>
        )}
      </section>

      <footer className="border-t border-line px-5 py-7 text-center text-xs leading-6 text-muted">{t.footer}</footer>
    </main>
  );
}

function AnalysisSkeleton() {
  return (
    <div className="result-card animate-pulse">
      <div className="min-h-[240px] bg-line/60" />
      <div className="space-y-4 p-8"><div className="h-3 w-24 rounded bg-line" /><div className="h-8 w-4/5 rounded bg-line" /><div className="h-14 rounded-2xl bg-line/70" /><div className="h-12 rounded-2xl bg-line" /></div>
    </div>
  );
}

function JobPanel({ job, label, t, onCancel, onSave, onRetry, onReset }: {
  job: DownloadJob;
  label: string;
  t: (typeof copy)[Lang];
  onCancel: () => void;
  onSave: () => void;
  onRetry: () => void;
  onReset: () => void;
}) {
  const active = ["preparing", "processing", "downloading"].includes(job.status);
  const progress = job.progress ?? 8;
  return (
    <div className="mt-8 rounded-3xl border border-line bg-paper p-5 sm:p-6">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className={`job-icon ${job.status}`}>
            {active ? <LoaderCircle className="animate-spin" size={20} /> : job.status === "completed" ? <Check size={20} /> : <X size={20} />}
          </span>
          <div><p className="text-[11px] font-bold uppercase tracking-wider text-muted">{t.job}</p><p className="font-bold">{label}</p></div>
        </div>
        {job.progress != null && <span className="font-mono text-lg font-bold">{Math.round(job.progress)}%</span>}
      </div>
      <div className="mt-5 h-2 overflow-hidden rounded-full bg-line">
        <div className={`h-full rounded-full transition-all duration-500 ${job.status === "failed" ? "bg-coral" : "bg-signal"}`} style={{ width: `${Math.max(0, Math.min(100, progress))}%` }} />
      </div>
      {job.filename && <div className="mt-4 flex justify-between gap-4 text-xs text-muted"><span className="truncate" dir="ltr">{job.filename}</span><span className="shrink-0 font-mono">{formatBytes(job.filesize)}</span></div>}
      {job.error && <p className="mt-4 rounded-xl bg-coral/10 p-3 text-xs leading-5 text-coral">{job.error}</p>}
      <div className="mt-5 flex gap-2">
        {active && <button onClick={onCancel} className="secondary-button flex-1"><X size={16} />{t.cancel}</button>}
        {job.status === "completed" && <button onClick={onSave} className="primary-button flex-1"><Download size={17} />{t.save}</button>}
        {["failed", "cancelled"].includes(job.status) && <button onClick={onRetry} className="primary-button flex-1"><RotateCcw size={16} />{t.retry}</button>}
        {["completed", "failed", "cancelled"].includes(job.status) && <button onClick={onReset} className="secondary-button"><RotateCcw size={16} /><span className="hidden sm:inline">{t.again}</span></button>}
      </div>
    </div>
  );
}
