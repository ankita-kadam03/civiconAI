import { ImagePlus, Leaf, X } from "lucide-react";
import { forwardRef, useState, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type TextareaHTMLAttributes } from "react";
import { cx } from "../lib/format";

export function Button({
  children,
  variant = "primary",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "soft" | "danger" }) {
  return (
    <button
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-full px-5 py-2.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50",
        variant === "primary" && "bg-navy text-white shadow-soft hover:bg-ink",
        variant === "ghost" && "bg-transparent text-navy hover:bg-white/70 dark:text-white",
        variant === "soft" && "bg-mint text-navy hover:bg-teal/20",
        variant === "danger" && "bg-coral text-navy hover:bg-rose-300",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}

export function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <label className="block space-y-1.5">
      <span className="text-sm font-semibold text-navy dark:text-slate-100">{label}</span>
      {children}
      {error ? <span className="text-xs text-rose-600">{error}</span> : null}
    </label>
  );
}

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(function Input(props, ref) {
  return (
    <input
      {...props}
      ref={ref}
      className={cx(
        "w-full rounded-2xl border border-navy/10 bg-white px-4 py-2.5 text-sm text-navy outline-none ring-teal/30 placeholder:text-navy/40 focus:ring-2 dark:border-white/10 dark:bg-slate-900 dark:text-white",
        props.className,
      )}
    />
  );
});

export const PasswordInput = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(function PasswordInput(
  props,
  ref,
) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="relative">
      <input
        {...props}
        ref={ref}
        type={visible ? "text" : "password"}
        className={cx(
          "w-full rounded-2xl border border-navy/10 bg-white py-2.5 pl-4 pr-11 text-sm text-navy outline-none ring-teal/30 placeholder:text-navy/40 focus:ring-2 dark:border-white/10 dark:bg-slate-900 dark:text-white",
          props.className,
        )}
      />
      <button
        type="button"
        tabIndex={-1}
        className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg p-1 text-lg leading-none opacity-70 transition hover:opacity-100"
        aria-label={visible ? "Hide password" : "Show password"}
        onClick={() => setVisible((v) => !v)}
      >
        👁
      </button>
    </div>
  );
});

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(function Textarea(props, ref) {
  return (
    <textarea
      {...props}
      ref={ref}
      className={cx(
        "min-h-[120px] w-full rounded-2xl border border-navy/10 bg-white px-4 py-2.5 text-sm text-navy outline-none ring-teal/30 placeholder:text-navy/40 focus:ring-2 dark:border-white/10 dark:bg-slate-900 dark:text-white",
        props.className,
      )}
    />
  );
});

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cx("card p-5 md:p-6", className)}>{children}</div>;
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cx("animate-pulse rounded-2xl bg-navy/10 dark:bg-white/10", className)} />;
}

export function FileUpload({
  files,
  onChange,
  max = 4,
  accept = "image/jpeg,image/png,image/webp,image/heic,image/heif",
}: {
  files: File[];
  onChange: (files: File[]) => void;
  max?: number;
  accept?: string;
}) {
  const inputId = "civicon-file-upload";
  function add(next: FileList | null) {
    if (!next?.length) return;
    const merged = [...files, ...Array.from(next)].slice(0, max);
    onChange(merged);
  }
  return (
    <div className="space-y-3">
      <input
        id={inputId}
        type="file"
        accept={accept}
        multiple
        className="sr-only"
        onChange={(e) => {
          add(e.target.files);
          e.target.value = "";
        }}
      />
      <div className="rounded-3xl border-2 border-dashed border-teal/45 bg-gradient-to-b from-mint/40 to-white p-6 text-center shadow-soft">
        <label htmlFor={inputId} className="flex cursor-pointer flex-col items-center gap-3">
          <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white text-teal shadow-soft ring-2 ring-teal/20">
            <ImagePlus size={26} />
          </span>
          <span className="text-lg font-bold text-navy">Add photos of the issue</span>
          <span className="max-w-sm text-sm text-navy/65">Drag files here or use the button below. JPEG, PNG or WebP · up to {max} · 8 MB each.</span>
          <span className="inline-flex rounded-full bg-navy px-5 py-2.5 text-sm font-semibold text-white shadow-soft">Choose files</span>
        </label>
      </div>
      {files.length ? (
        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {files.map((file, index) => (
            <li key={`${file.name}-${index}`} className="relative overflow-hidden rounded-2xl">
              <img src={URL.createObjectURL(file)} alt="" className="h-32 w-full object-cover" />
              <button
                type="button"
                className="absolute right-2 top-2 rounded-full bg-navy/80 p-1 text-white"
                aria-label="Remove photo"
                onClick={() => onChange(files.filter((_, i) => i !== index))}
              >
                <X size={14} />
              </button>
              <p className="truncate px-2 py-1 text-[10px] text-navy/60">{file.name}</p>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "danger",
  busy = false,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "danger" | "primary";
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="confirm-dialog-title">
      <button type="button" className="absolute inset-0 bg-navy/40 backdrop-blur-sm dark:bg-black/60" aria-label="Close dialog" onClick={onCancel} />
      <div className="card relative z-10 w-full max-w-md space-y-4 p-6 shadow-card">
        <h2 id="confirm-dialog-title" className="text-xl font-extrabold text-navy dark:text-white">
          {title}
        </h2>
        <p className="text-sm leading-relaxed text-navy/70 dark:text-slate-300">{description}</p>
        <div className="flex flex-wrap justify-end gap-2 pt-1">
          <Button type="button" variant="ghost" disabled={busy} onClick={onCancel}>
            {cancelLabel}
          </Button>
          <Button type="button" variant={variant === "danger" ? "danger" : "primary"} disabled={busy} onClick={onConfirm}>
            {busy ? "Please wait…" : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}

export function EmptyState({ title, body, action }: { title: string; body: string; action?: ReactNode }) {
  return (
    <div className="card flex flex-col items-center gap-3 px-6 py-12 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-lavender text-teal">
        <Leaf size={28} />
      </div>
      <h3 className="text-lg font-bold text-navy dark:text-white">{title}</h3>
      <p className="max-w-md text-sm text-navy/70 dark:text-slate-300">{body}</p>
      {action}
    </div>
  );
}
