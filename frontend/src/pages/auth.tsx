import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { Button, Card, Field, Input, PasswordInput } from "../components/ui";
import { roleHome } from "../features/auth/paths";
import { endpoints } from "../lib/api";
import { useAuth } from "../lib/auth";
import { loginSchema, signupSchema } from "../lib/schemas";
import { useToast } from "../lib/toast";

function AuthFrame({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="mx-auto grid max-w-5xl gap-8 md:grid-cols-2">
      <div className="hidden rounded-3xl bg-gradient-to-br from-lavender via-sky to-mint p-8 md:block">
        <p className="text-sm font-bold text-teal">Civicon AI</p>
        <h2 className="mt-6 text-4xl font-extrabold text-navy">A calmer way to look after your street.</h2>
        <p className="mt-4 text-navy/70">Sign in to report issues, follow progress, and keep your neighbourhood visible.</p>
      </div>
      <Card>
        <h1 className="text-2xl font-extrabold text-navy dark:text-white">{title}</h1>
        <div className="mt-6">{children}</div>
      </Card>
    </div>
  );
}

export function LoginPage() {
  const { login } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const form = useForm({ resolver: zodResolver(loginSchema), defaultValues: { email: "", password: "" } });

  return (
    <AuthFrame title="Welcome back">
      <form
        className="space-y-4"
        onSubmit={form.handleSubmit(async (values) => {
          try {
            const user = await login(values.email, values.password);
            const dest = (location.state as { from?: string } | null)?.from;
            navigate(dest || roleHome(user.role));
          } catch (err) {
            toast(err instanceof Error ? err.message : "Could not sign in", "err");
          }
        })}
      >
        <Field label="Email" error={form.formState.errors.email?.message}>
          <Input type="email" {...form.register("email")} />
        </Field>
        <Field label="Password" error={form.formState.errors.password?.message}>
          <PasswordInput autoComplete="current-password" {...form.register("password")} />
        </Field>
        <Button className="w-full" type="submit">
          Sign in
        </Button>
      </form>
      <p className="mt-4 text-sm">
        <Link className="font-semibold text-teal" to="/forgot-password">
          Forgot password
        </Link>
        {" · "}
        <Link className="font-semibold text-teal" to="/signup">
          Create an account
        </Link>
      </p>
    </AuthFrame>
  );
}

export function SignupPage() {
  const { signup } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [localities, setLocalities] = useState<Array<{ id: string; name: string }>>([]);
  const form = useForm({ resolver: zodResolver(signupSchema), defaultValues: { display_name: "", email: "", password: "", locality: "" } });
  useEffect(() => {
    endpoints.localities().then(setLocalities).catch(() => undefined);
  }, []);
  return (
    <AuthFrame title="Join your neighbourhood">
      <form
        className="space-y-4"
        onSubmit={form.handleSubmit(async (values) => {
          try {
            await signup(values);
            navigate(values.locality?.trim() ? "/app" : "/app/profile");
          } catch (err) {
            toast(err instanceof Error ? err.message : "Could not create account", "err");
          }
        })}
      >
        <Field label="Name" error={form.formState.errors.display_name?.message}>
          <Input {...form.register("display_name")} />
        </Field>
        <Field label="Email" error={form.formState.errors.email?.message}>
          <Input type="email" {...form.register("email")} />
        </Field>
        <Field label="Locality">
          <select
            className="w-full rounded-2xl border border-navy/10 bg-white px-4 py-2.5 text-sm text-navy dark:border-white/10 dark:bg-slate-900 dark:text-white"
            {...form.register("locality")}
          >
            <option value="">Select your area in Tambaram</option>
            {localities.map((loc) => (
              <option key={loc.id} value={loc.name}>
                {loc.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Password" error={form.formState.errors.password?.message}>
          <PasswordInput autoComplete="new-password" {...form.register("password")} />
        </Field>
        <Button className="w-full" type="submit">
          Create account
        </Button>
      </form>
    </AuthFrame>
  );
}

export function ForgotPage() {
  const toast = useToast();
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  return (
    <AuthFrame title="Reset your password">
      <form
        className="space-y-4"
        onSubmit={async (e) => {
          e.preventDefault();
          try {
            const res = await endpoints.forgot(email);
            toast(res.message, "info");
            if (res.reset_token) setToken(res.reset_token);
          } catch (err) {
            toast(err instanceof Error ? err.message : "Request failed", "err");
          }
        }}
      >
        <Field label="Email">
          <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Button className="w-full" type="submit">
          Send reset link
        </Button>
      </form>
      {token ? (
        <p className="mt-4 text-sm">
          Reset token issued. Continue to{" "}
          <Link className="font-semibold text-teal" to={`/reset-password?token=${encodeURIComponent(token)}`}>
            reset password
          </Link>
          .
        </p>
      ) : null}
    </AuthFrame>
  );
}

export function ResetPage() {
  const [params] = useSearchParams();
  const toast = useToast();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const token = params.get("token") || "";
  return (
    <AuthFrame title="Choose a new password">
      <form
        className="space-y-4"
        onSubmit={async (e) => {
          e.preventDefault();
          try {
            await endpoints.reset(token, password);
            toast("Password updated. Please sign in.");
            navigate("/login");
          } catch (err) {
            toast(err instanceof Error ? err.message : "Reset failed", "err");
          }
        }}
      >
        <Field label="New password">
          <PasswordInput autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} minLength={8} />
        </Field>
        <Button className="w-full" type="submit">
          Update password
        </Button>
      </form>
    </AuthFrame>
  );
}
