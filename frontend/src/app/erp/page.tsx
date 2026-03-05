"use client";
import React, { useState, useEffect } from 'react';
import { ChevronRight, Save, Database, Building2, CheckCircle2, Plus, FolderTree, FileDown, FileUp, GripVertical } from 'lucide-react';

export default function UnitPriceComposer() {
  const [workspaces, setWorkspaces] = useState(["DEMO123"]);
  const [licenseKey, setLicenseKey] = useState("DEMO123");
  const [newWorkspace, setNewWorkspace] = useState("");
  
  const [fasarRate, setFasarRate] = useState(1.1258);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState("");
  const [grandTotal, setGrandTotal] = useState(0);
  const [resources, setResources] = useState([]);

  const fetchCatalog = () => {
    fetch('http://localhost:8001/catalog', { headers: { 'X-License-Key': licenseKey } })
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) setResources(data.map(item => ({...item, description: item.description || ''})));
      });
  };

  useEffect(() => {
    fetch('http://localhost:8001/workspaces')
      .then(res => res.json())
      .then(data => {
        if(data.workspaces?.length > 0) {
            setWorkspaces(data.workspaces);
            if(!data.workspaces.includes(licenseKey)) setLicenseKey(data.workspaces[0]);
        }
      }).catch(() => {});
  }, []);

  useEffect(() => { fetchCatalog(); }, [licenseKey]); 

  // Multi-Mode Calculation (Supports Neodata standard imports AND explicit matrix recipes)
  useEffect(() => {
    let total = 0;
    resources.forEach(res => {
      let lineTotal = parseFloat(res.qty||0) * parseFloat(res.price||0);
      if (res.type === 'LAB') lineTotal *= fasarRate;
      
      const hasChildren = resources.some(r => r.parent_id === res.id);
      
      if (res.type === 'CONC') {
         if (!hasChildren) total += lineTotal; // imported concepts without explosion
      } else if (res.type === 'MAT' || res.type === 'LAB' || res.type === 'EQP') {
         const parentConcept = resources.find(p => p.id === res.parent_id);
         if (parentConcept) lineTotal *= parseFloat(parentConcept.qty || 1);
         if (!isNaN(lineTotal)) total += lineTotal;
      }
    });
    setGrandTotal(total);
  }, [resources, fasarRate]);

  const updateResource = (id, field, value) => {
    let cleanValue = value;
    if(field === 'qty' || field === 'price') cleanValue = value.replace(/[^0-9.]/g, '');
    setResources(resources.map(res => res.id === id ? { ...res, [field]: cleanValue } : res));
  };

  const addNode = (parentId, type, index) => {
    const newNode = {
        id: 'new_' + Date.now() + Math.floor(Math.random()*100),
        parent_id: parentId,
        code: 'NUEVO',
        description: type === 'CHAP' ? 'Nueva Partida' : type === 'CONC' ? 'Nuevo Concepto' : 'Nuevo Insumo',
        type: type,
        unit: type === 'CHAP' ? '' : 'PZA',
        qty: 1,
        price: 0
    };
    const newRes = [...resources];
    newRes.splice(index + 1, 0, newNode);
    setResources(newRes);
  };

  const handleCreateWorkspace = async () => {
    const cleanKey = newWorkspace.replace(/[^a-zA-Z0-9]/g, '').toUpperCase();
    if(!cleanKey) return;
    await fetch(`http://localhost:8001/workspaces/${cleanKey}`, { method: 'POST' });
    if(!workspaces.includes(cleanKey)) setWorkspaces([...workspaces, cleanKey]);
    setLicenseKey(cleanKey);
    setNewWorkspace("");
  };

  const saveMatrix = async () => {
    setSaving(true);
    setSaveStatus("Guardando...");
    try {
      const response = await fetch('http://localhost:8001/save_matrix', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-License-Key': licenseKey },
        body: JSON.stringify({ resources: resources })
      });
      if (response.ok) {
        setSaveStatus("¡Guardado!");
        fetchCatalog(); 
        setTimeout(() => setSaveStatus(""), 3000);
      }
    } finally { setSaving(false); }
  };

  const exportNeodata = () => { window.open(`http://localhost:8001/export_neodata?tenant=${licenseKey}`); };

  const importNeodata = (e) => {
    const file = e.target.files[0];
    if(!file) return;
    setSaveStatus("Importando...");
    const reader = new FileReader();
    reader.onload = async (event) => {
      await fetch('http://localhost:8001/import_neodata', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-License-Key': licenseKey },
        body: JSON.stringify({ csv_data: event.target.result })
      });
      fetchCatalog();
      setSaveStatus("¡Importado con Exito!");
      setTimeout(() => setSaveStatus(""), 3000);
    };
    reader.readAsText(file, 'UTF-8');
    e.target.value = null; // reset input
  };

  return (
    <div className="flex h-screen bg-slate-100 font-sans text-slate-900">
      <aside className="w-64 bg-slate-900 text-white flex flex-col shadow-xl z-20">
        <div className="p-6 font-black tracking-tighter text-xl">NEOCLOUD <span className="text-blue-500">ERP</span></div>
        
        <div className="px-4 mb-4 space-y-2">
          <label className="text-[10px] uppercase font-bold text-slate-500 block">Workspace</label>
          <div className="flex items-center gap-2 bg-slate-800 rounded-lg p-2 border border-slate-700">
            <Building2 size={14} className="text-blue-400 shrink-0" />
            <select className="bg-transparent text-sm font-mono text-white outline-none w-full cursor-pointer" value={licenseKey} onChange={(e) => setLicenseKey(e.target.value)}>
              {workspaces.map(ws => <option key={ws} value={ws} className="bg-slate-800">{ws}</option>)}
            </select>
          </div>
          <div className="flex items-center gap-2">
             <input type="text" placeholder="Nuevo Workspace" value={newWorkspace} onChange={e=>setNewWorkspace(e.target.value)} className="w-full bg-slate-800 border border-slate-700 rounded p-1.5 text-xs text-white outline-none focus:border-blue-500 font-mono uppercase" />
             <button onClick={handleCreateWorkspace} className="bg-blue-600 hover:bg-blue-500 p-1.5 rounded text-white transition-colors"><Plus size={14}/></button>
          </div>
        </div>

        <nav className="p-4 space-y-2">
          <div className="text-[10px] uppercase font-bold text-slate-500 mb-2 px-3">Explorador WBS</div>
          
          <button onClick={exportNeodata} className="w-full flex items-center gap-3 p-3 text-slate-300 hover:bg-slate-800 rounded-lg text-sm transition-all text-left">
            <FileDown size={16} className="text-emerald-400"/> Exportar CSV
          </button>
          
          <label className="w-full flex items-center gap-3 p-3 text-slate-300 hover:bg-slate-800 rounded-lg text-sm transition-all text-left cursor-pointer">
            <FileUp size={16} className="text-orange-400"/> Importar Neodata
            <input type="file" accept=".csv" className="hidden" onChange={importNeodata} />
          </label>
        </nav>
      </aside>

      <main className="flex-1 flex flex-col overflow-hidden relative">
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6 shadow-sm z-10">
          <div className="flex items-center gap-4">
            <h2 className="font-bold text-slate-700">WBS Editor</h2>
            <div className="h-4 w-px bg-slate-200"></div>
            <button onClick={()=>addNode(null, 'CHAP', resources.length-1)} className="flex items-center gap-1 text-xs font-bold text-blue-600 bg-blue-50 hover:bg-blue-100 px-3 py-1.5 rounded-md transition-colors border border-blue-200"><Plus size={14}/> Partida</button>
          </div>
          <div className="flex items-center gap-4">
            {saveStatus && <span className="text-xs font-bold text-emerald-500 flex items-center gap-1"><CheckCircle2 size={14}/> {saveStatus}</span>}
            <button onClick={saveMatrix} disabled={saving} className="flex items-center gap-2 px-6 py-2 bg-emerald-600 text-white text-xs font-bold rounded-lg hover:bg-emerald-500 shadow-lg active:scale-95 transition-all">
                <Save size={14}/> {saving ? 'GUARDANDO...' : 'GUARDAR WBS'}
            </button>
          </div>
        </header>

        <div className="flex-1 overflow-auto p-6">
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-[10px] uppercase font-black text-slate-500 tracking-widest">
                  <th className="p-2 w-8"></th>
                  <th className="p-3 w-16 text-center">Tipo</th>
                  <th className="p-3 w-32">Código</th>
                  <th className="p-3">Descripción</th>
                  <th className="p-3 text-center w-20">Unidad</th>
                  <th className="p-3 text-right w-24">Cantidad</th>
                  <th className="p-3 text-right w-28">P.U.</th>
                  <th className="p-3 text-right w-36">Importe</th>
                  <th className="p-3 w-12"></th>
                </tr>
              </thead>
              <tbody className="text-sm divide-y divide-slate-100">
                {resources.map((res, index) => {
                  const isChap = res.type === 'CHAP';
                  const isConc = res.type === 'CONC';
                  const isRes = !isChap && !isConc;
                  
                  let lineTotal = (parseFloat(res.qty)||0) * (parseFloat(res.price)||0);
                  if (res.type === 'LAB') lineTotal *= fasarRate;

                  return (
                    <tr key={res.id} className={`transition-colors group ${isChap ? 'bg-slate-800 text-white hover:bg-slate-700' : isConc ? 'bg-slate-100 hover:bg-slate-200' : 'hover:bg-blue-50/30'}`}>
                      <td className="p-2 text-center text-slate-400 opacity-0 group-hover:opacity-100 cursor-move"><GripVertical size={14}/></td>
                      <td className="p-2 text-center">
                        <select value={res.type} onChange={(e)=>updateResource(res.id, 'type', e.target.value)} className={`bg-transparent outline-none text-[9px] font-black uppercase appearance-none text-center cursor-pointer ${isChap ? 'text-slate-300' : isConc ? 'text-blue-700' : 'text-slate-500'}`}>
                           <option value="CHAP">CHAP</option><option value="CONC">CONC</option><option value="MAT">MAT</option><option value="LAB">LAB</option><option value="EQP">EQP</option>
                        </select>
                      </td>
                      
                      <td className={`p-2 ${isChap ? 'pl-0' : isConc ? 'pl-4' : 'pl-8'}`}>
                        <input type="text" value={res.code} onChange={(e)=>updateResource(res.id, 'code', e.target.value)} className={`w-full bg-transparent border-b border-transparent focus:border-blue-400 px-1 py-1 text-xs font-mono font-bold outline-none ${isChap ? 'text-blue-300' : isConc ? 'text-blue-700' : 'text-slate-500'}`} />
                      </td>

                      <td className="p-2 flex items-center gap-2">
                        {isChap && <FolderTree size={14} className="text-slate-400"/>}
                        {isConc && <ChevronRight size={14} className="text-blue-400"/>}
                        <input type="text" value={res.description} onChange={(e)=>updateResource(res.id, 'description', e.target.value)} className={`w-full bg-transparent border-b border-transparent focus:border-blue-400 px-1 py-1 text-xs outline-none ${isChap ? 'font-bold text-white' : isConc ? 'font-semibold text-slate-800' : 'text-slate-600'}`} />
                      </td>
                      
                      <td className="p-2">
                        <input type="text" value={res.unit} onChange={(e)=>updateResource(res.id, 'unit', e.target.value)} className={`w-full text-center bg-transparent border-b border-transparent focus:border-blue-400 px-1 py-1 text-xs font-bold outline-none ${isChap ? 'text-slate-400' : 'text-slate-600'}`} />
                      </td>
                      
                      <td className="p-2 text-right">
                        {!isChap && <input type="text" value={res.qty} onChange={(e)=>updateResource(res.id, 'qty', e.target.value)} className={`w-full text-right bg-transparent border-b border-transparent focus:border-blue-400 px-1 py-1 text-xs font-mono font-bold outline-none ${isConc ? 'text-blue-700' : 'text-slate-700'}`} />}
                      </td>
                      
                      <td className="p-2 text-right">
                        {!isChap && <input type="text" value={res.price} onChange={(e)=>updateResource(res.id, 'price', e.target.value)} className={`w-full text-right bg-transparent border-b border-transparent focus:border-blue-400 px-1 py-1 text-xs font-mono outline-none ${isConc ? 'text-slate-500' : 'text-slate-700'}`} />}
                      </td>
                      
                      <td className={`p-2 text-right font-mono font-black text-xs ${isChap ? 'text-emerald-400' : isConc ? 'text-emerald-600' : 'text-slate-400'}`}>
                        {(!isChap) && `$${lineTotal.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`}
                      </td>

                      <td className="p-2 text-center opacity-0 group-hover:opacity-100 transition-opacity">
                         {isChap && <button onClick={()=>addNode(res.id, 'CONC', index)} title="Agregar Concepto" className="text-blue-400 hover:text-white bg-slate-700 rounded p-1"><Plus size={14}/></button>}
                         {isConc && <button onClick={()=>addNode(res.id, 'MAT', index)} title="Agregar Insumo" className="text-blue-600 hover:text-blue-800 bg-blue-100 rounded p-1"><Plus size={14}/></button>}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
        
        <div className="h-20 bg-slate-900 text-white p-6 flex items-center justify-between z-20">
           <div className="flex gap-8">
              <div>
                <p className="text-[10px] font-bold text-slate-400 uppercase mb-1">FASAR Jalisco</p>
                <p className="text-xl font-black text-blue-400">{fasarRate.toFixed(4)}</p>
              </div>
           </div>
           <div className="flex items-center gap-6">
              <span className="text-xs font-bold uppercase text-slate-400 tracking-widest">Costo Directo Total:</span>
              <span className="text-3xl font-black text-emerald-400">${grandTotal.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
           </div>
        </div>
      </main>
    </div>
  );
}
