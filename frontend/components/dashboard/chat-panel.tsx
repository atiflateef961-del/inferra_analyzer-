"use client";

import { FormEvent, useRef, useState } from "react";
import { Mic, Paperclip, Send, Sparkles } from "lucide-react";

import { useDashboardData } from "@/components/dashboard/dashboard-data-provider";
import { sendAgentMessage } from "@/lib/api";

type ChatItem = { sender: "user" | "assistant"; text: string };

export function ChatPanel() {
  const fileRef = useRef<HTMLInputElement>(null);
  const { uploadFiles, health } = useDashboardData();
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatItem[]>([
    {
      sender: "assistant",
      text: "Import a spreadsheet or ask a question about the files in this workspace.",
    },
  ]);
  const [sending, setSending] = useState(false);

  async function onSubmit(event?: FormEvent) {
    event?.preventDefault();
    const question = input.trim();
    if (!question || sending) {
      return;
    }
    const history = messages.map((item) => ({
      role: item.sender === "user" ? "user" : "assistant",
      content: item.text,
    }));
    setInput("");
    setMessages((current) => [...current, { sender: "user", text: question }]);
    setSending(true);
    try {
      const result = await sendAgentMessage(question, history);
      setMessages((current) => [...current, { sender: "assistant", text: result.content }]);
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          sender: "assistant",
          text: error instanceof Error ? error.message : "The AI agent is unavailable.",
        },
      ]);
    } finally {
      setSending(false);
    }
  }

  function startVoice() {
    const speechWindow = window as typeof window & {
      webkitSpeechRecognition?: new () => {
        lang: string;
        start: () => void;
        onresult: ((event: { results: Array<Array<{ transcript: string }>> }) => void) | null;
      };
    };
    const SpeechRecognition = speechWindow.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setMessages((current) => [
        ...current,
        { sender: "assistant", text: "Voice input is not supported in this browser. Type the question instead." },
      ]);
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.onresult = (event) => {
      const transcript = event.results[0]?.[0]?.transcript ?? "";
      setInput(transcript);
    };
    recognition.start();
  }

  return (
    <div className="glass-card rounded-[28px] p-5 sm:p-6">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div>
          <p className="text-sm text-slate-300">Ask Inferra AI</p>
          <h3 className="text-xl font-semibold text-white">Business chat</h3>
        </div>
        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-emerald-500/10 text-emerald-300 ring-1 ring-emerald-400/20">
          <Sparkles className="h-4 w-4" />
        </div>
      </div>

      <p className="mb-3 text-xs text-slate-400">
        Agent {health?.ai?.configured ? `ready (${health.ai.model})` : "needs GROQ_API_KEY"}
      </p>

      <div className="space-y-3 rounded-[24px] border border-white/10 bg-slate-950/35 p-3">
        {messages.map((item, index) => (
          <div key={`${item.sender}-${index}`} className={`flex ${item.sender === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] rounded-2xl px-3 py-2.5 text-sm ${
                item.sender === "user"
                  ? "bg-emerald-500/15 text-emerald-50 ring-1 ring-emerald-400/20"
                  : "bg-white/[0.04] text-slate-200 ring-1 ring-white/10"
              }`}
            >
              {item.text}
            </div>
          </div>
        ))}
        {sending ? (
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-2xl bg-white/[0.04] px-3 py-2.5 text-sm text-slate-400 ring-1 ring-white/10">
              Analyzing imported files...
            </div>
          </div>
        ) : null}
      </div>

      <form onSubmit={onSubmit} className="mt-4 flex min-w-0 items-center gap-2 rounded-[22px] border border-white/10 bg-white/[0.03] p-2">
        <input
          ref={fileRef}
          type="file"
          className="hidden"
          multiple
          accept=".pdf,.xlsx,.csv,.docx,.txt,.png,.jpg,.jpeg"
          onChange={(event) => {
            if (event.target.files) {
              void uploadFiles(event.target.files);
            }
            event.target.value = "";
          }}
        />
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-slate-300 transition hover:bg-white/10"
          aria-label="Attach file"
        >
          <Paperclip className="h-4 w-4" />
        </button>
        <input
          aria-label="Chat question"
          placeholder="Ask about revenue, inventory, margins..."
          value={input}
          onChange={(event) => setInput(event.target.value)}
          className="min-w-0 flex-1 bg-transparent px-2 py-2 text-sm text-white placeholder:text-slate-500 focus:outline-none"
        />
        <button
          type="button"
          onClick={startVoice}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-slate-300 transition hover:bg-white/10"
          aria-label="Voice input"
        >
          <Mic className="h-4 w-4" />
        </button>
        <button
          type="submit"
          disabled={sending || !input.trim()}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-r from-emerald-500 to-violet-500 text-slate-950 shadow-lg shadow-emerald-500/20 disabled:opacity-50"
          aria-label="Send message"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}
