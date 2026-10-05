
CREATE TABLE system_config (
	id INTEGER NOT NULL, 
	max_upload_mb INTEGER NOT NULL, 
	nominal_threshold INTEGER NOT NULL, 
	retention_hours INTEGER NOT NULL, 
	PRIMARY KEY (id)
)

;


CREATE TABLE users (
	id VARCHAR(36) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	email VARCHAR(254) NOT NULL, 
	password_hash VARCHAR(100) NOT NULL, 
	role VARCHAR(10) NOT NULL, 
	verified BOOLEAN NOT NULL, 
	active BOOLEAN NOT NULL, 
	failed_attempts INTEGER NOT NULL, 
	locked_until TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (role IN ('user','admin'))
)

;

CREATE UNIQUE INDEX ix_users_email ON users (email);


CREATE TABLE action_tokens (
	token_hash VARCHAR(64) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	purpose VARCHAR(20) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (token_hash), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)

;

CREATE INDEX ix_action_tokens_user_id ON action_tokens (user_id);


CREATE TABLE conversions (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	filename VARCHAR(255) NOT NULL, 
	source_format VARCHAR(4) NOT NULL, 
	target_format VARCHAR(4) NOT NULL, 
	size INTEGER NOT NULL, 
	instance_count INTEGER NOT NULL, 
	attribute_count INTEGER NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)

;

CREATE INDEX ix_conversions_user_id ON conversions (user_id);

CREATE INDEX ix_conversions_created_at ON conversions (created_at);


CREATE TABLE events (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36), 
	kind VARCHAR(50) NOT NULL, 
	message TEXT NOT NULL, 
	details JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
)

;


CREATE TABLE sessions (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	refresh_hash VARCHAR(64) NOT NULL, 
	last_seen TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	UNIQUE (refresh_hash)
)

;

CREATE INDEX ix_sessions_user_id ON sessions (user_id);


CREATE TABLE uploads (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	filename VARCHAR(255) NOT NULL, 
	source_format VARCHAR(4) NOT NULL, 
	size INTEGER NOT NULL, 
	options JSON NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)

;

CREATE INDEX ix_uploads_expires_at ON uploads (expires_at);

CREATE INDEX ix_uploads_user_id ON uploads (user_id);