from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_documents_embedding")
    op.execute("ALTER TABLE documents ALTER COLUMN embedding TYPE vector(384)")
    op.execute(
        "\n        CREATE INDEX ix_documents_embedding\n        ON documents\n        USING ivfflat (embedding vector_cosine_ops)\n        WITH (lists = 100)\n        "
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_documents_embedding")
    op.execute("ALTER TABLE documents ALTER COLUMN embedding TYPE vector(1536)")
    op.execute(
        "\n        CREATE INDEX ix_documents_embedding\n        ON documents\n        USING ivfflat (embedding vector_cosine_ops)\n        WITH (lists = 100)\n        "
    )
