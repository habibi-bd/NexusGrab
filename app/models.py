from datetime import datetime
from sqlalchemy import Column, DateTime, Float, Integer, String
from app.database import Base


class DownloadAnalytics(Base):
    __tablename__ = "download_analytics"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=True)
    url = Column(String, nullable=False)
    domain = Column(String, nullable=False)
    duration = Column(Float, nullable=True)  # in seconds
    file_size = Column(Float, nullable=True)  # in MB
    downloaded_at = Column(DateTime, default=datetime.utcnow)
