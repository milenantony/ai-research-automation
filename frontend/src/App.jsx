import { useEffect, useState } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import AccountForm from './AccountForm.jsx'
import './App.css'

const markdownComponents = {
  h1: ({ children }) => <h2>{children}</h2>,
  h2: ({ children }) => (
    <h2 className={children === 'Reviewed research gaps' ? 'reviewed-gaps-heading' : undefined}>{children}</h2>
  ),
  table: ({ children }) => (
    <div className="markdown-table">
      <table>{children}</table>
    </div>
  ),
}

function ResearchMarkdown({ children }) {
  return (
    <div className="report-body">
      <Markdown components={markdownComponents} remarkPlugins={[remarkGfm]} skipHtml>
        {children}
      </Markdown>
    </div>
  )
}

async function fetchJobData(jobId, resource, errorMessage, signal) {
  const response = await fetch(`/research-jobs/${jobId}/${resource}`, { signal })
  if (!response.ok) throw new Error(errorMessage)
  return response.json()
}

const itemsPerPage = 8

async function fetchAllPages(path, errorMessage, signal) {
  const items = []
  const limit = 100

  for (let skip = 0; ; skip += limit) {
    const response = await fetch(`${path}?skip=${skip}&limit=${limit}`, { signal })
    if (!response.ok) throw new Error(errorMessage)
    const page = await response.json()
    items.push(...page)
    if (page.length < limit) return items
  }
}

function ListPagination({ page, count, onChange, label }) {
  const last = Math.ceil(count / itemsPerPage)
  if (last <= 1) return null

  return (
    <nav className="list-pagination" aria-label={label}>
      <button type="button" disabled={page <= 1} onClick={() => onChange(page - 1)}>Previous</button>
      <span aria-live="polite">Page {page} of {last}</span>
      <button type="button" disabled={page >= last} onClick={() => onChange(page + 1)}>Next</button>
    </nav>
  )
}

function pageItems(items, page) {
  const start = (page - 1) * itemsPerPage
  return items.slice(start, start + itemsPerPage)
}

const jobStatusLabels = {
  PENDING: 'Pending',
  RUNNING: 'In progress',
  PARTIALLY_COMPLETED: 'Partially completed',
  COMPLETED: 'Completed',
  FAILED: 'Failed',
}

function App() {
  const [account, setAccount] = useState(null)
  const [sessionLoading, setSessionLoading] = useState(true)
  const [sessionError, setSessionError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    fetch('/auth/session', { signal: controller.signal })
      .then(async (response) => {
        if (response.status === 401) return null
        if (!response.ok) throw new Error('Could not check your session.')
        return response.json()
      })
      .then(setAccount)
      .catch((failure) => {
        if (failure.name !== 'AbortError') setSessionError(failure.message)
      })
      .finally(() => {
        if (!controller.signal.aborted) setSessionLoading(false)
      })
    return () => controller.abort()
  }, [])

  async function signOut() {
    setSessionError('')
    try {
      const response = await fetch('/auth/session', { method: 'DELETE' })
      if (!response.ok) throw new Error('Could not sign out. Please try again.')
      setAccount(null)
      window.location.hash = '#/workspace'
    } catch (failure) {
      setSessionError(failure.message)
    }
  }

  return <WorkspaceApp key={account?.id ?? 'guest'} account={account}
    sessionLoading={sessionLoading} sessionError={sessionError}
    onSignIn={(nextAccount) => {
      setSessionError('')
      setAccount(nextAccount)
    }}
    onSignOut={signOut} />
}

function WorkspaceApp({ account, sessionLoading, sessionError, onSignIn, onSignOut }) {
  const [jobs, setJobs] = useState([])
  const [jobFilter, setJobFilter] = useState('')
  const [jobPage, setJobPage] = useState(1)
  const [paperPage, setPaperPage] = useState(1)
  const visibleJobs = jobs.filter((job) =>
    job.topic.toLowerCase().includes(jobFilter.trim().toLowerCase()),
  )
  const [topic, setTopic] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [papersByJob, setPapersByJob] = useState({})
  const [selectedPapersByJob, setSelectedPapersByJob] = useState({})
  const [summarizingJob, setSummarizingJob] = useState(null)
  const [summaryByJob, setSummaryByJob] = useState({})
  const [searchingJob, setSearchingJob] = useState(null)
  const [emptySearchByJob, setEmptySearchByJob] = useState({})
  const [analyzingJob, setAnalyzingJob] = useState(null)
  const [analysisByJob, setAnalysisByJob] = useState({})
  const [reportByJob, setReportByJob] = useState({})
  const [generatingReportJob, setGeneratingReportJob] = useState(null)
  const [route, setRoute] = useState(() => window.location.hash)
  const [savedJobLoad, setSavedJobLoad] = useState(null)
  const [savedJobRetry, setSavedJobRetry] = useState(0)
  const activeJobId = route.startsWith('#/workspace/jobs/')
    ? route.slice('#/workspace/jobs/'.length)
    : null
  const activeJob = jobs.find((job) => String(job.id) === activeJobId)
  const savedJobId = activeJob?.id
  const loadingSavedJob = savedJobLoad?.jobId !== savedJobId
  const savedJobError = savedJobLoad?.jobId === savedJobId ? savedJobLoad?.error : null

  useEffect(() => {
    if (!savedJobId) return

    const controller = new AbortController()
    const { signal } = controller

    Promise.all([
      fetchAllPages('/research-jobs/' + savedJobId + '/papers', 'Could not load saved papers.', signal),
      fetchJobData(savedJobId, 'summaries', 'Could not load saved summaries.', signal),
      fetchJobData(savedJobId, 'gap-analyses', 'Could not load saved gap analyses.', signal),
      fetchJobData(savedJobId, 'reports/latest', 'Could not load the saved report.', signal),
    ]).then(([papers, summaries, analyses, savedReport]) => {
      if (signal.aborted) return
      setPapersByJob((previous) => ({ ...previous, [savedJobId]: papers }))
      setSummaryByJob((previous) => ({ ...previous, [savedJobId]: summaries[0] ?? null }))
      setAnalysisByJob((previous) => ({ ...previous, [savedJobId]: analyses[0] ?? null }))
      setReportByJob((previous) => ({ ...previous, [savedJobId]: savedReport.report }))
      setSavedJobLoad({ jobId: savedJobId })
    }).catch((error) => {
      if (!signal.aborted) {
        setSavedJobLoad({ jobId: savedJobId, error: error.message })
      }
    })

    return () => controller.abort()
  }, [savedJobId, savedJobRetry])

  useEffect(() => {
    function handleRouteChange() {
      const hash = window.location.hash
      setRoute(hash)
      setPaperPage(1)
      setSavedJobLoad(null)
      if (!hash || hash === '#' || hash.startsWith('#/workspace')) window.scrollTo(0, 0)
    }

    window.addEventListener('hashchange', handleRouteChange)
    return () => window.removeEventListener('hashchange', handleRouteChange)
  }, [])


  async function loadJobs() {
    try {
      setJobs(await fetchAllPages('/research-jobs', 'Could not load research jobs.'))
      setError('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

useEffect(() => {
  if (!account) return
  const controller = new AbortController()

  fetchAllPages('/research-jobs', 'Could not load research jobs.', controller.signal)
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
}, [account])
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
      setJobPage(1)
      await loadJobs()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }
  async function loadLatestSummary(jobId) {
    const summaries = await fetchJobData(jobId, 'summaries', 'Could not load saved summaries.')
    setSummaryByJob((previous) => ({ ...previous, [jobId]: summaries[0] ?? null }))
  }

  async function loadLatestAnalysis(jobId) {
    const analyses = await fetchJobData(jobId, 'gap-analyses', 'Could not load saved gap analyses.')
    setAnalysisByJob((previous) => ({ ...previous, [jobId]: analyses[0] ?? null }))
  }

  function jobStatusLabel(job) {
    const status = searchingJob === job.id && job.status === 'PENDING' ? 'RUNNING' : job.status
    return jobStatusLabels[status] ?? status
  }

  function setJobStatus(jobId, status) {
    setJobs((previous) => previous.map((job) =>
      job.id === jobId ? { ...job, status } : job
    ))
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
      setJobStatus(jobId, 'COMPLETED')
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
  async function searchPapers(jobId) {
  setSearchingJob(jobId)
  setError('')
  setEmptySearchByJob((previous) => ({ ...previous, [jobId]: false }))

  try {
    const response = await fetch(`/research-jobs/${jobId}/papers:search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ max_results: 5, refine_query: false }),
    })

    const jobResponse = await fetch('/research-jobs/' + jobId).catch(() => null)
    if (jobResponse?.ok) {
      const updatedJob = await jobResponse.json()
      setJobStatus(jobId, updatedJob.status)
    }

    if (!response.ok) {
      const result = await response.json().catch(() => ({}))
      throw new Error(result.detail || 'Paper search failed.')
    }

    const results = await response.json()
    const papers = await fetchAllPages('/research-jobs/' + jobId + '/papers', 'Could not load the saved papers.')
    setEmptySearchByJob((previous) => ({ ...previous, [jobId]: results.length === 0 }))
    setPapersByJob((previous) => ({ ...previous, [jobId]: papers }))
  } catch (err) {
    setError(err.message)
  } finally {
    setSearchingJob(null)
  }
}

if (!route.startsWith('#/workspace')) {
  return (
    <main className="home" id="home">
      <header className="home-nav">
        <span className="brand"><span className="brand-mark" aria-hidden="true">X</span>PaperX</span>
        <nav aria-label="Homepage">
          <a href="#workflow">How it works</a>
          <a href="#features">Features</a>
        </nav>
        <a className="home-action home-action-secondary" href="#/workspace">Open workspace</a>
      </header>

      <section className="home-hero">
        <div>
          <p className="eyebrow">AI research workspace</p>
          <h1>From research question to clearer insight.</h1>
          <p>Find academic papers, summarize selected evidence, review potential gaps, and export a cited report.</p>
          <div className="home-hero-actions">
            <a className="home-action" href="#/workspace">Start researching <span aria-hidden="true">↗</span></a>
            <a href="#workflow">See how it works</a>
          </div>
        </div>
        <img className="home-image" src={import.meta.env.BASE_URL + 'paperx-research-desk.webp'}
          alt="Research papers with charts and a silver pen on a light desk" width="1200" height="900" fetchPriority="high" />
      </section>

      <section className="home-steps" id="workflow">
        <div className="home-section-inner">
          <h2>How it works</h2>
          <ol className="step-grid">
            <li><h3>Create a research job</h3><p>Enter a focused question or topic in your workspace.</p></li>
            <li id="discover-papers"><h3>Discover and select papers</h3><p>Search for related papers, read their abstracts, and choose the sources to include.</p></li>
            <li id="review-gaps"><h3>Summarize and review</h3><p>Generate a summary, examine evidence for potential gaps, and record your review.</p></li>
            <li id="export-report"><h3>Export your report</h3><p>Generate a cited report from reviewed evidence and use Save as PDF to keep a copy.</p></li>
          </ol>
        </div>
      </section>

      <section className="home-features" id="features">
        <img className="home-image" src={import.meta.env.BASE_URL + 'paperx-research-notes.webp'}
          alt="Open research notebook beside a stack of academic papers" width="1200" height="900" loading="lazy" />
        <div>
          <h2>Built for literature review</h2>
          <dl className="home-feature-list">
            <div><dt>Searchable research library</dt><dd>Filter saved topics and reopen a dedicated workspace for each job.</dd></div>
            <div><dt>Evidence you can review</dt><dd>Read abstracts, select sources, and approve or reject proposed research gaps.</dd></div>
            <div><dt>Reports ready to print</dt><dd>Export formatted reports with tables, references, and a scope statement.</dd></div>
          </dl>
          <details className="home-faq">
            <summary>What do AI summaries use?</summary>
            <p>PaperX summarizes the abstracts of the papers you select. Use the original papers to verify findings before citing them.</p>
          </details>
        </div>
      </section>

      <footer className="home-footer">
        <div className="home-section-inner">
          <div className="home-footer-grid">
            <div>
              <a className="brand" href="#home"><span className="brand-mark" aria-hidden="true">X</span>PaperX</a>
              <p>A workspace for academic paper discovery, evidence review, and cited reports.</p>
            </div>
            <nav aria-labelledby="footer-explore">
              <h2 id="footer-explore">Explore PaperX</h2>
              <ul>
                <li><a href="#/workspace">Research workspace</a></li>
                <li><a href="#workflow">How it works</a></li>
                <li><a href="#features">Features and FAQ</a></li>
              </ul>
            </nav>
            <nav aria-labelledby="footer-guide">
              <h2 id="footer-guide">Research guide</h2>
              <ul>
                <li><a href="#discover-papers">Find and select papers</a></li>
                <li><a href="#review-gaps">Review research gaps</a></li>
                <li><a href="#export-report">Export a report</a></li>
              </ul>
            </nav>
            <div>
              <h2>Saving as PDF</h2>
              <p>In a generated report, select <strong>Save report as PDF</strong>, then choose <strong>Save as PDF</strong> in your browser’s print dialog.</p>
            </div>
          </div>
          <div className="home-footer-bottom">
            <p>Reports use selected paper abstracts. Check the original sources before citing findings.</p>
            <a href="#home">Back to top <span aria-hidden="true">↑</span></a>
          </div>
        </div>
      </footer>
    </main>
  )
}
  if (!account) {
    return (
      <main className="app">
        <header className="header">
          <span className="brand"><span className="brand-mark" aria-hidden="true">X</span>PaperX</span>
          <a className="workspace-home-link" href="#">Home</a>
        </header>
        {sessionError && <p role="alert">{sessionError}</p>}
        {sessionLoading ? <p role="status">Checking your session…</p> : <AccountForm onSignIn={onSignIn} />}
      </main>
    )
  }

  return (
    <main className="app">
      <header className="header">
        <span className="brand"><span className="brand-mark" aria-hidden="true">X</span>PaperX</span>
        <a className="workspace-home-link" href="#">Home</a>
        <button type="button" onClick={onSignOut}>Sign out</button>
      </header>
      {sessionError && <p role="alert">{sessionError}</p>}

      {!activeJobId && <><section className="intro">
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
      </section></>}

      <section className="jobs-section">
        {activeJobId ? (
          <a className="library-back" href="#/workspace"><span aria-hidden="true">←</span> Research library</a>
        ) : (
          <div className="section-heading">
            <h2>Research jobs</h2>
            <span>{jobs.length} saved</span>
          </div>
        )}

        {error && <p role="alert" className="error">{error}</p>}
        {loading ? (
          <p>Loading research jobs…</p>
        ) : activeJobId && !activeJob ? (
          !error && <p className="empty">This research job could not be found.</p>
        ) : jobs.length === 0 ? (
          <p className="empty">No research jobs yet. Create your first one above.</p>
        ) : (
          <div className="workspace-layout workspace-page">
            {!activeJobId && <nav className="workspace-sidebar" aria-label="Research jobs">
              <div className="library-filter">
                <label htmlFor="job-filter">Find a research job</label>
                <input
                  id="job-filter"
                  type="search"
                  value={jobFilter}
                  onChange={(event) => {
                    setJobFilter(event.target.value)
                    setJobPage(1)
                  }}
                  placeholder="Filter by topic"
                />
              </div>
              <ul className="library-list">
                {pageItems(visibleJobs, jobPage).map((job) => (
                  <li key={job.id}>
                    <a href={`#/workspace/jobs/${job.id}`} title={job.topic}>
                      <span className="library-entry-status">{jobStatusLabel(job)}</span>
                      <span className="library-entry-title">{job.topic}</span>
                      <span className="library-entry-arrow" aria-hidden="true">↗</span>
                    </a>
                  </li>
                ))}
              </ul>
              <ListPagination page={jobPage} count={visibleJobs.length} onChange={setJobPage} label="Research jobs pages" />
              {visibleJobs.length === 0 && <p className="library-empty" role="status">No matching jobs.</p>}
            </nav>}
            {activeJob && <ul className="job-list">
              {[activeJob].map((job) => (
              <li className="job" key={job.id}>
                <header className="job-masthead">
                  <span className="status">{jobStatusLabel(job)}</span>
                  <h3>{job.topic}</h3>
                </header>
                <div className="job-actions">
                  <button
                    type="button"
                    disabled={loadingSavedJob || searchingJob === job.id}
                    onClick={() => searchPapers(job.id)}
                  >
                    {searchingJob === job.id ? 'Searching…' : 'Find papers'}
                  </button>
                </div>
                <div role="status">
                  {emptySearchByJob[job.id] && 'This search returned no papers. Try a more specific research topic.'}
                </div>
                {loadingSavedJob && <p className="job-load-status" role="status">Loading saved research…</p>}
                {savedJobError && (
                  <div className="job-load-status">
                    <p role="alert">{savedJobError}</p>
                    <button type="button" onClick={() => {
                      setSavedJobLoad(null)
                      setSavedJobRetry((attempt) => attempt + 1)
                    }}>
                      Retry loading saved research
                    </button>
                  </div>
                )}
                {!loadingSavedJob && papersByJob[job.id] && (
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
                            <div className="gap-review" key={index}>
                              <strong>{gap.category.replaceAll('_', ' ')}</strong>
                              <p>{gap.description}</p>
                              <p className="gap-evidence"><strong>Evidence</strong> {gap.evidence}</p>
                              {gap.cited_insights?.length > 0 && (
                                <ul className="gap-citations" aria-label="Cited insights">
                                  {gap.cited_insights.map((insight, index) => (
                                    <li key={`${insight.paper_id}-${index}`}>
                                      <strong>{insight.title}</strong>
                                      <p>{insight.claim}</p>
                                      <blockquote>{insight.evidence_quote}</blockquote>
                                    </li>
                                  ))}
                                </ul>
                              )}
                              <p className="gap-review-status">Status: {gap.review_status}</p>
                              <button type="button" onClick={() => reviewGap(job.id, index, 'approved')}>
                                Approve
                              </button>
                              <button className="gap-reject" type="button" onClick={() => reviewGap(job.id, index, 'rejected')}>
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
                        <ResearchMarkdown>{summaryByJob[job.id].summary}</ResearchMarkdown>
                      </section>
                    )}
                    {summaryByJob[job.id] && analysisByJob[job.id] && (
                      <button className="report-generate"
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
                        <ResearchMarkdown>
                          {reportByJob[job.id].replace(/\r?\n(?=\[\d+\] )/g, '\n\n')}
                        </ResearchMarkdown>
                      </section>
                    )}
                    {papersByJob[job.id].length === 0 ? (
                      !emptySearchByJob[job.id] && searchingJob !== job.id && <p>No papers saved yet.</p>
                    ) : (
                      <>
                      <ul>
                        {pageItems(papersByJob[job.id], Math.min(paperPage, Math.ceil(papersByJob[job.id].length / itemsPerPage))).map((paper) => (
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
                            {paper.abstract && <details className="paper-abstract"><summary>Read abstract</summary><p>{paper.abstract}</p></details>}
                          </li>
                        ))}
                      </ul>
                      <ListPagination page={Math.min(paperPage, Math.ceil(papersByJob[job.id].length / itemsPerPage))} count={papersByJob[job.id].length} onChange={setPaperPage} label="Saved papers pages" />
                      </>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>}
        </div>

        )}
      </section>
    </main>
  )
}

export default App