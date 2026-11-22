import { useEffect, useState } from 'react'
import './App.css'

function App() {
  const [jobs, setJobs] = useState([])
  const [topic, setTopic] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [papersByJob, setPapersByJob] = useState({})
  const [selectedPapersByJob, setSelectedPapersByJob] = useState({})
  const [summarizingJob, setSummarizingJob] = useState(null)
  const [summaryByJob, setSummaryByJob] = useState({})
  const [searchingJob, setSearchingJob] = useState(null)
  const [analyzingJob, setAnalyzingJob] = useState(null)
  const [analysisByJob, setAnalysisByJob] = useState({})
  const [reportByJob, setReportByJob] = useState({})
  const [generatingReportJob, setGeneratingReportJob] = useState(null)
  const [page, setPage] = useState('home')


  async function loadJobs() {
    try {
      const response = await fetch('/research-jobs?limit=100')
      if (!response.ok) throw new Error('Could not load research jobs.')
      setJobs(await response.json())
      setError('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

useEffect(() => {
  const controller = new AbortController()

  fetch('/research-jobs?limit=100', { signal: controller.signal })
    .then((response) => {
      if (!response.ok) throw new Error('Could not load research jobs.')
      return response.json()
    })
    .then((data) => {
      setJobs(data)
      setError('')
    })
    .catch((err) => {
      if (err.name !== 'AbortError') setError(err.message)
    })
    .finally(() => {
      if (!controller.signal.aborted) setLoading(false)
    })

  return () => controller.abort()
}, [])
  async function createJob(event) {
    event.preventDefault()
    const trimmedTopic = topic.trim()
    if (!trimmedTopic) return

    setSaving(true)
    setError('')

    try {
      const response = await fetch('/research-jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: trimmedTopic }),
      })

      if (!response.ok) throw new Error('Could not create the research job.')

      setTopic('')
      await loadJobs()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }
  async function loadLatestSummary(jobId) {
    const response = await fetch(`/research-jobs/${jobId}/summaries`)
    if (!response.ok) throw new Error('Could not load saved summaries.')

    const summaries = await response.json()
    setSummaryByJob((previous) => ({
      ...previous,
    [jobId]: summaries[0] || null,    }))
  }
  async function loadLatestAnalysis(jobId) {
    const response = await fetch(`/research-jobs/${jobId}/gap-analyses`)
    if (!response.ok) throw new Error('Could not load saved gap analyses.')

    const analyses = await response.json()
    setAnalysisByJob((previous) => ({
      ...previous,
      [jobId]: analyses[0] || null,
    }))
  }
  async function generateReport(jobId) {
    const summary = summaryByJob[jobId]
    const analysis = analysisByJob[jobId]
    if (!summary?.id || !analysis?.id) return

    setGeneratingReportJob(jobId)
    setError('')

    try {
      const response = await fetch(`/research-jobs/${jobId}/reports:generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          summary_id: summary.id,
          gap_analysis_id: analysis.id,
        }),
      })

      const result = await response.json()
      if (!response.ok) {
        throw new Error(result.detail || 'Report generation failed.')
      }

      setReportByJob((previous) => ({
        ...previous,
        [jobId]: result.report,
      }))
    } catch (err) {
      setError(err.message)
    } finally {
      setGeneratingReportJob(null)
    }
  }
  async function reviewGap(jobId, index, reviewStatus) {
    const analysis = analysisByJob[jobId]
    if (!analysis) return

    setError('')

    try {
      const response = await fetch(
        `/research-jobs/${jobId}/gap-analyses/${analysis.id}/review`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            gap_index: index,
            review_status: reviewStatus,
          }),
        },
      )

      const updated = await response.json()
      if (!response.ok) {
        throw new Error(updated.detail || 'Could not review this gap.')
      }

      setAnalysisByJob((previous) => ({
        ...previous,
        [jobId]: updated,
      }))
    } catch (err) {
      setError(err.message)
    }
  }
  async function analyzeGaps(jobId) {
    const paperIds = selectedPapersByJob[jobId] || []
    if (paperIds.length === 0) return

    setAnalyzingJob(jobId)
    setError('')

    try {
      const response = await fetch(`/research-jobs/${jobId}/papers:analyze-gaps`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paper_ids: paperIds }),
      })

      const result = await response.json()
      if (!response.ok) {
        throw new Error(result.detail || 'Gap analysis failed.')
      }

      await loadLatestAnalysis(jobId)    } catch (err) {
      setError(err.message)
    } finally {
      setAnalyzingJob(null)
    }
  }
  async function generateSummary(jobId) {
    const paperIds = selectedPapersByJob[jobId] || []
    if (paperIds.length === 0) return

    setSummarizingJob(jobId)
    setError('')

    try {
      const response = await fetch(
        `/research-jobs/${jobId}/papers:generate-summary`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ paper_ids: paperIds }),
        },
      )

      const result = await response.json()
      if (!response.ok) {
        throw new Error(result.detail || 'Summary generation failed.')
      }

    await loadLatestSummary(jobId)
    } catch (err) {
      setError(err.message)
    } finally {
      setSummarizingJob(null)
    }
  }
  function togglePaper(jobId, paperId) {
    setSelectedPapersByJob((previous) => {
        const selected = previous[jobId] || []
          return {
            ...previous,
            [jobId]: selected.includes(paperId)
              ? selected.filter((id) => id !== paperId)
              : [...selected, paperId],
          }
      })
  }
  async function loadPapers(jobId) {
    setError('')

    try {
      const response = await fetch(`/research-jobs/${jobId}/papers?limit=100`)
      if (!response.ok) throw new Error('Could not load saved papers.')

      const papers = await response.json()
      setPapersByJob((previous) => ({ ...previous, [jobId]: papers }))
      await loadLatestSummary(jobId)
      await loadLatestAnalysis(jobId)
    } catch (err) {
      setError(err.message)
    }
  }
  async function searchPapers(jobId) {
  setSearchingJob(jobId)
  setError('')

  try {
    const response = await fetch(`/research-jobs/${jobId}/papers:search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ max_results: 5, refine_query: false }),
    })

    if (!response.ok) {
      const result = await response.json().catch(() => ({}))
      throw new Error(result.detail || 'Paper search failed.')
    }

    const papersResponse = await fetch(`/research-jobs/${jobId}/papers?limit=100`)
    if (!papersResponse.ok) throw new Error('Could not load the saved papers.')

    const papers = await papersResponse.json()
    setPapersByJob((previous) => ({ ...previous, [jobId]: papers }))
  } catch (err) {
    setError(err.message)
  } finally {
    setSearchingJob(null)
  }
}

if (page === 'home') {
  return (
    <main className="home">
      <header className="home-nav">
        <span className="brand">PaperX</span>
        <button type="button" onClick={() => setPage('workspace')}>
          Open workspace
        </button>
      </header>

      <section className="home-hero">
        <div>
          <p className="eyebrow">AI RESEARCH WORKSPACE</p>
          <h1>From research question to clearer insight.</h1>
          <p>
            Discover academic papers, summarize selected evidence, explore
            research gaps, and create a reviewed report in one workspace.
          </p>
          <button type="button" onClick={() => setPage('workspace')}>
            Start researching
          </button>
        </div>

        <div className="home-visual" aria-hidden="true">
          <div className="visual-paper visual-paper-back" />
          <div className="visual-paper visual-paper-front">
            <span className="visual-line visual-line-short" />
            <span className="visual-line" />
            <span className="visual-line" />
            <span className="visual-line visual-line-medium" />
            <span className="visual-mark">✦</span>
          </div>
        </div>
      </section>

      <section className="home-steps">
        <h2>How it works</h2>
        <div className="step-grid">
          <article><span>01</span><h3>Discover</h3><p>Find papers related to your topic.</p></article>
          <article><span>02</span><h3>Examine</h3><p>Select papers and review summaries and potential gaps.</p></article>
          <article><span>03</span><h3>Report</h3><p>Approve supported gaps and create a cited report.</p></article>
        </div>
      </section>
    </main>
  )
}
  return (
    <main className="app">
      <header className="header">
        <span className="brand">PaperX</span>
        <button type="button" onClick={() => setPage('home')}>
          Home
        </button>
        <span className="header-label">AI Research Workspace</span>
      </header>

      <section className="intro">
        <p className="eyebrow">YOUR RESEARCH, ORGANIZED</p>
        <h1>Start with a question.</h1>
        <p>Create a research job to begin discovering papers and building your report.</p>
      </section>

      <section className="panel">
        <h2>New research job</h2>
        <form onSubmit={createJob} className="create-form">
          <label htmlFor="topic">Research topic</label>
          <div className="form-row">
            <input
              id="topic"
              value={topic}
              onChange={(event) => setTopic(event.target.value)}
              placeholder="e.g. Solar irradiance forecasting"
              maxLength={500}
              required
            />
            <button disabled={saving} type="submit">
              {saving ? 'Creating…' : 'Create job'}
            </button>
          </div>
        </form>
      </section>

      <section className="jobs-section">
        <div className="section-heading">
          <h2>Research jobs</h2>
          <span>{jobs.length} shown</span>
        </div>

        {error && <p role="alert" className="error">{error}</p>}
        {loading ? (
          <p>Loading research jobs…</p>
        ) : jobs.length === 0 ? (
          <p className="empty">No research jobs yet. Create your first one above.</p>
        ) : (
          <ul className="job-list">
            {jobs.map((job) => (
              <li className="job" key={job.id}>
                <div>
                  <h3>{job.topic}</h3>
                  <small>{job.id}</small>
                </div>
                <span className="status">{job.status}</span>
                <button type="button" onClick={() => loadPapers(job.id)}>
                  View saved papers
                </button>
                <button
                  type="button"
                  disabled={searchingJob === job.id}
                  onClick={() => searchPapers(job.id)}
                >
                  {searchingJob === job.id ? 'Searching…' : 'Find papers'}
                </button>
                {papersByJob[job.id] && (
                  <div className="papers">
                    <h4>Saved papers ({papersByJob[job.id].length})</h4>
                    <button
                        type="button"
                        disabled={
                          !(selectedPapersByJob[job.id] || []).length ||
                          summarizingJob === job.id
                        }
                        onClick={() => generateSummary(job.id)}
                      >
                        {summarizingJob === job.id ? 'Generating summary…' : 'Generate summary'}
                    </button>
                    <button
                      type="button"
                      disabled={
                        !(selectedPapersByJob[job.id] || []).length ||
                        analyzingJob === job.id
                      }
                      onClick={() => analyzeGaps(job.id)}
                    >
                    {analyzingJob === job.id ? 'Analyzing…' : 'Analyze research gaps'}
                    </button>
                    {analysisByJob[job.id] && (
                      <section className="summary">
                        <h4>Research gaps</h4>
                        {analysisByJob[job.id].gaps.length === 0 ? (
                          <p>No gaps identified.</p>
                        ) : (
                          analysisByJob[job.id].gaps.map((gap, index) => (
                            <div key={index}>
                              <strong>{gap.category.replaceAll('_', ' ')}</strong>
                              <p>{gap.description}</p>
                              <p><small>Evidence: {gap.evidence}</small></p>
                              <p>Status: {gap.review_status}</p>
                              <button type="button" onClick={() => reviewGap(job.id, index, 'approved')}>
                                Approve
                              </button>
                              <button type="button" onClick={() => reviewGap(job.id, index, 'rejected')}>
                                Reject
                              </button>
                            </div>
                          ))
                        )}
                      </section>
                    )}
                    {summaryByJob[job.id] && (
                      <section className="summary">
                        <h4>Research summary</h4>
                        <pre>{summaryByJob[job.id].summary}</pre>
                      </section>
                    )}
                    {summaryByJob[job.id] && analysisByJob[job.id] && (
                      <button
                        type="button"
                        disabled={
                          generatingReportJob === job.id ||
                          !analysisByJob[job.id].gaps.some(
                            (gap) => gap.review_status === 'approved',
                          )
                        }
                        onClick={() => generateReport(job.id)}
                      >
                        {generatingReportJob === job.id ? 'Generating report…' : 'Generate report'}
                      </button>
                    )}
                    {reportByJob[job.id] && (
                      <section className="summary printable-report">
                        <h4>Research report</h4>
                        <button type="button" onClick={() => window.print()}>
                          Save report as PDF
                        </button>
                        <pre>{reportByJob[job.id]}</pre>
                      </section>
                    )}
                    {papersByJob[job.id].length === 0 ? (
                      <p>No papers found for this topic.</p>
                    ) : (
                      <ul>
                        {papersByJob[job.id].map((paper) => (
                          <li key={paper.id}>
                            <label className="paper-choice">
                              <input
                                type="checkbox"
                                checked={(selectedPapersByJob[job.id] || []).includes(paper.id)}
                                onChange={() => togglePaper(job.id, paper.id)}
                              />
                              <strong>{paper.title}</strong>
                            </label>                            <span>{paper.source}</span>
                            {paper.paper_url && (
                              <a href={paper.paper_url} target="_blank" rel="noreferrer">
                                View paper
                              </a>
                            )}
                            {paper.abstract && <p>{paper.abstract}</p>}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  )
}

export default App