import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from linkedin.schemas.conversations import (
    AiSuggestionCreateRequest,
    ConversationCreateRequest,
    ConversationMessageCreateRequest,
)
from linkedin.services.conversations import (
    add_conversation_message,
    create_client_conversation,
    generate_ai_suggestion,
    stream_ai_suggestion,
)


class ConversationServiceTests(unittest.TestCase):
    @patch("linkedin.services.conversations.create_conversation")
    @patch("linkedin.services.conversations.get_project_for_user")
    @patch("linkedin.services.conversations.get_client_for_user")
    def test_create_client_conversation_validates_client_and_project(
        self,
        mock_get_client_for_user,
        mock_get_project_for_user,
        mock_create_conversation,
    ) -> None:
        db = Mock()
        user = SimpleNamespace(id="12345678-1234-5678-1234-567812345678")
        mock_get_client_for_user.return_value = SimpleNamespace()
        mock_get_project_for_user.return_value = SimpleNamespace()
        mock_create_conversation.return_value = SimpleNamespace()
        payload = ConversationCreateRequest(
            client_id="87654321-4321-6789-4321-678987654321",
            project_id="11111111-1111-1111-1111-111111111111",
            title="Conversation with Ava Thompson",
        )

        create_client_conversation(db, payload, user)

        mock_create_conversation.assert_called_once_with(
            db,
            user_id=user.id,
            client_id="87654321-4321-6789-4321-678987654321",
            project_id="11111111-1111-1111-1111-111111111111",
            title="Conversation with Ava Thompson",
        )

    @patch("linkedin.services.conversations.create_message")
    @patch("linkedin.services.conversations.get_client_conversation")
    def test_add_conversation_message_saves_message(
        self,
        mock_get_client_conversation,
        mock_create_message,
    ) -> None:
        db = Mock()
        user = SimpleNamespace(id="12345678-1234-5678-1234-567812345678")
        conversation = SimpleNamespace(id="conversation-id")
        mock_get_client_conversation.return_value = conversation
        payload = ConversationMessageCreateRequest(
            sender_type="client",
            message_text="Can you explain compliance?",
        )

        add_conversation_message(
            db,
            conversation_id="conversation-id",
            payload=payload,
            user=user,
        )

        mock_create_message.assert_called_once_with(
            db,
            conversation_id="conversation-id",
            sender_type="client",
            message_text="Can you explain compliance?",
        )

    @patch("linkedin.services.conversations.create_ai_suggestion")
    @patch("linkedin.services.conversations._stream_text_deltas")
    @patch("linkedin.services.conversations.list_recent_messages")
    @patch("linkedin.services.conversations.search_knowledge_vectors")
    @patch("linkedin.services.conversations.create_embeddings")
    @patch("linkedin.services.conversations.get_message_for_conversation")
    @patch("linkedin.services.conversations.get_client_conversation")
    def test_stream_ai_suggestion_uses_qdrant_chunks_and_saves_final_response(
        self,
        mock_get_client_conversation,
        mock_get_message_for_conversation,
        mock_create_embeddings,
        mock_search_knowledge_vectors,
        mock_list_recent_messages,
        mock_stream_text_deltas,
        mock_create_ai_suggestion,
    ) -> None:
        db = Mock()
        user = SimpleNamespace(id="user-id")
        conversation = SimpleNamespace(
            id="conversation-id",
            project_id="project-id",
            client=SimpleNamespace(name="Ava", company="Acme", notes=None),
            project=SimpleNamespace(name="Healthcare", description="Compliance"),
        )
        message = SimpleNamespace(
            id="message-id",
            sender_type="client",
            message_text="What is HIPAA?",
        )
        mock_get_client_conversation.return_value = conversation
        mock_get_message_for_conversation.return_value = message
        mock_create_embeddings.return_value = [[0.1, 0.2]]
        mock_search_knowledge_vectors.return_value = [
            {
                "chunk_id": "chunk-id",
                "score": 0.9,
                "payload": {"filename": "policy.pdf", "text": "HIPAA details"},
            }
        ]
        mock_list_recent_messages.return_value = [message]
        mock_stream_text_deltas.return_value = iter(["Suggested ", "reply"])
        mock_create_ai_suggestion.return_value = SimpleNamespace(
            id="suggestion-id",
            suggested_response="Suggested reply",
            status="draft",
        )
        payload = AiSuggestionCreateRequest(message_id="22222222-2222-2222-2222-222222222222")

        events = list(
            stream_ai_suggestion(
                db,
                conversation_id="conversation-id",
                payload=payload,
                user=user,
            )
        )

        self.assertEqual(events[0]["state"], "loading_conversation")
        self.assertEqual(events[1]["state"], "embedding_message")
        self.assertEqual(events[2]["state"], "searching_knowledge")
        self.assertEqual(events[3]["state"], "loading_history")
        self.assertEqual(events[4]["state"], "generating_response")
        self.assertEqual(events[5], {"type": "delta", "text": "Suggested "})
        self.assertEqual(events[6], {"type": "delta", "text": "reply"})
        self.assertEqual(events[7]["state"], "saving_suggestion")
        self.assertEqual(events[8]["type"], "done")
        mock_search_knowledge_vectors.assert_called_once_with(
            query_vector=[0.1, 0.2],
            user_id="user-id",
            project_id="project-id",
            limit=5,
        )
        mock_create_ai_suggestion.assert_called_once()
        self.assertEqual(
            mock_create_ai_suggestion.call_args.kwargs["suggested_response"],
            "Suggested reply",
        )
        used_chunks = mock_create_ai_suggestion.call_args.kwargs["used_chunks"]
        self.assertEqual(used_chunks[0]["source"], "policy.pdf")

    @patch("linkedin.services.conversations.create_ai_suggestion")
    @patch("linkedin.services.conversations._generate_response_text")
    @patch("linkedin.services.conversations.list_recent_messages")
    @patch("linkedin.services.conversations.search_knowledge_vectors")
    @patch("linkedin.services.conversations.create_embeddings")
    @patch("linkedin.services.conversations.get_message_for_conversation")
    @patch("linkedin.services.conversations.get_client_conversation")
    def test_generate_ai_suggestion_non_streaming_still_works(
        self,
        mock_get_client_conversation,
        mock_get_message_for_conversation,
        mock_create_embeddings,
        mock_search_knowledge_vectors,
        mock_list_recent_messages,
        mock_generate_response_text,
        mock_create_ai_suggestion,
    ) -> None:
        db = Mock()
        user = SimpleNamespace(id="user-id")
        conversation = SimpleNamespace(
            id="conversation-id",
            project_id="project-id",
            client=SimpleNamespace(name="Ava", company="Acme", notes=None),
            project=SimpleNamespace(name="Healthcare", description="Compliance"),
        )
        message = SimpleNamespace(
            id="message-id",
            sender_type="client",
            message_text="What is HIPAA?",
        )
        mock_get_client_conversation.return_value = conversation
        mock_get_message_for_conversation.return_value = message
        mock_create_embeddings.return_value = [[0.1, 0.2]]
        mock_search_knowledge_vectors.return_value = [
            {
                "chunk_id": "chunk-id",
                "score": 0.9,
                "payload": {"filename": "policy.pdf", "text": "HIPAA details"},
            }
        ]
        mock_list_recent_messages.return_value = [message]
        mock_generate_response_text.return_value = "Suggested reply"
        mock_create_ai_suggestion.return_value = SimpleNamespace()
        payload = AiSuggestionCreateRequest(message_id="22222222-2222-2222-2222-222222222222")

        generate_ai_suggestion(
            db,
            conversation_id="conversation-id",
            payload=payload,
            user=user,
        )

        mock_search_knowledge_vectors.assert_called_once_with(
            query_vector=[0.1, 0.2],
            user_id="user-id",
            project_id="project-id",
            limit=5,
        )
        mock_create_ai_suggestion.assert_called_once()
        used_chunks = mock_create_ai_suggestion.call_args.kwargs["used_chunks"]
        self.assertEqual(used_chunks[0]["source"], "policy.pdf")


if __name__ == "__main__":
    unittest.main()
