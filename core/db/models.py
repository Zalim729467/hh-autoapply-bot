"""SQLAlchemy ORM models matching §4 of the specification."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ---------- users / access ----------


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    hh_accounts: Mapped[list["HhAccount"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


# ---------- hh accounts / resumes ----------


class HhAccount(Base):
    __tablename__ = "hh_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    login: Mapped[str] = mapped_column(String(255))
    cookies_enc: Mapped[bytes | None] = mapped_column()
    status: Mapped[str] = mapped_column(String(32), default="active")
    last_auth_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    proxy_url: Mapped[str | None] = mapped_column(String(512))

    user: Mapped["User"] = relationship(back_populates="hh_accounts")
    resumes: Mapped[list["Resume"]] = relationship(
        back_populates="hh_account", cascade="all, delete-orphan"
    )


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True)
    hh_account_id: Mapped[int] = mapped_column(
        ForeignKey("hh_accounts.id", ondelete="CASCADE"), index=True
    )
    hh_resume_id: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(512))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    autoboost_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_boost_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    hh_account: Mapped["HhAccount"] = relationship(back_populates="resumes")


# ---------- search criteria ----------


class Keyword(Base):
    __tablename__ = "keywords"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    value: Mapped[str] = mapped_column(String(512))
    source: Mapped[str] = mapped_column(String(16), default="text")  # catalog | text
    catalog_id: Mapped[str | None] = mapped_column(String(64))


class StopWord(Base):
    __tablename__ = "stop_words"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    value: Mapped[str] = mapped_column(String(512))


class BlacklistCompany(Base):
    __tablename__ = "blacklist_companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    hh_company_id: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(512))


class Contact(Base):
    __tablename__ = "contacts"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(64))


class Filter(Base):
    __tablename__ = "filters"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    search_mode: Mapped[str] = mapped_column(
        String(32), default="keywords"
    )  # keywords | recommendations
    salary_min: Mapped[int | None] = mapped_column(Integer)
    salary_max: Mapped[int | None] = mapped_column(Integer)
    regions: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    employment: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    schedule: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    experience: Mapped[str | None] = mapped_column(String(32))
    ai_filter_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    daily_limit: Mapped[int] = mapped_column(Integer, default=200)
    delay_min_sec: Mapped[int] = mapped_column(Integer, default=5)
    delay_max_sec: Mapped[int] = mapped_column(Integer, default=25)
    schedule_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    schedule_morning_start: Mapped[time] = mapped_column(Time, default=time(11, 0))
    schedule_morning_end: Mapped[time] = mapped_column(Time, default=time(13, 0))
    schedule_evening_start: Mapped[time] = mapped_column(Time, default=time(18, 0))
    schedule_evening_end: Mapped[time] = mapped_column(Time, default=time(19, 0))
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Moscow")


class CoverSettings(Base):
    __tablename__ = "cover_settings"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    mode: Mapped[str] = mapped_column(String(16), default="ai")  # ai | custom | none
    custom_template: Mapped[str | None] = mapped_column(Text)
    send_to_all: Mapped[bool] = mapped_column(Boolean, default=False)
    stop_on_limit: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_prompt: Mapped[str | None] = mapped_column(Text)
    salary_mode: Mapped[str] = mapped_column(
        String(16), default="universal"
    )  # none|universal|from_resume|ask_each
    salary_min_expected: Mapped[int] = mapped_column(Integer, default=150000)
    salary_max_expected: Mapped[int] = mapped_column(Integer, default=180000)
    salary_currency: Mapped[str] = mapped_column(String(8), default="RUR")
    questions_mode: Mapped[str] = mapped_column(
        String(16), default="attention"
    )  # skip|attention|ai_draft


# ---------- pending attention ----------


class PendingAttention(Base):
    __tablename__ = "pending_attention"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    hh_account_id: Mapped[int] = mapped_column(
        ForeignKey("hh_accounts.id", ondelete="CASCADE")
    )
    hh_vacancy_id: Mapped[str] = mapped_column(String(64))
    vacancy_title: Mapped[str] = mapped_column(String(512))
    company_name: Mapped[str] = mapped_column(String(512))
    vacancy_url: Mapped[str] = mapped_column(String(1024))
    reason: Mapped[str] = mapped_column(
        String(32)
    )  # has_test|has_questions|needs_salary
    questions_json: Mapped[dict | list | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    draft_answers_json: Mapped[dict | list | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ---------- applications / runs ----------


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("user_id", "hh_vacancy_id", name="uq_app_user_vacancy"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    hh_account_id: Mapped[int] = mapped_column(
        ForeignKey("hh_accounts.id", ondelete="CASCADE")
    )
    hh_vacancy_id: Mapped[str] = mapped_column(String(64))
    hh_company_id: Mapped[str | None] = mapped_column(String(64))
    vacancy_title: Mapped[str] = mapped_column(String(512))
    company_name: Mapped[str] = mapped_column(String(512))
    resume_id: Mapped[int | None] = mapped_column(
        ForeignKey("resumes.id", ondelete="SET NULL")
    )
    cover_letter: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16))  # sent|skipped|error
    error_message: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    hh_account_id: Mapped[int] = mapped_column(
        ForeignKey("hh_accounts.id", ondelete="CASCADE")
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    found: Mapped[int] = mapped_column(Integer, default=0)
    sent: Mapped[int] = mapped_column(Integer, default=0)
    skipped: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[int] = mapped_column(Integer, default=0)
    is_dry_run: Mapped[bool] = mapped_column(Boolean, default=False)
    trigger: Mapped[str] = mapped_column(
        String(16), default="manual"
    )  # manual|schedule


class CoverLetterHistory(Base):
    __tablename__ = "cover_letters_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int | None] = mapped_column(
        ForeignKey("applications.id", ondelete="SET NULL")
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    vacancy_id: Mapped[str] = mapped_column(String(64))
    body: Mapped[str] = mapped_column(Text)
    ai_model: Mapped[str | None] = mapped_column(String(128))
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=Decimal("0"))
    was_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AiUsage(Base):
    __tablename__ = "ai_usage"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[date] = mapped_column(Date)
    purpose: Mapped[str] = mapped_column(String(32))  # cover_letter|vacancy_filter
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=Decimal("0"))


class EmployerMessage(Base):
    __tablename__ = "employer_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    hh_account_id: Mapped[int] = mapped_column(
        ForeignKey("hh_accounts.id", ondelete="CASCADE")
    )
    hh_negotiation_id: Mapped[str] = mapped_column(String(64), unique=True)
    company_name: Mapped[str] = mapped_column(String(512))
    vacancy_title: Mapped[str] = mapped_column(String(512))
    state: Mapped[str] = mapped_column(String(32))  # invitation|rejection|message
    preview: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    forwarded_message_id: Mapped[int | None] = mapped_column(BigInteger)


class ActiveRun(Base):
    __tablename__ = "active_runs"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))
    worker_id: Mapped[str] = mapped_column(String(128))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    heartbeat_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    type: Mapped[str] = mapped_column(String(64))
    payload_json: Mapped[dict | list | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
