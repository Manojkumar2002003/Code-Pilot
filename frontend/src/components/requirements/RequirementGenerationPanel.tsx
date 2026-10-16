import { useCallback, useEffect, useState } from 'react'
import LoadingState from '../common/LoadingState'
import {
  ApiError,
  type ClarificationAnswerInput,
  type ClarificationQuestion,
  type ClarificationSession,
  type Project,
  type RefinementExecutionResult,
  type RequirementDiffSummary,
  type RequirementGenerationResponse,
  type RequirementGenerationResult,
} from '../../services/api'
import {
  getClarificationSession,
  getLatestRequirementGeneration,
  startRequirementGeneration,
  submitClarificationAnswers,
  triggerRequirementRefinement,
} from '../../services/requirementGenerationService'

interface RequirementGenerationPanelProps {
  project: Project
  onSwitchToApproved?: () => void
}

type ResultTab = 'all' | 'functional' | 'non_functional' | 'user_stories' | 'business_rules' | 'assumptions_deps' | 'diff'

export default function RequirementGenerationPanel({
  project,
}: RequirementGenerationPanelProps) {
  // Generation state
  const [initialLoading, setInitialLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [refining, setRefining] = useState(false)
  const [savingAnswers, setSavingAnswers] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // Input state
  const [instructions, setInstructions] = useState('')

  // Data state
  const [generationResponse, setGenerationResponse] = useState<RequirementGenerationResponse | null>(null)
  const [session, setSession] = useState<ClarificationSession | null>(null)
  const [diffSummary, setDiffSummary] = useState<RequirementDiffSummary | null>(null)

  // Local answer inputs keyed by question_id
  const [answersMap, setAnswersMap] = useState<Record<string, { answer: string; selected_options: string[] }>>({})

  // Category view filter
  const [activeTab, setActiveTab] = useState<ResultTab>('all')

  // Check if project description has sufficient substance (>= 10 chars)
  const projectDescription = (project.description ?? '').trim()
  const isDescriptionSufficient = projectDescription.length >= 10

  // 1. Load latest generation on mount or project change
  const loadLatest = useCallback(async () => {
    setInitialLoading(true)
    setError(null)
    try {
      const latest = await getLatestRequirementGeneration(project.id)
      setGenerationResponse(latest)
      if (latest.session_id) {
        try {
          const sess = await getClarificationSession(project.id, latest.session_id)
          setSession(sess)
          // Pre-populate answers from session
          const initialMap: Record<string, { answer: string; selected_options: string[] }> = {}
          for (const a of sess.answers ?? []) {
            initialMap[a.question_id] = {
              answer: a.answer,
              selected_options: a.selected_options ?? [],
            }
          }
          setAnswersMap(initialMap)
        } catch {
          // If session fetch fails, still show the generation result
        }
      }
    } catch (caughtError) {
      if (caughtError instanceof ApiError && caughtError.status === 404) {
        // No generation yet - this is a normal initial state
        setGenerationResponse(null)
        setSession(null)
      } else if (caughtError instanceof ApiError) {
        setError(caughtError.message)
      } else {
        setError('Unable to check for existing requirement generations.')
      }
    } finally {
      setInitialLoading(false)
    }
  }, [project.id])

  useEffect(() => {
    void loadLatest()
  }, [loadLatest])

  // 2. Start initial generation
  const handleStartGeneration = async () => {
    if (generating || !isDescriptionSufficient) return

    setGenerating(true)
    setError(null)
    setSuccessMessage(null)

    try {
      const response = await startRequirementGeneration(project.id, {
        instructions: instructions.trim() || null,
      })
      setGenerationResponse(response)
      if (response.clarification_session) {
        setSession(response.clarification_session)
        const initialMap: Record<string, { answer: string; selected_options: string[] }> = {}
        for (const a of response.clarification_session.answers ?? []) {
          initialMap[a.question_id] = {
            answer: a.answer,
            selected_options: a.selected_options ?? [],
          }
        }
        setAnswersMap(initialMap)
      }
      setDiffSummary(null)
      setSuccessMessage('AI requirements specification generated successfully.')
    } catch (caughtError) {
      if (caughtError instanceof ApiError) {
        setError(caughtError.message)
      } else {
        setError('An unexpected error occurred while generating requirements.')
      }
    } finally {
      setGenerating(false)
    }
  }

  // 3. Question answer updates
  const handleAnswerTextChange = (questionId: string, text: string) => {
    setAnswersMap((prev) => ({
      ...prev,
      [questionId]: {
        answer: text,
        selected_options: prev[questionId]?.selected_options ?? [],
      },
    }))
  }

  const handleSelectOption = (questionId: string, option: string) => {
    setAnswersMap((prev) => {
      const current = prev[questionId] ?? { answer: '', selected_options: [] }
      const isAlreadySelected = current.selected_options.includes(option)
      const nextOptions = isAlreadySelected
        ? current.selected_options.filter((o) => o !== option)
        : [...current.selected_options, option]

      // If text is empty or matched previous option, update text as well
      let nextAnswer = current.answer
      if (!current.answer.trim() || current.selected_options.includes(current.answer.trim())) {
        nextAnswer = option
      }

      return {
        ...prev,
        [questionId]: {
          answer: nextAnswer,
          selected_options: nextOptions,
        },
      }
    })
  }

  // 4. Save clarification answers
  const handleSaveAnswers = async () => {
    if (!session || savingAnswers) return

    const answersPayload: ClarificationAnswerInput[] = []
    for (const [qId, data] of Object.entries(answersMap)) {
      if (data.answer.trim()) {
        answersPayload.push({
          question_id: qId,
          answer: data.answer.trim(),
          selected_options: data.selected_options,
        })
      }
    }

    if (answersPayload.length === 0) {
      setError('Please answer at least one question before saving.')
      return
    }

    setSavingAnswers(true)
    setError(null)
    setSuccessMessage(null)

    try {
      const updatedSession = await submitClarificationAnswers(project.id, session.id, answersPayload)
      setSession(updatedSession)
      setSuccessMessage('Clarification answers saved successfully.')
    } catch (caughtError) {
      if (caughtError instanceof ApiError) {
        setError(caughtError.message)
      } else {
        setError('Failed to save clarification answers.')
      }
    } finally {
      setSavingAnswers(false)
    }
  }

  // 5. Trigger Refinement
  const handleTriggerRefinement = async () => {
    if (!session || refining) return

    // Collect answers
    const answersPayload: ClarificationAnswerInput[] = []
    for (const [qId, data] of Object.entries(answersMap)) {
      if (data.answer.trim()) {
        answersPayload.push({
          question_id: qId,
          answer: data.answer.trim(),
          selected_options: data.selected_options,
        })
      }
    }

    // Client-side check for required questions
    const unansweredRequired = (session.questions ?? []).filter(
      (q) => q.is_required && !answersMap[q.id]?.answer?.trim(),
    )
    if (unansweredRequired.length > 0) {
      setError(
        `Please answer required question(s): ${unansweredRequired.map((q) => q.id).join(', ')} before refining.`,
      )
      return
    }

    setRefining(true)
    setError(null)
    setSuccessMessage(null)

    try {
      const result: RefinementExecutionResult = await triggerRequirementRefinement(
        project.id,
        session.id,
        {
          instructions: instructions.trim() || null,
          answers: answersPayload.length > 0 ? answersPayload : null,
        },
      )

      // Update states from refinement result
      setSession(result.session)
      setDiffSummary(result.diff_summary ?? null)

      // Update generation response to refined specification
      setGenerationResponse({
        generation_id: result.latest_generation.generation_id,
        project_id: project.id,
        session_id: result.session.id,
        status: result.session.status,
        revision_number: result.revision.revision_number,
        summary: result.latest_generation.summary,
        result: result.latest_generation,
        clarification_session: result.session,
        execution_metadata: result.execution_metadata,
        created_at: result.revision.created_at,
      })

      setSuccessMessage(
        `Specification successfully refined to Revision ${result.revision.revision_number}.`,
      )
    } catch (caughtError) {
      if (caughtError instanceof ApiError) {
        setError(caughtError.message)
      } else {
        setError('Refinement failed. Your submitted answers have been preserved.')
      }
    } finally {
      setRefining(false)
    }
  }

  if (initialLoading) {
    return <LoadingState message="Loading requirement generator..." />
  }

  const result: RequirementGenerationResult | null = generationResponse?.result ?? null
  const questions: ClarificationQuestion[] = session?.questions ?? result?.clarification_questions ?? []
  const hasUnansweredRequired = questions.some(
    (q) => q.is_required && !answersMap[q.id]?.answer?.trim(),
  )

  return (
    <div className="ai-generation-panel">
      {/* 1. Project Context & Generator Launch Card */}
      <section className="generation-context-card" aria-label="Project context and AI generator">
        <div className="context-card-header">
          <div className="context-badge">
            <span className="sparkle-icon">✨</span> AI Requirement Analyst
          </div>
          <h2>AI Software Requirements Generator</h2>
          <p className="context-description">
            Transform <strong>{project.name}</strong>'s description into a structured software requirements
            specification, complete with user stories, acceptance criteria, non-functional requirements, and clarification questions.
          </p>
        </div>

        <div className="context-details">
          <div className="context-row">
            <span className="context-label">Project Description:</span>
            <span className="context-value">
              {projectDescription || <em className="text-muted">No description provided yet.</em>}
            </span>
          </div>

          {!isDescriptionSufficient ? (
            <div className="state-panel error-state context-warning" role="alert">
              <strong>Insufficient project description:</strong> The AI Requirement Analyst requires a substantive description (at least 10 characters) to analyze domain requirements accurately. Please update your project description first.
            </div>
          ) : null}

          {isDescriptionSufficient && !generationResponse ? (
            <div className="generation-form-row">
              <label htmlFor="generation-instructions" className="field-label">
                Focus Guidance or Domain Rules (Optional)
              </label>
              <textarea
                id="generation-instructions"
                className="generation-instructions-input"
                rows={2}
                placeholder="e.g., Focus on security compliance, PostgreSQL database backend, and mobile responsive design..."
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                disabled={generating}
              />

              <div className="generation-action-bar">
                <button
                  type="button"
                  className="primary-button ai-generate-button"
                  onClick={handleStartGeneration}
                  disabled={generating || !isDescriptionSufficient}
                >
                  {generating ? (
                    <>
                      <span className="button-spinner" /> Analyzing & Generating...
                    </>
                  ) : (
                    '✨ Generate Requirements with AI'
                  )}
                </button>
              </div>
            </div>
          ) : null}
        </div>
      </section>

      {/* 2. Global Feedback & Error Banners */}
      {error ? (
        <div className="form-error global-error-banner" role="alert">
          <span className="error-icon">⚠️</span>
          <span>{error}</span>
          <button
            type="button"
            className="error-dismiss-button"
            onClick={() => setError(null)}
            aria-label="Dismiss error"
          >
            ×
          </button>
        </div>
      ) : null}

      {successMessage ? (
        <div className="success-banner" role="status">
          <span className="success-icon">✓</span>
          <span>{successMessage}</span>
          <button
            type="button"
            className="error-dismiss-button"
            onClick={() => setSuccessMessage(null)}
            aria-label="Dismiss message"
          >
            ×
          </button>
        </div>
      ) : null}

      {/* 3. Generating in-progress indicator */}
      {generating ? (
        <div className="generation-loading-panel">
          <LoadingState message="The Requirement Analyst is analyzing your project context and drafting specifications..." />
        </div>
      ) : null}

      {/* 4. Clarification Questions Section */}
      {generationResponse && questions.length > 0 ? (
        <section className="clarification-section" aria-label="Clarification questions">
          <div className="clarification-header">
            <div>
              <div className="section-pill">Interactive Clarification</div>
              <h3>Clarification Questions from Requirement Analyst</h3>
              <p className="clarification-subtitle">
                The agent identified architectural or business ambiguities. Answering these questions allows the analyst to refine the specification.
              </p>
            </div>

            <div className="clarification-status-badge">
              {questions.filter((q) => answersMap[q.id]?.answer?.trim()).length} of {questions.length} Answered
            </div>
          </div>

          <div className="clarification-questions-list">
            {questions.map((question) => {
              const currentAns = answersMap[question.id]?.answer ?? ''
              const currentSelected = answersMap[question.id]?.selected_options ?? []
              const isAnswered = Boolean(currentAns.trim())

              return (
                <div
                  key={question.id}
                  className={`clarification-card ${isAnswered ? 'card-answered' : 'card-pending'}`}
                  aria-label={`Question ${question.id}`}
                >
                  <div className="clarification-card-header">
                    <div className="question-tags">
                      <span className="question-id-badge">{question.id}</span>
                      <span className={`requirement-badge ${question.is_required ? 'badge-required' : 'badge-optional'}`}>
                        {question.is_required ? 'Required' : 'Optional'}
                      </span>
                      {question.category ? (
                        <span className="category-tag">{question.category}</span>
                      ) : null}
                    </div>

                    <div className="answer-status-indicator">
                      {isAnswered ? (
                        <span className="status-answered">✓ Answered</span>
                      ) : (
                        <span className="status-pending">Pending</span>
                      )}
                    </div>
                  </div>

                  <p className="question-text">{question.question}</p>

                  {question.rationale ? (
                    <div className="question-rationale">
                      <strong>Why this matters:</strong> {question.rationale}
                    </div>
                  ) : null}

                  {question.suggested_options && question.suggested_options.length > 0 ? (
                    <div className="suggested-options-group">
                      <span className="suggested-options-label">Suggested Options:</span>
                      <div className="suggested-options-list">
                        {question.suggested_options.map((option) => {
                          const isOptionSelected = currentSelected.includes(option)
                          return (
                            <button
                              type="button"
                              key={option}
                              className={`option-chip ${isOptionSelected ? 'option-chip-selected' : ''}`}
                              onClick={() => handleSelectOption(question.id, option)}
                              disabled={refining || savingAnswers}
                            >
                              {isOptionSelected ? '✓ ' : '+ '}
                              {option}
                            </button>
                          )
                        })}
                      </div>
                    </div>
                  ) : null}

                  <div className="question-input-group">
                    <label htmlFor={`answer-${question.id}`} className="field-label visually-hidden">
                      Your response to {question.id}
                    </label>
                    <textarea
                      id={`answer-${question.id}`}
                      className="clarification-textarea"
                      rows={2}
                      placeholder={
                        question.is_required
                          ? 'Enter your answer (Required)...'
                          : 'Enter your answer or select a suggested option...'
                      }
                      value={currentAns}
                      onChange={(e) => handleAnswerTextChange(question.id, e.target.value)}
                      disabled={refining || savingAnswers}
                    />
                  </div>
                </div>
              )
            })}
          </div>

          <div className="clarification-actions-bar">
            <button
              type="button"
              className="secondary-button"
              onClick={handleSaveAnswers}
              disabled={savingAnswers || refining}
            >
              {savingAnswers ? 'Saving Answers...' : 'Save Answers'}
            </button>

            <button
              type="button"
              className="primary-button refine-button"
              onClick={handleTriggerRefinement}
              disabled={refining || savingAnswers || hasUnansweredRequired}
              title={
                hasUnansweredRequired
                  ? 'All required questions must be answered before refining.'
                  : 'Refine specification with submitted answers'
              }
            >
              {refining ? (
                <>
                  <span className="button-spinner" /> Refining Specification...
                </>
              ) : (
                '✨ Refine Specification'
              )}
            </button>
          </div>
        </section>
      ) : null}

      {/* 5. Generation Results Section */}
      {result ? (
        <section className="proposals-results-section" aria-label="Generated software requirement specification">
          {/* Human Review Boundary Warning */}
          <div className="proposals-boundary-banner" role="status">
            <div className="boundary-badge">Awaiting Human Review</div>
            <p>
              The items below are <strong>AI-generated proposals</strong> for <strong>Revision {generationResponse?.revision_number ?? 1}</strong>. They are maintained separately and will not be added to your approved requirements until formally accepted.
            </p>
          </div>

          {/* Results Header with Telemetry */}
          <div className="results-header-card">
            <div className="results-header-top">
              <div>
                <h2>Generated Requirements Specification</h2>
                <span className="revision-pill">
                  Revision {generationResponse?.revision_number ?? 1}
                  {session?.status ? ` • Status: ${session.status}` : ''}
                </span>
              </div>

              {result.execution_metadata ? (
                <div className="telemetry-pill">
                  <span>🤖 {result.execution_metadata.final_provider ?? 'Cloud LLM'}</span>
                  {result.execution_metadata.duration_seconds ? (
                    <span>⏱️ {result.execution_metadata.duration_seconds}s</span>
                  ) : null}
                </div>
              ) : null}
            </div>

            <div className="executive-summary">
              <h3>Executive Summary</h3>
              <p>{result.summary}</p>
            </div>
          </div>

          {/* Category Navigation Tabs */}
          <nav className="proposal-category-tabs" aria-label="Requirement categories">
            <button
              type="button"
              className={`category-tab ${activeTab === 'all' ? 'active' : ''}`}
              onClick={() => setActiveTab('all')}
            >
              All Proposals
            </button>
            <button
              type="button"
              className={`category-tab ${activeTab === 'functional' ? 'active' : ''}`}
              onClick={() => setActiveTab('functional')}
            >
              Functional ({result.functional_requirements.length})
            </button>
            <button
              type="button"
              className={`category-tab ${activeTab === 'non_functional' ? 'active' : ''}`}
              onClick={() => setActiveTab('non_functional')}
            >
              Non-Functional ({result.non_functional_requirements.length})
            </button>
            <button
              type="button"
              className={`category-tab ${activeTab === 'user_stories' ? 'active' : ''}`}
              onClick={() => setActiveTab('user_stories')}
            >
              User Stories ({result.user_stories?.length ?? 0})
            </button>
            <button
              type="button"
              className={`category-tab ${activeTab === 'business_rules' ? 'active' : ''}`}
              onClick={() => setActiveTab('business_rules')}
            >
              Business Rules ({result.business_rules?.length ?? 0})
            </button>
            <button
              type="button"
              className={`category-tab ${activeTab === 'assumptions_deps' ? 'active' : ''}`}
              onClick={() => setActiveTab('assumptions_deps')}
            >
              Assumptions & Deps ({(result.assumptions?.length ?? 0) + (result.dependencies?.length ?? 0)})
            </button>
            {diffSummary ? (
              <button
                type="button"
                className={`category-tab diff-tab ${activeTab === 'diff' ? 'active' : ''}`}
                onClick={() => setActiveTab('diff')}
              >
                Revision Diff ({diffSummary.new_requirements.length + diffSummary.changed_requirements.length})
              </button>
            ) : null}
          </nav>

          {/* Tab 1: Functional Requirements */}
          {(activeTab === 'all' || activeTab === 'functional') && (
            <div className="proposal-group">
              <h3>Functional Requirements</h3>
              {result.functional_requirements.length === 0 ? (
                <p className="empty-category-text">No functional requirements generated.</p>
              ) : (
                <div className="proposals-grid">
                  {result.functional_requirements.map((fr) => (
                    <article key={fr.id} className="proposal-card" aria-label={`Functional requirement ${fr.id}`}>
                      <div className="proposal-card-header">
                        <span className="proposal-id-badge">{fr.id}</span>
                        <h4>{fr.title}</h4>
                      </div>
                      <p className="proposal-description">{fr.description}</p>

                      <div className="proposal-section">
                        <strong>Expected Behavior:</strong>
                        <p>{fr.expected_behavior}</p>
                      </div>

                      {fr.acceptance_criteria && fr.acceptance_criteria.length > 0 ? (
                        <div className="acceptance-criteria-block">
                          <strong>Acceptance Criteria:</strong>
                          <ul>
                            {fr.acceptance_criteria.map((ac, idx) => (
                              <li key={idx}>{ac}</li>
                            ))}
                          </ul>
                        </div>
                      ) : null}
                    </article>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Tab 2: Non-Functional Requirements */}
          {(activeTab === 'all' || activeTab === 'non_functional') && (
            <div className="proposal-group">
              <h3>Non-Functional Requirements</h3>
              {result.non_functional_requirements.length === 0 ? (
                <p className="empty-category-text">No non-functional requirements generated.</p>
              ) : (
                <div className="proposals-grid">
                  {result.non_functional_requirements.map((nfr) => (
                    <article key={nfr.id} className="proposal-card" aria-label={`Non-functional requirement ${nfr.id}`}>
                      <div className="proposal-card-header">
                        <span className="proposal-id-badge">{nfr.id}</span>
                        <h4>{nfr.title}</h4>
                        <span className="nfr-category-tag">{nfr.category}</span>
                      </div>
                      <p className="proposal-description">{nfr.description}</p>
                      {nfr.target_metric ? (
                        <div className="target-metric-pill">
                          <strong>Target Metric:</strong> {nfr.target_metric}
                        </div>
                      ) : null}
                    </article>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Tab 3: User Stories */}
          {(activeTab === 'all' || activeTab === 'user_stories') && (
            <div className="proposal-group">
              <h3>User Stories</h3>
              {(result.user_stories ?? []).length === 0 ? (
                <p className="empty-category-text">No user stories in this specification.</p>
              ) : (
                <div className="proposals-grid">
                  {(result.user_stories ?? []).map((us) => (
                    <article key={us.id} className="proposal-card user-story-card" aria-label={`User story ${us.id}`}>
                      <div className="proposal-card-header">
                        <span className="proposal-id-badge">{us.id}</span>
                        <h4>{us.title}</h4>
                      </div>
                      <div className="story-statement">
                        <p><strong>As a</strong> {us.as_a}</p>
                        <p><strong>I want</strong> {us.i_want}</p>
                        <p><strong>So that</strong> {us.so_that}</p>
                      </div>
                      {us.acceptance_criteria && us.acceptance_criteria.length > 0 ? (
                        <div className="acceptance-criteria-block">
                          <strong>Acceptance Criteria:</strong>
                          <ul>
                            {us.acceptance_criteria.map((ac, idx) => (
                              <li key={idx}>{ac}</li>
                            ))}
                          </ul>
                        </div>
                      ) : null}
                    </article>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Tab 4: Business Rules */}
          {(activeTab === 'all' || activeTab === 'business_rules') && (
            <div className="proposal-group">
              <h3>Business Rules</h3>
              {(result.business_rules ?? []).length === 0 ? (
                <p className="empty-category-text">No business rules identified.</p>
              ) : (
                <div className="proposals-grid">
                  {(result.business_rules ?? []).map((br) => (
                    <article key={br.id} className="proposal-card" aria-label={`Business rule ${br.id}`}>
                      <div className="proposal-card-header">
                        <span className="proposal-id-badge">{br.id}</span>
                        <h4>{br.title}</h4>
                        {br.provenance ? (
                          <span className="provenance-tag">{br.provenance}</span>
                        ) : null}
                      </div>
                      <p className="proposal-description"><strong>Rule:</strong> {br.rule_statement}</p>
                      {br.rationale ? (
                        <p className="rule-rationale"><strong>Rationale:</strong> {br.rationale}</p>
                      ) : null}
                    </article>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Tab 5: Assumptions & Dependencies */}
          {(activeTab === 'all' || activeTab === 'assumptions_deps') && (
            <div className="proposal-group">
              <h3>Assumptions & Dependencies</h3>
              <div className="assumptions-dependencies-grid">
                <div className="subgroup">
                  <h4>Assumptions</h4>
                  {(result.assumptions ?? []).length === 0 ? (
                    <p className="empty-category-text">No explicit assumptions.</p>
                  ) : (
                    <ul>
                      {(result.assumptions ?? []).map((asm) => (
                        <li key={asm.id} className="assumption-item">
                          <span className="bullet-id">{asm.id}:</span> {asm.description}
                          {asm.impact_if_invalid ? (
                            <div className="assumption-impact"><em>Impact if invalid:</em> {asm.impact_if_invalid}</div>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                <div className="subgroup">
                  <h4>Dependencies</h4>
                  {(result.dependencies ?? []).length === 0 ? (
                    <p className="empty-category-text">No external dependencies specified.</p>
                  ) : (
                    <ul>
                      {(result.dependencies ?? []).map((dep) => (
                        <li key={dep.id} className="dependency-item">
                          <span className="bullet-id">{dep.id}:</span> <strong>{dep.dependency_name}</strong> ({dep.dependency_type})
                          {dep.description ? <p>{dep.description}</p> : null}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Tab 6: Revision Diff */}
          {diffSummary && (activeTab === 'all' || activeTab === 'diff') && (
            <div className="proposal-group diff-group">
              <h3>Revision Changes</h3>
              <div className="diff-stats-bar">
                <span className="diff-stat-pill new">+{diffSummary.new_requirements.length} New</span>
                <span className="diff-stat-pill changed">~{diffSummary.changed_requirements.length} Changed</span>
                <span className="diff-stat-pill retained">={diffSummary.retained_requirements.length} Retained</span>
                <span className="diff-stat-pill removed">-{diffSummary.removed_requirements.length} Removed</span>
              </div>

              <div className="diff-items-list">
                {diffSummary.diff_items.map((item) => (
                  <div key={item.id} className={`diff-item-row diff-${item.change_type}`}>
                    <span className={`diff-type-badge ${item.change_type}`}>{item.change_type.toUpperCase()}</span>
                    <strong>{item.id}: {item.title}</strong>
                    <span className="diff-details">{item.details}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Restart / Re-generate Action */}
          <div className="re-generate-bar">
            <button
              type="button"
              className="secondary-button"
              onClick={() => {
                setGenerationResponse(null)
                setSession(null)
                setDiffSummary(null)
                setInstructions('')
              }}
            >
              🔄 Start New Generation Attempt
            </button>
          </div>
        </section>
      ) : null}
    </div>
  )
}
