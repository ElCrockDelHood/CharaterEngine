"""Role service for CHARACTER ENGINE backend (C6).

Implements role management: creation, bootstrap, assignment, revocation and
current-role queries, following the append-only ``UserRole`` history model
(spec section 4.4).

Persistence notes
-----------------
``UserRole.role_id`` is a FOREIGN KEY to ``roles.id`` (the surrogate UUID),
NOT to the human readable ``roles.role_id`` (``"user"`` / ``"admin"``). All
public methods of this service accept the human readable identifier and
resolve it internally, so callers never deal with surrogate keys.
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.authorization.authorization_domain import (
    AuthorizationError,
    LastAdminError,
    Role,
    RoleAlreadyExistsError,
    RoleAssignment,
    RoleAssignmentError,
    RoleNotFoundError,
)
from backend.database.models import Role as RoleModel
from backend.database.models import UserRole as UserRoleModel

VALID_ROLE_IDS = ("user", "admin")
USER_ROLE_ID = "user"
ADMIN_ROLE_ID = "admin"


def _utcnow() -> datetime:
    """Naive UTC timestamp compatible with the DateTime columns used by the models."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RoleService:
    """Role service for role management."""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_role_id(role_id: str) -> None:
        if role_id not in VALID_ROLE_IDS:
            raise RoleAssignmentError(
                f"Invalid role_id: {role_id!r}. Must be one of {VALID_ROLE_IDS}."
            )

    @staticmethod
    def _get_role_model(db: Session, role_id: str) -> Optional[RoleModel]:
        return db.execute(
            select(RoleModel).where(RoleModel.role_id == role_id)
        ).scalar_one_or_none()

    @staticmethod
    def _require_role_model(db: Session, role_id: str) -> RoleModel:
        role_model = RoleService._get_role_model(db, role_id)
        if role_model is None:
            raise RoleNotFoundError(f"Role {role_id!r} not found. Run bootstrap_roles first.")
        return role_model

    @staticmethod
    def _to_domain(role_model: RoleModel) -> Role:
        return Role(
            role_id=role_model.role_id,
            role_name=role_model.role_name,
            description=role_model.description,
            created_at=role_model.created_at,
        )

    @staticmethod
    def _assignment_to_domain(user_role: UserRoleModel, role_id: str) -> RoleAssignment:
        return RoleAssignment(
            assignment_id=user_role.id,
            user_id=user_role.user_id,
            role_id=role_id,
            assigned_by=user_role.assigned_by,
            assigned_at=user_role.assigned_at,
            revoked_at=user_role.revoked_at,
        )

    @staticmethod
    def _get_active_assignment(db: Session, user_id: str, role_pk: str) -> Optional[UserRoleModel]:
        return db.execute(
            select(UserRoleModel).where(
                UserRoleModel.user_id == user_id,
                UserRoleModel.role_id == role_pk,
                UserRoleModel.revoked_at.is_(None),
            )
        ).scalar_one_or_none()

    # ------------------------------------------------------------------
    # Roles
    # ------------------------------------------------------------------
    @staticmethod
    def create_role(
        db: Session,
        role_id: str,
        role_name: str,
        description: Optional[str] = None
    ) -> Role:
        """Create a new role.

        Raises:
            RoleAssignmentError: If role_id is not a known role identifier.
            RoleAlreadyExistsError: If the role already exists.
        """
        RoleService._validate_role_id(role_id)

        if RoleService._get_role_model(db, role_id) is not None:
            raise RoleAlreadyExistsError(f"Role with role_id {role_id!r} already exists")

        role_model = RoleModel(
            id=str(uuid4()),
            role_id=role_id,
            role_name=role_name,
            description=description,
            created_at=_utcnow(),
        )

        try:
            db.add(role_model)
            db.commit()
            db.refresh(role_model)
        except Exception as exc:  # pragma: no cover - defensive
            db.rollback()
            raise AuthorizationError("Failed to persist role") from exc

        return RoleService._to_domain(role_model)

    @staticmethod
    def get_role(db: Session, role_id: str) -> Optional[Role]:
        """Get role by human readable identifier, or None if not found."""
        role_model = RoleService._get_role_model(db, role_id)
        return RoleService._to_domain(role_model) if role_model else None

    @staticmethod
    def bootstrap_roles(db: Session) -> None:
        """Bootstrap initial roles (USER and ADMIN). Idempotent-safe: fails loudly if run twice.

        Raises:
            RoleAlreadyExistsError: If any role already exists.
        """
        if RoleService._get_role_model(db, USER_ROLE_ID) or RoleService._get_role_model(db, ADMIN_ROLE_ID):
            raise RoleAlreadyExistsError("Roles already exist. Bootstrap can only be run once.")

        RoleService.create_role(
            db=db,
            role_id=USER_ROLE_ID,
            role_name="User",
            description="Standard user role with self-permissions",
        )
        RoleService.create_role(
            db=db,
            role_id=ADMIN_ROLE_ID,
            role_name="Administrator",
            description="System administrator with system-permissions",
        )

    # ------------------------------------------------------------------
    # Assignments (append-only history)
    # ------------------------------------------------------------------
    @staticmethod
    def assign_role(
        db: Session,
        user_id: str,
        role_id: str,
        assigned_by: Optional[str]
    ) -> RoleAssignment:
        """Assign a role to a user.

        Args:
            db: Database session
            user_id: Target user ID
            role_id: Human readable role identifier ("user" / "admin")
            assigned_by: User ID of the actor performing the assignment
                (``None`` only for SYSTEM assignments such as user creation)

        Raises:
            RoleAssignmentError: invalid role, duplicate active assignment,
                or admin self-assignment.
            RoleNotFoundError: role has not been bootstrapped.
        """
        RoleService._validate_role_id(role_id)
        if not user_id:
            raise RoleAssignmentError("user_id must be a non-empty string")

        # Spec 4.2: self-assignment of the admin role is prohibited.
        if role_id == ADMIN_ROLE_ID and assigned_by is not None and assigned_by == user_id:
            raise RoleAssignmentError("Self-assignment of the admin role is prohibited")

        role_model = RoleService._require_role_model(db, role_id)

        if RoleService._get_active_assignment(db, user_id, role_model.id) is not None:
            raise RoleAssignmentError(f"User already has active role {role_id!r}")

        user_role = UserRoleModel(
            id=str(uuid4()),
            user_id=user_id,
            role_id=role_model.id,
            assigned_by=assigned_by,
            assigned_at=_utcnow(),
            revoked_at=None,
        )

        try:
            db.add(user_role)
            db.commit()
            db.refresh(user_role)
        except Exception as exc:
            db.rollback()
            raise RoleAssignmentError("Failed to persist role assignment") from exc

        return RoleService._assignment_to_domain(user_role, role_id)

    @staticmethod
    def revoke_role(
        db: Session,
        user_id: str,
        role_id: str,
        revoked_by: Optional[str]
    ) -> Optional[RoleAssignment]:
        """Revoke a role from a user (append-only: sets ``revoked_at``).

        Returns:
            The revoked assignment, or ``None`` if the user had no active assignment.

        Raises:
            RoleAssignmentError: attempting to revoke the USER role (spec 4.1)
                or admin self-revocation (spec 4.2).
            LastAdminError: attempting to revoke the last active admin.
        """
        RoleService._validate_role_id(role_id)

        if role_id == USER_ROLE_ID:
            raise RoleAssignmentError("The USER role cannot be revoked")

        if role_id == ADMIN_ROLE_ID and revoked_by is not None and revoked_by == user_id:
            raise RoleAssignmentError("Self-revocation of the admin role is prohibited")

        role_model = RoleService._require_role_model(db, role_id)
        user_role = RoleService._get_active_assignment(db, user_id, role_model.id)
        if user_role is None:
            return None

        if role_id == ADMIN_ROLE_ID:
            admin_count = db.execute(
                select(func.count()).select_from(UserRoleModel).where(
                    UserRoleModel.role_id == role_model.id,
                    UserRoleModel.revoked_at.is_(None),
                )
            ).scalar_one()
            if admin_count <= 1:
                raise LastAdminError("Cannot revoke the last admin role in the system")

        user_role.revoked_at = _utcnow()
        try:
            db.commit()
            db.refresh(user_role)
        except Exception as exc:
            db.rollback()
            raise RoleAssignmentError("Failed to persist role revocation") from exc

        return RoleService._assignment_to_domain(user_role, role_id)

    @staticmethod
    def get_user_roles(db: Session, user_id: str) -> List[str]:
        """Get the ACTIVE role identifiers of a user (``revoked_at IS NULL``)."""
        rows = db.execute(
            select(RoleModel.role_id)
            .join(UserRoleModel, UserRoleModel.role_id == RoleModel.id)
            .where(
                UserRoleModel.user_id == user_id,
                UserRoleModel.revoked_at.is_(None),
            )
            .order_by(RoleModel.role_id)
        ).scalars().all()
        return list(rows)

    @staticmethod
    def get_role_history(db: Session, user_id: str) -> List[RoleAssignment]:
        """Get the complete (active + revoked) assignment history of a user."""
        rows = db.execute(
            select(UserRoleModel, RoleModel.role_id)
            .join(RoleModel, RoleModel.id == UserRoleModel.role_id)
            .where(UserRoleModel.user_id == user_id)
            .order_by(UserRoleModel.assigned_at)
        ).all()
        return [RoleService._assignment_to_domain(user_role, role_id) for user_role, role_id in rows]

    @staticmethod
    def has_role(db: Session, user_id: str, role_id: str) -> bool:
        """Check whether the user currently holds the given role."""
        return role_id in RoleService.get_user_roles(db, user_id)

    @staticmethod
    def count_active_admins(db: Session) -> int:
        """Number of users currently holding the ADMIN role."""
        role_model = RoleService._get_role_model(db, ADMIN_ROLE_ID)
        if role_model is None:
            return 0
        return db.execute(
            select(func.count()).select_from(UserRoleModel).where(
                UserRoleModel.role_id == role_model.id,
                UserRoleModel.revoked_at.is_(None),
            )
        ).scalar_one()

    @staticmethod
    def assign_user_role_on_creation(db: Session, user_id: str) -> RoleAssignment:
        """Assign the USER role to a newly created user (SYSTEM assignment, ``assigned_by=None``)."""
        return RoleService.assign_role(db, user_id=user_id, role_id=USER_ROLE_ID, assigned_by=None)
