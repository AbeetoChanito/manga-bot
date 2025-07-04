import motor
import motor.motor_asyncio
from dataclasses import dataclass
from typing import Optional, Mapping
import asyncio


class Backend:
    __instance: Optional["Backend"] = None
    __lock = asyncio.Lock()

    def __init__(self):
        assert self.__instance is None, "Backend instance already exists."
        self.client = motor.motor_asyncio.AsyncIOMotorClient(
            "mongodb://localhost:27017/"
        )
        self.db = self.client["db"]
        self.users = self.db["users"]

    @classmethod
    async def get_instance(cls) -> "Backend":
        async with cls.__lock:
            if cls.__instance is None:
                cls.__instance = Backend()
            return cls.__instance

    async def add_new_user(self, user_id: int):
        # we only add a new user if the user doesn't exist
        await self.users.update_one(
            {"_id": user_id}, {"$setOnInsert": {"bookmarks": []}}, upsert=True
        )

    async def add_new_bookmark(
        self, user_id: int, manga_link: int, chapter_number: int
    ):
        await self.add_new_user(user_id)

        # if the manga link isn't already registered with the user,
        # then we push it
        await self.users.update_one(
            {"_id": user_id, "bookmarks.link": {"$ne": manga_link}},
            {"$push": {"bookmarks": {"link": manga_link, "chapter": chapter_number}}},
        )

        # if the manga link is registered with the user,
        # we update the bookmark
        await self.users.update_one(
            {"_id": user_id, "bookmarks.link": manga_link},
            {"$set": {"bookmarks.$.chapter": chapter_number}},
        )

    async def get_bookmarks(self, user_id: int) -> list[Mapping[str, str]]:
        await self.add_new_user(user_id)
        user = await self.users.find_one({"_id": user_id}, {"_id": 0, "bookmarks": 1})
        return user.get("bookmarks", [])
