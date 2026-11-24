import { Bot, Mic, MicOff, Send, Sparkles, Volume2, VolumeX, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "../api";

// Browser speech: SpeechRecognition (Chrome / Edge) for listening, speechSynthesis for talking. Both free, no keys.
const Recognition = typeof window !== "undefined" ? window.SpeechRecognition || window.webkitSpeechRecognition : null;
const LANGS = [["en-IN", "English"], ["hi-IN", "हिन्दी"], ["ta-IN", "தமிழ்"]];
const SUGGESTIONS = ["Which doctor treats glaucoma?", "Free slots with Dr Rao tomorrow", "Show my appointments"];

export default function VoiceAssistant() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([{ from: "bot", text: "Hi, I'm Netra. Ask me to find a doctor, check free times, or book and cancel appointments. Tap the mic and speak." }]);
  const [input, setInput] = useState("");
  const [listening, setListening] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [speak, setSpeak] = useState(true);
  const [lang, setLang] = useState("en-IN");
  const [mode, setMode] = useState(null);
  const conversationId = useRef(null);
  const recRef = useRef(null);
  const endRef = useRef(null);

  useEffect(() => { api.assistantStatus().then((s) => setMode(s.ai ? "ai" : "basic")).catch(() => {}); }, []);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, thinking]);
  useEffect(() => () => { recRef.current?.abort(); window.speechSynthesis?.cancel(); }, []);

  const say = (text) => {
    if (!speak || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = lang;
    u.rate = 1;
    const voice = window.speechSynthesis.getVoices().find((v) => v.lang === lang) || window.speechSynthesis.getVoices().find((v) => v.lang.startsWith(lang.slice(0, 2)));
    if (voice) u.voice = voice;
    window.speechSynthesis.speak(u);
  };

  const send = async (text) => {
    const msg = text.trim().slice(0, 600);
    if (!msg || thinking) return;
    setInput("");
    setMessages((m) => [...m, { from: "me", text: msg }]);
    setThinking(true);
    try {
      const res = await api.chat({ message: msg, conversation_id: conversationId.current || undefined });
      conversationId.current = res.conversation_id;
      setMode(res.mode === "safety" ? mode : res.mode);
      setMessages((m) => [...m, { from: "bot", text: res.reply, urgent: res.mode === "safety" }]);
      say(res.reply);
      if (res.actions?.length) window.dispatchEvent(new Event("netracare:changed"));
    } catch (e) {
      setMessages((m) => [...m, { from: "bot", text: e.message, error: true }]);
    } finally {
      setThinking(false);
    }
  };

  const toggleMic = () => {
    if (!Recognition) {
      setMessages((m) => [...m, { from: "bot", text: "Voice input needs Chrome or Edge. You can still type your question.", error: true }]);
      return;
    }
    if (listening) {
      recRef.current?.stop();
      return;
    }
    window.speechSynthesis?.cancel();
    const rec = new Recognition();
    rec.lang = lang;
    rec.interimResults = true;
    rec.maxAlternatives = 1;
    let finalText = "";
    rec.onresult = (e) => {
      const transcript = [...e.results].map((r) => r[0].transcript).join("");
      setInput(transcript);
      if (e.results[e.results.length - 1].isFinal) finalText = transcript;
    };
    rec.onerror = (e) => {
      if (e.error === "not-allowed") setMessages((m) => [...m, { from: "bot", text: "Microphone access was blocked. Please allow it in your browser.", error: true }]);
    };
    rec.onend = () => {
      setListening(false);
      if (finalText) send(finalText);
    };
    recRef.current = rec;
    setListening(true);
    rec.start();
  };

  return (
    <>
      {!open && (
        <button onClick={() => setOpen(true)} aria-label="Open voice assistant"
          className="fixed bottom-6 right-6 z-50 grid h-16 w-16 place-items-center rounded-full bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-2xl shadow-brand-700/40 transition hover:scale-105">
          <span className="absolute inset-0 animate-pulse-ring rounded-full bg-brand-400" />
          <Mic className="relative h-7 w-7" />
        </button>
      )}
      {open && (
        <div className="fixed inset-x-3 bottom-3 z-50 flex h-[min(640px,85vh)] flex-col overflow-hidden rounded-3xl bg-white shadow-2xl ring-1 ring-slate-200 sm:inset-x-auto sm:right-6 sm:bottom-6 sm:w-[400px]">
          <header className="flex items-center gap-3 bg-gradient-to-r from-brand-600 to-brand-800 px-5 py-4 text-white">
            <span className="grid h-10 w-10 place-items-center rounded-full bg-white/15"><Bot className="h-5 w-5" /></span>
            <div className="flex-1">
              <p className="font-bold">Netra assistant</p>
              <p className="flex items-center gap-1 text-xs text-white/70">
                {mode === "ai" ? <><Sparkles className="h-3 w-3" /> AI mode</> : mode === "basic" ? "Basic mode" : "…"}
              </p>
            </div>
            <select value={lang} onChange={(e) => setLang(e.target.value)} className="rounded-lg bg-white/15 px-2 py-1 text-xs outline-none" aria-label="Language">
              {LANGS.map(([v, l]) => <option key={v} value={v} className="text-slate-900">{l}</option>)}
            </select>
            <button onClick={() => { setSpeak(!speak); window.speechSynthesis?.cancel(); }} aria-label={speak ? "Mute voice" : "Unmute voice"}>
              {speak ? <Volume2 className="h-5 w-5" /> : <VolumeX className="h-5 w-5" />}
            </button>
            <button onClick={() => { setOpen(false); recRef.current?.abort(); window.speechSynthesis?.cancel(); }} aria-label="Close"><X className="h-5 w-5" /></button>
          </header>

          <div className="flex-1 space-y-3 overflow-y-auto bg-slate-50 px-4 py-4" aria-live="polite">
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.from === "me" ? "justify-end" : ""}`}>
                <p className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm ${
                  m.from === "me" ? "rounded-br-sm bg-brand-600 text-white"
                    : m.urgent ? "rounded-bl-sm bg-rose-600 font-semibold text-white"
                    : m.error ? "rounded-bl-sm bg-rose-50 text-rose-800 ring-1 ring-rose-200"
                    : "rounded-bl-sm bg-white text-slate-800 shadow-sm ring-1 ring-slate-200"}`}>{m.text}</p>
              </div>
            ))}
            {thinking && (
              <div className="flex gap-1 px-2">{[0, 1, 2].map((i) => <span key={i} className="h-2 w-2 animate-bounce rounded-full bg-brand-400" style={{ animationDelay: `${i * 0.15}s` }} />)}</div>
            )}
            {messages.length === 1 && (
              <div className="flex flex-wrap gap-2 pt-2">
                {SUGGESTIONS.map((s) => <button key={s} onClick={() => send(s)} className="rounded-full bg-white px-3 py-1.5 text-xs font-medium text-brand-700 ring-1 ring-brand-200 hover:bg-brand-50">{s}</button>)}
              </div>
            )}
            <div ref={endRef} />
          </div>

          <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="flex items-center gap-2 border-t border-slate-100 p-3">
            <button type="button" onClick={toggleMic} aria-label={listening ? "Stop listening" : "Speak"}
              className={`relative grid h-11 w-11 shrink-0 place-items-center rounded-full transition ${listening ? "bg-rose-500 text-white" : "bg-brand-50 text-brand-700 hover:bg-brand-100"}`}>
              {listening && <span className="absolute inset-0 animate-pulse-ring rounded-full bg-rose-400" />}
              {listening ? <MicOff className="relative h-5 w-5" /> : <Mic className="h-5 w-5" />}
            </button>
            <input className="input" placeholder={listening ? "Listening…" : "Type or tap the mic…"} maxLength={600} value={input} onChange={(e) => setInput(e.target.value)} />
            <button className="btn-primary h-11 w-11 shrink-0 p-0" disabled={!input.trim() || thinking} aria-label="Send"><Send className="h-4 w-4" /></button>
          </form>
        </div>
      )}
    </>
  );
}
