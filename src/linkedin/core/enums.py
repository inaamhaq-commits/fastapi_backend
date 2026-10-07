from enum import StrEnum


class JobStatus(StrEnum):
    QUEUED = "queued"
    PLANNING = "planning"
    RUNNING = "running"
    AGGREGATING = "aggregating"
    COMPLETED = "completed"
    PARTIAL_FAILED = "partial_failed"
    FAILED = "failed"


class ActorTaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ClientStatus(StrEnum):
    NEW = "new"
    ACTIVE = "active"
    INACTIVE = "inactive"


class UserRole(StrEnum):
    USER = "user"
    MANAGER = "manager"


class KnowledgeProjectStatus(StrEnum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    ACTIVE = "active"
    PARTIAL_FAILED = "partial_failed"
    FAILED = "failed"


class KnowledgeFileUploadStatus(StrEnum):
    PENDING = "pending"
    UPLOADED = "uploaded"
    FAILED = "failed"


class KnowledgeFileProcessingStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class KnowledgeChunkStatus(StrEnum):
    ACTIVE = "active"
    DELETED = "deleted"


class ConversationStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class ConversationSenderType(StrEnum):
    CLIENT = "client"
    USER = "user"
    AI = "ai"
    FINALIZED = "finalized"


class AiSuggestionStatus(StrEnum):
    DRAFT = "draft"
    EDITED = "edited"
    FINALIZED = "finalized"
    REJECTED = "rejected"
