from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class Edital(Base):
    __tablename__ = "editais"
    id = Column(Integer, primary_key=True, index=True)
    nome_concurso = Column(String(255), nullable=False)
    banca = Column(String(255), nullable=True)
    data_prova = Column(Date, nullable=True)

    disciplinas = relationship("Disciplina", back_populates="edital", cascade="all, delete-orphan")


class Disciplina(Base):
    __tablename__ = "disciplinas"
    id = Column(Integer, primary_key=True, index=True)
    edital_id = Column(Integer, ForeignKey("editais.id", ondelete="CASCADE"), nullable=False)
    nome = Column(String(255), nullable=False)
    peso = Column(Integer, nullable=True)

    edital = relationship("Edital", back_populates="disciplinas")
    topicos = relationship("Topico", back_populates="disciplina", cascade="all, delete-orphan")


class Topico(Base):
    __tablename__ = "topicos"
    id = Column(Integer, primary_key=True, index=True)
    disciplina_id = Column(Integer, ForeignKey("disciplinas.id", ondelete="CASCADE"), nullable=False)
    nome = Column(String(255), nullable=False)
    nivel_dominio = Column(Integer, nullable=False, default=1)
    revisado = Column(Boolean, default=False, nullable=False)

    __table_args__ = (
        CheckConstraint('nivel_dominio >= 1 AND nivel_dominio <= 4', name='check_nivel_dominio'),
    )

    disciplina = relationship("Disciplina", back_populates="topicos")
    historicos = relationship("QuestaoHistorico", back_populates="topico", cascade="all, delete-orphan")


class QuestaoHistorico(Base):
    __tablename__ = "questoes_historico"
    id = Column(Integer, primary_key=True, index=True)
    topico_id = Column(Integer, ForeignKey("topicos.id", ondelete="CASCADE"), nullable=False)
    acertos = Column(Integer, default=0, nullable=False)
    erros = Column(Integer, default=0, nullable=False)
    data_resolucao = Column(DateTime, default=datetime.utcnow, nullable=False)

    topico = relationship("Topico", back_populates="historicos")


class Flashcard(Base):
    __tablename__ = "flashcards"
    id = Column(Integer, primary_key=True, index=True)
    topico_id = Column(Integer, ForeignKey("topicos.id", ondelete="CASCADE"), nullable=False)
    frente = Column(String, nullable=False)
    verso = Column(String, nullable=False)
    tags = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    topico = relationship("Topico")
