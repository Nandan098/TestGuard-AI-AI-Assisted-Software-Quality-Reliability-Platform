import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from './api';

function fmtDate(value) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function MetricCard({ label, value, detail, icon, tone = '' }) {
  return (
    <div className={`metric-card ${tone}`}>
      <div className="metric-top"><span className="metric-label">{label}</span><span className="metric-icon">{icon}</span></div>
      <div className="metric-value">{value}</div>
      <div className="metric-detail">{detail}</div>
    </div>
  );
}

function StatusPill({ status }) {
  return <span className={`status-pill ${status === 'passed' ? 'status-passed' : 'status-failed'}`}><span className="status-dot" />{status}</span>;
}

function TrendChart({ data }) {
  const points = useMemo(() => {
    if (!data?.length) return [];
    const width = 560;
    const height = 160;
    const pad = 16;
    return data.map((item, index) => ({
      ...item,
      x: data.length === 1 ? width / 2 : pad + (index * (width - pad * 2)) / (data.length - 1),
      y: height - pad - ((Math.max(0, Math.min(100, item.pass_rate)) / 100) * (height - pad * 2)),
    }));
  }, [data]);
  const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
  return (
    <div className="chart-wrap">
      {points.length ? (
        <>
          <div className="chart-y-labels"><span>100%</span><span>50%</span><span>0%</span></div>
          <svg viewBox="0 0 560 160" className="trend-chart" role="img" aria-label="Pass rate over recent test runs">
            {[16, 80, 144].map(y => <line key={y} x1="16" y1={y} x2="544" y2={y} className="chart-grid" />)}
            <path d={path} className="chart-line" />
            {points.map((p) => <circle key={p.id} cx={p.x} cy={p.y} r="4" className="chart-point"><title>{`Run #${p.id}: ${p.pass_rate}%`}</title></circle>)}
          </svg>
        </>
      ) : <div className="empty-chart">Run the test suite to populate your quality trend.</div>}
    </div>
  );
}

export default function App() {
  const [health, setHealth] = useState(null);
  const [overview, setOverview] = useState(null);
  const [cases, setCases] = useState([]);
  const [runs, setRuns] = useState([]);
  const [selectedRun, setSelectedRun] = useState(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const refresh = useCallback(async (keepSelected = true) => {
    setLoading(true);
    try {
      const [h, o, c, r] = await Promise.all([api.health(), api.overview(), api.testCases(), api.runs()]);
      setHealth(h);
      setOverview(o);
      setCases(c);
      setRuns(r);
      setError('');
      if (keepSelected && selectedRun?.id) {
        try { setSelectedRun(await api.runDetail(selectedRun.id)); }
        catch { setSelectedRun(null); }
      } else if (!selectedRun && r.length) {
        setSelectedRun(await api.runDetail(r[0].id));
      }
    } catch (err) {
      setError(`${err.message}. Start the backend at http://localhost:8000 and the demo target API at http://localhost:8001.`);
    } finally {
      setLoading(false);
    }
  }, [selectedRun]);

  useEffect(() => { refresh(false); }, []); // initial load only

  async function runTests() {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const result = await api.runSuite();
      setSelectedRun(result);
      setNotice(`Run #${result.id} completed: ${result.passed}/${result.total} checks passed.`);
      await refresh(true);
      setSelectedRun(result);
    } catch (err) {
      setError(`${err.message}. Confirm the demo target service is running on port 8001.`);
    } finally {
      setBusy(false);
    }
  }

  async function viewRun(id) {
    try {
      setSelectedRun(await api.runDetail(id));
      setError('');
    } catch (err) { setError(err.message); }
  }

  async function clearHistory() {
    if (!window.confirm('Delete all saved test run history?')) return;
    try {
      await api.clearRuns();
      setSelectedRun(null);
      setNotice('Run history cleared.');
      await refresh(false);
    } catch (err) { setError(err.message); }
  }

  const latest = overview?.latest_run;
  const passRate = latest?.pass_rate ?? 0;
  const results = selectedRun?.results || [];
  const failures = results.filter(item => item.status === 'failed');

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup"><div className="brand-mark">TG</div><div><div className="brand-name">TestGuard <span>AI</span></div><div className="brand-caption">QUALITY INTELLIGENCE</div></div></div>
        <div className="side-section-label">WORKSPACE</div>
        <a className="nav-item active" href="#overview"><span className="nav-glyph">◫</span> Overview</a>
        <a className="nav-item" href="#results"><span className="nav-glyph">✓</span> Test results</a>
        <a className="nav-item" href="#catalog"><span className="nav-glyph">▤</span> Test catalog</a>
        <a className="nav-item" href="#history"><span className="nav-glyph">↻</span> Run history</a>
        <div className="sidebar-spacer" />
        <div className="target-card"><div className="target-card-label">TARGET SERVICE</div><div className="target-status"><span className={`pulse ${health ? 'pulse-on' : ''}`} />{health ? 'Connected' : 'Checking connection'}</div><div className="target-url">{health?.target_base_url || 'http://localhost:8001'}</div><a href="http://localhost:8001/docs" target="_blank" rel="noreferrer">Open target API ↗</a></div>
        <div className="sidebar-footer"><span className="avatar">NP</span><div><strong>Developer workspace</strong><small>Local environment</small></div><span className="footer-dots">•••</span></div>
      </aside>

      <main className="main-content" id="overview">
        <header className="topbar"><div className="breadcrumb">Workspace <span>/</span> <strong>Overview</strong></div><div className="topbar-actions"><span className="environment"><span className="pulse pulse-on" /> DEMO ENVIRONMENT</span><button className="icon-button" title="Refresh data" onClick={() => refresh(true)} disabled={loading}>↻</button></div></header>
        <section className="page-heading"><div><div className="eyebrow">AUTOMATED QUALITY MONITORING</div><h1>Quality overview</h1><p>Catch regressions early. Understand failures faster. Ship with confidence.</p></div><button className="primary-button" onClick={runTests} disabled={busy || loading}><span className={busy ? 'button-spinner' : ''}>{busy ? '◌' : '▶'}</span>{busy ? 'Running test suite…' : 'Run test suite'}</button></section>

        {error && <div className="alert alert-error"><strong>Connection issue</strong><span>{error}</span><button onClick={() => setError('')} aria-label="Dismiss">×</button></div>}
        {notice && <div className="alert alert-success"><strong>✓</strong><span>{notice}</span><button onClick={() => setNotice('')} aria-label="Dismiss">×</button></div>}

        <section className="metrics-grid">
          <MetricCard label="TOTAL TEST RUNS" value={overview?.total_runs ?? '—'} detail="Saved execution history" icon="↻" />
          <MetricCard label="LATEST PASS RATE" value={latest ? `${passRate}%` : '—'} detail={latest ? `${latest.passed} of ${latest.total} checks passed` : 'No runs yet'} icon="✓" tone={passRate >= 90 && latest ? 'metric-green' : ''} />
          <MetricCard label="LATEST FAILURES" value={latest?.failed ?? '—'} detail="Checks requiring attention" icon="!" tone={latest?.failed ? 'metric-red' : ''} />
          <MetricCard label="AVG. RESPONSE TIME" value={latest ? `${latest.avg_duration_ms} ms` : '—'} detail="Across the latest run" icon="◷" />
        </section>

        <section className="content-grid">
          <div className="panel trend-panel"><div className="panel-heading"><div><h2>Quality trend</h2><p>Pass rate across the last 10 runs</p></div><span className="subtle-chip">PASS RATE</span></div><TrendChart data={overview?.trend || []} /><div className="chart-legend"><span className="legend-dot" /> Test pass rate <span className="chart-footnote">New runs appear automatically</span></div></div>
          <div className="panel health-panel"><div className="panel-heading"><div><h2>System health</h2><p>Connected components</p></div><span className="live-badge"><span className="pulse pulse-on" /> LIVE</span></div><div className="health-row"><div className="health-icon">API</div><div className="health-copy"><strong>TestGuard API</strong><small>Orchestration & reporting</small></div><span className="health-check">{health ? 'Operational' : 'Unknown'}</span></div><div className="health-row"><div className="health-icon target">DB</div><div className="health-copy"><strong>Run history database</strong><small>Persistent test results</small></div><span className="health-check">{health ? 'Operational' : 'Unknown'}</span></div><div className="health-row"><div className="health-icon target">QA</div><div className="health-copy"><strong>Target API</strong><small>{health?.target_base_url || 'Waiting for backend'}</small></div><span className="health-check">{health ? 'Configured' : 'Unknown'}</span></div><div className="health-note">Target reachability is verified when a test run executes.</div></div>
        </section>

        <section className="panel results-panel" id="results"><div className="panel-heading"><div><h2>{selectedRun ? `Run #${selectedRun.id} results` : 'Latest test results'}</h2><p>{selectedRun ? `Executed ${fmtDate(selectedRun.started_at)}` : 'Run the suite to see detailed assertions'}</p></div><div className="panel-heading-actions">{selectedRun && <span className={`run-summary ${selectedRun.failed ? 'summary-failed' : 'summary-passed'}`}>{selectedRun.passed}/{selectedRun.total} passed</span>}<button className="text-button" onClick={() => refresh(true)} disabled={loading}>Refresh ↻</button></div></div>
          {selectedRun?.summary && <div className={`run-insight ${selectedRun.failed ? 'insight-warning' : 'insight-good'}`}><span className="insight-symbol">{selectedRun.failed ? '!' : '✓'}</span><div><strong>Run analysis</strong><p>{selectedRun.summary}</p></div></div>}
          <div className="table-scroll"><table><thead><tr><th>TEST CASE</th><th>ENDPOINT</th><th>STATUS</th><th>DURATION</th><th>FAILURE CATEGORY</th></tr></thead><tbody>{results.length ? results.map((item) => <tr key={item.id || item.test_name}><td><strong>{item.test_name}</strong><small>{item.description}</small></td><td><code>{item.endpoint}</code></td><td><StatusPill status={item.status} /></td><td>{item.duration_ms} ms</td><td>{item.status === 'failed' ? <span className="failure-category">{item.category || 'Unclassified'}</span> : <span className="muted">—</span>}</td></tr>) : <tr><td colSpan="5" className="empty-row">No execution results yet. Select <strong>Run test suite</strong> to begin.</td></tr>}</tbody></table></div>
        </section>

        {failures.length > 0 && <section className="panel failure-panel"><div className="panel-heading"><div><h2>Failure triage</h2><p>Rule-based, AI-assisted diagnostic suggestions</p></div><span className="subtle-chip">{failures.length} NEED ATTENTION</span></div><div className="failure-list">{failures.map((item) => <article className="failure-card" key={item.id || item.test_name}><div className="failure-card-top"><span className="failure-marker">!</span><div><strong>{item.test_name}</strong><small>{item.endpoint} · {item.category}</small></div></div><div className="failure-detail"><span>DIAGNOSIS</span><p>{item.diagnosis || 'Review the response against the expected contract.'}</p></div><div className="failure-detail"><span>SUGGESTED NEXT STEP</span><p>{item.recommendation || 'Inspect logs and reproduce the failing request.'}</p></div><details><summary>Expected vs actual</summary><div className="compare-grid"><div><small>EXPECTED</small><code>{item.expected}</code></div><div><small>ACTUAL</small><code>{item.actual}</code></div></div></details></article>)}</div></section>}

        <section className="panel catalog-panel" id="catalog"><div className="panel-heading"><div><h2>Test catalog</h2><p>Built-in API contract and regression checks</p></div><span className="subtle-chip">{cases.length} TESTS</span></div><div className="catalog-grid">{cases.map((item, index) => <div className="catalog-card" key={item.name}><div className="catalog-card-top"><span className="case-number">{String(index + 1).padStart(2, '0')}</span><span className={`method method-${item.method.toLowerCase()}`}>{item.method}</span></div><strong>{item.name}</strong><p>{item.description}</p><code>{item.path}</code></div>)}</div></section>

        <section className="panel history-panel" id="history"><div className="panel-heading"><div><h2>Recent runs</h2><p>Select a run to inspect its full report</p></div><button className="text-button danger-text" onClick={clearHistory} disabled={!runs.length}>Clear history</button></div><div className="history-list">{runs.length ? runs.map(run => <button className={`history-item ${selectedRun?.id === run.id ? 'history-selected' : ''}`} key={run.id} onClick={() => viewRun(run.id)}><span className="history-run-id">#{run.id}</span><span className="history-date">{fmtDate(run.started_at)}</span><span className="history-track"><span style={{ width: `${run.pass_rate}%` }} /></span><span className="history-rate">{run.pass_rate}%</span><span className={`history-count ${run.failed ? 'has-failures' : ''}`}>{run.failed} failed</span></button>) : <div className="empty-row">No saved runs yet.</div>}</div></section>

        <footer className="page-footer"><span>TestGuard AI <span className="footer-separator">/</span> Portfolio demo</span><span>Failure insights are heuristic suggestions, not guaranteed root-cause analysis.</span></footer>
      </main>
    </div>
  );
}
