"""Fanella.

uk workflows
"""

from __future__ import annotations

import asyncio
import dataclasses
import functools
import logging
import typing

import aiofiles
import aiohttp
import uvloop

if typing.TYPE_CHECKING:
    import datetime
    import io

    import pydantic

_fanella_bad = RuntimeError('Error from our side sorry we will fix it')
_coder_bad = RuntimeError(
    'Error from your side fix it chat support on https://fanella.ai. Error: %s'
)

# https://api.fanella.ai/v1
BASE_URL = 'http://localhost:8000/v1'

logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(name)s "%(message)s"',
)
log = logging.getLogger(__name__)


# DONT DO KDA KOL MARA U NEED HAGA GET L LOOP TANI
try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    uvloop.install()
    loop = uvloop.new_event_loop()
    asyncio.set_event_loop(loop)


@dataclasses.dataclass
class Request[responseType]:
    """Make a request to Fanella."""

    _path: str
    _auth: bool = dataclasses.field(default=True, kw_only=True)
    token_defn: typing.Callable[[Client], typing.Awaitable[str]] = (
        dataclasses.field(
            init=False,
            repr=False,
        )
    )

    async def _send(
        self,
        method: str,
        path: str,
        json: dict[str, int | str | None] | None = None,
        data: aiohttp.FormData | None = None,
    ) -> responseType:
        async with (
            aiohttp.ClientSession() as session,
            getattr(session, method)(
                path,
                json=json,
                data=data,
                headers={'Authorization': f'Bearer {await self.token_defn()}'}
                if self._auth
                else {},
            ) as response,
        ):
            server_error = 5
            user_error = 4

            if response.status // 100 == server_error:
                raise _fanella_bad
            if response.status // 100 == user_error:
                log.exception(await response.json())
                raise _coder_bad

            return await response.json()

    async def post(
        self,
        *,
        json: dict[str, str | int | None] | None = None,
        form: aiohttp.FormData | None = None,
    ) -> responseType:
        """Add data."""
        return await self._send(
            'post',
            BASE_URL + self._path,
            data=form,
            json=json,
        )

    async def patch(
        self,
        id_: int,
        *,
        json: dict[str, str | int | None] | None = None,
    ) -> responseType:
        """Change data."""
        return await self._send(
            'post',
            BASE_URL + f'{self._path}/{id_}/',
            json=json,
        )

    async def get_all(self, *, page: int = 1, rows: int = 10) -> responseType:
        """Get all your data."""
        return await self._send(
            'post',
            BASE_URL + f'{self._path}/me?page={page}&rows={rows}',
        )

    async def get(self, id_: int) -> responseType:
        """Get data by id."""
        return await self._send(
            'post',
            BASE_URL + f'{self._path}/{id_}',
        )

    async def delete(self, id_: int) -> responseType:
        """Get data by id."""
        return await self._send(
            'post',
            BASE_URL + f'{self._path}/{id_}',
        )


@dataclasses.dataclass
class Resource:
    """Base for any Fanella recourse."""

    id: int = dataclasses.field(init=False)
    uuid: pydantic.UUID4 = dataclasses.field(init=False)
    created_at: datetime.datetime = dataclasses.field(init=False)

    _client: Client = dataclasses.field(kw_only=True, repr=False)


@dataclasses.dataclass
class OwnerMixin:
    """For recourses owned by a user."""

    guest_id: int | None = dataclasses.field(init=False)
    identity_id: int | None = dataclasses.field(init=False)
    organization_id: int | None = dataclasses.field(init=False)


@dataclasses.dataclass
class ArchiveMixin:
    """For recourses that have can be archived."""

    archived_at: datetime.datetime | None = dataclasses.field(init=False)
    archived_by_id: int | None = dataclasses.field(init=False, repr=False)


@dataclasses.dataclass
class BackgroundTaskMixin:
    """For recourses that run background task."""

    state: str = dataclasses.field(init=False)
    error: bool = dataclasses.field(init=False)

    completed_at: datetime.datetime | None = dataclasses.field(init=False)


@dataclasses.dataclass
class Client:
    """Your entry point to Fanella.

    We support 3 types of auth, guest, password, client_credentials. Fel api
    hna we only support guest and client_credentials, don't call haga to get
    guest
    >>> import fanella
    >>> fanella.Client() # guest
    """

    client_id: str = ''
    client_secret: str = dataclasses.field(default='', repr=False)
    _request: Request = dataclasses.field(
        default_factory=lambda: Request[
            typing.TypedDict(
                'Auth',
                {'access_token': str, 'refresh_token': str},
            )
        ]('/auth/token/', _auth=False),
        init=False,
        repr=False,
    )
    Source: functools.partial[Source] = dataclasses.field(
        init=False,
        repr=False,
    )
    _access_token: str = dataclasses.field(default='', init=False, repr=False)
    _refresh_token: str = dataclasses.field(default='', init=False, repr=False)

    def __post_init__(self) -> None:
        """Auth & prepare Fanella resources."""
        loop.run_until_complete(self._auth())
        self.Source = functools.partial(Source, _client=self)
        Request.token_defn = self._auth

    async def _auth(self) -> str:
        """Do whatever it takes to get you a token.

        It would log you in or refresh your current token or give you guest
        access or hack into our servers.
        """
        if not self._access_token:
            data = aiohttp.FormData()
            grant_type = 'client_credentials'
            if not all((self.client_id, self.client_id)):
                grant_type = 'guest'
                log.warning('GUEST')

            data.add_field('grant_type', grant_type)
            data.add_field('client_id', self.client_id)
            data.add_field('client_secret', self.client_secret)
            self._access_token, self._refresh_token = (
                await self._request.post(form=data)
            ).values()
        return self._access_token


@dataclasses.dataclass
class Source(OwnerMixin, BackgroundTaskMixin, ArchiveMixin, Resource):
    """A source of data.

    Either pass a link, text, path, bytes or io obj.
    """

    name: str = ''
    link: str | None = None
    source_id: int | None = dataclasses.field(default=None, repr=False)
    text: str | None = dataclasses.field(default=None, repr=False)
    file_path: str | None = dataclasses.field(default=None, repr=False)
    file_bytes: bytes | None = dataclasses.field(default=None, repr=False)
    file: io.TextIOWrapper | None = dataclasses.field(default=None, repr=False)
    external_type: str | None = dataclasses.field(default=None, init=False)
    version: int = dataclasses.field(init=False)
    size_bytes: int = dataclasses.field(init=False)
    _request: Request = dataclasses.field(
        default_factory=lambda: Request['Source']('/sources/'),
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        """Set request manager and upload source."""
        data = aiohttp.FormData()

        if not (
            bool(self.text)
            ^ bool(self.link)
            ^ bool(self.file)
            ^ bool(self.file_path)
            ^ bool(self.file_bytes)
        ):
            log.exception('You need one of these')
            raise RuntimeError

        if self.file_path:
            file_name, self.file_bytes = loop.run_until_complete(
                self._read_file(self.file_path),
            )
            self.name = self.name or file_name
        elif self.file:
            ...
        elif self.link:
            data.add_field('link', self.link)
        elif self.text:
            data.add_field('text', self.text)

        data.add_field('name', self.name)
        # check kda l aiohttp FormData law it can help in a better way??

        if self.file_bytes:
            data.add_field('file', self.file_bytes)

        self.__dict__.update(
            loop.run_until_complete(self._request.post(form=data)),
        )

    async def _read_file(self, file_path: str) -> tuple[str, bytes]:
        async with aiofiles.open(file_path, 'rb') as f:
            return f.name, await f.read()


@dataclasses.dataclass
class Section(OwnerMixin, Resource):
    """A section is usually part of a source."""


if __name__ == '__main__':
    log.setLevel(level=logging.INFO)
    client = Client()
    source = client.Source(
        name='MySource',
        file_path='/Users/gaytomycode/Downloads/temp.pdf',
    )
    log.info(source)
