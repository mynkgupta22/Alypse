from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from app.models.user import User, UserEmail, UserSession, UserRole
from app.schemas.user_schemas import UserCreate
from app.auth.auth_utils import get_password_hash, generate_session_token, verify_password
from datetime import datetime, timedelta
from typing import Optional,List
import logging

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # -------------------------
    # GETTERS
    # -------------------------
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        result = await self.db.execute(
            select(User).options(selectinload(User.emails)).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).options(selectinload(User.emails)).where(User.username == username.lower())
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).join(UserEmail).options(selectinload(User.emails))
            .where(UserEmail.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_user_by_google_id(self, google_id: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).options(selectinload(User.emails)).where(User.google_id == google_id)
        )
        return result.scalar_one_or_none()

    async def username_exists(self, username: str) -> bool:
        result = await self.db.execute(
            select(User.id).where(User.username == username.lower())
        )
        return result.scalar_one_or_none() is not None

    async def email_exists(self, email: str) -> bool:
        result = await self.db.execute(
            select(UserEmail.id).where(UserEmail.email == email.lower())
        )
        return result.scalar_one_or_none() is not None

    # -------------------------
    # CREATE USER
    # -------------------------
    async def create_user(self, user_data: UserCreate) -> User:
        try:
            db_user = User(
                username=user_data.username.lower(),
                full_name=user_data.full_name,
                password_hash=get_password_hash(user_data.password) if user_data.password else None,
                role=UserRole.FREE_USER,
                is_verified=False
            )

            self.db.add(db_user)
            await self.db.flush()

            # Add emails
            primary_set = False
            for email_data in user_data.emails:
                is_primary = email_data.is_primary or not primary_set
                if is_primary:
                    primary_set = True

                db_email = UserEmail(
                    user_id=db_user.id,
                    email=email_data.email.lower(),
                    is_primary=is_primary,
                    is_verified=False
                )
                self.db.add(db_email)

            await self.db.commit()
            await self.db.refresh(db_user)

            # Reload with emails
            result = await self.db.execute(
                select(User).options(selectinload(User.emails)).where(User.id == db_user.id)
            )
            db_user = result.scalar_one()

            logger.info(f"Created user: {db_user.username} (ID: {db_user.id})")
            return db_user

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating user: {e}")
            raise

    async def create_google_user(self, google_data: dict) -> User:
        try:
            base_username = google_data["email"].split("@")[0].lower()
            username = base_username
            counter = 1

            while await self.username_exists(username):
                username = f"{base_username}{counter}"
                counter += 1

            db_user = User(
                google_id=google_data["google_id"],
                username=username,
                full_name=google_data["full_name"],
                role=UserRole.FREE_USER,
                is_verified=google_data.get("verified_email", False)
            )

            self.db.add(db_user)
            await self.db.flush()

            db_email = UserEmail(
                user_id=db_user.id,
                email=google_data["email"].lower(),
                is_primary=True,
                is_verified=google_data.get("verified_email", False),
                verified_at=datetime.utcnow() if google_data.get("verified_email") else None
            )
            self.db.add(db_email)

            await self.db.commit()
            await self.db.refresh(db_user)

            result = await self.db.execute(
                select(User).options(selectinload(User.emails)).where(User.id == db_user.id)
            )
            db_user = result.scalar_one()

            logger.info(f"Created Google user: {db_user.username} (ID: {db_user.id})")
            return db_user

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating Google user: {e}")
            raise

    # -------------------------
    # AUTHENTICATION
    # -------------------------
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        user = await self.get_user_by_username(username)
        if not user or not user.password_hash:
            return None

        if not verify_password(password, user.password_hash):
            return None

        return user

    # -------------------------
    # SESSION MANAGEMENT
    # -------------------------
    async def create_session(
        self,
        user_id: int,
        ip_address: str = None,
        user_agent: str = None,
        login_method: str = "password"
    ) -> UserSession:
        try:
            session = UserSession(
                user_id=user_id,
                session_token=generate_session_token(),
                expires_at=datetime.utcnow() + timedelta(hours=24),
                ip_address=ip_address,
                user_agent=user_agent,
                login_method=login_method
            )

            self.db.add(session)
            await self.db.commit()
            await self.db.refresh(session)
            logger.info(f"Created session for user {user_id}")
            return session

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating session: {e}")
            raise

    async def deactivate_user_sessions(self, user_id: int):
        try:
            await self.db.execute(
                update(UserSession).where(UserSession.user_id == user_id).values(is_active=False)
            )
            await self.db.commit()
            logger.info(f"Deactivated sessions for user {user_id}")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deactivating sessions: {e}")
            raise

    async def get_active_sessions(self, user_id: int) -> List[UserSession]:
        result = await self.db.execute(
            select(UserSession).where(UserSession.user_id == user_id, UserSession.is_active == True)
        )
        return result.scalars().all()

    async def refresh_session(self, session_token: str, hours: int = 24) -> Optional[UserSession]:
        try:
            result = await self.db.execute(
                select(UserSession).where(
                    UserSession.session_token == session_token, UserSession.is_active == True
                )
            )
            session = result.scalar_one_or_none()
            if not session:
                return None

            session.expires_at = datetime.utcnow() + timedelta(hours=hours)
            session.last_used_at = datetime.utcnow()

            await self.db.commit()
            await self.db.refresh(session)
            return session

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error refreshing session: {e}")
            raise    

    # -------------------------
    # EMAIL MANAGEMENT
    # -------------------------
    async def add_email_to_user(
        self, user_id: int, email: str, is_primary: bool = False
    ) -> UserEmail:
        try:
            if is_primary:
                await self.db.execute(
                    update(UserEmail).where(UserEmail.user_id == user_id).values(is_primary=False)
                )

            db_email = UserEmail(
                user_id=user_id,
                email=email.lower(),
                is_primary=is_primary,
                is_verified=False,
            )

            self.db.add(db_email)
            await self.db.commit()
            await self.db.refresh(db_email)
            return db_email

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error adding email to user: {e}")
            raise

    async def verify_email(self, token: str) -> bool:
        """Mark email as verified if token matches"""
        try:
            result = await self.db.execute(
                select(UserEmail).where(UserEmail.verification_token == token)
            )
            email = result.scalar_one_or_none()
            if not email:
                return False

            email.is_verified = True
            email.verified_at = datetime.utcnow()
            email.verification_token = None
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error verifying email: {e}")
            raise

    # -------------------------
    # USER PROFILE MANAGEMENT
    # -------------------------
    async def update_user_profile(
        self,
        user_id: int,
        full_name: Optional[str] = None,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[User]:
        try:
            result = await self.db.execute(select(User).where(User.id == user_id, User.is_deleted == False))
            user = result.scalar_one_or_none()
            if not user:
                return None

            if full_name:
                user.full_name = full_name
            if role:
                user.role = role
            if is_active is not None:
                user.is_active = is_active

            user.updated_at = datetime.utcnow()

            await self.db.commit()
            await self.db.refresh(user)
            return user
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating user profile: {e}")
            raise

    async def delete_user(self, user_id: int) -> bool:
        """Soft delete a user (mark is_deleted=True)"""
        try:
            result = await self.db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                return False

            user.is_deleted = True
            user.is_active = False

            # deactivate sessions too
            await self.deactivate_user_sessions(user_id)

            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting user: {e}")
            raise