import os
import requests
import time
import shutil
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool
from dotenv import load_dotenv

load_dotenv()

# --- 1. ENVIRONMENT SETUP ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.getcwd(), ".."))
ENV_DEV = os.path.join(os.getcwd(), "env_dev")
ENV_SIT = os.path.join(os.getcwd(), "env_sit")
ENV_PROD = os.path.join(os.getcwd(), "env_prod")
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")

LIVE_FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend", "src", "app", "erp")
LIVE_FRONTEND_FILE = os.path.join(LIVE_FRONTEND_DIR, "page.tsx")

def clean_workspaces():
    for d in [ENV_DEV, ENV_SIT, ENV_PROD, DOCS_DIR]:
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d, exist_ok=True)
    os.makedirs(LIVE_FRONTEND_DIR, exist_ok=True)
    
    placeholder_api = """from fastapi import FastAPI\nfrom fastapi.middleware.cors import CORSMiddleware\napp = FastAPI()\napp.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])\n@app.get("/{path:path}")\ndef wait(): return {"status": "AI is writing..."}\n@app.post("/{path:path}")\ndef wait_post(): return {"status": "AI is writing..."}"""
    with open(os.path.join(ENV_PROD, "fasar_calc.py"), 'w', encoding='utf-8') as f:
        f.write(placeholder_api)

def broadcast(msg: str):
    try: requests.post("http://localhost:8000/broadcast-agent", json={"payload": msg})
    except: pass

# --- 2. BACKEND API TOOL ---

@tool("generate_backend_api")
def generate_backend_api(command: str) -> str:
    """Generates the Backend API with Neodata Import/Export."""
    broadcast("💻 ACTION: Building WBS CRUD & Neodata Sync Engine...")
    fastapi_code = """from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import os
import csv
import io

app = FastAPI(title="NEOCLOUD ERP")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def get_tenant_db(request: Request):
    tenant = request.headers.get("x-license-key") or request.query_params.get("tenant") or "DEMO123"
    safe_key = "".join(c for c in tenant if c.isalnum())
    db_file = f"tenant_{safe_key}.db"
    
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    
    # Base Schema
    c.execute('''CREATE TABLE IF NOT EXISTS wbs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, parent_id INTEGER NULL, code TEXT, description TEXT, type TEXT, unit TEXT, qty REAL DEFAULT 1.0, price REAL DEFAULT 0.0)''')
                 
    # AUTO-MIGRATOR: Safe update for sort_order
    try:
        c.execute("ALTER TABLE wbs ADD COLUMN sort_order INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass # Column already exists
        
    c.execute("SELECT COUNT(*) FROM wbs")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO wbs (parent_id, code, description, type, unit, qty, price, sort_order) VALUES (NULL, 'CH-01', 'Obras Preliminares', 'CHAP', '', 1, 0, 0)")
        chap_id = c.lastrowid
        c.execute("INSERT INTO wbs (parent_id, code, description, type, unit, qty, price, sort_order) VALUES (?, 'C-01.01', 'Trazo y Nivelacion', 'CONC', 'M2', 150, 0, 1)", (chap_id,))
        conc_id = c.lastrowid
        c.execute("INSERT INTO wbs (parent_id, code, description, type, unit, qty, price, sort_order) VALUES (?, 'PEON', 'Peon General', 'LAB', 'JOR', 0.1, 450.00, 2)", (conc_id,))
    conn.commit()
    return db_file

@app.get("/workspaces")
def get_workspaces():
    files = [f for f in os.listdir('.') if f.startswith('tenant_') and f.endswith('.db')]
    return {"workspaces": [f.replace('tenant_', '').replace('.db', '') for f in files] or ["DEMO123"]}

@app.post("/workspaces/{new_key}")
def create_workspace(new_key: str):
    conn = sqlite3.connect(f"tenant_{new_key}.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS wbs (id INTEGER PRIMARY KEY AUTOINCREMENT, parent_id INTEGER NULL, code TEXT, description TEXT, type TEXT, unit TEXT, qty REAL DEFAULT 1.0, price REAL DEFAULT 0.0, sort_order INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.get("/catalog")
def get_catalog(db_file: str = Depends(get_tenant_db)):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute("SELECT id, parent_id, code, description, type, unit, qty, price FROM wbs ORDER BY sort_order ASC, id ASC")
    items = [{"id": r[0], "parent_id": r[1], "code": r[2], "description": r[3], "type": r[4], "unit": r[5], "qty": r[6], "price": r[7]} for r in c.fetchall()]
    conn.close()
    return items

@app.post("/save_matrix")
async def save_matrix(request: Request, db_file: str = Depends(get_tenant_db)):
    data = await request.json()
    resources = data.get("resources", [])
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    try:
        # We process linearly to respect UI ordering
        for idx, res in enumerate(resources):
            is_new = str(res.get('id')).startswith('new_')
            if is_new:
                c.execute("INSERT INTO wbs (parent_id, code, description, type, unit, qty, price, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                          (res.get('parent_id'), res.get('code'), res.get('description'), res.get('type'), res.get('unit'), float(res.get('qty') or 1), float(res.get('price') or 0), idx))
            else:
                c.execute("UPDATE wbs SET code=?, description=?, unit=?, qty=?, price=?, sort_order=? WHERE id=?", 
                          (res.get('code'), res.get('description'), res.get('unit'), float(res.get('qty') or 0), float(res.get('price') or 0), idx, res.get('id')))
        conn.commit()
        return {"status": "success"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/export_neodata")
def export_neodata(db_file: str = Depends(get_tenant_db)):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute("SELECT type, code, description, unit, qty, price FROM wbs ORDER BY sort_order ASC")
    rows = c.fetchall()
    conn.close()
    
    csv_text = "Tipo,Codigo,Descripcion,Unidad,Cantidad,PrecioBase\\n"
    for r in rows:
        desc = str(r[2]).replace(',', ' ')
        csv_text += f"{r[0]},{r[1]},{desc},{r[3]},{r[4]},{r[5]}\\n"
    return PlainTextResponse(content=csv_text, headers={"Content-Disposition": "attachment; filename=Presupuesto_Neodata.csv"})

@app.post("/import_neodata")
async def import_neodata(request: Request, db_file: str = Depends(get_tenant_db)):
    payload = await request.json()
    csv_text = payload.get("csv_data", "")
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    try:
        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)
        
        start_idx = 0
        for i, row in enumerate(rows):
            if row and row[0].strip().lower() in ['código', 'codigo']:
                start_idx = i + 1
                break
                
        c.execute("DELETE FROM wbs") 
        current_chap_id = None
        
        for idx, row in enumerate(rows[start_idx:]):
            if not row or len(row) < 2 or not row[0].strip(): continue
            code = row[0].strip()
            desc = row[1].strip()
            unit = row[2].strip() if len(row) > 2 else ""
            qty_str = str(row[3]).strip().replace(',', '') if len(row) > 3 else "1"
            price_str = str(row[4]).strip().replace(',', '') if len(row) > 4 else "0"
            
            try: qty = float(qty_str) if qty_str else 1.0
            except: qty = 1.0
            try: price = float(price_str) if price_str else 0.0
            except: price = 0.0
            
            # Neodata implicitly defines Chapters if there's no unit
            node_type = 'CHAP' if not unit else 'CONC'
            
            if node_type == 'CHAP':
                c.execute("INSERT INTO wbs (parent_id, code, description, type, unit, qty, price, sort_order) VALUES (NULL, ?, ?, ?, ?, ?, ?, ?)", (code, desc, node_type, unit, 1.0, 0.0, idx))
                current_chap_id = c.lastrowid
            else:
                c.execute("INSERT INTO wbs (parent_id, code, description, type, unit, qty, price, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (current_chap_id, code, desc, node_type, unit, qty, price, idx))
        
        conn.commit()
        return {"status": "success"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
"""
    with open(os.path.join(ENV_DEV, "fasar_calc.py"), 'w', encoding='utf-8') as f:
        f.write(fastapi_code)
    return "SUCCESS: Backend created."

# --- 3. FRONTEND UI TOOL ---

@tool("compile_frontend_dashboard")
def compile_frontend_dashboard(command: str) -> str:
    """Compiles the React Dashboard with WBS Editing and File Import/Export."""
    broadcast("🎨 ACTION: Compiling WBS Editor & Import Modules...")
    react_code = """"use client";
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
"""
    with open(os.path.join(ENV_DEV, "Dashboard.tsx"), 'w', encoding='utf-8') as f:
        f.write(react_code)
    return "SUCCESS: Dashboard compiled."

@tool("generate_documentation")
def generate_documentation(command: str) -> str:
    """Generates Markdown and Mermaid.js documentation for the project."""
    broadcast("📝 ACTION: Generating Docs...")
    
    arch_md = f"""# NeoCloud ERP Architecture

## WBS Editor & Neodata Sync
The system now features a fully editable Work Breakdown Structure and cross-platform compatibility.

\x60\x60\x60mermaid
graph LR
    ND[Neodata .CSV] -->|Import/Upload| API[FastAPI]
    API -->|Parse & Map Hierarchy| DB[(SQLite Tenant)]
    DB -->|Fetch| React[Next.js WBS Grid]
    React -->|Add Row & UPSERT| API
\x60\x60\x60
"""
    with open(os.path.join(DOCS_DIR, "architecture.md"), 'w', encoding='utf-8') as f:
        f.write(arch_md)
    return "SUCCESS: Docs created."

@tool("qa_and_deploy_pipeline")
def qa_and_deploy_pipeline(command: str) -> str:
    """Deploys files."""
    broadcast("🚀 ACTION: Deploying WBS Editor...")
    
    src_back = os.path.join(ENV_DEV, "fasar_calc.py")
    dst_back = os.path.join(ENV_PROD, "fasar_calc.py")
    if os.path.exists(src_back): shutil.copy(src_back, dst_back)
    
    src_front = os.path.join(ENV_DEV, "Dashboard.tsx")
    if os.path.exists(src_front):
        shutil.copyfile(src_front, LIVE_FRONTEND_FILE)
        broadcast(f"⚡ HOT RELOAD TRIGGERED!")
    return "SUCCESS: Deployed."

# --- 3. LLM CONFIG ---
local_llm = LLM(
    model="openai/qwen/qwen3.5-35b-a3b", 
    base_url="http://192.168.1.90:1234/v1",
    api_key="lm-studio",
    temperature=0.0, 
    max_tokens=2000,
    stop=["\nObservation:", "Observation:"] 
)

strict_format = " YOU MUST USE THE TOOL using exactly this format: {\"command\": \"generate\"}. DO NOT skip the tool."
strict_deploy = " YOU MUST USE THE TOOL using exactly this format: {\"command\": \"deploy\"}. DO NOT skip the tool."

backend_agent = Agent(role='Backend Engineer', goal='Generate API.', backstory='Use generate_backend_api tool.' + strict_format, llm=local_llm, tools=[generate_backend_api], allow_delegation=False)
frontend_agent = Agent(role='Frontend Architect', goal='Compile Dashboard.', backstory='Use compile_frontend_dashboard tool.' + strict_format, llm=local_llm, tools=[compile_frontend_dashboard], allow_delegation=False)
tech_writer_agent = Agent(role='Technical Writer', goal='Generate docs.', backstory='Use generate_documentation tool.' + strict_format, llm=local_llm, tools=[generate_documentation], allow_delegation=False)
qa_agent = Agent(role='Release Manager', goal='Deploy.', backstory='Use qa_and_deploy_pipeline tool.' + strict_deploy, llm=local_llm, tools=[qa_and_deploy_pipeline], allow_delegation=False)

tasks = [
    Task(description="Call generate_backend_api first. After you get the SUCCESS observation, output exactly: BACKEND_DONE", expected_output="BACKEND_DONE", agent=backend_agent),
    Task(description="Call compile_frontend_dashboard first. After you get the SUCCESS observation, output exactly: FRONTEND_DONE", expected_output="FRONTEND_DONE", agent=frontend_agent),
    Task(description="Call generate_documentation first. After you get the SUCCESS observation, output exactly: DOCS_DONE", expected_output="DOCS_DONE", agent=tech_writer_agent), 
    Task(description="Call qa_and_deploy_pipeline first. After you get the SUCCESS observation, output exactly: QA_DONE", expected_output="QA_DONE", agent=qa_agent)
]

def run_sdlc():
    clean_workspaces()
    Crew(agents=[backend_agent, frontend_agent, tech_writer_agent, qa_agent], tasks=tasks, process=Process.sequential, verbose=True).kickoff()

if __name__ == "__main__":
    broadcast("🟢 Booting WBS Editor & Neodata Sync Engine...")
    run_sdlc()
    broadcast("🏁 Sprint Concluded.")