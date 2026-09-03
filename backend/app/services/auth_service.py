"""
Authentication and authorization service using JWT.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import uuid

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer  # Added this import

from app.models.geospatial import User
from app.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    """Authentication service for user management and JWT tokens."""
    
    def __init__(self):
        self.secret_key = settings.JWT_SECRET
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_minutes = settings.JWT_EXPIRE_MINUTES
        
        # This fixes the AttributeError: 'AuthService' object has no attribute 'oauth2_scheme'
        # It points to the 'token' endpoint which should be defined in your auth routes.
        self.oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Generate password hash."""
        return pwd_context.hash(password)
    
    def authenticate_user(self, db: Session, email: str, password: str) -> Optional[User]:
        """Authenticate a user by email and password."""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode and verify a JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None
    
    def get_current_user(self, db: Session, token: str) -> Optional[User]:
        """Get current user from JWT token."""
        payload = self.decode_token(token)
        if payload is None:
            return None
        
        user_id = payload.get("sub")
        if user_id is None:
            return None
        
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            return None
        
        user = db.query(User).filter(User.id == user_uuid).first()
        return user
    
    def create_user(self, db: Session, user_data: Dict[str, Any]) -> User:
        """Create a new user."""
        existing_user = db.query(User).filter(
            (User.email == user_data["email"]) | (User.username == user_data["username"])
        ).first()
        
        if existing_user:
            raise ValueError("User with this email or username already exists")
        
        hashed_password = self.get_password_hash(user_data["password"])
        
        user = User(
            email=user_data["email"],
            username=user_data["username"],
            full_name=user_data.get("full_name", ""),
            hashed_password=hashed_password,
            is_active=True,
            is_superuser=user_data.get("is_superuser", False)
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def update_user(self, db: Session, user_id: uuid.UUID, update_data: Dict[str, Any]) -> User:
        """Update user information."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        for key, value in update_data.items():
            if key == "password":
                user.hashed_password = self.get_password_hash(value)
            elif key == "email":
                existing = db.query(User).filter(User.email == value, User.id != user_id).first()
                if existing:
                    raise ValueError("Email already in use")
                user.email = value
            elif key == "username":
                existing = db.query(User).filter(User.username == value, User.id != user_id).first()
                if existing:
                    raise ValueError("Username already in use")
                user.username = value
            elif hasattr(user, key):
                setattr(user, key, value)
        
        db.commit()
        db.refresh(user)
        return user
    
    def delete_user(self, db: Session, user_id: uuid.UUID) -> bool:
        """Delete a user."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        db.delete(user)
        db.commit()
        return True
    
    def generate_password_reset_token(self, email: str) -> str:
        """Generate a password reset token."""
        expire = datetime.utcnow() + timedelta(hours=24)
        to_encode = {"sub": email, "exp": expire, "type": "password_reset"}
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def verify_password_reset_token(self, token: str) -> Optional[str]:
        """Verify a password reset token and return email."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            if payload.get("type") != "password_reset":
                return None
            return payload.get("sub")
        except JWTError:
            return None

# Create global auth service instance
auth_service = AuthService()