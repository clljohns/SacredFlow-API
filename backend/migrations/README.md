# Migrations

This service uses SQLAlchemy metadata, but you can bootstrap the chat tables quickly with Alembic:

```bash
cd backend
alembic init migrations
# update alembic.ini connection url or use env var
alembic revision --autogenerate -m "chat tables"
alembic upgrade head
```

For simple setups, you can also run the SQL below:

```
CREATE TABLE affiliates (
    id uuid PRIMARY KEY,
    name varchar(255) NOT NULL,
    email varchar(255) UNIQUE NOT NULL
);

CREATE TABLE customers (
    id uuid PRIMARY KEY,
    email varchar(255) UNIQUE NOT NULL,
    name varchar(255),
    affiliate_id uuid REFERENCES affiliates(id)
);

CREATE TABLE conversations (
    id uuid PRIMARY KEY,
    customer_id uuid NOT NULL REFERENCES customers(id),
    affiliate_id uuid REFERENCES affiliates(id),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_conversations_customer_id ON conversations(customer_id);

CREATE TYPE sender_type AS ENUM ('customer','affiliate','admin','system');
CREATE TYPE message_status AS ENUM ('received','sent','delivered','read');

CREATE TABLE messages (
    id uuid PRIMARY KEY,
    conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_type sender_type NOT NULL,
    content text NOT NULL,
    status message_status NOT NULL,
    metadata text,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_messages_conversation_id ON messages(conversation_id);
CREATE INDEX ix_messages_conversation_created ON messages(conversation_id, created_at DESC);
```
