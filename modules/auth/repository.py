from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.auth.models import Permission, Role, RolePermission, User, UserRole
from app.shared.base_repository import BaseRepository, TenantScopedRepository


class UserRepository(TenantScopedRepository[User]):
    model = User

    async def get_by_email(self, tenant_id: UUID, email: str) -> User | None:
        stmt = select(User).where(User.tenant_id == tenant_id, User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_roles(self, user_id: UUID) -> User | None:
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.roles).selectinload(UserRole.role))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class RoleRepository(TenantScopedRepository[Role]):
    model = Role

    async def get_by_name(self, tenant_id: UUID, name: str) -> Role | None:
        stmt = select(Role).where(Role.tenant_id == tenant_id, Role.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class PermissionRepository(BaseRepository[Permission]):
    model = Permission

    async def get_by_code(self, code: str) -> Permission | None:
        stmt = select(Permission).where(Permission.code == code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_codes(self, codes: list[str]) -> list[Permission]:
        stmt = select(Permission).where(Permission.code.in_(codes))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class UserRoleRepository(BaseRepository[UserRole]):
    model = UserRole

    async def assign_role(self, user_id: UUID, role_id: UUID, tenant_id: UUID) -> UserRole:
        user_role = UserRole(user_id=user_id, role_id=role_id, tenant_id=tenant_id)
        return await self.create(user_role)


class RolePermissionRepository(BaseRepository[RolePermission]):
    model = RolePermission

    async def assign_permission(self, role_id: UUID, permission_id: UUID) -> RolePermission:
        rp = RolePermission(role_id=role_id, permission_id=permission_id)
        return await self.create(rp)
