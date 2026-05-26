from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "\n        CREATE TABLE clients (\n            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n            first_name  VARCHAR(255) NOT NULL,\n            last_name   VARCHAR(255) NOT NULL,\n            email       VARCHAR(255) NOT NULL UNIQUE,\n            description TEXT,\n            social_links TEXT[],\n            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),\n            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()\n        )\n        "
    )
    op.execute("CREATE INDEX ix_clients_email ON clients (email)")
    op.execute(
        "\n        CREATE TABLE documents (\n            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n            client_id     UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,\n            title         VARCHAR(500) NOT NULL,\n            content       TEXT NOT NULL,\n            doc_type      VARCHAR(100),\n            search_vector TSVECTOR,\n            embedding     vector(1536),\n            summary       TEXT,\n            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),\n            updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()\n        )\n        "
    )
    op.execute("CREATE INDEX ix_documents_client_id ON documents (client_id)")
    op.execute("CREATE INDEX ix_documents_doc_type  ON documents (doc_type)")
    op.execute(
        "CREATE INDEX ix_documents_search_vector ON documents USING gin (search_vector)"
    )
    op.execute(
        "\n        CREATE INDEX ix_documents_embedding\n        ON documents\n        USING ivfflat (embedding vector_cosine_ops)\n        WITH (lists = 100)\n        "
    )
    op.execute(
        "\n        CREATE OR REPLACE FUNCTION documents_search_vector_update()\n        RETURNS trigger AS $$\n        BEGIN\n            NEW.search_vector :=\n                setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||\n                setweight(to_tsvector('english', coalesce(NEW.content, '')), 'B');\n            RETURN NEW;\n        END;\n        $$ LANGUAGE plpgsql\n        "
    )
    op.execute(
        "\n        CREATE TRIGGER trg_documents_search_vector\n        BEFORE INSERT OR UPDATE OF title, content\n        ON documents\n        FOR EACH ROW EXECUTE FUNCTION documents_search_vector_update()\n        "
    )
    op.execute(
        "\n        CREATE OR REPLACE FUNCTION set_updated_at()\n        RETURNS trigger AS $$\n        BEGIN\n            NEW.updated_at = now();\n            RETURN NEW;\n        END;\n        $$ LANGUAGE plpgsql\n        "
    )
    for tbl in ("clients", "documents"):
        op.execute(
            f"\n            CREATE TRIGGER trg_{tbl }_updated_at\n            BEFORE UPDATE ON {tbl }\n            FOR EACH ROW EXECUTE FUNCTION set_updated_at()\n            "
        )


def downgrade() -> None:
    for tbl in ("clients", "documents"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{tbl }_updated_at ON {tbl }")
    op.execute("DROP TRIGGER IF EXISTS trg_documents_search_vector ON documents")
    op.execute("DROP FUNCTION IF EXISTS documents_search_vector_update()")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")
    op.execute("DROP TABLE IF EXISTS documents")
    op.execute("DROP TABLE IF EXISTS clients")
