import asyncio
import typing

import pyrogram
from aiogram.types import User
from pyrogram import Client
from pyrogram.errors import RPCError, UsernameNotOccupied, FloodWait

from app.models.config import TgClientConfig
from app.services.restrict_call import RestrictCall
from app.utils.log import Logger


logger = Logger(__name__)
SLEEP_TIME = 100


class UserGetter:
    def __init__(self, client_config: TgClientConfig):
        self._client_api_bot = Client(
            "karma_bot",
            bot_token=client_config.bot_token,
            api_id=client_config.api_id,
            api_hash=client_config.api_hash,
            no_updates=True
        )

    async def get_user(self, username: str = None, fullname: str = None, chat_id: int = None) -> User:
        async def try_by_name() -> typing.Optional[User]:
            try:
                return await self.get_user_by_fullname(chat_id, fullname)
            except (IndexError, RPCError):
                return None

        if username is not None:
            try:
                user_tg = await self.get_user_by_username(username)
            except RPCError:
                user_tg = await try_by_name()
        else:
            user_tg = await try_by_name()
        return user_tg

    @RestrictCall(SLEEP_TIME)
    async def get_user_by_username(self, username: str) -> User:
        try:
            logger.info("get user of username {username}", username=username)
            user = await self._client_api_bot.get_users(username)
            logger.info("found user {user}", user=self.get_user_dict_for_log(user))
        except UsernameNotOccupied:
            logger.info("Username not found {username}", username=username)
            raise
        except FloodWait as e:
            logger.error("Flood Wait {e}", e=e)
            await asyncio.sleep(e.x)
            raise IndexError

        return self.get_aiogram_user_by_pyrogram(user)

    @RestrictCall(SLEEP_TIME)
    async def get_user_by_fullname(self, chat_id: int, fullname: str) -> User:
        try:
            logger.info("get user of name {name}", name=fullname)
            chat_members = await self._client_api_bot.get_chat_members(chat_id=chat_id, query=fullname)
            logger.info(
                "found: {users}",
                users=[self.get_user_dict_for_log(chat_member.user) for chat_member in chat_members]
            )
            user = chat_members[0].user
        except IndexError:
            logger.info("name not found {name}", name=fullname)
            raise
        except FloodWait as e:
            logger.error("Flood Wait {e}", e=e)
            await asyncio.sleep(e.x)
            raise IndexError
        return self.get_aiogram_user_by_pyrogram(user)

    @staticmethod
    def get_aiogram_user_by_pyrogram(user: pyrogram.types.User) -> User:
        return User(
            id=user.id,
            is_bot=user.is_bot,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            language_code=user.language_code,
        )

    @staticmethod
    def get_user_dict_for_log(user: pyrogram.types.User) -> dict:
        return dict(
            id=user.id,
            is_bot=user.is_bot,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
        )

    async def start(self):
        if not self._client_api_bot.is_connected:
            await self._client_api_bot.start()

    async def stop(self):
        if self._client_api_bot.is_connected:
            await self._client_api_bot.stop()

    async def __aenter__(self) -> "UserGetter":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
