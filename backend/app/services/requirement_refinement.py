"""Requirement Refinement Service for CodePilot.

Coordinates the clarification workflow, manages session lifecycles,
validates user answers, tracks generation revisions, detects context
conflicts, and orchestrates iterative refinement via the Requirement Analyst.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.agents.requirement_analyst import RequirementAnalystAgent
from app.models.clarification import ClarificationSession, GenerationRevision
from app.repositories.clarification import (
    ClarificationSessionRepository,
    GenerationRevisionRepository,
)
from app.repositories.project import ProjectRepository
from app.repositories.requirement import RequirementRepository
from app.schemas.clarification import (
    ClarificationAnswerSubmission,
    ClarificationSessionConcurrencyError,
    ClarificationSessionCreate,
    ClarificationSessionNotFoundError,
    ClarificationSessionProjectMismatchError,
    ClarificationSessionResponse,
    ClarificationSessionStatus,
    GenerationNotFoundError,
    GenerationProjectMismatchError,
    GenerationRevisionNotFoundError,
    GenerationRevisionResponse,
    InvalidClarificationAnswerError,
    InvalidSessionStateError,
    RefinementExecutionResult,
    RefinementTriggerRequest,
    RequirementDiffItem,
    RequirementDiffSummary,
    RequirementGenerationResponse,
    RequirementGenerationStartRequest,
)
from app.schemas.project_context import (
    ClarificationAnswer,
    ClarificationQuestion,
    ProjectContext,
)
from app.schemas.requirement_generation import (
    GenerationMode,
    RequirementGenerationResult,
)
from app.services.project import ProjectNotFoundError
from app.services.project_context_builder import (
    ProjectContextBuilder,
    detect_context_conflicts,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RequirementRefinementService:
    """Orchestrates iterative requirement generation and clarifications."""

    def __init__(
        self,
        session_repository: ClarificationSessionRepository,
        revision_repository: GenerationRevisionRepository,
        project_repository: ProjectRepository,
        requirement_repository: RequirementRepository,
        agent: RequirementAnalystAgent,
        context_builder: ProjectContextBuilder,
    ) -> None:
        self.session_repo = session_repository
        self.revision_repo = revision_repository
        self.project_repo = project_repository
        self.requirement_repo = requirement_repository
        self.agent = agent
        self.context_builder = context_builder

    def _get_validated_session(
        self, project_id: str, session_id: str
    ) -> ClarificationSession:
        """Fetch session and strictly enforce project boundary."""
        session = self.session_repo.get_by_id(session_id)
        if session is None:
            raise ClarificationSessionNotFoundError(session_id)
        if session.project_id != project_id:
            raise ClarificationSessionProjectMismatchError(
                session_id=session_id,
                target_project_id=project_id,
                actual_project_id=session.project_id,
            )
        return session

    def _to_session_response(
        self, session: ClarificationSession
    ) -> ClarificationSessionResponse:
        """Convert a ClarificationSession ORM model into a Pydantic schema."""
        raw_questions = session.questions or []
        parsed_questions: list[ClarificationQuestion] = []
        raw_answers = session.answers or {}
        parsed_answers: list[ClarificationAnswer] = []

        for q in raw_questions:
            try:
                question_obj = ClarificationQuestion.model_validate(q)
                if question_obj.id in raw_answers:
                    ans_data = raw_answers[question_obj.id]
                    question_obj.user_response = ans_data.get("answer")
                    question_obj.selected_options = ans_data.get(
                        "selected_options", []
                    )
                parsed_questions.append(question_obj)
            except Exception:
                continue

        for ans_dict in raw_answers.values():
            try:
                parsed_answers.append(
                    ClarificationAnswer.model_validate(ans_dict)
                )
            except Exception:
                continue

        answered_ids = set(raw_answers.keys())
        unanswered_ids = [
            q.id for q in parsed_questions if q.id not in answered_ids
        ]
        has_unanswered_required = any(
            q.is_required
            for q in parsed_questions
            if q.id not in answered_ids
        )

        return ClarificationSessionResponse(
            id=session.id,
            project_id=session.project_id,
            generation_id=session.generation_id,
            status=ClarificationSessionStatus(session.status),
            current_revision=session.current_revision,
            questions=parsed_questions,
            answers=parsed_answers,
            unanswered_question_ids=unanswered_ids,
            has_unanswered_required_questions=has_unanswered_required,
            last_error=session.last_error,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )

    def _to_revision_response(
        self,
        revision: GenerationRevision,
        result: RequirementGenerationResult | None = None,
    ) -> GenerationRevisionResponse:
        """Convert a GenerationRevision ORM model into a Pydantic schema."""
        parsed_result = result or RequirementGenerationResult.model_validate(
            revision.result_data
        )
        return GenerationRevisionResponse(
            id=revision.id,
            project_id=revision.project_id,
            session_id=revision.session_id,
            generation_id=revision.generation_id,
            parent_generation_id=revision.parent_generation_id,
            revision_number=revision.revision_number,
            generation_mode=revision.generation_mode,
            summary=revision.summary,
            created_at=revision.created_at,
            result=parsed_result,
        )

    def _to_generation_response(
        self,
        revision: GenerationRevision,
        session: ClarificationSession | None = None,
        result: RequirementGenerationResult | None = None,
    ) -> RequirementGenerationResponse:
        """Convert a GenerationRevision and optional ClarificationSession into a RequirementGenerationResponse."""
        parsed_result = result or RequirementGenerationResult.model_validate(
            revision.result_data
        )
        if session is None and revision.session_id:
            session = self.session_repo.get_by_id(revision.session_id)
        session_resp = self._to_session_response(session) if session else None
        gen_status = (
            session_resp.status.value
            if session_resp
            else (
                ClarificationSessionStatus.AWAITING_CLARIFICATION.value
                if parsed_result.clarification_questions
                else ClarificationSessionStatus.COMPLETED.value
            )
        )
        return RequirementGenerationResponse(
            generation_id=revision.generation_id,
            project_id=revision.project_id,
            session_id=session.id if session else revision.session_id,
            status=gen_status,
            revision_number=revision.revision_number,
            summary=revision.summary,
            result=parsed_result,
            clarification_session=session_resp,
            execution_metadata=parsed_result.execution_metadata,
            created_at=revision.created_at,
        )

    def create_session(
        self,
        project_id: str,
        data: ClarificationSessionCreate,
    ) -> ClarificationSessionResponse:
        """Create or initialize a clarification session for a project."""
        project = self.project_repo.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)

        questions_payload: list[dict[str, Any]] = []
        if data.questions:
            questions_payload = [
                q.model_dump(mode="json") for q in data.questions
            ]
        else:
            existing_rev = self.revision_repo.get_by_generation_id(
                data.generation_id
            )
            if (
                existing_rev
                and "clarification_questions" in existing_rev.result_data
            ):
                questions_payload = existing_rev.result_data[
                    "clarification_questions"
                ]

        has_required = any(
            q.get("is_required", False) for q in questions_payload
        )
        initial_status = (
            ClarificationSessionStatus.AWAITING_CLARIFICATION
            if (questions_payload and has_required)
            else (
                ClarificationSessionStatus.AWAITING_CLARIFICATION
                if questions_payload
                else ClarificationSessionStatus.READY_FOR_REFINEMENT
            )
        )

        orig_context = (
            data.initial_context.model_dump(mode="json")
            if data.initial_context
            else None
        )

        session = ClarificationSession(
            project_id=project_id,
            generation_id=data.generation_id,
            status=initial_status.value,
            current_revision=1,
            original_context=orig_context,
            questions=questions_payload,
            answers={},
            last_error=None,
        )
        self.session_repo.create(session)

        existing_rev = self.revision_repo.get_by_generation_id(
            data.generation_id
        )
        if existing_rev and existing_rev.session_id is None:
            existing_rev.session_id = session.id
            self.revision_repo.update(existing_rev)

        return self._to_session_response(session)

    def initialize_from_generation(
        self,
        project_id: str,
        result: RequirementGenerationResult,
        context: ProjectContext | None = None,
    ) -> ClarificationSessionResponse:
        """Initialize Revision 1 and session from initial generation."""
        project = self.project_repo.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)

        questions_payload = [
            q.model_dump(mode="json") for q in result.clarification_questions
        ]
        initial_status = (
            ClarificationSessionStatus.AWAITING_CLARIFICATION
            if result.clarification_questions
            else ClarificationSessionStatus.COMPLETED
        )

        session = ClarificationSession(
            project_id=project_id,
            generation_id=result.generation_id,
            status=initial_status.value,
            current_revision=1,
            original_context=(
                context.model_dump(mode="json") if context else None
            ),
            questions=questions_payload,
            answers={},
            last_error=None,
        )
        self.session_repo.create(session)

        revision = GenerationRevision(
            project_id=project_id,
            session_id=session.id,
            generation_id=result.generation_id,
            parent_generation_id=None,
            revision_number=1,
            generation_mode=GenerationMode.INITIAL.value,
            summary=result.summary,
            result_data=result.model_dump(mode="json"),
        )
        self.revision_repo.create(revision)

        return self._to_session_response(session)

    async def start_initial_generation(
        self,
        project_id: str,
        request: RequirementGenerationStartRequest | None = None,
    ) -> RequirementGenerationResponse:
        """Start a new requirement generation attempt for an existing project."""
        project = self.project_repo.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)

        req = request or RequirementGenerationStartRequest()

        # 1. Idempotency check: if client supplied request_id and not force_new, check if already exists
        if req.request_id and not req.force_new:
            existing_rev = self.revision_repo.get_by_project_and_generation_id(
                project_id, req.request_id
            )
            if existing_rev:
                return self._to_generation_response(existing_rev)

        # 2. Concurrency check: verify no active refinement is in progress
        active_sessions = self.session_repo.list_by_project(project_id)
        for s in active_sessions:
            if s.status == ClarificationSessionStatus.REFINEMENT_IN_PROGRESS.value:
                raise ClarificationSessionConcurrencyError(
                    f"A requirement refinement is already in progress for project '{project_id}'."
                )

        # 3. Build project context
        context = self.context_builder.build_context(
            project_id=project_id,
            goals=req.goals,
            include_approved_requirements=False,
        )

        # 4. Generate requirements using AI agent
        result = await self.agent.generate_requirements(
            context=context,
            mode=GenerationMode.INITIAL,
            instructions=req.instructions,
            target_categories=req.target_categories,
            goals=req.goals,
            provider=req.provider,
            model=req.model,
            temperature=req.temperature,
        )

        # If client provided request_id, use it as the generation_id
        if req.request_id:
            result.generation_id = req.request_id

        # 5. Initialize clarification session and persist Revision 1
        session_resp = self.initialize_from_generation(project_id, result, context)
        session = self.session_repo.get_by_id(session_resp.id)
        revision = self.revision_repo.get_by_generation_id(result.generation_id)
        if revision is None:
            revision = self.revision_repo.get_latest_by_session(session_resp.id)

        return self._to_generation_response(revision, session, result)

    def get_generation(
        self, project_id: str, generation_id: str
    ) -> RequirementGenerationResponse:
        """Retrieve status and result of a specific generation attempt."""
        project = self.project_repo.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)

        revision = self.revision_repo.get_by_generation_id(generation_id)
        if revision is None:
            raise GenerationNotFoundError(generation_id)

        if revision.project_id != project_id:
            raise GenerationProjectMismatchError(
                generation_id=generation_id,
                target_project_id=project_id,
                actual_project_id=revision.project_id,
            )

        return self._to_generation_response(revision)

    def get_latest_generation_for_project(
        self, project_id: str
    ) -> RequirementGenerationResponse:
        """Retrieve the latest generation result for a project."""
        project = self.project_repo.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)

        latest_revision = self.revision_repo.get_latest_by_project(project_id)
        if latest_revision is None:
            raise GenerationNotFoundError(
                f"latest requirement generation for project '{project_id}'"
            )

        return self._to_generation_response(latest_revision)

    def get_session(
        self, project_id: str, session_id: str
    ) -> ClarificationSessionResponse:
        """Retrieve a specific clarification session."""
        session = self._get_validated_session(project_id, session_id)
        return self._to_session_response(session)

    def list_sessions(
        self, project_id: str
    ) -> list[ClarificationSessionResponse]:
        """List all clarification sessions for a project."""
        project = self.project_repo.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)
        sessions = self.session_repo.list_by_project(project_id)
        return [self._to_session_response(s) for s in sessions]

    def get_questions(
        self, project_id: str, session_id: str, pending_only: bool = False
    ) -> list[ClarificationQuestion]:
        """Retrieve questions for a session."""
        session_resp = self.get_session(project_id, session_id)
        if pending_only:
            answered_ids = {a.question_id for a in session_resp.answers}
            return [
                q for q in session_resp.questions
                if q.id not in answered_ids
            ]
        return session_resp.questions

    def submit_answers(
        self,
        project_id: str,
        session_id: str,
        submission: ClarificationAnswerSubmission,
    ) -> ClarificationSessionResponse:
        """Validate and apply user answers to session questions."""
        session = self._get_validated_session(project_id, session_id)

        current_status = ClarificationSessionStatus(session.status)
        if current_status == ClarificationSessionStatus.CANCELLED:
            raise InvalidSessionStateError(
                f"Cannot submit answers to cancelled session '{session_id}'."
            )
        if current_status == ClarificationSessionStatus.REFINEMENT_IN_PROGRESS:
            raise ClarificationSessionConcurrencyError(
                f"Cannot submit answers: refinement is currently in progress "
                f"for session '{session_id}'."
            )

        seen_submission_qids: set[str] = set()
        for ans in submission.answers:
            if ans.question_id in seen_submission_qids:
                raise InvalidClarificationAnswerError(
                    f"Duplicate answer for question '{ans.question_id}' "
                    f"in submission."
                )
            seen_submission_qids.add(ans.question_id)

        questions_by_id: dict[str, dict[str, Any]] = {
            q.get("id"): q
            for q in session.questions
            if isinstance(q, dict) and "id" in q
        }
        for ans in submission.answers:
            if ans.question_id not in questions_by_id:
                raise InvalidClarificationAnswerError(
                    f"Question '{ans.question_id}' does not exist in "
                    f"clarification session '{session_id}'."
                )
            q_info = questions_by_id[ans.question_id]
            if q_info.get("is_required", False) and not ans.answer.strip():
                raise InvalidClarificationAnswerError(
                    f"Clarification answer for required question "
                    f"'{ans.question_id}' cannot be empty."
                )

        current_answers = dict(session.answers or {})
        for ans in submission.answers:
            clarification_answer = ClarificationAnswer(
                question_id=ans.question_id,
                project_id=project_id,
                answer=ans.answer.strip(),
                selected_options=ans.selected_options,
                answered_at=utc_now(),
            )
            current_answers[ans.question_id] = (
                clarification_answer.model_dump(mode="json")
            )

        session.answers = current_answers

        answered_ids = set(current_answers.keys())
        has_unanswered_required = any(
            q.get("is_required", False)
            for q in session.questions
            if q.get("id") not in answered_ids
        )

        if not has_unanswered_required:
            session.status = ClarificationSessionStatus.READY_FOR_REFINEMENT.value
        else:
            session.status = ClarificationSessionStatus.AWAITING_CLARIFICATION.value

        session.last_error = None
        self.session_repo.update(session)
        return self._to_session_response(session)

    async def refine_requirements(
        self,
        project_id: str,
        session_id: str,
        request: RefinementTriggerRequest,
    ) -> RefinementExecutionResult:
        """Trigger iterative refinement with updated context."""
        session = self._get_validated_session(project_id, session_id)
        current_status = ClarificationSessionStatus(session.status)

        if current_status == ClarificationSessionStatus.REFINEMENT_IN_PROGRESS:
            raise ClarificationSessionConcurrencyError(
                f"A refinement operation is already in progress for "
                f"session '{session_id}'."
            )
        if current_status == ClarificationSessionStatus.CANCELLED:
            raise InvalidSessionStateError(
                f"Cannot refine cancelled session '{session_id}'."
            )

        if request.answers:
            self.submit_answers(
                project_id=project_id,
                session_id=session_id,
                submission=ClarificationAnswerSubmission(answers=request.answers),
            )
            session = self._get_validated_session(project_id, session_id)

        answered_ids = set((session.answers or {}).keys())
        unanswered_required = [
            q.get("id")
            for q in session.questions
            if q.get("is_required", False) and q.get("id") not in answered_ids
        ]
        if unanswered_required:
            raise InvalidSessionStateError(
                f"Cannot proceed with refinement: required clarification "
                f"questions {unanswered_required} must be answered first."
            )

        session.status = ClarificationSessionStatus.REFINEMENT_IN_PROGRESS.value
        session.last_error = None
        self.session_repo.update(session)

        previous_revision = (
            self.revision_repo.get_latest_by_session(session_id)
            or self.revision_repo.get_by_generation_id(session.generation_id)
        )
        previous_generation_result: RequirementGenerationResult | None = None
        existing_proposed: list[dict[str, Any]] = []

        if previous_revision and previous_revision.result_data:
            try:
                previous_generation_result = (
                    RequirementGenerationResult.model_validate(
                        previous_revision.result_data
                    )
                )
                for fr in previous_generation_result.functional_requirements:
                    existing_proposed.append(fr.model_dump())
                for nfr in previous_generation_result.non_functional_requirements:
                    existing_proposed.append(nfr.model_dump())
            except Exception:
                pass

        parsed_answers: list[ClarificationAnswer] = []
        for ans_dict in (session.answers or {}).values():
            try:
                parsed_answers.append(
                    ClarificationAnswer.model_validate(ans_dict)
                )
            except Exception:
                pass

        parsed_questions: list[ClarificationQuestion] = []
        for q_dict in (session.questions or []):
            try:
                parsed_questions.append(
                    ClarificationQuestion.model_validate(q_dict)
                )
            except Exception:
                pass

        context = self.context_builder.build_context(
            project_id=project_id,
            user_clarifications=parsed_answers,
            include_approved_requirements=request.include_approved_requirements,
            existing_proposed_requirements=existing_proposed,
            clarification_questions=parsed_questions,
        )

        detected_conflicts = detect_context_conflicts(context, parsed_answers)

        try:
            refined_result = await self.agent.generate_requirements(
                project_id=project_id,
                context=context,
                mode=GenerationMode.REFINEMENT,
                instructions=request.instructions,
                user_clarifications=parsed_answers,
                include_approved_requirements=request.include_approved_requirements,
                provider=request.provider,
                model=request.model,
                temperature=request.temperature,
            )
        except Exception as exc:
            session.status = ClarificationSessionStatus.FAILED.value
            session.last_error = str(exc)
            self.session_repo.update(session)
            raise

        diff_summary: RequirementDiffSummary | None = None
        if previous_generation_result:
            diff_summary = self.compute_diff(
                previous_generation_result, refined_result
            )

        new_revision_number = session.current_revision + 1
        new_revision = GenerationRevision(
            project_id=project_id,
            session_id=session.id,
            generation_id=refined_result.generation_id,
            parent_generation_id=session.generation_id,
            revision_number=new_revision_number,
            generation_mode=GenerationMode.REFINEMENT.value,
            summary=refined_result.summary,
            result_data=refined_result.model_dump(mode="json"),
        )
        self.revision_repo.create(new_revision)

        session.generation_id = refined_result.generation_id
        session.current_revision = new_revision_number
        session.last_error = None

        new_questions_to_ask: list[ClarificationQuestion] = []
        already_answered_ids = set((session.answers or {}).keys())
        for cq in refined_result.clarification_questions:
            if cq.id not in already_answered_ids:
                new_questions_to_ask.append(cq)

        session.questions = [
            q.model_dump(mode="json") for q in new_questions_to_ask
        ]

        if not new_questions_to_ask:
            session.status = ClarificationSessionStatus.COMPLETED.value
        else:
            has_new_required = any(q.is_required for q in new_questions_to_ask)
            session.status = (
                ClarificationSessionStatus.AWAITING_CLARIFICATION.value
                if has_new_required
                else ClarificationSessionStatus.READY_FOR_REFINEMENT.value
            )

        self.session_repo.update(session)

        return RefinementExecutionResult(
            session=self._to_session_response(session),
            latest_generation=refined_result,
            revision=self._to_revision_response(new_revision, refined_result),
            diff_summary=diff_summary,
            new_clarification_questions=new_questions_to_ask,
            execution_metadata=refined_result.execution_metadata,
            context_conflicts=detected_conflicts,
        )

    def compute_diff(
        self,
        previous_result: RequirementGenerationResult,
        new_result: RequirementGenerationResult,
    ) -> RequirementDiffSummary:
        """Compute structured difference between two generation revisions."""
        prev_map: dict[str, Any] = {}
        new_map: dict[str, Any] = {}

        for fr in previous_result.functional_requirements:
            prev_map[fr.id] = fr
        for nfr in previous_result.non_functional_requirements:
            prev_map[nfr.id] = nfr

        for fr in new_result.functional_requirements:
            new_map[fr.id] = fr
        for nfr in new_result.non_functional_requirements:
            new_map[nfr.id] = nfr

        prev_ids = set(prev_map.keys())
        new_ids = set(new_map.keys())

        added_ids = sorted(new_ids - prev_ids)
        removed_ids = sorted(prev_ids - new_ids)
        common_ids = sorted(prev_ids & new_ids)

        changed_ids: list[str] = []
        retained_ids: list[str] = []
        diff_items: list[RequirementDiffItem] = []

        for req_id in added_ids:
            req = new_map[req_id]
            diff_items.append(
                RequirementDiffItem(
                    id=req_id,
                    title=req.title,
                    change_type="new",
                    details=f"New requirement: {req.description[:80]}",
                )
            )

        for req_id in removed_ids:
            req = prev_map[req_id]
            diff_items.append(
                RequirementDiffItem(
                    id=req_id,
                    title=req.title,
                    change_type="removed",
                    details="Requirement removed in this revision.",
                )
            )

        for req_id in common_ids:
            p = prev_map[req_id]
            n = new_map[req_id]
            title_changed = p.title != n.title
            desc_changed = p.description != n.description
            prio_changed = (
                getattr(p, "priority", None) != getattr(n, "priority", None)
            )
            ac_changed = (
                getattr(p, "acceptance_criteria", [])
                != getattr(n, "acceptance_criteria", [])
            )

            if title_changed or desc_changed or prio_changed or ac_changed:
                changed_ids.append(req_id)
                changes: list[str] = []
                if title_changed:
                    changes.append("title updated")
                if desc_changed:
                    changes.append("description refined")
                if prio_changed:
                    changes.append("priority changed")
                if ac_changed:
                    changes.append("acceptance criteria updated")
                diff_items.append(
                    RequirementDiffItem(
                        id=req_id,
                        title=n.title,
                        change_type="changed",
                        details=", ".join(changes),
                    )
                )
            else:
                retained_ids.append(req_id)
                diff_items.append(
                    RequirementDiffItem(
                        id=req_id,
                        title=n.title,
                        change_type="retained",
                        details="Unchanged from previous revision.",
                    )
                )

        return RequirementDiffSummary(
            new_requirements=added_ids,
            changed_requirements=changed_ids,
            retained_requirements=retained_ids,
            removed_requirements=removed_ids,
            diff_items=diff_items,
            total_current=len(new_map),
            total_previous=len(prev_map),
        )

    def list_revisions(
        self, project_id: str, session_id: str
    ) -> list[GenerationRevisionResponse]:
        """List all generation revisions for a clarification session."""
        self._get_validated_session(project_id, session_id)
        revisions = self.revision_repo.list_by_session(session_id)
        return [self._to_revision_response(r) for r in revisions]

    def get_revision(
        self, project_id: str, session_id: str, revision_number: int
    ) -> GenerationRevisionResponse:
        """Retrieve a specific revision number for a clarification session."""
        self._get_validated_session(project_id, session_id)
        rev = self.revision_repo.get_by_session_and_revision(
            session_id, revision_number
        )
        if rev is None:
            raise GenerationRevisionNotFoundError(
                f"Revision {revision_number} for session '{session_id}'"
            )
        return self._to_revision_response(rev)

    def get_latest_generation(
        self, project_id: str, session_id: str
    ) -> RequirementGenerationResult:
        """Retrieve the latest generation result for a clarification session."""
        session = self._get_validated_session(project_id, session_id)
        rev = self.revision_repo.get_latest_by_session(session_id)
        if rev is None:
            rev = self.revision_repo.get_by_generation_id(session.generation_id)
        if rev is None:
            raise GenerationRevisionNotFoundError(
                f"Latest generation for session '{session_id}'"
            )
        return RequirementGenerationResult.model_validate(rev.result_data)


__all__ = ["RequirementRefinementService"]
