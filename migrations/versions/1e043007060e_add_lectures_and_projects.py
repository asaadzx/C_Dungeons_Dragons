"""add lectures and projects

Revision ID: 1e043007060e
Revises: 8f55f46e6b40
Create Date: 2026-10-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "1e043007060e"
down_revision = "8f55f46e6b40"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "lectures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_lectures_date"), "lectures", ["date"], unique=False)

    op.create_table(
        "lecture_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lecture_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(length=300), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["lecture_id"], ["lectures.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("projects")
    op.drop_table("lecture_items")
    op.drop_index(op.f("ix_lectures_date"), table_name="lectures")
    op.drop_table("lectures")
