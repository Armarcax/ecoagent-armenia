"use client";

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";

const SECTORS = [
  { id: "all",          label: "Բոլոր ոլորտներ",    icon: "🌿" },
  { id: "construction", label: "Շինարարություն",       icon: "🏗️" },
  { id: "mining",       label: "Հանքարդյունաբերություն", icon: "⛏️" },
  { id: "waste",        label: "Թափոններ",              icon: "♻️" },
  { id: "water",        label: "Ջուր",                 icon: "💧" },
  { id: "air",          label: "Օդ",                   icon: "💨" },
  { id: "forestry",     label: "Անտառ",                icon: "🌲" },
  { id: "agriculture",  label: "Գյուղատնտեսություն",   icon: "🌾" },
  { id: "energy",       label: "Էներգետիկա",           icon: "☀️" },
  { id: "esg",          label: "ESG",                  icon: "📊" },
];

const EXAMPLES = [
  "Ի՞նչ ՇՄԱԳ է պետք Երևանում 5-հարկ շինարարել",
  "Շինարարական թափոնն ինչպես հեռացնել?",
  "Գետի աղտոտման մեծացման չափն ավելացնել կարելի է?",
  "Ինչ է ESG հիմնադրույթը շինարարական ընկերությունում?",
];

const STORAGE_KEY = "ecoagent_chat_history";

interface Source {
  title: string;
  doc_number: string;
  url: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  timestamp: string;
}

export default function EcoAgentDashboard() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput]       = useState("");
  const [sector, setSector]     = useState("all");
  const [loading, setLoading]   = useState(false);
  const [streaming, setStreaming] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  // Load history on mount
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        setMessages(JSON.parse(saved));
      } catch (e) {
        console.error("Failed to load chat history", e);
      }
    }
  }, []);

  // Save history on change
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
    }
  }, [messages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming]);

  const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  async function sendMessage(text: string) {
    if (!text.trim() || loading) return;
    const userMsg: Message = { role: "user", content: text, timestamp: new Date().toISOString() };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);
    setStreaming("");

    let sources: Source[] = [];
    let fullText = "";

    try {
      const resp = await fetch(`${API}/query/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: text, sector: sector === "all" ? null : sector }),
      });
      const reader = resp.body!.getReader();
      const decoder = new TextDecoder();
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const lines = decoder.decode(value).split("\n").filter(l => l.startsWith("data: "));
        for (const line of lines) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.type === "sources") sources = data.sources;
            else if (data.type === "text") {
              fullText += data.content;
              setStreaming(fullText);
            }
            else if (data.type === "done") {
              setMessages(m => [...m, { role: "assistant", content: fullText, sources, timestamp: new Date().toISOString() }]);
              setStreaming("");
            }
          } catch {}
        }
      }
    } catch {
      try {
        const r = await fetch(`${API}/query`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: text, sector: sector === "all" ? null : sector }),
        });
        const data = await r.json();
        setMessages(m => [...m, { role: "assistant", content: data.answer, sources: data.sources || [], timestamp: data.timestamp }]);
        setStreaming("");
      } catch {
        setMessages(m => [...m, { role: "assistant", content: "⚠️ Բեքենդի հետ կապակցություն չկա. Ստուգիր http://localhost:8000", timestamp: new Date().toISOString() }]);
      }
    }
    setLoading(false);
  }

  function clearHistory() {
    setMessages([]);
    localStorage.removeItem(STORAGE_KEY);
  }

  return (
    <div style={{ minHeight:"100vh", background:"#0a0f0a", color:"#e8f0e8", fontFamily:"'IBM Plex Mono',monospace", display:"flex", flexDirection:"column" }}>

      {/* Header */}
      <header style={{ borderBottom:"1px solid #1a3a1a", padding:"20px 32px", display:"flex", alignItems:"center", justifyContent:"space-between", background:"#080d08" }}>
        <div style={{ display:"flex", alignItems:"center", gap:14 }}>
          <span style={{ fontSize:28 }}>🌿</span>
          <div>
            <div style={{ fontSize:20, fontWeight:700, color:"#4caf50", letterSpacing:"0.05em" }}>
              EcoAgent <span style={{ color:"#81c784" }}>Armenia</span>
            </div>
            <div style={{ fontSize:11, color:"#4a7a4a", letterSpacing:"0.1em" }}>
              ՀՀ ԲՆԱՊԱՀՊԱՆԱԿԱՆ ՕՐԵՆՍԴՐՈՒԹՅՈՒՆ AI
            </div>
          </div>
        </div>
        <div style={{ display:"flex", alignItems:"center", gap:12 }}>
          <button onClick={clearHistory} style={{ background:"transparent", border:"1px solid #1a4a1a", color:"#4a7a4a", fontSize:10, padding:"4px 10px", borderRadius:4, cursor:"pointer" }}>
            Մաքրել պատմությունը
          </button>
          <div style={{ display:"flex", gap:8, fontSize:12, color:"#4a7a4a" }}>
            {["arlis.am ✓","EU Directives ✓","ISO ✓"].map(t => (
              <span key={t} style={{ background:"#0d2a0d", border:"1px solid #1a4a1a", borderRadius:4, padding:"4px 10px" }}>{t}</span>
            ))}
          </div>
        </div>
      </header>

      <div style={{ display:"flex", flex:1, overflow:"hidden" }}>

        {/* Sidebar */}
        <aside style={{ width:200, borderRight:"1px solid #1a3a1a", padding:"20px 0", background:"#080d08", overflowY:"auto" }}>
          <div style={{ padding:"0 16px", marginBottom:12, fontSize:10, color:"#3a6a3a", letterSpacing:"0.15em" }}>ՈԼՈՐՏՆԵՐ</div>
          {SECTORS.map(s => (
            <button key={s.id} onClick={() => setSector(s.id)} style={{
              width:"100%", textAlign:"left", padding:"10px 16px",
              background: sector===s.id ? "#0d2a0d" : "transparent",
              border:"none", borderLeft:`3px solid ${sector===s.id ? "#4caf50" : "transparent"}`,
              color: sector===s.id ? "#81c784" : "#5a8a5a",
              cursor:"pointer", fontSize:12, display:"flex", alignItems:"center", gap:8,
            }}>
              <span>{s.icon}</span><span>{s.label}</span>
            </button>
          ))}
        </aside>

        {/* Main */}
        <main style={{ flex:1, display:"flex", flexDirection:"column", overflow:"hidden" }}>
          <div style={{ flex:1, overflowY:"auto", padding:"24px 32px" }}>

            {messages.length === 0 && !streaming && (
              <div style={{ textAlign:"center", paddingTop:60 }}>
                <div style={{ fontSize:48, marginBottom:16 }}>🌿</div>
                <div style={{ fontSize:18, color:"#4caf50", marginBottom:8 }}>EcoAgent Armenia</div>
                <div style={{ fontSize:13, color:"#4a7a4a", marginBottom:40 }}>
                  Ձեզ հայտնի է ՀՀ բնապահպանական օրենսդրությունը
                </div>
                <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12, maxWidth:600, margin:"0 auto" }}>
                  {EXAMPLES.map((ex,i) => (
                    <button key={i} onClick={() => sendMessage(ex)} style={{
                      background:"#0d1a0d", border:"1px solid #1a3a1a", borderRadius:8,
                      padding:"14px 16px", color:"#5a8a5a", cursor:"pointer",
                      fontSize:12, textAlign:"left", lineHeight:1.5,
                    }}>{ex}</button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg,i) => (
              <div key={i} style={{ marginBottom:24, display:"flex", gap:14, flexDirection: msg.role==="user" ? "row-reverse" : "row" }}>
                <div style={{ width:32, height:32, borderRadius:"50%", background: msg.role==="user" ? "#1a3a1a" : "#0d2a0d", border:`1px solid ${msg.role==="user" ? "#2a5a2a" : "#1a4a1a"}`, display:"flex", alignItems:"center", justifyContent:"center", fontSize:14, flexShrink:0 }}>
                  {msg.role==="user" ? "👤" : "🌿"}
                </div>
                <div style={{ maxWidth:"75%" }}>
                  <div style={{ background: msg.role==="user" ? "#0d1a0d" : "#080d08", border:`1px solid ${msg.role==="user" ? "#1a3a1a" : "#142814"}`, borderRadius:10, padding:"14px 18px", fontSize:13, lineHeight:1.7, color: msg.role==="user" ? "#81c784" : "#c8e6c9" }}>
                    <div className="prose-green">
                      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
                        {msg.content}
                      </ReactMarkdown>
                    </div>
                  </div>
                  {msg.sources && msg.sources.length > 0 && (
                    <div style={{ marginTop:8, display:"flex", flexWrap:"wrap", gap:6 }}>
                      {msg.sources.map((s,si) => (
                        <a key={si} href={s.url} target="_blank" rel="noreferrer" style={{ fontSize:10, color:"#4a7a4a", background:"#0d1a0d", border:"1px solid #1a3a1a", borderRadius:4, padding:"3px 8px", textDecoration:"none" }}>
                          📋 {s.doc_number || (s.title ? s.title.substring(0,30) : "Աղբյուր")}
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {streaming && (
              <div style={{ marginBottom:24, display:"flex", gap:14 }}>
                <div style={{ width:32, height:32, borderRadius:"50%", background:"#0d2a0d", border:"1px solid #1a4a1a", display:"flex", alignItems:"center", justifyContent:"center", fontSize:14 }}>🌿</div>
                <div style={{ background:"#080d08", border:"1px solid #142814", borderRadius:10, padding:"14px 18px", fontSize:13, lineHeight:1.7, color:"#c8e6c9", maxWidth:"75%" }}>
                  <div className="prose-green">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
                      {streaming}
                    </ReactMarkdown>
                  </div>
                  <span style={{ display:"inline-block", width:8, height:14, background:"#4caf50", marginLeft:2, animation:"blink 1s step-end infinite" }}/>
                </div>
              </div>
            )}

            {loading && !streaming && (
              <div style={{ display:"flex", gap:14, marginBottom:24 }}>
                <div style={{ width:32, height:32, borderRadius:"50%", background:"#0d2a0d", border:"1px solid #1a4a1a", display:"flex", alignItems:"center", justifyContent:"center", fontSize:14 }}>🌿</div>
                <div style={{ background:"#080d08", border:"1px solid #142814", borderRadius:10, padding:"14px 18px", display:"flex", gap:6, alignItems:"center" }}>
                  {[0,1,2].map(i => <div key={i} style={{ width:6, height:6, borderRadius:"50%", background:"#4caf50", animation:`bounce 1.2s ease-in-out ${i*0.2}s infinite` }}/>)}
                </div>
              </div>
            )}
            <div ref={bottomRef}/>
          </div>

          {/* Input */}
          <div style={{ borderTop:"1px solid #1a3a1a", padding:"20px 32px", background:"#080d08" }}>
            <div style={{ display:"flex", gap:12, background:"#0d1a0d", border:"1px solid #1a3a1a", borderRadius:10, padding:"4px 4px 4px 16px", alignItems:"flex-end" }}>
              <textarea
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => { if (e.key==="Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(input); } }}
                placeholder="Ձեր հարցը հայերեն... (ՇՄԱԳ, թափոններ, նորմեր)"
                rows={2}
                style={{ flex:1, background:"transparent", border:"none", outline:"none", color:"#c8e6c9", fontSize:13, fontFamily:"inherit", resize:"none", lineHeight:1.6, padding:"10px 0" }}
              />
              <button onClick={() => sendMessage(input)} disabled={loading || !input.trim()} style={{ background: loading||!input.trim() ? "#0d2a0d" : "#1a4a1a", border:"none", borderRadius:8, width:44, height:44, cursor: loading||!input.trim() ? "not-allowed" : "pointer", color: loading||!input.trim() ? "#2a5a2a" : "#81c784", fontSize:18, display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0, marginBottom:2 }}>↑</button>
            </div>
            <div style={{ fontSize:10, color:"#2a5a2a", marginTop:8, textAlign:"center" }}>
              Enter — ուղարկել · Shift+Enter — նոր տող
            </div>
          </div>
        </main>
      </div>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;700&display=swap');
        * { box-sizing:border-box; margin:0; padding:0; }
        ::-webkit-scrollbar { width:4px; }
        ::-webkit-scrollbar-track { background:#080d08; }
        ::-webkit-scrollbar-thumb { background:#1a4a1a; border-radius:2px; }
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
        @keyframes bounce { 0%,80%,100%{transform:scale(0)} 40%{transform:scale(1)} }
      `}</style>
    </div>
  );
}
