# ADR-0003: Repository Pattern for Data Access

## Status

Deprecated (January 2026)

> **Note**: This ADR is deprecated. The repository pattern and PostgreSQL database layer were removed as part of the refactoring to a minimal API-only backend. Kept for historical reference.

## Context

We need a data access strategy that:

- Decouples business logic from database implementation
- Enables unit testing without a real database
- Supports async database operations with SQLAlchemy 2.x
- Allows potential future migration to different data stores
- Provides a consistent API for CRUD operations

This decision implements the data access layer within the architecture defined in ADR-0001.

## Decision

We adopt the **Repository Pattern** with abstract interfaces in the domain layer and concrete implementations in the infrastructure layer.

### Structure

```
src/
├── domain/
│   ├── entities.py        # Pydantic domain models
│   └── repositories.py    # Abstract repository interfaces
│
└── infrastructure/
    ├── database/
    │   ├── models.py      # SQLAlchemy ORM models
    │   └── session.py     # Database session management
    └── repositories/
        ├── user_repo.py
        ├── audit_repo.py
        └── refresh_token_repo.py
```

### Implementation Pattern

**1. Domain Entity (Pydantic)**

```python
class User(BaseModel):
    id: UUID
    email: str
    password_hash: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

**2. Abstract Repository Interface**

```python
class UserRepository(ABC):
    @abstractmethod
    async def create(self, user: User) -> User: ...

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[User]: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]: ...

    @abstractmethod
    async def update(self, user: User) -> User: ...

    @abstractmethod
    async def delete(self, user_id: UUID) -> None: ...
```

**3. SQLAlchemy Model**

```python
class UserModel(Base):
    __tablename__ = "users"
    id = Column(UUID, primary_key=True)
    email = Column(String, unique=True)
    # ... other columns
```

**4. Concrete Repository Implementation**

```python
class UserRepositoryImpl(UserRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(
            select(UserModel).where(UserModel.email == email)
        )
        model = result.scalar_one_or_none()
        return User.model_validate(model) if model else None
```

### Dependency Injection

Repositories are injected via FastAPI's `Depends()`:

```python
def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepositoryImpl(db)

def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
) -> AuthService:
    return AuthService(user_repo=user_repo, ...)
```

## Consequences

### Positive

- **Testability**: Services can be tested with mock repositories
- **Separation**: Domain entities independent of ORM models
- **Flexibility**: Can swap database implementations without changing services
- **Async support**: Clean async/await throughout the data access layer
- **Type safety**: Abstract interfaces enforce consistent API

### Negative

- **Mapping overhead**: Entity ↔ Model conversion on each operation
- **More code**: Both interface and implementation for each repository
- **Indirection**: Additional layer between service and database

### Neutral

- Services work with domain entities, not ORM models
- Database session managed at request scope via dependency injection

## Alternatives Considered

### Alternative 1: Direct ORM Access in Services

Services directly use SQLAlchemy sessions and models.

**Rejected because**:

- Couples business logic to SQLAlchemy
- Harder to test services without database
- Domain entities would be ORM models

### Alternative 2: Active Record Pattern

Entities have their own persistence methods (`user.save()`).

**Rejected because**:

- Couples entities to database
- Harder to test
- Less explicit about database operations

### Alternative 3: Generic Repository

Single generic repository `Repository[T]` for all entities.

**Considered but not fully adopted**:

- Less type safety for entity-specific queries
- May add generic base class later for common operations
- Current implementation keeps entity-specific interfaces for clarity

### Alternative 4: CQRS (Command Query Separation)

Separate read and write models/repositories.

**Rejected because**:

- Adds significant complexity
- Overkill for current requirements
- Can be adopted later for read-heavy scenarios

## Implementation Notes

### Entity to Model Mapping

Using Pydantic's `model_validate()` for automatic mapping:

```python
# Model -> Entity
User.model_validate(user_model)

# Entity -> Model (explicit)
user_model = UserModel(**user.model_dump())
```

### Session Lifecycle

Database sessions are scoped to HTTP requests:

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
```

## References

- [Repository Pattern - Martin Fowler](https://martinfowler.com/eaaCatalog/repository.html)
- [SQLAlchemy 2.0 Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- ADR-0001: Layered Architecture (defines layer boundaries)
