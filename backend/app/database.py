import logging
from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

logger = logging.getLogger("uvicorn.error")

class Database:
    def __init__(self):
        self.client = None
        self.db = None
        self._fallback_mode = False
        self._fallback_analyses = []
        self._fallback_trainees = [
            {"trainee_id": "T001", "name": "Arjun Kumar", "trade": "Welder", "attendance_status": "Present"},
            {"trainee_id": "T002", "name": "Rohan Patel", "trade": "Electrician", "attendance_status": "Present"},
            {"trainee_id": "T003", "name": "Deepika Rao", "trade": "Fitter", "attendance_status": "Late"},
            {"trainee_id": "T004", "name": "Siddharth Singh", "trade": "CNC Operator", "attendance_status": "Absent"}
        ]

    async def connect(self):
        try:
            logger.info(f"Connecting to MongoDB at {settings.MONGODB_URL}...")
            self.client = AsyncIOMotorClient(settings.MONGODB_URL, serverSelectionTimeoutMS=2000)
            self.db = self.client["trainee_analytics"]
            # Trigger a simple command to test if the connection actually works
            await self.client.admin.command('ping')
            logger.info("Connected to MongoDB successfully.")
            
            # Seed default trainees if collection is empty
            count = await self.db.trainees.count_documents({})
            if count == 0:
                await self.db.trainees.insert_many(self._fallback_trainees)
                logger.info("Seeded default trainees in MongoDB.")
        except Exception as e:
            logger.warning(f"Could not connect to MongoDB: {e}. Falling back to in-memory storage.")
            self._fallback_mode = True
            self.db = None

    def is_fallback(self) -> bool:
        return self._fallback_mode

    async def get_trainees(self):
        if self._fallback_mode or self.db is None:
            return self._fallback_trainees
        raw_trainees = await self.db.trainees.find().to_list(100)
        for t in raw_trainees:
            t.pop("_id", None)
        return raw_trainees

    async def get_trainee(self, trainee_id: str):
        if self._fallback_mode or self.db is None:
            for t in self._fallback_trainees:
                if t["trainee_id"] == trainee_id:
                    return t
            return None
        trainee = await self.db.trainees.find_one({"trainee_id": trainee_id})
        if trainee:
            trainee.pop("_id", None)
        return trainee

    async def save_analysis(self, analysis: dict):
        if self._fallback_mode or self.db is None:
            self._fallback_analyses.insert(0, analysis)
        else:
            # MongoDB will add _id, so make a copy to save
            save_doc = dict(analysis)
            await self.db.question_analyses.insert_one(save_doc)

    async def get_analyses(self, trainee_id: str = None):
        if self._fallback_mode or self.db is None:
            if trainee_id:
                return [a for a in self._fallback_analyses if a.get("trainee_id") == trainee_id]
            return self._fallback_analyses
        
        query = {}
        if trainee_id:
            query["trainee_id"] = trainee_id
        
        from pymongo import DESCENDING
        analyses = await self.db.question_analyses.find(query).sort("timestamp", DESCENDING).limit(50).to_list(50)
        for item in analyses:
            item["_id"] = str(item["_id"])
        return analyses

    async def clear_analyses(self):
        if self._fallback_mode or self.db is None:
            self._fallback_analyses = []
        else:
            await self.db.question_analyses.delete_many({})

db_instance = Database()
