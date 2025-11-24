-- Migration: Video Recommendation System Schema
-- Phase 1: Create all tables for video recommendations
-- Date: 2025-11-24

-- ==============================================================================
-- video_rec: Recommendation videos (separate from existing cache)
-- ==============================================================================
DEFINE TABLE video_rec SCHEMAFULL;

-- Core identity
DEFINE FIELD video_id ON video_rec TYPE string;
DEFINE FIELD url ON video_rec TYPE string;
DEFINE FIELD title ON video_rec TYPE string;
DEFINE FIELD channel_id ON video_rec TYPE string;
DEFINE FIELD channel_name ON video_rec TYPE string;

-- Metadata (from YouTube API)
DEFINE FIELD thumbnail_url ON video_rec TYPE string;
DEFINE FIELD duration_seconds ON video_rec TYPE int;
DEFINE FIELD view_count ON video_rec TYPE int;
DEFINE FIELD like_count ON video_rec TYPE option<int>;
DEFINE FIELD upload_date ON video_rec TYPE datetime;
DEFINE FIELD description ON video_rec TYPE option<string>;

-- Content analysis
DEFINE FIELD transcript ON video_rec TYPE option<string>;
DEFINE FIELD tags ON video_rec TYPE array<string>;
DEFINE FIELD categories ON video_rec TYPE array<string>;

-- ML features (flexible JSON for experimentation)
DEFINE FIELD features ON video_rec TYPE option<object>;

-- Embeddings (for semantic search)
DEFINE FIELD embedding ON video_rec TYPE option<array<float>>;

-- Timestamps
DEFINE FIELD created_at ON video_rec TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON video_rec TYPE datetime DEFAULT time::now();

-- Indexes
DEFINE INDEX idx_video_id ON video_rec FIELDS video_id UNIQUE;
DEFINE INDEX idx_channel ON video_rec FIELDS channel_id;
DEFINE INDEX idx_upload ON video_rec FIELDS upload_date;

-- ==============================================================================
-- user_video_signal: User interactions with videos
-- ==============================================================================
DEFINE TABLE user_video_signal SCHEMAFULL;

DEFINE FIELD user_id ON user_video_signal TYPE string;
DEFINE FIELD video_id ON user_video_signal TYPE string;
DEFINE FIELD signal_type ON user_video_signal TYPE string;  -- 'watched', 'thumbs_up', 'thumbs_down', 'not_interested', 'ingested'
DEFINE FIELD source ON user_video_signal TYPE string;  -- 'brave', 'takeout', 'api', 'mentat', 'ui'
DEFINE FIELD timestamp ON user_video_signal TYPE datetime DEFAULT time::now();
DEFINE FIELD metadata ON user_video_signal TYPE option<object>;

-- Indexes
DEFINE INDEX idx_user_video ON user_video_signal FIELDS user_id, video_id;
DEFINE INDEX idx_user_type ON user_video_signal FIELDS user_id, signal_type;

-- ==============================================================================
-- user_channel_preference: Channel-level tracking
-- ==============================================================================
DEFINE TABLE user_channel_preference SCHEMAFULL;

DEFINE FIELD user_id ON user_channel_preference TYPE string;
DEFINE FIELD channel_id ON user_channel_preference TYPE string;
DEFINE FIELD channel_name ON user_channel_preference TYPE string;

-- Aggregated signals
DEFINE FIELD videos_watched ON user_channel_preference TYPE int DEFAULT 0;
DEFINE FIELD thumbs_up ON user_channel_preference TYPE int DEFAULT 0;
DEFINE FIELD thumbs_down ON user_channel_preference TYPE int DEFAULT 0;
DEFINE FIELD affinity_score ON user_channel_preference TYPE float DEFAULT 0.5;

DEFINE FIELD updated_at ON user_channel_preference TYPE datetime DEFAULT time::now();

DEFINE INDEX idx_user_channel ON user_channel_preference FIELDS user_id, channel_id UNIQUE;

-- ==============================================================================
-- user_category: Discovered interest categories
-- ==============================================================================
DEFINE TABLE user_category SCHEMAFULL;

DEFINE FIELD user_id ON user_category TYPE string;
DEFINE FIELD category_name ON user_category TYPE string;
DEFINE FIELD description ON user_category TYPE option<string>;
DEFINE FIELD keywords ON user_category TYPE array<string>;
DEFINE FIELD source ON user_category TYPE string;  -- 'agent', 'manual', 'imported'
DEFINE FIELD interest_score ON user_category TYPE float DEFAULT 0.5;
DEFINE FIELD active ON user_category TYPE bool DEFAULT true;
DEFINE FIELD created_at ON user_category TYPE datetime DEFAULT time::now();

DEFINE INDEX idx_user_category ON user_category FIELDS user_id, category_name UNIQUE;

-- ==============================================================================
-- user_persona: Interest clusters (multi-persona embeddings)
-- ==============================================================================
DEFINE TABLE user_persona SCHEMAFULL;

DEFINE FIELD user_id ON user_persona TYPE string;
DEFINE FIELD persona_index ON user_persona TYPE int;
DEFINE FIELD label ON user_persona TYPE option<string>;
DEFINE FIELD centroid ON user_persona TYPE array<float>;
DEFINE FIELD activity_score ON user_persona TYPE float DEFAULT 0.5;
DEFINE FIELD last_activity ON user_persona TYPE datetime;
DEFINE FIELD video_count ON user_persona TYPE int DEFAULT 0;
DEFINE FIELD sample_video_ids ON user_persona TYPE array<string>;

DEFINE FIELD created_at ON user_persona TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON user_persona TYPE datetime DEFAULT time::now();

DEFINE INDEX idx_user_persona ON user_persona FIELDS user_id, persona_index UNIQUE;

-- ==============================================================================
-- persona_config: Clustering configuration and metadata multipliers
-- ==============================================================================
DEFINE TABLE persona_config SCHEMAFULL;

DEFINE FIELD user_id ON persona_config TYPE string;
DEFINE FIELD k ON persona_config TYPE int;
DEFINE FIELD last_clustered ON persona_config TYPE datetime;
DEFINE FIELD clustering_samples ON persona_config TYPE int;
DEFINE FIELD silhouette_score ON persona_config TYPE option<float>;

-- Decay parameters
DEFINE FIELD activity_half_life_days ON persona_config TYPE float DEFAULT 14.0;
DEFINE FIELD activity_floor ON persona_config TYPE float DEFAULT 0.1;

-- Metadata multiplier weights (tunable)
DEFINE FIELD channel_boost_weight ON persona_config TYPE float DEFAULT 1.0;
DEFINE FIELD view_health_weight ON persona_config TYPE float DEFAULT 1.0;
DEFINE FIELD recency_weight ON persona_config TYPE float DEFAULT 1.0;

DEFINE INDEX idx_user_config ON persona_config FIELDS user_id UNIQUE;

-- ==============================================================================
-- ml_model: Trained models (for future use)
-- ==============================================================================
DEFINE TABLE ml_model SCHEMAFULL;

DEFINE FIELD user_id ON ml_model TYPE string;
DEFINE FIELD model_type ON ml_model TYPE string;
DEFINE FIELD version ON ml_model TYPE int;
DEFINE FIELD model_data ON ml_model TYPE bytes;
DEFINE FIELD training_samples ON ml_model TYPE int;
DEFINE FIELD metrics ON ml_model TYPE object;
DEFINE FIELD created_at ON ml_model TYPE datetime DEFAULT time::now();

DEFINE INDEX idx_user_model ON ml_model FIELDS user_id, model_type;
