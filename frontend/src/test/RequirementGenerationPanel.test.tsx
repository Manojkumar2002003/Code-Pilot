import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Outlet, Route, Routes } from 'react-router-dom'

import RequirementGenerationPanel from '../components/requirements/RequirementGenerationPanel'
import RequirementsPage from '../pages/RequirementsPage'
import * as requirementGenService from '../services/requirementGenerationService'
import * as requirementService from '../services/requirementService'
import * as taskService from '../services/taskService'
import {
  ApiError,
  type ClarificationSession,
  type Project,
  type RefinementExecutionResult,
  type Requirement,
  type RequirementGenerationResponse,
  type RequirementGenerationResult,
} from '../services/api'

const mockProject: Project = {
  id: 'proj-123',
  name: 'CodePilot Web',
  description: 'AI-assisted developer platform with requirement generation.',
  status: 'active',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const mockShortProject: Project = {
  id: 'proj-short',
  name: 'Tiny App',
  description: 'Short',
  status: 'active',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const mockApprovedRequirements: Requirement[] = [
  {
    id: 'req-appr-1',
    project_id: 'proj-123',
    title: 'Pre-existing Approved Requirement',
    description: 'This is an approved requirement that must not be altered.',
    type: 'functional',
    priority: 'high',
    status: 'approved',
    task_ids: [],
    created_at: '2026-02-01T10:00:00Z',
    updated_at: '2026-02-01T10:00:00Z',
  },
]

const mockGenerationResult: RequirementGenerationResult = {
  generation_id: 'gen-001',
  project_id: 'proj-123',
  summary: 'AI generated requirements specification for CodePilot Web.',
  functional_requirements: [
    {
      id: 'FR-001',
      title: 'GitHub OAuth Authentication',
      description: 'Users can authenticate via GitHub OAuth2 protocol.',
      expected_behavior: 'User can click Sign In with GitHub and complete OAuth flow.',
      acceptance_criteria: ['Given user clicks Sign In with GitHub, then they are redirected to GitHub consent screen.'],
    },
  ],
  non_functional_requirements: [
    {
      id: 'NFR-001',
      category: 'performance',
      title: 'Sub-second API Latency',
      description: 'API endpoints respond in under 500ms.',
      target_metric: 'p95 < 500ms',
    },
  ],
  user_stories: [
    {
      id: 'US-001',
      title: 'Generate Requirements from Idea',
      as_a: 'developer',
      i_want: 'to generate requirements from an idea',
      so_that: 'I save time creating specifications',
      acceptance_criteria: ['Structured requirements generated in under 10 seconds'],
    },
  ],
  business_rules: [
    {
      id: 'BR-001',
      title: 'Project Description Minimum Length',
      rule_statement: 'Project description must contain at least 10 non-whitespace characters.',
    },
  ],
  assumptions: [
    {
      id: 'ASM-001',
      description: 'Cloud LLM provider credentials are configured.',
      impact_if_invalid: 'AI generation will fail with provider error if not configured.',
    },
  ],
  dependencies: [
    {
      id: 'DEP-001',
      dependency_name: 'FastAPI Backend',
      dependency_type: 'service',
      description: 'REST API service hosting requirement generation engine.',
    },
  ],
  clarification_questions: [
    {
      id: 'q-1',
      question: 'Which authentication methods do you plan to support?',
      rationale: 'Clarifies authentication architectural scope.',
      suggested_options: ['GitHub OAuth only', 'GitHub + Google OAuth', 'Email and Password'],
      category: 'functional',
      is_required: true,
    },
    {
      id: 'q-2',
      question: 'Do you require multi-tenant data isolation?',
      rationale: 'Guides database schema design.',
      suggested_options: ['Shared database with tenant_id', 'Dedicated database per tenant'],
      category: 'architecture',
      is_required: false,
    },
  ],
}

const mockGenerationResponse: RequirementGenerationResponse = {
  generation_id: 'gen-001',
  project_id: 'proj-123',
  status: 'completed',
  revision_number: 1,
  summary: 'AI generated requirements specification for CodePilot Web.',
  result: mockGenerationResult,
  session_id: 'sess-001',
  created_at: '2026-02-01T12:00:00Z',
}

const mockSession: ClarificationSession = {
  id: 'sess-001',
  project_id: 'proj-123',
  generation_id: 'gen-001',
  status: 'awaiting_clarification',
  current_revision: 1,
  created_at: '2026-02-01T12:00:00Z',
  updated_at: '2026-02-01T12:00:00Z',
  answers: [],
  questions: mockGenerationResult.clarification_questions,
  unanswered_question_ids: ['q-1', 'q-2'],
  has_unanswered_required_questions: true,
}

const mockRefinementResult: RefinementExecutionResult = {
  session: {
    ...mockSession,
    status: 'completed',
    answers: [
      {
        question_id: 'q-1',
        project_id: 'proj-123',
        answer: 'GitHub + Google OAuth',
        selected_options: ['GitHub + Google OAuth'],
      },
    ],
  },
  latest_generation: {
    ...mockGenerationResult,
    generation_id: 'gen-002',
    clarification_questions: [],
  },
  revision: {
    id: 'rev-002',
    project_id: 'proj-123',
    session_id: 'sess-001',
    generation_id: 'gen-002',
    revision_number: 2,
    generation_mode: 'refine',
    summary: 'Refined requirements specification with dual OAuth support.',
    created_at: '2026-02-01T12:05:00Z',
    result: {
      ...mockGenerationResult,
      generation_id: 'gen-002',
      clarification_questions: [],
    },
  },
  diff_summary: {
    total_current: 2,
    total_previous: 1,
    new_requirements: ['FR-002'],
    changed_requirements: ['FR-001'],
    retained_requirements: ['NFR-001'],
    removed_requirements: [],
    diff_items: [
      {
        id: 'FR-001',
        title: 'GitHub OAuth Authentication',
        change_type: 'changed',
        details: 'Updated scope to include GitHub + Google OAuth based on clarification.',
      },
    ],
  },
}

function renderPanel(project = mockProject) {
  return render(<RequirementGenerationPanel project={project} />)
}

function renderPage(project = mockProject) {
  return render(
    <MemoryRouter initialEntries={[`/projects/${project.id}/requirements`]}>
      <Routes>
        <Route path="/projects/:projectId" element={<Outlet context={{ project }} />}>
          <Route path="requirements" element={<RequirementsPage />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

describe('RequirementGenerationPanel (S3.7)', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(taskService, 'getTasks').mockResolvedValue([])
    vi.spyOn(requirementService, 'getRequirements').mockResolvedValue(mockApprovedRequirements)
  })

  it('1. Renders project context and entry point properly', async () => {
    vi.spyOn(requirementGenService, 'getLatestRequirementGeneration').mockRejectedValue(
      new ApiError('Not found', 404),
    )

    renderPanel()

    await waitFor(() => {
      expect(screen.getByText('AI Requirement Analyst')).toBeInTheDocument()
    })

    expect(screen.getByText('CodePilot Web')).toBeInTheDocument()
    expect(screen.getByText(mockProject.description!)).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: '✨ Generate Requirements with AI' }),
    ).toBeInTheDocument()
  })

  it('2. Shows warning when project description has insufficient substance (<10 chars)', async () => {
    vi.spyOn(requirementGenService, 'getLatestRequirementGeneration').mockRejectedValue(
      new ApiError('Not found', 404),
    )

    renderPanel(mockShortProject)

    await waitFor(() => {
      expect(screen.getByText(/Insufficient project description:/i)).toBeInTheDocument()
    })

    expect(
      screen.queryByRole('button', { name: /Generate Requirements/i }),
    ).not.toBeInTheDocument()
  })

  it('3. Starts generation successfully and shows proposals', async () => {
    const user = userEvent.setup()
    vi.spyOn(requirementGenService, 'getLatestRequirementGeneration').mockRejectedValue(
      new ApiError('Not found', 404),
    )
    const startSpy = vi
      .spyOn(requirementGenService, 'startRequirementGeneration')
      .mockResolvedValue(mockGenerationResponse)
    vi.spyOn(requirementGenService, 'getClarificationSession').mockResolvedValue(mockSession)

    renderPanel()

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: '✨ Generate Requirements with AI' }),
      ).toBeEnabled()
    })

    await user.click(screen.getByRole('button', { name: '✨ Generate Requirements with AI' }))

    await waitFor(() => {
      expect(startSpy).toHaveBeenCalledWith('proj-123', {
        instructions: null,
      })
    })

    // Functional requirement rendered
    await waitFor(() => {
      expect(screen.getByText('GitHub OAuth Authentication')).toBeInTheDocument()
    })

    // Non-functional requirement rendered
    expect(screen.getByText('Sub-second API Latency')).toBeInTheDocument()

    // Clarification question rendered
    expect(
      screen.getByText('Which authentication methods do you plan to support?'),
    ).toBeInTheDocument()

    // Human review banner present
    expect(screen.getByText('Awaiting Human Review')).toBeInTheDocument()
  })

  it('4. Renders user stories, business rules, assumptions, and dependencies', async () => {
    vi.spyOn(requirementGenService, 'getLatestRequirementGeneration').mockResolvedValue(
      mockGenerationResponse,
    )
    vi.spyOn(requirementGenService, 'getClarificationSession').mockResolvedValue(mockSession)

    renderPanel()

    await waitFor(() => {
      expect(screen.getByText('GitHub OAuth Authentication')).toBeInTheDocument()
    })

    expect(screen.getByText('Generate Requirements from Idea')).toBeInTheDocument()
    expect(screen.getByText('Project Description Minimum Length')).toBeInTheDocument()
    expect(screen.getByText('Cloud LLM provider credentials are configured.')).toBeInTheDocument()
    expect(screen.getByText('FastAPI Backend')).toBeInTheDocument()
  })

  it('5. Distinguishes required vs optional questions and displays rationale', async () => {
    vi.spyOn(requirementGenService, 'getLatestRequirementGeneration').mockResolvedValue(
      mockGenerationResponse,
    )
    vi.spyOn(requirementGenService, 'getClarificationSession').mockResolvedValue(mockSession)

    renderPanel()

    await waitFor(() => {
      expect(screen.getByText('Required')).toBeInTheDocument()
    })

    expect(screen.getByText('Optional')).toBeInTheDocument()
    expect(screen.getByText('Clarifies authentication architectural scope.')).toBeInTheDocument()
    expect(screen.getByText('Guides database schema design.')).toBeInTheDocument()
  })

  it('6. Allows selecting suggested answer options and typing custom text', async () => {
    const user = userEvent.setup()
    vi.spyOn(requirementGenService, 'getLatestRequirementGeneration').mockResolvedValue(
      mockGenerationResponse,
    )
    vi.spyOn(requirementGenService, 'getClarificationSession').mockResolvedValue(mockSession)

    renderPanel()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /GitHub \+ Google OAuth/i })).toBeInTheDocument()
    })

    // Click suggested option chip
    const optionChip = screen.getByRole('button', { name: /GitHub \+ Google OAuth/i })
    await user.click(optionChip)

    // Option becomes selected and auto-fills answer textarea
    const answerTextarea = screen.getByLabelText('Your response to q-1')
    expect(answerTextarea).toHaveValue('GitHub + Google OAuth')

    // Type additional custom notes
    await user.type(answerTextarea, ' with strict scopes')
    expect(answerTextarea).toHaveValue('GitHub + Google OAuth with strict scopes')
  })

  it('7. Client-side validates incomplete required answers and enables refine button when answered', async () => {
    const user = userEvent.setup()
    vi.spyOn(requirementGenService, 'getLatestRequirementGeneration').mockResolvedValue(
      mockGenerationResponse,
    )
    vi.spyOn(requirementGenService, 'getClarificationSession').mockResolvedValue(mockSession)

    renderPanel()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Refine Specification/i })).toBeInTheDocument()
    })

    // Required question q-1 is not answered yet -> button is disabled
    const refineBtn = screen.getByRole('button', { name: /Refine Specification/i })
    expect(refineBtn).toBeDisabled()

    // Answer required question
    await user.click(screen.getByRole('button', { name: /GitHub \+ Google OAuth/i }))

    // Refine button now enabled!
    expect(screen.getByRole('button', { name: /Refine Specification/i })).toBeEnabled()
  })

  it('8. Successfully saves answers and triggers refinement', async () => {
    const user = userEvent.setup()
    vi.spyOn(requirementGenService, 'getLatestRequirementGeneration').mockResolvedValue(
      mockGenerationResponse,
    )
    vi.spyOn(requirementGenService, 'getClarificationSession').mockResolvedValue(mockSession)

    const saveSpy = vi
      .spyOn(requirementGenService, 'submitClarificationAnswers')
      .mockResolvedValue({
        id: 'sess-001',
        project_id: 'proj-123',
        generation_id: 'gen-001',
        status: 'awaiting_clarification',
        current_revision: 1,
        created_at: '2026-02-01T12:00:00Z',
        updated_at: '2026-02-01T12:05:00Z',
        answers: [
          {
            question_id: 'q-1',
            project_id: 'proj-123',
            answer: 'GitHub + Google OAuth',
            selected_options: ['GitHub + Google OAuth'],
          },
        ],
        questions: mockGenerationResult.clarification_questions,
        unanswered_question_ids: ['q-2'],
        has_unanswered_required_questions: false,
      })

    const refineSpy = vi
      .spyOn(requirementGenService, 'triggerRequirementRefinement')
      .mockResolvedValue(mockRefinementResult)

    renderPanel()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /GitHub \+ Google OAuth/i })).toBeInTheDocument()
    })

    // Answer required question
    await user.click(screen.getByRole('button', { name: /GitHub \+ Google OAuth/i }))

    // Save answers explicitly
    const saveBtn = screen.getByRole('button', { name: 'Save Answers' })
    await user.click(saveBtn)

    await waitFor(() => {
      expect(saveSpy).toHaveBeenCalledWith('proj-123', 'sess-001', [
        {
          question_id: 'q-1',
          answer: 'GitHub + Google OAuth',
          selected_options: ['GitHub + Google OAuth'],
        },
      ])
    })

    // Click Refine
    const refineBtn = screen.getByRole('button', { name: /Refine Specification/i })
    await user.click(refineBtn)

    await waitFor(() => {
      expect(refineSpy).toHaveBeenCalledWith('proj-123', 'sess-001', {
        instructions: null,
        answers: [
          {
            question_id: 'q-1',
            answer: 'GitHub + Google OAuth',
            selected_options: ['GitHub + Google OAuth'],
          },
        ],
      })
    })

    // Shows success message and diff
    await waitFor(() => {
      expect(
        screen.getByText('Specification successfully refined to Revision 2.'),
      ).toBeInTheDocument()
    })
    expect(screen.getByText('Revision Changes')).toBeInTheDocument()
  })

  it('9. Preserves previous generation results when refinement fails', async () => {
    const user = userEvent.setup()
    vi.spyOn(requirementGenService, 'getLatestRequirementGeneration').mockResolvedValue(
      mockGenerationResponse,
    )
    vi.spyOn(requirementGenService, 'getClarificationSession').mockResolvedValue(mockSession)
    vi.spyOn(requirementGenService, 'submitClarificationAnswers').mockResolvedValue(mockSession)
    vi.spyOn(requirementGenService, 'triggerRequirementRefinement').mockRejectedValue(
      new ApiError('Refinement failed: provider rate limit reached.', 429),
    )

    renderPanel()

    await waitFor(() => {
      expect(screen.getByText('GitHub OAuth Authentication')).toBeInTheDocument()
    })

    // Answer required question
    await user.click(screen.getByRole('button', { name: /GitHub OAuth only/i }))

    // Trigger refinement
    await user.click(screen.getByRole('button', { name: /Refine Specification/i }))

    // Error is displayed safely
    await waitFor(() => {
      expect(
        screen.getByText('Refinement failed: provider rate limit reached.'),
      ).toBeInTheDocument()
    })

    // Previous results are still preserved and displayed!
    expect(screen.getByText('GitHub OAuth Authentication')).toBeInTheDocument()
  })

  it('10. Prevents duplicate submissions and disables buttons during generation', async () => {
    vi.spyOn(requirementGenService, 'getLatestRequirementGeneration').mockRejectedValue(
      new ApiError('Not found', 404),
    )
    vi.spyOn(requirementGenService, 'startRequirementGeneration').mockReturnValue(
      new Promise(() => {}), // never resolves
    )

    renderPanel()

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: '✨ Generate Requirements with AI' }),
      ).toBeEnabled()
    })

    const generateBtn = screen.getByRole('button', {
      name: '✨ Generate Requirements with AI',
    })
    await userEvent.click(generateBtn)

    // Button shows loading indicator and is disabled
    expect(
      screen.getByRole('button', { name: /Analyzing & Generating/i }),
    ).toBeDisabled()
  })

  it('11. Displays backend errors safely without exposing internal details', async () => {
    vi.spyOn(requirementGenService, 'getLatestRequirementGeneration').mockRejectedValue(
      new ApiError('Cloud provider quota exceeded for Gemini.', 503),
    )

    renderPanel()

    await waitFor(() => {
      expect(
        screen.getByText('Cloud provider quota exceeded for Gemini.'),
      ).toBeInTheDocument()
    })

    expect(screen.queryByText(/sk-[a-zA-Z0-9]+/)).not.toBeInTheDocument()
  })

  it('12. Distinguishes AI proposals from approved requirements in RequirementsPage', async () => {
    const user = userEvent.setup()
    vi.spyOn(requirementGenService, 'getLatestRequirementGeneration').mockResolvedValue(
      mockGenerationResponse,
    )
    vi.spyOn(requirementGenService, 'getClarificationSession').mockResolvedValue(mockSession)

    renderPage()

    // Initially loads approved requirements
    await waitFor(() => {
      expect(screen.getByText('Pre-existing Approved Requirement')).toBeInTheDocument()
    })

    // Switch to AI Analyst tab
    const aiTab = screen.getByRole('button', { name: '✨ AI Requirement Analyst' })
    await user.click(aiTab)

    // AI Proposal is rendered
    await waitFor(() => {
      expect(screen.getByText('GitHub OAuth Authentication')).toBeInTheDocument()
    })
    expect(screen.getByText('Awaiting Human Review')).toBeInTheDocument()

    // Switch back to Approved tab
    const approvedTab = screen.getByRole('button', { name: /Approved Requirements/i })
    await user.click(approvedTab)

    // Approved requirement is still intact
    await waitFor(() => {
      expect(screen.getByText('Pre-existing Approved Requirement')).toBeInTheDocument()
    })
  })
})
