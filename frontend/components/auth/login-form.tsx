"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, LockKeyhole, Mail, ShieldCheck } from "lucide-react";

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!email.trim() || !password.trim()) {
      setMessage("Enter work email and password.");
      return;
    }
    window.localStorage.setItem("inferra-local-user", email.trim());
    router.push("/");
  }

  return (
    <div className="glass-card w-full max-w-md rounded-[30px] p-6 sm:p-7">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-emerald-200">Secure access</p>
          <h1 className="mt-2 text-3xl font-semibold text-white">Welcome back</h1>
        </div>
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-500/10 text-emerald-300 ring-1 ring-emerald-400/20">
          <ShieldCheck className="h-5 w-5" />
        </div>
      </div>

      <form className="space-y-4" onSubmit={onSubmit}>
        <label className="block">
          <span className="mb-2 block text-sm text-slate-300">Work email</span>
          <div className="glass-input flex items-center gap-3 rounded-2xl px-3 py-3">
            <Mail className="h-4 w-4 text-slate-400" />
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="name@company.com"
              className="w-full bg-transparent text-sm text-white placeholder:text-slate-500 focus:outline-none"
            />
          </div>
        </label>

        <label className="block">
          <span className="mb-2 block text-sm text-slate-300">Password</span>
          <div className="glass-input flex items-center gap-3 rounded-2xl px-3 py-3">
            <LockKeyhole className="h-4 w-4 text-slate-400" />
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Enter password"
              className="w-full bg-transparent text-sm text-white placeholder:text-slate-500 focus:outline-none"
            />
          </div>
        </label>

        {message ? <p className="text-sm text-amber-200">{message}</p> : null}

        <div className="flex items-center justify-between text-sm text-slate-300">
          <label className="inline-flex items-center gap-2">
            <input type="checkbox" className="h-4 w-4 rounded border-white/10 bg-slate-900/60" />
            Keep me signed in
          </label>
          <Link href="/" className="text-emerald-200 transition hover:text-emerald-100">
            Continue as guest
          </Link>
        </div>

        <button
          type="submit"
          className="flex w-full items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-emerald-500 via-teal-500 to-violet-500 px-4 py-3 text-sm font-medium text-slate-950 shadow-[0_16px_36px_rgba(16,185,129,0.35)] transition hover:translate-y-[-1px]"
        >
          Sign in
          <ArrowRight className="h-4 w-4" />
        </button>
      </form>

      <div className="mt-5 flex items-center gap-3 text-xs uppercase tracking-[0.2em] text-slate-400">
        <span className="h-px flex-1 bg-white/10" />
        Or
        <span className="h-px flex-1 bg-white/10" />
      </div>

      <button
        type="button"
        onClick={() => router.push("/")}
        className="mt-5 flex w-full items-center justify-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-medium text-slate-100 transition hover:bg-white/10"
      >
        Continue to workspace
      </button>

      <p className="mt-6 text-center text-sm text-slate-300">
        Firebase admin is optional in local development.{" "}
        <Link href="/" className="font-medium text-emerald-200 hover:text-emerald-100">
          Open dashboard
        </Link>
      </p>
    </div>
  );
}
