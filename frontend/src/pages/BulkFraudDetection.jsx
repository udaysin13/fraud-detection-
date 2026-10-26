import React, { useMemo, useRef, useState } from 'react';
import { Upload, FileSpreadsheet, Download, RotateCcw, AlertTriangle, Search, ChevronDown, ChevronUp } from 'lucide-react';
import { apiClient } from '../api/client';
import { formatINR } from '../utils/formatters';

const PAGE_SIZE = 10;

export const BulkFraudDetection = () => {
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [query, setQuery] = useState('');
  const [risk, setRisk] = useState('All');
  const [prediction, setPrediction] = useState('All');
  const [sort, setSort] = useState('source');
  const [expandedRow, setExpandedRow] = useState(null);
  const [page, setPage] = useState(1);

  const selectFile = (candidate) => {
    setError('');
    setResult(null);
    setPage(1);
    setFile(null);
    if (!candidate) return;
    if (!candidate.name.toLowerCase().endsWith('.csv')) {
      setError('Select a CSV file. The server also validates its contents.');
      return;
    }
    setFile(candidate);
  };

  const analyse = async () => {
    if (!file) return setError('Choose a CSV file before analysing it.');
    setLoading(true); setError('');
    try { setResult(await apiClient.uploadBulkCsv(file)); }
    catch (err) { setError(err.message || 'The CSV could not be analysed.'); }
    finally { setLoading(false); }
  };
  const reset = () => { setFile(null); setResult(null); setError(''); setQuery(''); setRisk('All'); setPrediction('All'); setSort('source'); setExpandedRow(null); setPage(1); };
  const filtered = useMemo(() => (result?.records || []).filter((row) => {
    const matchesText = !query || String(row.transaction_id || '').toLowerCase().includes(query.toLowerCase());
    return matchesText && (risk === 'All' || row.risk_category === risk) && (prediction === 'All' || row.predicted_class === prediction);
  }).sort((a, b) => {
    if (sort === 'risk-desc') return (b.risk_score ?? -1) - (a.risk_score ?? -1);
    if (sort === 'amount-desc') return Number(b.original?.amount_inr ?? -1) - Number(a.original?.amount_inr ?? -1);
    if (sort === 'amount-asc') return Number(a.original?.amount_inr ?? Infinity) - Number(b.original?.amount_inr ?? Infinity);
    return a.source_row - b.source_row;
  }), [result, query, risk, prediction, sort]);
  const visible = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));

  return <div className="space-y-6">
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-card-soft flex flex-wrap justify-between gap-4">
      <div className="flex gap-3"><div className="p-2.5 bg-blue-50 text-blue-600 rounded-xl"><FileSpreadsheet /></div><div><h2 className="text-lg font-bold text-slate-800">Bulk Fraud Detection</h2><p className="text-xs text-slate-500">Analyse a CSV locally through the configured model. Predictions are not confirmed fraud.</p></div></div>
      <a className="text-xs font-bold text-blue-600 hover:underline self-center" href={apiClient.getBulkSampleUrl()}>Download working sample CSV</a>
    </div>

    {!result && <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-card-soft space-y-5">
      <button type="button" onClick={() => inputRef.current?.click()} onDragOver={(e) => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={(e) => { e.preventDefault(); setDragging(false); selectFile(e.dataTransfer.files?.[0]); }} className={`w-full rounded-xl border-2 border-dashed p-10 text-center transition-colors ${dragging ? 'border-blue-500 bg-blue-50' : 'border-slate-200 hover:border-blue-400 bg-slate-50'}`}>
        <Upload className="w-8 h-8 mx-auto text-blue-600 mb-3" /><p className="text-sm font-bold text-slate-700">Drop a CSV here, or browse</p><p className="text-xs text-slate-500 mt-1">Required: transaction_id, timestamp, amount_inr, sender_id. UTF-8 CSV; max 10,000 rows / 5 MB by default.</p>
      </button>
      <input ref={inputRef} className="hidden" type="file" accept=".csv,text/csv" onChange={(e) => selectFile(e.target.files?.[0])} />
      {file && <div className="flex items-center justify-between rounded-lg border border-slate-200 p-3 text-xs"><span className="font-semibold text-slate-700">{file.name} ({(file.size / 1024).toFixed(1)} KB)</span><button onClick={reset} className="text-slate-500 hover:text-rose-600">Remove</button></div>}
      {error && <div className="flex gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700"><AlertTriangle className="w-4 h-4 shrink-0" />{error}</div>}
      <div className="flex flex-wrap gap-3"><button disabled={loading || !file} onClick={analyse} className="px-4 py-2 rounded-lg bg-blue-600 text-white text-xs font-bold disabled:opacity-50">{loading ? 'Analysing uploaded rows…' : 'Analyse CSV'}</button><button onClick={reset} className="px-4 py-2 rounded-lg border border-slate-200 text-xs font-bold text-slate-600">Reset</button></div>
      <p className="text-[11px] text-slate-500">Optional model context: beneficiary_id, merchant_id, channel, transaction_type, merchant_category, device_id, is_new_device, sim_change_flag. A supplied is_fraud value is retained as unverified user input and never used for inference or performance claims. Uploads are held in memory only for this result and export.</p>
    </div>}

    {result && <>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">{[['Uploaded', result.summary.total_rows], ['Analysed', result.summary.analysed_rows], ['Invalid', result.summary.invalid_rows], ['Suspected fraud', result.summary.suspected_fraud], ['High risk', result.summary.high_risk], ['Normal predictions', result.summary.normal_predictions], ['Average risk', result.summary.average_risk_score ?? '—']].map(([label, value]) => <div key={label} className="bg-white border border-slate-200 rounded-xl p-4 shadow-card-soft"><p className="text-[11px] font-bold uppercase text-slate-400">{label}</p><p className="text-xl font-bold text-slate-800 mt-1">{value}</p></div>)}</div>
      {result.extra_columns?.length > 0 && <div className="text-xs rounded-lg border border-amber-200 bg-amber-50 p-3 text-amber-800">Extra columns were preserved in the report but not used by the model: {result.extra_columns.join(', ')}</div>}
      <div className="bg-white border border-slate-200 rounded-xl shadow-card-soft overflow-hidden">
        <div className="p-4 flex flex-wrap gap-3 justify-between border-b border-slate-200"><div className="flex flex-wrap gap-2"><div className="relative"><Search className="w-4 h-4 absolute left-2 top-2 text-slate-400"/><input value={query} onChange={(e) => { setQuery(e.target.value); setPage(1); }} placeholder="Transaction ID" className="pl-8 pr-3 py-1.5 border rounded-lg text-xs" /></div><select value={risk} onChange={(e) => { setRisk(e.target.value); setPage(1); }} className="border rounded-lg text-xs px-2"><option>All</option><option>LOW_RISK</option><option>REVIEW</option><option>HIGH_RISK</option></select><select value={prediction} onChange={(e) => { setPrediction(e.target.value); setPage(1); }} className="border rounded-lg text-xs px-2"><option>All</option><option>Normal Prediction</option><option>Suspected Fraud</option></select><select value={sort} onChange={(e) => { setSort(e.target.value); setPage(1); }} className="border rounded-lg text-xs px-2" aria-label="Sort results"><option value="source">Original row order</option><option value="risk-desc">Risk score: high to low</option><option value="amount-desc">Amount: high to low</option><option value="amount-asc">Amount: low to high</option></select></div><div className="flex gap-2"><a href={apiClient.getBulkExportUrl(result.analysis_id)} className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-teal-600 text-white text-xs font-bold"><Download className="w-3.5 h-3.5"/>Download results</a><button onClick={reset} className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border text-xs font-bold"><RotateCcw className="w-3.5 h-3.5"/>New upload</button></div></div>
        <div className="overflow-x-auto"><table className="min-w-full text-xs"><thead className="bg-slate-50 text-slate-500"><tr><th className="p-3 text-left">Row / Transaction</th><th className="p-3 text-left">Prediction</th><th className="p-3 text-left">Risk</th><th className="p-3 text-left">Action</th><th className="p-3 text-left">Details</th></tr></thead><tbody>{visible.map((row) => <tr key={row.source_row} className="border-t border-slate-100 align-top"><td className="p-3 font-mono text-slate-700">{row.source_row} · {row.transaction_id || '—'}</td><td className="p-3 font-semibold">{row.validation_status === 'invalid' ? 'Invalid row' : row.predicted_class}</td><td className="p-3">{row.risk_score ?? '—'} {row.risk_category && <span className="text-slate-500">{row.risk_category}</span>}</td><td className="p-3">{row.recommended_action || '—'}</td><td className="p-3 text-slate-500 max-w-xs">{row.error_reason || row.reasons?.join('; ') || '—'}</td></tr>)}</tbody></table></div>
        <div className="p-3 flex justify-between text-xs text-slate-500"><span>{filtered.length} matching rows</span><span><button disabled={page === 1} onClick={() => setPage(page - 1)} className="mr-2 disabled:opacity-40">Previous</button>{page} / {pages}<button disabled={page === pages} onClick={() => setPage(page + 1)} className="ml-2 disabled:opacity-40">Next</button></span></div>
      </div>
    </>}
  </div>;
};
