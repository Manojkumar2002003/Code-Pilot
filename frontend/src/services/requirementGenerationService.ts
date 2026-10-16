import { request } from './api'
import type {
  ClarificationAnswerInput,
  ClarificationQuestion,
  ClarificationSession,
  GenerationRevision,
  RefinementExecutionResult,
  RefinementTriggerRequest,
  RequirementGenerationResponse,
  RequirementGenerationStartRequest,
} from './api'

/**
 * Start initial requirement generation using AI based on project description and context.
 */
export async function startRequirementGeneration(
  projectId: string,
  data?: RequirementGenerationStartRequest,
): Promise<RequirementGenerationResponse> {
  return request<RequirementGenerationResponse>(`/api/projects/${projectId}/requirement-generations`, {
    method: 'POST',
    body: JSON.stringify(data ?? {}),
  })
}

/**
 * Retrieve the latest generation specification and clarification session for a project.
 */
export async function getLatestRequirementGeneration(
  projectId: string,
): Promise<RequirementGenerationResponse> {
  return request<RequirementGenerationResponse>(`/api/projects/${projectId}/requirement-generations/latest`)
}

/**
 * Retrieve a specific requirement generation by generation ID.
 */
export async function getRequirementGeneration(
  projectId: string,
  generationId: string,
): Promise<RequirementGenerationResponse> {
  return request<RequirementGenerationResponse>(`/api/projects/${projectId}/requirement-generations/${generationId}`)
}

/**
 * Retrieve clarification session state, questions, and answers by session ID.
 */
export async function getClarificationSession(
  projectId: string,
  sessionId: string,
): Promise<ClarificationSession> {
  return request<ClarificationSession>(`/api/projects/${projectId}/clarification-sessions/${sessionId}`)
}

/**
 * Retrieve questions for a clarification session, optionally filtering for unanswered questions only.
 */
export async function getClarificationQuestions(
  projectId: string,
  sessionId: string,
  pendingOnly = false,
): Promise<ClarificationQuestion[]> {
  const query = pendingOnly ? '?pending_only=true' : ''
  return request<ClarificationQuestion[]>(
    `/api/projects/${projectId}/clarification-sessions/${sessionId}/questions${query}`,
  )
}

/**
 * Submit answers to one or more questions in a clarification session.
 */
export async function submitClarificationAnswers(
  projectId: string,
  sessionId: string,
  answers: ClarificationAnswerInput[],
): Promise<ClarificationSession> {
  return request<ClarificationSession>(`/api/projects/${projectId}/clarification-sessions/${sessionId}/answers`, {
    method: 'POST',
    body: JSON.stringify({ answers }),
  })
}

/**
 * Trigger iterative requirement refinement using submitted clarification answers.
 */
export async function triggerRequirementRefinement(
  projectId: string,
  sessionId: string,
  data?: RefinementTriggerRequest,
): Promise<RefinementExecutionResult> {
  return request<RefinementExecutionResult>(`/api/projects/${projectId}/clarification-sessions/${sessionId}/refine`, {
    method: 'POST',
    body: JSON.stringify(data ?? {}),
  })
}

/**
 * List historical generation revisions for a clarification session.
 */
export async function getClarificationRevisions(
  projectId: string,
  sessionId: string,
): Promise<GenerationRevision[]> {
  return request<GenerationRevision[]>(`/api/projects/${projectId}/clarification-sessions/${sessionId}/revisions`)
}
