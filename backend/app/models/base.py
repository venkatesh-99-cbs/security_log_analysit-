from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Float, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database.session import Base

class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    filepath = Column(String)
    status = Column(String)  # uploaded, processing, processed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    file_size = Column(Integer, nullable=True)       # bytes on disk
    findings_count = Column(Integer, nullable=True)  # alerts detected during pipeline
    logs = relationship("SecurityLog", back_populates="file", cascade="all, delete-orphan")

class SecurityLog(Base):
    __tablename__ = "security_logs"
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("uploaded_files.id"))
    timestamp = Column(DateTime)
    source = Column(String)
    category = Column(String)
    severity = Column(String)
    message = Column(Text)
    raw_data = Column(JSON)
    file = relationship("UploadedFile", back_populates="logs")

class Incident(Base):
    __tablename__ = "incidents"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(Text)
    status = Column(String)
    severity = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    mitre_mappings = relationship("MitreMapping", back_populates="incident", cascade="all, delete-orphan")
    analyses = relationship("AIAnalysis", back_populates="incident", cascade="all, delete-orphan")

class AIAnalysis(Base):
    __tablename__ = "ai_analyses"
    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"))
    query = Column(Text)
    response = Column(Text)
    analysis_type = Column(String) # summary, explanation, recommendation
    created_at = Column(DateTime, default=datetime.utcnow)
    incident = relationship("Incident", back_populates="analyses")

class MitreMapping(Base):
    __tablename__ = "mitre_mappings"
    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"))
    technique_id = Column(String)
    technique_name = Column(String)
    tactic = Column(String)
    incident = relationship("Incident", back_populates="mitre_mappings")

class ThreatIntelligence(Base):
    __tablename__ = "threat_intelligence"
    id = Column(Integer, primary_key=True, index=True)
    indicator = Column(String, unique=True, index=True)
    type = Column(String) # ip, domain, hash
    description = Column(Text)
    severity = Column(String)
    source = Column(String)
    last_updated = Column(DateTime, default=datetime.utcnow)

class DetectionRule(Base):
    __tablename__ = "detection_rules"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(Text)
    rule_type = Column(String) # sigma, yara, custom
    content = Column(Text)
    is_active = Column(Boolean, default=True)

class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    content = Column(Text)
    source_url = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Report(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    report_type = Column(String) # incident, executive, trend
    filepath = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class ChatHistory(Base):
    __tablename__ = "chat_histories"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    role = Column(String) # user, assistant
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    action = Column(String)
    details = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
