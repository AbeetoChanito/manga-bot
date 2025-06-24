import motor
import motor.motor_asyncio
from dataclasses import dataclass


class Backend:
    def __init__(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(
            "mongodb://localhost:27017/"
        )
        self.db = self.client["db"]
        self.users = self.db["users"]

    async def add_new_user(self, user_id: int):
        await self.users.update_one(
            {"_id": user_id}, {"$setOnInsert": {"bookmarks": []}}, upsert=True
        )

    async def add_new_bookmark(
        self, user_id: int, manga_link: int, chapter_number: int
    ):
        await self.add_new_user(user_id)

        await self.users.update_one(
            {"_id": user_id, "bookmarks.link": {"$ne": manga_link}},
            {"$push": {"bookmarks": {"link": manga_link, "chapter": chapter_number}}},
        )

        await self.users.update_one(
            {"_id": user_id, "bookmarks.link": manga_link},
            {"$set": {"bookmarks.$.chapter": chapter_number}},
        )

    async def get_bookmarks(self, user_id: int) -> list[str]:
        await self.add_new_user(user_id)
        user = await self.users.find_one({"_id": user_id}, {"_id": 0, "bookmarks": 1})
        return user.get("bookmarks", [])
