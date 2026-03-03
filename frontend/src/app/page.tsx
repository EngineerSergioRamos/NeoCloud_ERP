'use client';

import React, { useEffect, useState } from 'react';
import { 
  Activity, Terminal, Code2, GitMerge, 
  ShieldCheck, CheckCircle, HardDrive, FileCode2, AlertTriangle
} from 'lucide-react';

function AgentConsole({ missionProgress }: { missionProgress: number }) {
  const [logs, setLogs] = useState<string[]>([]);

  useEffect(() => {
    const socket = new WebSocket('ws://localhost:8000/ws');
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'AGENT_THOUGHT') {
        setLogs(prev => [...prev.slice(-14), data.payload]);
      }
    };
    return () => socket.close();
  }, []);

  return (
    <div className="bg-slate-950 rounded-2xl border border-blue-900/30 p-5 font-mono text-[10px] shadow-2xl h-full flex flex-col min-h-[400px]">
      <div className="flex justify-between items-center mb-4 border-b border-slate-900 pb-3">
        <div className="flex items-center gap-2">
          <Terminal size={14} className="text-blue-500" />
          <span className="text-slate-500 uppercase tracking-widest font-black">Cluster Telemetry</span>
        </div>
        <span className="text-blue-500 font-bold">{missionProgress}%</span>
      </div>
      <div className="w-full h-1 bg-slate-900 rounded-full mb-4 overflow-hidden">
        <div className="h-full bg-blue-500 transition-all duration-700 shadow-[0_0_12px_rgba(59,130,246,0.5)]" style={{ width: `${missionProgress}%` }} />
      </div>
      <div className="space-y-2 overflow-y-auto scrollbar-hide flex-grow">
        {logs.length === 0 && <div className="text-slate-800 italic animate-pulse">Waiting for AI Cluster telemetry...</div>}
        {logs.map((log, i) => (
          <div key={i} className="text-blue-400/90 leading-relaxed border-l border-blue-900/40 pl-3 py-1">
            <span className="text-blue-900 font-bold mr-2">{new Date().toLocaleTimeString([], {hour12: false})}</span> 
            {log}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function NeoCloudERP() {
  const [status, setStatus] = useState('Idle');
  const [missionProgress, setMissionProgress] = useState(0);
  const [proposal, setProposal] = useState<string | null>(null);
  const [feedback, setFeedback] = useState('');
  const [isApproved, setIsApproved] = useState(false);

  const activeFiles = [
    { name: 'fasar_calc.py', status: 'Pending', type: 'Backend (Python)' },
    { name: 'Dashboard.tsx', status: 'Pending', type: 'Frontend (React)' }
  ];

  useEffect(() => {
    const socket = new WebSocket('ws://localhost:8000/ws');
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'AGENT_PROPOSAL') {
        setProposal(data.payload);
        setMissionProgress(90);
        setStatus('Awaiting PR Review');
      }
      if (data.type === 'AGENT_THOUGHT') {
        const p = data.payload.toUpperCase();
        if (p.includes("BACKEND")) setMissionProgress(25);
        if (p.includes("FRONTEND")) setMissionProgress(50);
        if (p.includes("TEST")) setMissionProgress(75);
      }
    };
    return () => socket.close();
  }, []);

  const startDevCycle = async () => {
    setMissionProgress(5);
    setProposal(null);
    setIsApproved(false);
    setStatus('Engineering Cluster Active');
    await fetch('http://localhost:8000/start-dev-crew', { method: 'POST' });
  };

  // This will now work even if the page was refreshed and proposal is null
  const handleApprove = async () => {
    const res = await fetch('http://localhost:8000/submit-approval', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: feedback || "LGTM. Proceed with deployment." })
    });
    if (res.ok) {
      setIsApproved(true);
      setStatus('Code Merged to Prod');
      setMissionProgress(100);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 p-8 font-sans selection:bg-blue-500/30">
      <div className="max-w-6xl mx-auto space-y-6">
        <header className="flex justify-between items-end mb-8 border-b border-slate-900 pb-6">
          <div className="space-y-1">
            <h1 className="text-3xl font-black italic tracking-tighter flex items-center gap-3 uppercase">
              NEOCLOUD <span className="text-blue-500 tracking-normal font-light">DEV</span>
            </h1>
            <p className="text-[8px] font-bold text-slate-700 uppercase tracking-[0.4em]">Autonomous Software Engineering Cluster</p>
          </div>
          <div className="text-[10px] font-bold text-slate-500 flex items-center gap-3 bg-slate-900/50 px-5 py-2.5 rounded-full border border-slate-800 shadow-inner">
            <Activity size={12} className={status.includes('Active') ? "text-green-500 animate-pulse" : "text-blue-500"} /> 
            {status}
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          <div className="lg:col-span-3">
            <AgentConsole missionProgress={missionProgress} />
          </div>

          <div className="lg:col-span-2 flex flex-col gap-6">
            <div className="bg-slate-900/40 p-6 rounded-2xl border border-slate-800 shadow-lg">
              <button onClick={startDevCycle} className="w-full bg-blue-600 hover:bg-blue-500 text-white font-black py-4 rounded-xl transition-all uppercase text-[10px] tracking-widest shadow-xl shadow-blue-900/20 active:translate-y-0.5 mb-3">
                Initialize Dev Sprint
              </button>
              
              <div className="flex items-center justify-between mt-4">
                <span className="text-[8px] text-slate-600 uppercase font-black">Hardware Target</span>
                <div className="flex items-center gap-2 text-[8px] text-green-500 font-bold uppercase tracking-widest">
                  <HardDrive size={10} /> 7800X3D + 9070 XT
                </div>
              </div>
            </div>

            {/* Permanent Authorization Box - No longer hidden by state refresh */}
            <div className="bg-blue-900/10 border border-blue-500/30 rounded-2xl p-5 shadow-lg flex-grow flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2 text-blue-400">
                  <GitMerge size={16} />
                  <span className="text-[10px] font-black uppercase tracking-widest">Director Authorization</span>
                </div>
              </div>

              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-[10px] font-mono text-blue-100 h-24 overflow-y-auto mb-4 leading-relaxed opacity-80">
                {proposal ? proposal : <span className="text-slate-600 italic">No Active PR text loaded. (If agent is paused in terminal, you can still force approval below).</span>}
              </div>

              <textarea 
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                placeholder="Type feedback or leave blank for default approval..."
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-[10px] font-mono text-blue-300 mb-4 h-16 outline-none focus:border-blue-500"
              />
              
              <div className="flex gap-2 mt-auto">
                <button onClick={handleApprove} disabled={isApproved} className={`w-full flex items-center justify-center gap-2 py-3 rounded-xl font-black text-[9px] uppercase tracking-widest transition-all ${isApproved ? "bg-green-600/20 text-green-500 border border-green-500/30" : "bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-900/20"}`}>
                  {isApproved ? <CheckCircle size={14}/> : <ShieldCheck size={14}/>}
                  {isApproved ? "Merged" : "Approve & Merge"}
                </button>
                
                {/* Emergency Unblock Button in case of desync */}
                <button onClick={handleApprove} disabled={isApproved} title="Force unblock terminal" className="bg-slate-800 hover:bg-orange-900/50 text-slate-400 hover:text-orange-500 p-3 rounded-xl transition-all border border-slate-700 hover:border-orange-500/50">
                  <AlertTriangle size={14} />
                </button>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-slate-900/50 rounded-2xl border border-slate-800 overflow-hidden shadow-2xl mt-6">
          <div className="bg-slate-800/20 p-5 border-b border-slate-800 flex items-center gap-2">
            <FileCode2 size={14} className="text-slate-500" />
            <span className="text-[10px] uppercase font-black text-slate-500 tracking-widest">Workspace Tracking</span>
          </div>
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-800/30 text-[8px] uppercase font-black text-slate-500 tracking-[0.2em] border-b border-slate-800">
              <tr><th className="p-6">Target File</th><th className="p-6">Domain</th><th className="p-6 text-right">AI Status</th></tr>
            </thead>
            <tbody>
              {activeFiles.map((f, i) => (
                <tr key={i} className="border-b border-slate-900/50">
                  <td className="p-6 font-bold font-mono text-blue-400">{f.name}</td>
                  <td className="p-6 text-slate-400 text-xs">{f.type}</td>
                  <td className="p-6 text-right font-bold text-[10px] uppercase tracking-widest">
                    {isApproved ? <span className="text-green-500">Live in Prod</span> : <span className="text-yellow-500">In Dev/SIT</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}