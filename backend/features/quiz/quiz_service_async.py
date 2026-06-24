"""
Quiz Builder Service - Business logic for quiz CRUD operations (Async)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime
import os
import secrets

from persistence.models.quiz import (
    Quiz,
    Question,
    QuizFolder,
    FolderShare,
    QuizStatus,
    QuizType,
    QuestionType,
    TemplateScope,
    QuizSession,
    QuizSessionStatus,
    Participant,
    Answer,
    QuizFeedback,
    SessionQuestionTiming,
)
from persistence.models.core import Event, UserRole
from features.quiz.schemas import (
    QuizCreate, QuizUpdate, QuizResponse, QuizListResponse,
    QuestionCreate, QuestionUpdate, QuestionResponse,
    TemplateDesignationRequest, TemplateQuizListItemResponse,
    FolderCreateRequest, FolderUpdateRequest, FolderResponse, FolderShareRequest, FolderShareEntry,
    OfflinePollPublishResponse,
)
from shared.exceptions.quiz import (
    QuizNotFoundError, QuestionNotFoundError, QuizValidationError,
    InvalidQuizStatusError, TierLimitExceededError
)
from core.config.tier_service import TierService
from core.auth.dependencies import CurrentUser
from core.storage import ImageService


class QuizBuilderServiceAsync:
    """Async service for quiz builder operations"""
    
    def __init__(self, tier_service: TierService):
        self.tier_service = tier_service

    def _folder_path_names(self, folder: Optional[QuizFolder]) -> list[str]:
        if not folder:
            return []
        return [folder.name]

    async def _compute_folder_path_names(self, db: AsyncSession, folder: QuizFolder) -> list[str]:
        names: list[str] = [folder.name]
        parent_id = folder.parent_id
        guard = 0
        while parent_id is not None and guard < 100:
            parent = (
                await db.execute(
                    select(QuizFolder).filter(
                        QuizFolder.id == parent_id,
                        QuizFolder.tenant_id == folder.tenant_id,
                    )
                )
            ).scalar_one_or_none()
            if not parent:
                break
            names.append(parent.name)
            parent_id = parent.parent_id
            guard += 1
        names.reverse()
        return names

    def _folder_to_tree(self, folder: QuizFolder, parents: dict[int, Optional[QuizFolder]], by_parent: dict[Optional[int], list[QuizFolder]], share_count_map: dict[int, int] | None = None) -> FolderResponse:
        path_names = self._folder_path_names_with_lookup(folder, parents)
        children = sorted(by_parent.get(folder.id, []), key=lambda f: (f.sort_order, f.name.lower(), f.id))
        return FolderResponse(
            id=folder.id,
            name=folder.name,
            parent_id=folder.parent_id,
            sort_order=folder.sort_order or 0,
            path=" / ".join(path_names),
            children=[self._folder_to_tree(child, parents, by_parent, share_count_map) for child in children],
            share_count=(share_count_map or {}).get(folder.id, 0),
        )

    def _folder_path_names_with_lookup(self, folder: QuizFolder, parents: dict[int, Optional[QuizFolder]]) -> list[str]:
        names: list[str] = []
        cursor: Optional[QuizFolder] = folder
        guard = 0
        while cursor is not None and guard < 50:
            names.append(cursor.name)
            cursor = parents.get(cursor.id)
            guard += 1
        names.reverse()
        return names

    async def list_folders(self, db: AsyncSession, current_user: CurrentUser) -> list[FolderResponse]:
        # Own folders
        own_rows = (
            await db.execute(
                select(QuizFolder)
                .filter(
                    QuizFolder.tenant_id == current_user.tenant_id,
                    QuizFolder.created_by_id == current_user.user_id,
                )
                .order_by(QuizFolder.parent_id.asc(), QuizFolder.sort_order.asc(), QuizFolder.name.asc())
            )
        ).scalars().all()

        # Shared-to-me folders (flat, not nested under own tree)
        share_rows = (
            await db.execute(
                select(FolderShare, QuizFolder)
                .join(QuizFolder, QuizFolder.id == FolderShare.folder_id)
                .filter(
                    FolderShare.shared_with_user_id == current_user.user_id,
                )
            )
        ).all()

        shared_folder_ids = {share.FolderShare.folder_id for share in share_rows}
        shared_can_edit = {share.FolderShare.folder_id: share.FolderShare.can_edit for share in share_rows}

        # Share counts for owned folders (how many people the owner shared each folder with)
        own_folder_ids = [f.id for f in own_rows]
        share_count_map: dict[int, int] = {}
        if own_folder_ids:
            sc_rows = await db.execute(
                select(FolderShare.folder_id, func.count(FolderShare.id).label("cnt"))
                .filter(FolderShare.folder_id.in_(own_folder_ids))
                .group_by(FolderShare.folder_id)
            )
            share_count_map = {row.folder_id: row.cnt for row in sc_rows}

        by_id = {f.id: f for f in own_rows}
        parents: dict[int, Optional[QuizFolder]] = {f.id: by_id.get(f.parent_id) for f in own_rows}
        by_parent: dict[Optional[int], list[QuizFolder]] = {}
        for folder in own_rows:
            by_parent.setdefault(folder.parent_id, []).append(folder)

        roots = sorted(by_parent.get(None, []), key=lambda f: (f.sort_order, f.name.lower(), f.id))
        result = [self._folder_to_tree(root, parents, by_parent, share_count_map) for root in roots]

        # Append shared-to-me folders as top-level items
        for share_row in share_rows:
            f = share_row.QuizFolder
            path_names = await self._compute_folder_path_names(db, f)
            result.append(FolderResponse(
                id=f.id,
                name=f.name,
                parent_id=None,  # appears at root for the recipient
                sort_order=f.sort_order or 0,
                path=" / ".join(path_names),
                children=[],
                is_shared_to_me=True,
                can_edit=shared_can_edit.get(f.id, False),
            ))

        return result

    async def create_folder(self, db: AsyncSession, request: FolderCreateRequest, current_user: CurrentUser) -> FolderResponse:
        parent: Optional[QuizFolder] = None
        if request.parent_id is not None:
            parent = (
                await db.execute(
                    select(QuizFolder).filter(
                        QuizFolder.id == request.parent_id,
                        QuizFolder.tenant_id == current_user.tenant_id,
                        QuizFolder.created_by_id == current_user.user_id,
                    )
                )
            ).scalar_one_or_none()
            if not parent:
                raise QuizNotFoundError("Parent folder not found")

        existing = (
            await db.execute(
                select(QuizFolder).filter(
                    QuizFolder.tenant_id == current_user.tenant_id,
                    QuizFolder.parent_id == request.parent_id,
                    func.lower(QuizFolder.name) == request.name.strip().lower(),
                )
            )
        ).scalar_one_or_none()
        if existing:
            raise QuizValidationError("A folder with this name already exists in the selected parent")

        max_order = (
            await db.execute(
                select(func.coalesce(func.max(QuizFolder.sort_order), 0)).filter(
                    QuizFolder.tenant_id == current_user.tenant_id,
                    QuizFolder.parent_id == request.parent_id,
                )
            )
        ).scalar_one()

        folder = QuizFolder(
            tenant_id=current_user.tenant_id,
            created_by_id=current_user.user_id,
            parent_id=request.parent_id,
            name=request.name.strip(),
            sort_order=(max_order or 0) + 1,
        )
        db.add(folder)
        await db.commit()
        await db.refresh(folder)

        path_names = await self._compute_folder_path_names(db, folder)
        return FolderResponse(
            id=folder.id,
            name=folder.name,
            parent_id=folder.parent_id,
            sort_order=folder.sort_order or 0,
            path=" / ".join(path_names),
            children=[],
        )

    async def update_folder(self, db: AsyncSession, folder_id: int, request: FolderUpdateRequest, current_user: CurrentUser) -> FolderResponse:
        folder = (
            await db.execute(
                select(QuizFolder).filter(
                    QuizFolder.id == folder_id,
                    QuizFolder.tenant_id == current_user.tenant_id,
                    QuizFolder.created_by_id == current_user.user_id,
                )
            )
        ).scalar_one_or_none()
        if not folder:
            raise QuizNotFoundError("Folder not found")

        parent_update_requested = "parent_id" in request.model_fields_set
        target_parent_id = request.parent_id if parent_update_requested else folder.parent_id

        if parent_update_requested and request.parent_id == folder.id:
            raise QuizValidationError("Folder cannot be its own parent")

        if parent_update_requested and request.parent_id is not None:
            parent = (
                await db.execute(
                    select(QuizFolder).filter(
                        QuizFolder.id == request.parent_id,
                        QuizFolder.tenant_id == current_user.tenant_id,
                        QuizFolder.created_by_id == current_user.user_id,
                    )
                )
            ).scalar_one_or_none()
            if not parent:
                raise QuizNotFoundError("Parent folder not found")

            cursor = parent
            guard = 0
            while cursor is not None and guard < 100:
                if cursor.id == folder.id:
                    raise QuizValidationError("Folder move would create a cycle")
                if cursor.parent_id is None:
                    break
                cursor = (
                    await db.execute(
                        select(QuizFolder).filter(
                            QuizFolder.id == cursor.parent_id,
                            QuizFolder.tenant_id == current_user.tenant_id,
                        )
                    )
                ).scalar_one_or_none()
                guard += 1

        if parent_update_requested:
            folder.parent_id = request.parent_id

        if request.name is not None:
            candidate = request.name.strip()
            existing = (
                await db.execute(
                    select(QuizFolder).filter(
                        QuizFolder.tenant_id == current_user.tenant_id,
                        QuizFolder.parent_id == target_parent_id,
                        func.lower(QuizFolder.name) == candidate.lower(),
                        QuizFolder.id != folder.id,
                    )
                )
            ).scalar_one_or_none()
            if existing:
                raise QuizValidationError("A folder with this name already exists in the selected parent")
            folder.name = candidate

        await db.commit()
        await db.refresh(folder)
        return FolderResponse(
            id=folder.id,
            name=folder.name,
            parent_id=folder.parent_id,
            sort_order=folder.sort_order or 0,
            path=" / ".join(await self._compute_folder_path_names(db, folder)),
            children=[],
        )

    async def delete_folder(self, db: AsyncSession, folder_id: int, current_user: CurrentUser) -> None:
        folder = (
            await db.execute(
                select(QuizFolder).filter(
                    QuizFolder.id == folder_id,
                    QuizFolder.tenant_id == current_user.tenant_id,
                    QuizFolder.created_by_id == current_user.user_id,
                )
            )
        ).scalar_one_or_none()
        if not folder:
            raise QuizNotFoundError("Folder not found")

        child_rows = (
            await db.execute(
                select(QuizFolder.id).filter(
                    QuizFolder.tenant_id == current_user.tenant_id,
                    QuizFolder.parent_id == folder_id,
                )
            )
        ).all()
        child_ids = [r.id for r in child_rows]
        if child_ids:
            await db.execute(
                update(QuizFolder)
                .where(QuizFolder.id.in_(child_ids))
                .values(parent_id=folder.parent_id)
            )

        await db.execute(
            update(Quiz)
            .where(
                Quiz.tenant_id == current_user.tenant_id,
                Quiz.folder_id == folder_id,
            )
            .values(folder_id=folder.parent_id)
        )
        await db.delete(folder)
        await db.commit()

    async def share_folder(
        self,
        db: AsyncSession,
        folder_id: int,
        request: FolderShareRequest,
        current_user: CurrentUser,
    ) -> list[FolderShareEntry]:
        """Replace the share list for a folder (only the owner can do this)."""
        from persistence.models.core import User
        folder = (
            await db.execute(
                select(QuizFolder).filter(
                    QuizFolder.id == folder_id,
                    QuizFolder.tenant_id == current_user.tenant_id,
                    QuizFolder.created_by_id == current_user.user_id,
                )
            )
        ).scalar_one_or_none()
        if not folder:
            raise QuizNotFoundError("Folder not found or not owned by you")

        # Validate that all users belong to the same tenant
        if request.user_ids:
            users = (
                await db.execute(
                    select(User).filter(
                        User.id.in_(request.user_ids),
                        User.tenant_id == current_user.tenant_id,
                    )
                )
            ).scalars().all()
            if len(users) != len(request.user_ids):
                raise QuizValidationError("One or more users not found in your tenant")
        else:
            users = []

        # Replace shares: delete existing, insert new
        await db.execute(
            delete(FolderShare).where(FolderShare.folder_id == folder_id)
        )
        for uid in request.user_ids:
            db.add(FolderShare(folder_id=folder_id, shared_with_user_id=uid, can_edit=request.can_edit))
        await db.commit()

        return [
            FolderShareEntry(
                user_id=u.id,
                email=u.email,
                display_name=getattr(u, "display_name", None) or u.email,
                can_edit=request.can_edit,
            )
            for u in users
        ]

    async def list_folder_shares(
        self,
        db: AsyncSession,
        folder_id: int,
        current_user: CurrentUser,
    ) -> list[FolderShareEntry]:
        """List current shares for a folder (owner only)."""
        from persistence.models.core import User
        folder = (
            await db.execute(
                select(QuizFolder).filter(
                    QuizFolder.id == folder_id,
                    QuizFolder.tenant_id == current_user.tenant_id,
                    QuizFolder.created_by_id == current_user.user_id,
                )
            )
        ).scalar_one_or_none()
        if not folder:
            raise QuizNotFoundError("Folder not found or not owned by you")

        rows = (
            await db.execute(
                select(FolderShare, User)
                .join(User, User.id == FolderShare.shared_with_user_id)
                .filter(FolderShare.folder_id == folder_id)
            )
        ).all()

        return [
            FolderShareEntry(
                user_id=row.User.id,
                email=row.User.email,
                display_name=getattr(row.User, "display_name", None) or row.User.email,
                can_edit=row.FolderShare.can_edit,
            )
            for row in rows
        ]

    async def assign_quiz_folder(self, db: AsyncSession, quiz_id: int, folder_id: Optional[int], current_user: CurrentUser) -> QuizResponse:
        result = await db.execute(
            select(Quiz)
            .filter(
                Quiz.id == quiz_id,
                Quiz.tenant_id == current_user.tenant_id
            )
            .options(selectinload(Quiz.questions), selectinload(Quiz.folder))
        )
        quiz = result.scalar_one_or_none()
        if not quiz:
            raise QuizNotFoundError("Quiz not found")

        if folder_id is not None:
            folder = (
                await db.execute(
                    select(QuizFolder).filter(
                        QuizFolder.id == folder_id,
                        QuizFolder.tenant_id == current_user.tenant_id,
                    )
                )
            ).scalar_one_or_none()
            if not folder:
                raise QuizNotFoundError("Folder not found")
            quiz.folder_id = folder_id
        else:
            quiz.folder_id = None

        await db.commit()
        await db.refresh(quiz)
        return self._to_quiz_response(quiz)
    
    async def create_quiz(
        self,
        db: AsyncSession,
        request: QuizCreate,
        current_user: CurrentUser
    ) -> QuizResponse:
        """
        Create new quiz in DRAFT status
        
        Args:
            db: Database session
            request: Quiz creation data
            current_user: Current authenticated user
            
        Returns:
            Created quiz
            
        Raises:
            QuizNotFoundError: If event not found
        """
        # Auto-create event if not provided
        event_id = request.event_id
        
        if not event_id:
            # Create a default event for this quiz
            event = Event(
                tenant_id=current_user.tenant_id,
                creator_id=current_user.user_id,
                title=f"Quiz Session - {request.title}",
                description=None,
                join_code=None
            )
            db.add(event)
            await db.flush()
            event_id = event.id
        else:
            # Verify event exists and belongs to tenant
            result = await db.execute(
                select(Event).filter(
                    Event.id == event_id,
                    Event.tenant_id == current_user.tenant_id
                )
            )
            event = result.scalar_one_or_none()
            
            if not event:
                raise QuizNotFoundError("Event not found")
        
        # Explicitly determine quiz type
        raw_type = request.quiz_type.value if hasattr(request.quiz_type, 'value') else str(request.quiz_type)
        q_type = QuizType.EXAM if any(k in raw_type.lower() for k in ["exam", "test"]) else QuizType(raw_type)
        
        # Create quiz
        quiz = Quiz(
            tenant_id=current_user.tenant_id,
            event_id=event_id,
            title=request.title,
            description=request.description,
            quiz_type=q_type,
            status=QuizStatus.DRAFT,
            proctoring_policy=request.proctoring_policy
        )

        # Offline poll fields
        if request.quiz_type.value == "offline_poll":
            quiz.offline_start_at = request.offline_start_at
            quiz.offline_end_at = request.offline_end_at
            quiz.offline_results_email = request.offline_results_email

        # Exam fields
        if request.quiz_type.value == "exam":
            quiz.exam_start_at = request.exam_start_at
            quiz.exam_end_at = request.exam_end_at
            quiz.exam_time_limit_seconds = request.exam_time_limit_seconds
            quiz.exam_results_email = request.exam_results_email

        db.add(quiz)
        await db.commit()
        await db.refresh(quiz)

        return self._to_quiz_response(quiz)
    
    async def get_quiz(
        self,
        db: AsyncSession,
        quiz_id: int,
        current_user: CurrentUser
    ) -> QuizResponse:
        """Get quiz by ID"""
        shared_folder_ids = select(FolderShare.folder_id).filter(
            FolderShare.shared_with_user_id == current_user.user_id
        )
        result = await db.execute(
            select(Quiz)
            .filter(
                Quiz.id == quiz_id,
                or_(
                    Quiz.tenant_id == current_user.tenant_id,
                    Quiz.folder_id.in_(shared_folder_ids),
                ),
            )
            .options(selectinload(Quiz.questions), selectinload(Quiz.folder).selectinload(QuizFolder.parent))
        )
        quiz = result.scalar_one_or_none()

        if not quiz:
            raise QuizNotFoundError("Quiz not found")
        
        return self._to_quiz_response(quiz)
    
    async def list_quizzes(
        self,
        db: AsyncSession,
        current_user: CurrentUser,
        event_id: Optional[int] = None,
        include_archived: bool = False,
    ) -> List[QuizListResponse]:
        """List quizzes for tenant + quizzes in folders shared to the user"""
        shared_folder_ids_q = select(FolderShare.folder_id).filter(
            FolderShare.shared_with_user_id == current_user.user_id
        )
        query = select(Quiz).filter(
            or_(
                Quiz.tenant_id == current_user.tenant_id,
                Quiz.folder_id.in_(shared_folder_ids_q),
            )
        )

        if not include_archived:
            query = query.filter(Quiz.archived_at.is_(None))

        if event_id:
            query = query.filter(Quiz.event_id == event_id)

        # Eagerly load questions to avoid lazy loading in async context
        query = query.options(selectinload(Quiz.questions), selectinload(Quiz.folder).selectinload(QuizFolder.parent))
        query = query.order_by(Quiz.created_at.desc())
        result = await db.execute(query)
        quizzes = result.scalars().all()

        active_session_rows = await db.execute(
            select(
                QuizSession.quiz_id,
                func.max(QuizSession.id).label("active_session_id")
            ).filter(
                QuizSession.tenant_id == current_user.tenant_id,
                QuizSession.status.in_([QuizSessionStatus.CREATED, QuizSessionStatus.ACTIVE])
            ).group_by(QuizSession.quiz_id)
        )
        active_session_map = {
            row.quiz_id: row.active_session_id
            for row in active_session_rows
        }

        quiz_ids = [q.id for q in quizzes]
        response_count_map: dict[int, int] = {}
        if quiz_ids:
            response_rows = await db.execute(
                select(QuizSession.quiz_id, func.count(Participant.id).label("cnt"))
                .join(Participant, Participant.session_id == QuizSession.id)
                .join(Quiz, Quiz.id == QuizSession.quiz_id)
                .filter(
                    QuizSession.quiz_id.in_(quiz_ids),
                    # For exam quizzes: only count from the designated exam session
                    # For regular quizzes: count from all sessions
                    (Quiz.exam_session_id.is_(None)) | (QuizSession.id == Quiz.exam_session_id),
                )
                .group_by(QuizSession.quiz_id)
            )
            response_count_map = {row.quiz_id: row.cnt for row in response_rows}

        return [
            QuizListResponse(
                id=q.id,
                event_id=q.event_id,
                title=q.title,
                quiz_type=q.quiz_type,
                status=q.status,
                folder_id=q.folder_id,
                folder_path=" / ".join(self._folder_path_names(q.folder)) if q.folder else None,
                is_template=q.is_template,
                template_scope=q.template_scope,
                question_count=len(q.questions),
                response_count=response_count_map.get(q.id, 0),
                has_active_session=q.id in active_session_map,
                active_session_id=active_session_map.get(q.id),
                created_at=q.created_at.isoformat(),
                poll_slug=getattr(q, 'poll_slug', None),
                poll_url=(
                    f"{os.getenv('FRONTEND_URL', 'https://www.swaya.me')}/poll/{q.poll_slug}"
                    if getattr(q, 'poll_slug', None) else None
                ),
                offline_start_at=getattr(q, 'offline_start_at', None),
                offline_end_at=getattr(q, 'offline_end_at', None),
                exam_slug=getattr(q, 'exam_slug', None),
                exam_url=(
                    f"{os.getenv('FRONTEND_URL', 'https://www.swaya.me')}/e/{q.exam_slug}"
                    if getattr(q, 'exam_slug', None) else None
                ),
                exam_start_at=getattr(q, 'exam_start_at', None),
                exam_end_at=getattr(q, 'exam_end_at', None),
                archived_at=getattr(q, 'archived_at', None),
            )
            for q in quizzes
        ]

    async def set_template_status(
        self,
        db: AsyncSession,
        quiz_id: int,
        request: TemplateDesignationRequest,
        current_user: CurrentUser
    ) -> QuizResponse:
        """Mark/unmark a quiz as template"""
        result = await db.execute(
            select(Quiz)
            .filter(
                Quiz.id == quiz_id,
                Quiz.tenant_id == current_user.tenant_id
            )
            .options(selectinload(Quiz.questions), selectinload(Quiz.folder))
        )
        quiz = result.scalar_one_or_none()
        if not quiz:
            raise QuizNotFoundError("Quiz not found")

        if request.is_template:
            quiz.is_template = True
            if current_user.user.role == UserRole.super_admin:
                quiz.template_scope = TemplateScope.GLOBAL
            else:
                quiz.template_scope = TemplateScope.TENANT
        else:
            quiz.is_template = False
            quiz.template_scope = TemplateScope.TENANT

        await db.commit()
        await db.refresh(quiz)
        return self._to_quiz_response(quiz)

    async def list_public_templates(
        self,
        db: AsyncSession,
    ) -> List[TemplateQuizListItemResponse]:
        """List globally-scoped templates — no auth required (explore page)."""
        result = await db.execute(
            select(Quiz)
            .options(selectinload(Quiz.questions))
            .where(Quiz.is_template == True, Quiz.template_scope == TemplateScope.GLOBAL)
            .order_by(Quiz.template_use_count.desc(), Quiz.id)
        )
        templates = result.scalars().all()
        return [
            TemplateQuizListItemResponse(
                id=q.id,
                title=q.title,
                description=q.description,
                quiz_type=q.quiz_type,
                status=q.status,
                question_count=len(q.questions),
                template_scope=q.template_scope,
                tenant_id=q.tenant_id,
                created_at=q.created_at,
                template_category=q.template_category,
                template_use_count=q.template_use_count or 0,
            )
            for q in templates
        ]

    async def list_available_templates(
        self,
        db: AsyncSession,
        current_user: CurrentUser
    ) -> List[TemplateQuizListItemResponse]:
        """List templates visible to current user"""
        result = await db.execute(
            select(Quiz)
            .options(selectinload(Quiz.questions))
            .order_by(Quiz.updated_at.desc())
        )
        all_quizzes = result.scalars().all()
        templates = []
        for quiz in all_quizzes:
            scope_value = quiz.template_scope.value if hasattr(quiz.template_scope, "value") else str(quiz.template_scope)
            if not quiz.is_template:
                continue
            if quiz.tenant_id == current_user.tenant_id or scope_value == TemplateScope.GLOBAL.value:
                templates.append(quiz)

        return [
            TemplateQuizListItemResponse(
                id=q.id,
                title=q.title,
                description=q.description,
                quiz_type=q.quiz_type,
                status=q.status,
                question_count=len(q.questions),
                template_scope=q.template_scope,
                tenant_id=q.tenant_id,
                created_at=q.created_at,
                template_category=q.template_category,
                template_use_count=q.template_use_count or 0,
            )
            for q in templates
        ]

    async def create_quiz_from_template(
        self,
        db: AsyncSession,
        template_quiz_id: int,
        current_user: CurrentUser
    ) -> QuizResponse:
        """Create a new draft quiz from a visible template"""
        template_result = await db.execute(
            select(Quiz)
            .filter(Quiz.id == template_quiz_id)
            .options(selectinload(Quiz.questions))
        )
        template_quiz = template_result.scalar_one_or_none()
        if not template_quiz or not template_quiz.is_template:
            raise QuizNotFoundError("Template quiz not found")
        scope_value = template_quiz.template_scope.value if hasattr(template_quiz.template_scope, "value") else str(template_quiz.template_scope)
        if template_quiz.tenant_id != current_user.tenant_id and scope_value != TemplateScope.GLOBAL.value:
            raise QuizNotFoundError("Template quiz not found")

        tier_limits = await self.tier_service.get_tier_config(db, current_user.tenant.tier)
        max_questions = tier_limits["max_questions"]
        if len(template_quiz.questions) > max_questions:
            raise TierLimitExceededError(f"Template has {len(template_quiz.questions)} questions, but your tier allows {max_questions}")

        event = Event(
            tenant_id=current_user.tenant_id,
            creator_id=current_user.user_id,
            title=f"Template Session - {template_quiz.title}",
            description=None,
            join_code=None
        )
        db.add(event)
        await db.flush()

        copy_title = f"{template_quiz.title} (Template Copy)"
        if len(copy_title) > 255:
            copy_title = f"{template_quiz.title[:239]} (Template Copy)"

        new_quiz = Quiz(
            tenant_id=current_user.tenant_id,
            event_id=event.id,
            title=copy_title,
            description=template_quiz.description,
            quiz_type=template_quiz.quiz_type,
            status=QuizStatus.DRAFT,
            is_template=False,
            template_scope=TemplateScope.TENANT,
        )
        db.add(new_quiz)
        await db.flush()

        for question in sorted(template_quiz.questions, key=lambda q: q.order):
            db.add(
                Question(
                    quiz_id=new_quiz.id,
                    question_type=question.question_type,
                    text=question.text,
                    order=question.order,
                    options=list(question.options) if question.options else None,
                    correct_answer_index=question.correct_answer_index,
                    question_image_url=question.question_image_url,
                    question_video_url=question.question_video_url,
                    option_images=dict(question.option_images) if question.option_images else None,
                    points=question.points,
                    max_time_seconds=question.max_time_seconds,
                )
            )

        template_quiz.template_use_count = (template_quiz.template_use_count or 0) + 1
        await db.commit()

        quiz_result = await db.execute(
            select(Quiz)
            .filter(
                Quiz.id == new_quiz.id,
                Quiz.tenant_id == current_user.tenant_id
            )
            .options(selectinload(Quiz.questions))
        )
        created_quiz = quiz_result.scalar_one()
        return self._to_quiz_response(created_quiz)

    async def update_quiz(
        self,
        db: AsyncSession,
        quiz_id: int,
        request: QuizUpdate,
        current_user: CurrentUser
    ) -> QuizResponse:
        """Update quiz (only in DRAFT status)"""
        result = await db.execute(
            select(Quiz).filter(
                Quiz.id == quiz_id,
                Quiz.tenant_id == current_user.tenant_id
            )
        )
        quiz = result.scalar_one_or_none()
        
        if not quiz:
            raise QuizNotFoundError("Quiz not found")

        # Always allow proctoring_policy updates on published exams; all other edits require DRAFT
        if quiz.status != QuizStatus.DRAFT:
            if request.proctoring_policy is not None:
                data = request.model_dump(exclude_unset=True)
                if set(data.keys()) - {'proctoring_policy'}:
                    raise InvalidQuizStatusError("Can only edit quizzes in DRAFT status")
                quiz.proctoring_policy = request.proctoring_policy
                await db.commit()
                await db.refresh(quiz)
                return self._to_quiz_response(quiz)
            raise InvalidQuizStatusError("Can only edit quizzes in DRAFT status")

        # Update fields
        if request.title is not None:
            quiz.title = request.title
        if request.description is not None:
            quiz.description = request.description
        if request.quiz_type is not None:
            raw_type = request.quiz_type.value if hasattr(request.quiz_type, 'value') else str(request.quiz_type)
            quiz.quiz_type = QuizType.EXAM if any(k in raw_type.lower() for k in ["exam", "test"]) else QuizType(raw_type)
        # Offline poll fields
        if request.offline_start_at is not None:
            quiz.offline_start_at = request.offline_start_at
        if request.offline_end_at is not None:
            quiz.offline_end_at = request.offline_end_at
        if request.offline_results_email is not None:
            quiz.offline_results_email = request.offline_results_email

        # Exam fields
        if request.exam_start_at is not None:
            quiz.exam_start_at = request.exam_start_at
        if request.exam_end_at is not None:
            quiz.exam_end_at = request.exam_end_at
        if request.exam_time_limit_seconds is not None:
            quiz.exam_time_limit_seconds = request.exam_time_limit_seconds
        if request.exam_results_email is not None:
            quiz.exam_results_email = request.exam_results_email
        if request.exam_require_email is not None:
            quiz.exam_require_email = request.exam_require_email
        if request.exam_allowed_domains is not None:
            quiz.exam_allowed_domains = request.exam_allowed_domains or None

        # Proctoring policy
        if request.proctoring_policy is not None:
            quiz.proctoring_policy = request.proctoring_policy

        # Participant skin
        if 'skin' in request.model_fields_set:
            quiz.skin = request.skin

        # Emoji reactions
        if 'reaction_style' in request.model_fields_set:
            from features.quiz.reaction_sets import VALID_STYLES
            if request.reaction_style and request.reaction_style not in VALID_STYLES:
                raise QuizValidationError(f"Invalid reaction style: {request.reaction_style}")
            quiz.reaction_style = request.reaction_style

        await db.commit()
        await db.refresh(quiz)

        return self._to_quiz_response(quiz)

    async def delete_quiz(
        self,
        db: AsyncSession,
        quiz_id: int,
        current_user: CurrentUser
    ):
        """Delete quiz and all dependent data (sessions, participants, answers, feedback)."""
        result = await db.execute(
            select(Quiz).filter(
                Quiz.id == quiz_id,
                Quiz.tenant_id == current_user.tenant_id
            )
        )
        quiz = result.scalar_one_or_none()

        if not quiz:
            raise QuizNotFoundError("Quiz not found")

        if quiz.status not in (QuizStatus.DRAFT, QuizStatus.READY, QuizStatus.ARCHIVED):
            raise InvalidQuizStatusError("Quiz cannot be deleted in its current status")

        # Break circular FKs (quizzes.exam_session_id / offline_session_id → quiz_sessions)
        if quiz.exam_session_id is not None or quiz.offline_session_id is not None:
            quiz.exam_session_id = None
            quiz.offline_session_id = None
            await db.flush()

        # Get all session IDs for this quiz
        session_id_rows = (await db.execute(
            select(QuizSession.id).filter(QuizSession.quiz_id == quiz_id)
        )).scalars().all()
        session_ids = list(session_id_rows)

        if session_ids:
            # Delete quiz feedback tied to these sessions
            await db.execute(
                delete(QuizFeedback).where(QuizFeedback.session_id.in_(session_ids))
            )
            # Delete answers (references participants + questions)
            await db.execute(
                delete(Answer).where(Answer.session_id.in_(session_ids))
            )
            # Delete participants
            await db.execute(
                delete(Participant).where(Participant.session_id.in_(session_ids))
            )
            # Delete session question timings
            await db.execute(
                delete(SessionQuestionTiming).where(SessionQuestionTiming.session_id.in_(session_ids))
            )
            # Delete sessions
            await db.execute(
                delete(QuizSession).where(QuizSession.id.in_(session_ids))
            )

        # Delete quiz feedback tied directly to the quiz (not via session)
        await db.execute(
            delete(QuizFeedback).where(
                QuizFeedback.quiz_id == quiz_id,
                QuizFeedback.session_id.is_(None)
            )
        )

        await db.delete(quiz)
        await db.commit()
    
    async def publish_quiz(
        self,
        db: AsyncSession,
        quiz_id: int,
        current_user: CurrentUser
    ) -> QuizResponse:
        """Publish quiz (validate and change status to READY)"""
        result = await db.execute(
            select(Quiz)
            .filter(
                Quiz.id == quiz_id,
                Quiz.tenant_id == current_user.tenant_id
            )
            .options(selectinload(Quiz.questions))
        )
        quiz = result.scalar_one_or_none()
        
        if not quiz:
            raise QuizNotFoundError("Quiz not found")
        
        if quiz.status != QuizStatus.DRAFT:
            raise InvalidQuizStatusError("Quiz is already published")
        
        # Validate quiz
        self._validate_quiz(quiz)
        
        # Change status
        quiz.status = QuizStatus.READY
        await db.commit()
        await db.refresh(quiz)

        return self._to_quiz_response(quiz)

    async def publish_offline_poll(
        self,
        db: AsyncSession,
        quiz_id: int,
        current_user: CurrentUser
    ) -> OfflinePollPublishResponse:
        """Publish an offline poll: create a permanent ACTIVE session and generate a shareable slug."""
        from apscheduler.triggers.date import DateTrigger
        from core.stats import scheduler as stats_scheduler

        result = await db.execute(
            select(Quiz)
            .filter(
                Quiz.id == quiz_id,
                Quiz.tenant_id == current_user.tenant_id
            )
            .options(selectinload(Quiz.questions))
        )
        quiz = result.scalar_one_or_none()

        if not quiz:
            raise QuizNotFoundError("Quiz not found")

        if quiz.quiz_type != QuizType.OFFLINE_POLL:
            raise InvalidQuizStatusError("Quiz is not an offline poll")

        if quiz.status not in (QuizStatus.DRAFT, QuizStatus.READY):
            raise InvalidQuizStatusError("Offline poll is already active or archived")

        if quiz.poll_slug:
            raise InvalidQuizStatusError("Offline poll is already published")

        # Validate
        if not quiz.offline_start_at or not quiz.offline_end_at:
            raise QuizValidationError("Offline poll must have start and end dates set")

        if quiz.offline_end_at <= quiz.offline_start_at:
            raise QuizValidationError("End date must be after start date")

        # Validate quiz has at least one question
        if not quiz.questions:
            raise QuizValidationError("Offline poll must have at least one question")

        # Generate unique slug (retry up to 3 times)
        slug = None
        for _ in range(3):
            candidate = secrets.token_urlsafe(8)
            existing = await db.execute(
                select(Quiz).filter(Quiz.poll_slug == candidate)
            )
            if not existing.scalar_one_or_none():
                slug = candidate
                break

        if not slug:
            raise QuizValidationError("Failed to generate unique poll slug, please try again")

        # Create the permanent session in ACTIVE state
        session = QuizSession(
            quiz_id=quiz.id,
            tenant_id=quiz.tenant_id,
            status=QuizSessionStatus.ACTIVE,
            current_question_index=-1,
        )
        db.add(session)
        await db.flush()

        quiz.poll_slug = slug
        quiz.offline_session_id = session.id
        quiz.status = QuizStatus.READY
        await db.commit()
        await db.refresh(quiz)

        # Schedule results email job
        if quiz.offline_results_email and quiz.offline_end_at and stats_scheduler.scheduler:
            try:
                from features.quiz.offline_poll_service_async import send_results_email
                stats_scheduler.scheduler.add_job(
                    send_results_email,
                    trigger=DateTrigger(run_date=quiz.offline_end_at),
                    args=[quiz.id],
                    id=f"offline-poll-results:{quiz.id}",
                    replace_existing=True,
                    misfire_grace_time=300,
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to schedule results email for quiz {quiz.id}: {e}")

        frontend_url = os.getenv('FRONTEND_URL', 'https://www.swaya.me')
        return OfflinePollPublishResponse(
            poll_url=f"{frontend_url}/poll/{slug}",
            poll_slug=slug,
            quiz_id=quiz.id,
        )

    async def duplicate_quiz(
        self,
        db: AsyncSession,
        quiz_id: int,
        current_user: CurrentUser
    ) -> QuizResponse:
        """Duplicate quiz and all its questions as a new DRAFT quiz"""
        try:
            result = await db.execute(
                select(Quiz)
                .filter(
                    Quiz.id == quiz_id,
                    Quiz.tenant_id == current_user.tenant_id
                )
                .options(selectinload(Quiz.questions))
            )
            source_quiz = result.scalar_one_or_none()

            if not source_quiz:
                raise QuizNotFoundError("Quiz not found")

            duplicate_title = f"{source_quiz.title} (Copy)"
            if len(duplicate_title) > 255:
                duplicate_title = f"{source_quiz.title[:248]} (Copy)"

            duplicated_quiz = Quiz(
                tenant_id=current_user.tenant_id,
                event_id=source_quiz.event_id,
                title=duplicate_title,
                description=source_quiz.description,
                quiz_type=source_quiz.quiz_type,
                status=QuizStatus.DRAFT
            )
            db.add(duplicated_quiz)
            await db.flush()

            for question in sorted(source_quiz.questions, key=lambda q: q.order):
                db.add(
                    Question(
                        quiz_id=duplicated_quiz.id,
                        question_type=question.question_type,
                        text=question.text,
                        order=question.order,
                        options=list(question.options) if question.options else None,
                        correct_answer_index=question.correct_answer_index,
                        question_image_url=question.question_image_url,
                        question_video_url=question.question_video_url,
                        option_images=dict(question.option_images) if question.option_images else None,
                    )
                )

            await db.commit()

            duplicated_result = await db.execute(
                select(Quiz)
                .filter(
                    Quiz.id == duplicated_quiz.id,
                    Quiz.tenant_id == current_user.tenant_id
                )
                .options(selectinload(Quiz.questions))
            )
            duplicated_quiz = duplicated_result.scalar_one()

            return self._to_quiz_response(duplicated_quiz)
        except QuizNotFoundError:
            raise
        except Exception as e:
            await db.rollback()
            raise QuizValidationError(f"Failed to duplicate quiz: {str(e)}")
    
    async def unpublish_quiz(
        self,
        db: AsyncSession,
        quiz_id: int,
        current_user: CurrentUser
    ) -> QuizResponse:
        """Unpublish quiz (revert status to DRAFT for editing)"""
        result = await db.execute(
            select(Quiz).filter(
                Quiz.id == quiz_id,
                Quiz.tenant_id == current_user.tenant_id
            )
        )
        quiz = result.scalar_one_or_none()
        
        if not quiz:
            raise QuizNotFoundError("Quiz not found")
        
        if quiz.status == QuizStatus.DRAFT:
            raise InvalidQuizStatusError("Quiz is already in DRAFT status")
        
        # Change status back to DRAFT
        quiz.status = QuizStatus.DRAFT
        await db.commit()
        await db.refresh(quiz)

        return self._to_quiz_response(quiz)

    async def archive_quiz(
        self,
        db: AsyncSession,
        quiz_id: int,
        current_user: CurrentUser
    ) -> QuizListResponse:
        """Soft-archive a quiz — hidden from default list but recoverable."""
        result = await db.execute(
            select(Quiz)
            .filter(Quiz.id == quiz_id, Quiz.tenant_id == current_user.tenant_id)
            .options(selectinload(Quiz.questions), selectinload(Quiz.folder))
        )
        quiz = result.scalar_one_or_none()
        if not quiz:
            raise QuizNotFoundError("Quiz not found")
        if quiz.archived_at is not None:
            raise InvalidQuizStatusError("Quiz is already archived")
        quiz.archived_at = datetime.utcnow()
        await db.commit()
        await db.refresh(quiz)
        quiz_ids = [quiz.id]
        response_count_map: dict[int, int] = {}
        response_rows = await db.execute(
            select(QuizSession.quiz_id, func.count(Participant.id).label("cnt"))
            .join(Participant, Participant.session_id == QuizSession.id)
            .filter(QuizSession.quiz_id.in_(quiz_ids))
            .group_by(QuizSession.quiz_id)
        )
        response_count_map = {row.quiz_id: row.cnt for row in response_rows}
        return QuizListResponse(
            id=quiz.id,
            event_id=quiz.event_id,
            title=quiz.title,
            quiz_type=quiz.quiz_type,
            status=quiz.status,
            folder_id=quiz.folder_id,
            folder_path=" / ".join(self._folder_path_names(quiz.folder)) if quiz.folder else None,
            is_template=quiz.is_template,
            template_scope=quiz.template_scope,
            question_count=len(quiz.questions),
            response_count=response_count_map.get(quiz.id, 0),
            has_active_session=False,
            active_session_id=None,
            created_at=quiz.created_at.isoformat(),
            archived_at=quiz.archived_at,
        )

    async def unarchive_quiz(
        self,
        db: AsyncSession,
        quiz_id: int,
        current_user: CurrentUser
    ) -> QuizListResponse:
        """Restore an archived quiz back to its previous status."""
        result = await db.execute(
            select(Quiz)
            .filter(Quiz.id == quiz_id, Quiz.tenant_id == current_user.tenant_id)
            .options(selectinload(Quiz.questions), selectinload(Quiz.folder))
        )
        quiz = result.scalar_one_or_none()
        if not quiz:
            raise QuizNotFoundError("Quiz not found")
        if quiz.archived_at is None:
            raise InvalidQuizStatusError("Quiz is not archived")
        quiz.archived_at = None
        await db.commit()
        await db.refresh(quiz)
        return QuizListResponse(
            id=quiz.id,
            event_id=quiz.event_id,
            title=quiz.title,
            quiz_type=quiz.quiz_type,
            status=quiz.status,
            folder_id=quiz.folder_id,
            folder_path=" / ".join(self._folder_path_names(quiz.folder)) if quiz.folder else None,
            is_template=quiz.is_template,
            template_scope=quiz.template_scope,
            question_count=len(quiz.questions),
            response_count=0,
            has_active_session=False,
            active_session_id=None,
            created_at=quiz.created_at.isoformat(),
            archived_at=None,
        )

    def _validate_quiz(self, quiz: Quiz):
        """Validate quiz before publishing"""
        if not quiz.questions:
            raise QuizValidationError("Quiz must have at least one question")
        
        if len(quiz.questions) < 1:
            raise QuizValidationError("Quiz must have at least one question")
        
        # Validate each question
        for question in quiz.questions:
            if not question.text or not question.text.strip():
                raise QuizValidationError("All questions must have text")
            
            # Validate based on question type
            if question.question_type == QuestionType.MCQ:
                if not question.options or len(question.options) < 2:
                    raise QuizValidationError("MCQ questions must have at least 2 options")
                if len(question.options) > 10:
                    raise QuizValidationError("MCQ questions can have at most 10 options")
                if (
                    question.correct_answer_index is not None
                    and not (0 <= question.correct_answer_index < len(question.options))
                ):
                    raise QuizValidationError("MCQ questions must have valid correct answer index")
                if quiz.quiz_type != QuizType.POLL and question.correct_answer_index is None:
                    raise QuizValidationError("MCQ questions must have a correct answer for quiz mode")
            elif question.question_type == QuestionType.SCALE:
                if not question.options or len(question.options) != 5:
                    raise QuizValidationError("Scale questions must have exactly 5 options")
                if (
                    question.correct_answer_index is not None
                    and (question.correct_answer_index < 0 or question.correct_answer_index > 4)
                ):
                    raise QuizValidationError("Scale questions must have a valid correct answer index")
                if quiz.quiz_type != QuizType.POLL and question.correct_answer_index is None:
                    raise QuizValidationError("Scale questions must have a correct answer for quiz mode")
            elif question.question_type == QuestionType.WORD_CLOUD:
                # Word cloud questions don't need options or correct answer
                pass
            elif question.question_type in (QuestionType.SINGLE_LINE, QuestionType.PARAGRAPH):
                if question.options is not None and len(question.options) > 1:
                    raise QuizValidationError("Text questions can have at most one expected answer")
                if question.correct_answer_index is not None:
                    raise QuizValidationError("Text questions cannot have a correct answer index")
    
    def _to_quiz_response(self, quiz: Quiz) -> QuizResponse:
        """Convert quiz to response model"""
        # Get base URL from environment
        base_url = os.getenv('BASE_URL', 'http://localhost:8000')
        loaded_questions = quiz.__dict__.get("questions") or []
        
        loaded_folder = quiz.__dict__.get("folder")
        return QuizResponse(
            id=quiz.id,
            event_id=quiz.event_id,
            title=quiz.title,
            description=quiz.description,
            quiz_type=quiz.quiz_type,
            status=quiz.status,
            folder_id=quiz.folder_id,
            folder_path=" / ".join(self._folder_path_names(loaded_folder)) if loaded_folder else None,
            is_template=quiz.is_template,
            template_scope=quiz.template_scope,
            questions=[
                QuestionResponse(
                    id=q.id,
                    question_type=q.question_type,
                    text=q.text,
                    options=q.options,
                    order=q.order,
                    correct_answer_index=q.correct_answer_index,
                    question_image_url=ImageService.to_absolute_url(
                        q.question_image_url, base_url
                    ),
                    question_video_url=q.question_video_url,
                    option_images={
                        key: ImageService.to_absolute_url(path, base_url)
                        for key, path in (q.option_images or {}).items()
                    } if q.option_images else None,
                    points=q.points,
                    max_time_seconds=q.max_time_seconds,
                    negative_points=getattr(q, 'negative_points', 0) or 0,
                    answer_explanation=q.answer_explanation,
                )
                for q in sorted(loaded_questions, key=lambda x: x.order)
            ],
            question_count=len(loaded_questions),
            created_at=quiz.created_at.isoformat(),
            updated_at=quiz.updated_at.isoformat(),
            poll_slug=getattr(quiz, 'poll_slug', None),
            poll_url=(
                f"{os.getenv('FRONTEND_URL', 'https://www.swaya.me')}/poll/{quiz.poll_slug}"
                if getattr(quiz, 'poll_slug', None) else None
            ),
            offline_start_at=getattr(quiz, 'offline_start_at', None),
            offline_end_at=getattr(quiz, 'offline_end_at', None),
            offline_results_email=getattr(quiz, 'offline_results_email', None),
            exam_slug=getattr(quiz, 'exam_slug', None),
            exam_url=(
                f"{os.getenv('FRONTEND_URL', 'https://www.swaya.me')}/e/{quiz.exam_slug}"
                if getattr(quiz, 'exam_slug', None) else None
            ),
            exam_start_at=getattr(quiz, 'exam_start_at', None),
            exam_end_at=getattr(quiz, 'exam_end_at', None),
            exam_time_limit_seconds=getattr(quiz, 'exam_time_limit_seconds', None),
            exam_results_email=getattr(quiz, 'exam_results_email', None),
            exam_require_email=bool(getattr(quiz, 'exam_require_email', False)),
            exam_allowed_domains=getattr(quiz, 'exam_allowed_domains', None),
            has_previous_session=bool(getattr(quiz, 'exam_session_id', None)),
            proctoring_policy=getattr(quiz, 'proctoring_policy', None),
            skin=getattr(quiz, 'skin', None),
            reaction_style=getattr(quiz, 'reaction_style', None),
        )
