'use client';

import React, { useState } from 'react';

interface FasarCellProps {
  initialBase: number;
  onUpdate: (data: any) => void;
}

export default function FasarCell({ initialBase, onUpdate }: FasarCellProps) {
  const [base, setBase] = useState(initialBase);
  const [loading, setLoading] = useState(false);

  const handleChange = async (newVal: string) => {
    const numVal = parseFloat(newVal);
    setBase(numVal);
    if (isNaN(numVal)) return;

    setLoading(true);
    try {
      // Hit your new 2026 Brain API
      const res = await fetch(`http://localhost:8000/calculate-fasar/${numVal}`);
      const data = await res.json();
      onUpdate(data); // Send the new Factor/Total back to the table
    } catch (err) {
      console.error("API Error:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-1">
      <input
        type="number"
        value={base}
        onChange={(e) => handleChange(e.target.value)}
        className="bg-slate-700 border border-slate-600 rounded px-2 py-1 text-blue-200 w-24 focus:outline-none focus:ring-1 focus:ring-blue-500"
      />
      {loading && <span className="text-[10px] text-blue-400 animate-pulse">Calculating...</span>}
    </div>
  );
}