'use client';

import React, { useEffect, useState } from 'react';

export default function MatrixDetails({ projectId }: { projectId: number }) {
  const [items, setItems] = useState<any[]>([]);

  useEffect(() => {
    fetch(`http://localhost:8000/matrix/${projectId}`)
      .then(res => res.json())
      .then(data => setItems(data));
  }, [projectId]);

  return (
    <div className="mt-4 p-4 bg-slate-900 rounded border border-blue-900/50">
      <h3 className="text-blue-400 text-sm font-bold mb-3 uppercase tracking-tighter">Matrix Breakdown (Project {projectId})</h3>
      <div className="grid grid-cols-5 text-[10px] text-slate-500 uppercase pb-2 border-b border-slate-800">
        <span className="col-span-1">Code</span>
        <span className="col-span-2">Description</span>
        <span className="col-span-1 text-center">Qty</span>
        <span className="col-span-1 text-right">Unit</span>
      </div>
      {items.map((item, i) => (
        <div key={i} className="grid grid-cols-5 text-xs py-2 border-b border-slate-800/50 items-center">
          <span className="font-mono text-blue-300">{item.code}</span>
          <span className="col-span-2 text-slate-300 truncate pr-2">{item.description}</span>
          <span className="text-center font-bold text-white">{item.qty}</span>
          <span className="text-right text-slate-500">{item.unit}</span>
        </div>
      ))}
    </div>
  );
}