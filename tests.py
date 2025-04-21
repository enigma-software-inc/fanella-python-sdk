"""Pytests for Fanella."""

import os
import tempfile
from unittest.mock import AsyncMock

import pytest

from fanella import Client, Request, Source, _coder_bad, _fanella_bad


@pytest.fixture
def mock_client() -> None:
    """Fixture for creating a mock Client object."""
    client = Client(client_id='test_id', client_secret='test_secret')
    client._access_token = 'test_token'
    client._refresh_token = 'test_refresh_token'
    return client


@pytest.fixture
def mock_aiohttp_session(mocker) -> None:
    """Fixture for mocking aiohttp.ClientSession."""
    mock_session = AsyncMock()
    mocker.patch('aiohttp.ClientSession', return_value=mock_session)
    return mock_session


@pytest.fixture
def mock_response(mocker) -> None:
    """Fixture for mocking aiohttp.ClientResponse."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {'key': 'value'}
    return mock_response


class TestRequest:
    """Tests for the Request class."""

    @pytest.mark.asyncio
    async def test_send_success(
        self,
        mocker,
        mock_aiohttp_session,
        mock_response,
    ) -> None:
        """Test successful _send method."""
        mock_aiohttp_session.getattr.return_value.return_value = mock_response
        request = Request[dict]('/test')
        request.token_defn = AsyncMock(return_value='test_token')
        result = await request._send('get', 'http://example.com/test')

        assert result == {'key': 'value'}
        mock_aiohttp_session.getattr.assert_called_once_with('get')
        mock_aiohttp_session.getattr.return_value.return_value.__aenter__.assert_called_once()
        mock_aiohttp_session.getattr.return_value.return_value.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_fanella_error(
        self,
        mocker,
        mock_aiohttp_session,
        mock_response,
    ) -> None:
        """Test _send method with Fanella error (5xx)."""
        mock_response.status = 500
        mock_aiohttp_session.getattr.return_value.return_value = mock_response
        request = Request[dict]('/test')
        request.token_defn = AsyncMock(return_value='test_token')

        with pytest.raises(_fanella_bad):
            await request._send('get', 'http://example.com/test')

    @pytest.mark.asyncio
    async def test_send_coder_error(
        self,
        mocker,
        mock_aiohttp_session,
        mock_response,
    ) -> None:
        """Test _send method with coder error (4xx)."""
        mock_response.status = 400
        mock_response.json.return_value = {'error': 'Bad Request'}
        mock_aiohttp_session.getattr.return_value.return_value = mock_response
        request = Request[dict]('/test')
        request.token_defn = AsyncMock(return_value='test_token')

        with pytest.raises(_coder_bad) as exc_info:
            await request._send('get', 'http://example.com/test')
        assert 'Bad Request' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_post(
        self, mocker, mock_aiohttp_session, mock_response
    ) -> None:
        """Test post method."""
        mock_aiohttp_session.getattr.return_value.return_value = mock_response
        request = Request[dict]('/test')
        request.token_defn = AsyncMock(return_value='test_token')

        await request.post(json={'data': 'test'})

        mock_aiohttp_session.getattr.assert_called_once_with('post')
        mock_aiohttp_session.getattr.return_value.return_value.__aenter__.assert_called_once()
        mock_aiohttp_session.getattr.return_value.return_value.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_patch(
        self, mocker, mock_aiohttp_session, mock_response
    ) -> None:
        """Test patch method."""
        mock_aiohttp_session.getattr.return_value.return_value = mock_response
        request = Request[dict]('/test')
        request.token_defn = AsyncMock(return_value='test_token')

        await request.patch(1, json={'data': 'test'})

        mock_aiohttp_session.getattr.assert_called_once_with('post')
        mock_aiohttp_session.getattr.return_value.return_value.__aenter__.assert_called_once()
        mock_aiohttp_session.getattr.return_value.return_value.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all(
        self, mocker, mock_aiohttp_session, mock_response
    ) -> None:
        """Test get_all method."""
        mock_aiohttp_session.getattr.return_value.return_value = mock_response
        request = Request[dict]('/test')
        request.token_defn = AsyncMock(return_value='test_token')

        await request.get_all(page=2, rows=20)

        mock_aiohttp_session.getattr.assert_called_once_with('post')
        mock_aiohttp_session.getattr.return_value.return_value.__aenter__.assert_called_once()
        mock_aiohttp_session.getattr.return_value.return_value.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_get(
        self, mocker, mock_aiohttp_session, mock_response
    ) -> None:
        """Test get method."""
        mock_aiohttp_session.getattr.return_value.return_value = mock_response
        request = Request[dict]('/test')
        request.token_defn = AsyncMock(return_value='test_token')

        await request.get(1)

        mock_aiohttp_session.getattr.assert_called_once_with('post')
        mock_aiohttp_session.getattr.return_value.return_value.__aenter__.assert_called_once()
        mock_aiohttp_session.getattr.return_value.return_value.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete(
        self, mocker, mock_aiohttp_session, mock_response
    ) -> None:
        """Test delete method."""
        mock_aiohttp_session.getattr.return_value.return_value = mock_response
        request = Request[dict]('/test')
        request.token_defn = AsyncMock(return_value='test_token')

        await request.delete(1)

        mock_aiohttp_session.getattr.assert_called_once_with('post')
        mock_aiohttp_session.getattr.return_value.return_value.__aenter__.assert_called_once()
        mock_aiohttp_session.getattr.return_value.return_value.__aexit__.assert_called_once()


class TestClient:
    """Tests for the Client class."""

    @pytest.mark.asyncio
    async def test_auth_client_credentials(
        self, mocker, mock_aiohttp_session
    ) -> None:
        """Test authentication with client credentials."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            'access_token': 'test_token',
            'refresh_token': 'test_refresh_token',
        }
        mock_aiohttp_session.post.return_value = mock_response
        client = Client(client_id='test_id', client_secret='test_secret')
        await client._auth()
        assert client._access_token == 'test_token'
        assert client._refresh_token == 'test_refresh_token'
        mock_aiohttp_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_auth_guest(self, mocker, mock_aiohttp_session) -> None:
        """Test authentication as guest."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            'access_token': 'guest_token',
            'refresh_token': 'guest_refresh_token',
        }
        mock_aiohttp_session.post.return_value = mock_response
        client = Client()  # No client_id or client_secret
        await client._auth()
        assert client._access_token == 'guest_token'
        assert client._refresh_token == 'guest_refresh_token'
        mock_aiohttp_session.post.assert_called_once()


class TestSource:
    """Tests for the Source class."""

    @pytest.mark.asyncio
    async def test_source_init_with_text(self, mocker, mock_client) -> None:
        """Test Source initialization with text."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {'id': 1, 'name': 'Test Source'}
        mocker.patch('aiohttp.ClientSession.post', return_value=mock_response)
        source = Source(
            name='Test Source', text='Some text', _client=mock_client
        )

        assert source.name == 'Test Source'
        assert source.id == 1

    @pytest.mark.asyncio
    async def test_source_init_with_link(self, mocker, mock_client) -> None:
        """Test Source initialization with link."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {'id': 2, 'name': 'Link Source'}
        mocker.patch('aiohttp.ClientSession.post', return_value=mock_response)
        source = Source(
            name='Link Source', link='http://example.com', _client=mock_client
        )

        assert source.name == 'Link Source'
        assert source.id == 2

    @pytest.mark.asyncio
    async def test_source_init_with_file_path(
        self, mocker, mock_client
    ) -> None:
        """Test Source initialization with file path."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {'id': 3, 'name': 'File Source'}
        mocker.patch('aiohttp.ClientSession.post', return_value=mock_response)
        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b'Test file content')
            file_path = temp_file.name

        source = Source(
            name='File Source', file_path=file_path, _client=mock_client
        )

        assert source.name == 'File Source'
        assert source.id == 3
        os.remove(file_path)  # Clean up the temporary file

    @pytest.mark.asyncio
    async def test_source_init_with_file_bytes(
        self, mocker, mock_client
    ) -> None:
        """Test Source initialization with file bytes."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {'id': 4, 'name': 'Bytes Source'}
        mocker.patch('aiohttp.ClientSession.post', return_value=mock_response)
        file_bytes = b'Test bytes content'
        source = Source(
            name='Bytes Source', file_bytes=file_bytes, _client=mock_client
        )

        assert source.name == 'Bytes Source'
        assert source.id == 4

    @pytest.mark.asyncio
    async def test_source_init_with_file_object(
        self, mocker, mock_client
    ) -> None:
        """Test Source initialization with file object."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {'id': 5, 'name': 'Object Source'}
        mocker.patch('aiohttp.ClientSession.post', return_value=mock_response)

        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write('Test file content')
            file_path = temp_file.name

        # Open the file in read mode
        with open(file_path) as file_obj:
            source = Source(
                name='Object Source', file=file_obj, _client=mock_client
            )

        assert source.name == 'Object Source'
        assert source.id == 5

        os.remove(file_path)  # Clean up the temporary file

    @pytest.mark.asyncio
    async def test_source_init_no_data(self, mock_client) -> None:
        """Test Source initialization with no data."""
        with pytest.raises(RuntimeError):
            Source(name='No Data Source', _client=mock_client)

    @pytest.mark.asyncio
    async def test_read_file(self, mocker, mock_client) -> None:
        """Test the _read_file method."""
        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b'Test file content')
            file_path = temp_file.name

        source = Source(
            name='Test Source', file_path=file_path, _client=mock_client
        )
        result = await source._read_file(file_path)

        assert result == (file_path, b'Test file content')

        os.remove(file_path)  # Clean up the temporary file
