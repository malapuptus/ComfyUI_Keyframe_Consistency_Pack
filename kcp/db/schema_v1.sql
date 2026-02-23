PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assets (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT DEFAULT '',
  tags_json TEXT DEFAULT '[]',
  positive_fragment TEXT NOT NULL,
  negative_fragment TEXT DEFAULT '',
  json_fields TEXT DEFAULT '{}',
  thumb_path TEXT DEFAULT '',
  image_path TEXT DEFAULT '',
  image_hash TEXT DEFAULT '',
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  parent_id TEXT DEFAULT NULL,
  is_archived INTEGER NOT NULL DEFAULT 0,
  UNIQUE(type, name)
);

CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(type);
CREATE INDEX IF NOT EXISTS idx_assets_updated ON assets(updated_at);
CREATE INDEX IF NOT EXISTS idx_assets_archived ON assets(is_archived);

CREATE TABLE IF NOT EXISTS stacks (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  notes TEXT DEFAULT '',
  character_id TEXT,
  environment_id TEXT,
  action_id TEXT,
  camera_id TEXT,
  lighting_id TEXT,
  style_id TEXT,
  json_overrides TEXT DEFAULT '{}',
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  is_archived INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY(character_id) REFERENCES assets(id),
  FOREIGN KEY(environment_id) REFERENCES assets(id),
  FOREIGN KEY(action_id) REFERENCES assets(id),
  FOREIGN KEY(camera_id) REFERENCES assets(id),
  FOREIGN KEY(lighting_id) REFERENCES assets(id),
  FOREIGN KEY(style_id) REFERENCES assets(id)
);

CREATE INDEX IF NOT EXISTS idx_stacks_archived ON stacks(is_archived);

CREATE TABLE IF NOT EXISTS keyframe_sets (
  id TEXT PRIMARY KEY,
  name TEXT DEFAULT '',
  stack_id TEXT NOT NULL,
  variant_policy_id TEXT NOT NULL,
  variant_policy_json TEXT NOT NULL,
  base_seed INTEGER NOT NULL,
  width INTEGER NOT NULL,
  height INTEGER NOT NULL,
  model_ref TEXT DEFAULT '',
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  picked_index INTEGER DEFAULT NULL,
  notes TEXT DEFAULT '',
  FOREIGN KEY(stack_id) REFERENCES stacks(id)
);

CREATE INDEX IF NOT EXISTS idx_sets_stack ON keyframe_sets(stack_id);
CREATE INDEX IF NOT EXISTS idx_sets_created ON keyframe_sets(created_at);

CREATE TABLE IF NOT EXISTS keyframe_set_items (
  id TEXT PRIMARY KEY,
  set_id TEXT NOT NULL,
  idx INTEGER NOT NULL,
  seed INTEGER NOT NULL,
  positive_prompt TEXT NOT NULL,
  negative_prompt TEXT DEFAULT '',
  gen_params_json TEXT NOT NULL,
  image_path TEXT DEFAULT '',
  thumb_path TEXT DEFAULT '',
  score_json TEXT DEFAULT '{}',
  created_at INTEGER NOT NULL,
  UNIQUE(set_id, idx),
  FOREIGN KEY(set_id) REFERENCES keyframe_sets(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_items_set ON keyframe_set_items(set_id);

CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  notes TEXT DEFAULT '',
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS shots (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  seq INTEGER NOT NULL,
  name TEXT DEFAULT '',
  stack_id TEXT,
  overrides_json TEXT DEFAULT '{}',
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  UNIQUE(project_id, seq),
  FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
  FOREIGN KEY(stack_id) REFERENCES stacks(id)
);

CREATE INDEX IF NOT EXISTS idx_shots_project ON shots(project_id);
