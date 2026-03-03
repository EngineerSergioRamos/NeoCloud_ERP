'use client';

import React, { useEffect, useState } from 'react';
import { Terminal, Cpu, Zap } from 'lucide-react';

export default function AgentConsole() {
  const [logs, setLogs] = useState<string[]>([]);

  useEffect(() => {
    const socket = new WebSocket('ws://localhost:8000/ws');
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      // We listen for a new message type 'AGENT_THOUGHT'
      if (data.type === 'AGENT_THOUGHT') {
        setLogs(prev => [...prev.slice(-15), data.payload]); // Keep last 15 lines
      }
    };
    return () => socket.close();
  }, []);

  return (
    <div className="bg-slate-950 rounded-2xl border border-blue-900/30 p-4 font-mono text-[10px] shadow-2xl">
      <div className="flex items-center gap-2 mb-3 border-b border-slate-900 pb-2">
        <Terminal size={14} className="text-blue-500" />
        <span className="text-slate-500 uppercase tracking-widest font-black">Autonomous Agent Feed</span>
        <div className="flex-1" />
        <div className="flex gap-1">
          <div className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
          <div className="w-1.5 h-1.5 rounded-full bg-yellow-500" />
          <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
        </div>
      </div>
      <div className="space-y-1 h-32 overflow-y-auto custom-scrollbar">
        {logs.map((log, i) => (
          <div key={i} className="text-blue-300/80">
            <span className="text-blue-600 mr-2">▶</span> {log}
          </div>
        ))}
        {logs.length === 0 && <div className="text-slate-800 italic">Standby. Awaiting agent initiation...</div>}
      </div>
    </div>
  );
}