from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from database.models import Conversation, Message
from datetime import datetime, timezone
from database.models import Document, UsageLog
from utils.errors import NotFoundError
import logging

from fastapi.encoders import jsonable_encoder
from redis.exceptions import RedisError

from cache.redis_cache import (
    CACHE_TTL,
    cache_get_or_set,
    cache_delete_pattern,
)

logger = logging.getLogger(__name__)

class ConversationService:
        
    @staticmethod
    def invalidate_conversation_cache(user_id: str):
        try:
            cache_delete_pattern(
                f"conversations:{user_id}:*"
            )
        except RedisError:
            logger.exception(
                "Failed to invalidate conversation cache "
                "for user %s",
                user_id,
            )

    def create_conversation(
        self,
        db: Session,
        user_id: str,
        title: str,
    ):
        conversation = Conversation(
            user_id=user_id,
            title=title,
        )

        db.add(conversation)

        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

        db.refresh(conversation)
        self.invalidate_conversation_cache(user_id)
        return conversation

    
    def list_conversations(
        self,
        db: Session,
        user_id: str,
        page: int = 1,
        limit: int = 20,
    ):
        key = f"conversations:{user_id}:{page}:{limit}"

        def fetch():
            result = self._list_conversations_from_db(
                db=db,
                user_id=user_id,
                page=page,
                limit=limit,
            )

            return jsonable_encoder(result)

        try:
            return cache_get_or_set(
                key=key,
                ttl=CACHE_TTL["CONVERSATION_LIST"],
                fetch_fn=fetch,
            )

        except RedisError:
            logger.exception(
                "Conversation cache unavailable"
            )
            return fetch()


    def _list_conversations_from_db(
        self,
        db: Session,
        user_id: str,
        page: int = 1,
        limit: int = 20,
    ):
        total = db.scalar(
            select(func.count(Conversation.id))
            .where(Conversation.user_id == user_id)
        ) or 0

        latest_message = aliased(Message)

        latest_message_id = (
            select(latest_message.id)
            .where(
                latest_message.conversation_id == Conversation.id
            )
            .order_by(
                latest_message.created_at.desc(),
                latest_message.id.desc(),
            )
            .limit(1)
            .correlate(Conversation)
            .scalar_subquery()
        )

        message_count = (
            select(func.count(Message.id))
            .where(Message.conversation_id == Conversation.id)
            .correlate(Conversation)
            .scalar_subquery()
        )

        stmt = (
            select(
                Conversation,
                message_count.label("message_count"),
                Message.content.label("last_content"),
                Message.role.label("last_role"),
                Message.created_at.label("last_created_at"),
            )
            .outerjoin(Message, Message.id == latest_message_id)
            .where(Conversation.user_id == user_id)
            .order_by(
                Conversation.updated_at.desc(),
                Conversation.id.desc(),
            )
            .offset((page - 1) * limit)
            .limit(limit)
        )

        rows = db.execute(stmt).all()

        data = []

        for conversation, count, content, role, created_at in rows:
            last_message = None

            if created_at is not None:
                last_message = {
                    "content": content,
                    "role": role,
                    "createdAt": created_at,
                }

            data.append({
                "id": conversation.id,
                "title": conversation.title,
                "messageCount": count,
                "lastMessage": last_message,
                "updatedAt": conversation.updated_at,
            })

        return {
            "data": data,
            "meta": {
                "page": page,
                "limit": limit,
                "total": total,
            },
        }

    def send_message(
        self,
        db: Session,
        conversation_id: str,
        user_id: str,
        content: str,
        document_id: str | None = None,
    ):
        try:
            conversation = db.scalar(
                select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id,
                ).with_for_update()
            )

            if conversation is None:
                raise NotFoundError("Conversation not found")

            if document_id is not None:
                document = db.scalar(
                    select(Document).where(
                        Document.id == document_id,
                        Document.user_id == user_id,
                        Document.deleted_at.is_(None),
                    )
                )

                if document is None:
                    raise NotFoundError("Document not found")

            user_message = Message(
                conversation_id=conversation_id,
                document_id=document_id,
                role="user",
                content=content,
            )

            assistant_message = Message(
                conversation_id=conversation_id,
                document_id=document_id,
                role="assistant",
                content="AI response placeholder (Week 4)",
                prompt_tokens=0,
                completion_tokens=0,
                cost_usd=0,
            )

            db.add_all([user_message, assistant_message])

            conversation.updated_at = datetime.now(timezone.utc)

            usage_log = UsageLog(
                user_id=user_id,
                action="chat",
                tokens=0,
                cost_usd=0,
            )

            db.add(usage_log)

            db.commit()

        except Exception:
            db.rollback()
            raise

        db.refresh(user_message)
        db.refresh(assistant_message)
        self.invalidate_conversation_cache(user_id)

        return {
            "userMessage": user_message,
            "assistantMessage": assistant_message,
        }
    