import { forwardRef, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export const Button = forwardRef<HTMLButtonElement, ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "ghost" | "danger" }>(
  ({ className, variant = "primary", ...props }, ref) => (
    <button ref={ref} className={cn("inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition-all focus:outline-none focus:ring-2 focus:ring-slate-900/20 disabled:cursor-not-allowed disabled:opacity-50", {
      "bg-slate-950 text-white hover:bg-slate-800": variant === "primary",
      "bg-white text-slate-900 ring-1 ring-slate-200 hover:bg-slate-50": variant === "secondary",
      "text-slate-600 hover:bg-slate-100 hover:text-slate-950": variant === "ghost",
      "bg-rose-600 text-white hover:bg-rose-700": variant === "danger",
    }, className)} {...props} />
  ),
);
Button.displayName = "Button";

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn("rounded-2xl border border-slate-200/80 bg-white shadow-[0_8px_30px_rgb(15,23,42,0.04)]", className)}>{children}</div>;
}
export function Badge({ children, tone = "slate" }: { children: ReactNode; tone?: "slate" | "green" | "amber" | "blue" | "rose" }) {
  return <span className={cn("inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-bold uppercase tracking-[0.12em]", {
    "bg-slate-100 text-slate-600": tone === "slate",
    "bg-emerald-50 text-emerald-700": tone === "green",
    "bg-amber-50 text-amber-700": tone === "amber",
    "bg-blue-50 text-blue-700": tone === "blue",
    "bg-rose-50 text-rose-700": tone === "rose",
  })}>{children}</span>;
}
export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(({ className, ...props }, ref) => <input ref={ref} className={cn("w-full rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-4 focus:ring-slate-900/5 placeholder:text-slate-400", className)} {...props} />);
Input.displayName = "Input";
export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(({ className, ...props }, ref) => <select ref={ref} className={cn("w-full rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-sm text-slate-900 outline-none focus:border-slate-500 focus:ring-4 focus:ring-slate-900/5", className)} {...props} />);
Select.displayName = "Select";
export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(({ className, ...props }, ref) => <textarea ref={ref} className={cn("min-h-28 w-full resize-y rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-sm text-slate-900 outline-none focus:border-slate-500 focus:ring-4 focus:ring-slate-900/5 placeholder:text-slate-400", className)} {...props} />);
Textarea.displayName = "Textarea";
export function Field({ label, children }: { label: string; children: ReactNode }) { return <label className="grid gap-2 text-sm font-medium text-slate-700"><span>{label}</span>{children}</label>; }
export function PageHeader({ eyebrow, title, description, action }: { eyebrow?: string; title: string; description?: string; action?: ReactNode }) { return <div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div>{eyebrow && <p className="mb-2 text-xs font-bold uppercase tracking-[0.18em] text-slate-400">{eyebrow}</p>}<h1 className="text-3xl font-semibold tracking-[-0.04em] text-slate-950 md:text-4xl">{title}</h1>{description && <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">{description}</p>}</div>{action}</div>; }
export function EmptyState({ title, body, action }: { title: string; body: string; action?: ReactNode }) { return <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/70 p-10 text-center"><p className="font-semibold text-slate-900">{title}</p><p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">{body}</p>{action && <div className="mt-5">{action}</div>}</div>; }