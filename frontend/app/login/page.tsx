import { Sparkles } from "lucide-react";

import { LoginForm } from "@/components/auth/login-form";

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="w-full max-w-6xl overflow-hidden rounded-[36px] border border-white/10 bg-slate-950/40 shadow-[0_30px_80px_rgba(2,6,23,0.8)] backdrop-blur-xl">
        <div className="grid lg:grid-cols-[1.1fr_0.9fr]">
          <div className="relative hidden bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.2),transparent_20%),radial-gradient(circle_at_bottom_right,rgba(168,85,247,0.18),transparent_35%)] p-8 lg:flex lg:flex-col lg:justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-400 to-violet-500 shadow-lg shadow-emerald-500/20">
                <Sparkles className="h-5 w-5 text-slate-950" />
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-slate-400">AI business</p>
                <h1 className="text-2xl font-semibold text-white">Inferra AI</h1>
              </div>
            </div>

            <div className="max-w-md space-y-5 py-12">
              <p className="text-sm uppercase tracking-[0.2em] text-emerald-200">Business intelligence engine</p>
              <h2 className="text-4xl font-semibold leading-tight text-white">
                Turn documents into decisions your team can trust.
              </h2>
              <p className="text-base text-slate-300">
                Upload financial documents, track anomalies, uncover revenue opportunities, and ask business questions grounded in your verified data.
              </p>
            </div>

            <div className="flex items-center gap-3 text-sm text-slate-300">
              <span className="inline-flex items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-500/10 px-3 py-1.5 text-emerald-200">
                <span className="h-2 w-2 rounded-full bg-emerald-300" />
                Live monitoring
              </span>
            </div>
          </div>

          <div className="flex items-center justify-center p-5 sm:p-8">
            <LoginForm />
          </div>
        </div>
      </div>
    </div>
  );
}
