"""
Unit tests for the Playground Saver Flask API.

Run with: pytest tests/test_api.py -v
"""

import base64
import io
import json
import pytest
from unittest.mock import MagicMock, patch

# Import app from both locations for testing
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestLocalApp:
    """Tests for the local Flask app (app.py)."""

    @pytest.fixture
    def app(self):
        """Create test app."""
        from app import app
        app.config['TESTING'] = True
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    def test_index_returns_html(self, client):
        """Test that the index route returns HTML."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'<!DOCTYPE html>' in response.data
        assert b'Playground Saver' in response.data

    def test_models_endpoint_requires_api_key(self, client):
        """Test that /api/models requires an API key."""
        response = client.get('/api/models')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'API key' in data['error']

    @patch('app.get_client')
    def test_models_endpoint_returns_models(self, mock_get_client, client):
        """Test that /api/models returns model list when given a valid key."""
        # Mock the OpenAI client
        mock_client = MagicMock()
        mock_model_1 = MagicMock()
        mock_model_1.id = 'gpt-4o'
        mock_model_2 = MagicMock()
        mock_model_2.id = 'gpt-4o-mini'
        mock_model_3 = MagicMock()
        mock_model_3.id = 'text-embedding-ada-002'  # Should be filtered out

        mock_models = MagicMock()
        mock_models.data = [mock_model_1, mock_model_2, mock_model_3]
        mock_client.models.list.return_value = mock_models
        mock_get_client.return_value = mock_client

        response = client.get('/api/models?api_key=sk-test-key')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'models' in data
        assert 'gpt-4o' in data['models']
        assert 'gpt-4o-mini' in data['models']
        # Embeddings model should be filtered out
        assert 'text-embedding-ada-002' not in data['models']

    def test_send_endpoint_requires_api_key(self, client):
        """Test that /api/send requires an API key."""
        response = client.post('/api/send', data={
            'message': 'Hello'
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'API key' in data['error']

    def test_send_endpoint_requires_message_or_images(self, client):
        """Test that /api/send requires a message or images."""
        response = client.post('/api/send', data={
            'api_key': 'sk-test-key'
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Message or images required' in data['error']

    @patch('app.get_client')
    def test_send_message_success(self, mock_get_client, client):
        """Test successful message sending."""
        # Mock the OpenAI client
        mock_client = MagicMock()

        # Mock response
        mock_content = MagicMock()
        mock_content.type = 'output_text'
        mock_content.text = 'Hello! How can I help you?'

        mock_message = MagicMock()
        mock_message.type = 'message'
        mock_message.content = [mock_content]

        mock_response = MagicMock()
        mock_response.id = 'resp_test123'
        mock_response.model = 'gpt-4o'
        mock_response.output = [mock_message]

        mock_client.responses.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        response = client.post('/api/send', data={
            'api_key': 'sk-test-key',
            'message': 'Hello!',
            'model': 'gpt-4o'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['response'] == 'Hello! How can I help you?'
        assert data['new_response_id'] == 'resp_test123'
        assert data['model'] == 'gpt-4o'

    @patch('app.get_client')
    def test_send_message_with_previous_response_id(self, mock_get_client, client):
        """Test message sending with previous_response_id."""
        mock_client = MagicMock()

        mock_content = MagicMock()
        mock_content.type = 'output_text'
        mock_content.text = 'Continuing our conversation...'

        mock_message = MagicMock()
        mock_message.type = 'message'
        mock_message.content = [mock_content]

        mock_response = MagicMock()
        mock_response.id = 'resp_test456'
        mock_response.model = 'gpt-4o'
        mock_response.output = [mock_message]

        mock_client.responses.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        response = client.post('/api/send', data={
            'api_key': 'sk-test-key',
            'response_id': 'resp_previous123',
            'message': 'Continue please',
            'model': 'gpt-4o'
        })

        assert response.status_code == 200

        # Verify previous_response_id was passed
        call_args = mock_client.responses.create.call_args
        assert call_args.kwargs.get('previous_response_id') == 'resp_previous123'

    def test_history_endpoint_requires_api_key(self, client):
        """Test that /api/history requires an API key."""
        response = client.get('/api/history/resp_test123')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'API key' in data['error']


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_encode_image_bytes_png(self):
        """Test encoding PNG image bytes."""
        from app import encode_image_bytes

        # Create a simple test image (1x1 white PNG)
        png_bytes = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
        )

        encoded, mime_type = encode_image_bytes(png_bytes, 'test.png')

        assert mime_type == 'image/png'
        assert isinstance(encoded, str)
        # Verify it's valid base64
        decoded = base64.b64decode(encoded)
        assert decoded == png_bytes

    def test_encode_image_bytes_jpeg(self):
        """Test encoding JPEG image bytes."""
        from app import encode_image_bytes

        # Simple JPEG header bytes for testing
        jpeg_bytes = b'\xff\xd8\xff\xe0\x00\x10JFIF'

        encoded, mime_type = encode_image_bytes(jpeg_bytes, 'photo.jpg')

        assert mime_type == 'image/jpeg'
        assert isinstance(encoded, str)

    def test_encode_image_bytes_unknown_extension(self):
        """Test encoding with unknown extension defaults to PNG."""
        from app import encode_image_bytes

        test_bytes = b'test data'

        encoded, mime_type = encode_image_bytes(test_bytes, 'file.unknownext')

        # Unknown extension should default to image/png
        assert mime_type == 'image/png'

    def test_build_input_text_only(self):
        """Test build_input with text only."""
        from app import build_input

        result = build_input('Hello world', [])

        assert result == 'Hello world'

    def test_build_input_with_images(self):
        """Test build_input with images."""
        from app import build_input

        images = [
            {'data': 'base64data1', 'mime_type': 'image/png'},
            {'data': 'base64data2', 'mime_type': 'image/jpeg'},
        ]

        result = build_input('Describe these', images)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]['role'] == 'user'

        content = result[0]['content']
        assert len(content) == 3  # 1 text + 2 images

        assert content[0]['type'] == 'input_text'
        assert content[0]['text'] == 'Describe these'

        assert content[1]['type'] == 'input_image'
        assert 'data:image/png;base64,' in content[1]['image_url']

        assert content[2]['type'] == 'input_image'
        assert 'data:image/jpeg;base64,' in content[2]['image_url']

    def test_build_input_images_only(self):
        """Test build_input with images but no text."""
        from app import build_input

        images = [{'data': 'base64data', 'mime_type': 'image/png'}]

        result = build_input('', images)

        assert isinstance(result, list)
        content = result[0]['content']
        assert len(content) == 1  # Just the image, no text
        assert content[0]['type'] == 'input_image'


class TestVercelApp:
    """Tests for the Vercel serverless function (api/index.py)."""

    @pytest.fixture
    def app(self):
        """Create test app from Vercel function."""
        from api.index import app
        app.config['TESTING'] = True
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    def test_index_returns_html(self, client):
        """Test that the index route returns HTML."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'<!DOCTYPE html>' in response.data

    def test_models_endpoint_requires_api_key(self, client):
        """Test that /api/models requires an API key."""
        response = client.get('/api/models')
        assert response.status_code == 400

    def test_send_endpoint_requires_api_key(self, client):
        """Test that /api/send requires an API key."""
        response = client.post('/api/send', data={'message': 'Hello'})
        assert response.status_code == 400

    def test_conversations_endpoint_requires_api_key(self, client):
        """Test that /api/conversations requires an API key."""
        response = client.post('/api/conversations', data={})
        assert response.status_code == 400

    def test_conversation_items_requires_api_key(self, client):
        """Test that conversation items endpoint requires an API key."""
        response = client.get('/api/conversations/conv_test123/items')
        assert response.status_code == 400


class TestCLIModules:
    """Tests for CLI helper functions."""

    def test_continue_conversation_encode_image(self, tmp_path):
        """Test image encoding in continue_conversation module."""
        from continue_conversation import encode_image

        # Create a test file
        test_file = tmp_path / "test.png"
        # Write a minimal PNG file
        png_data = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
        )
        test_file.write_bytes(png_data)

        encoded, mime_type = encode_image(str(test_file))

        assert mime_type == 'image/png'
        assert isinstance(encoded, str)
        # Verify round-trip
        assert base64.b64decode(encoded) == png_data

    def test_continue_conversation_encode_image_not_found(self):
        """Test that encode_image raises for missing files."""
        from continue_conversation import encode_image

        with pytest.raises(FileNotFoundError):
            encode_image('/nonexistent/file.png')

    def test_continue_conversation_build_input_text_only(self):
        """Test build_input in continue_conversation module."""
        from continue_conversation import build_input

        result = build_input('Hello')
        assert result == 'Hello'

    def test_chat_build_input_text_only(self):
        """Test build_input in chat module."""
        from chat import build_input

        result = build_input('Hello')
        assert result == 'Hello'

    def test_chat_build_input_with_images(self, tmp_path):
        """Test build_input with images in chat module."""
        from chat import build_input

        # Create test files
        test_file = tmp_path / "test.png"
        png_data = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
        )
        test_file.write_bytes(png_data)

        result = build_input('Describe this', [str(test_file)])

        assert isinstance(result, list)
        assert result[0]['role'] == 'user'
        assert len(result[0]['content']) == 2  # text + image

    def test_chat_build_input_with_urls(self):
        """Test build_input with image URLs in chat module."""
        from chat import build_input

        result = build_input('Describe this', None, ['https://example.com/img.png'])

        assert isinstance(result, list)
        content = result[0]['content']
        assert len(content) == 2  # text + image URL
        assert content[1]['image_url'] == 'https://example.com/img.png'

