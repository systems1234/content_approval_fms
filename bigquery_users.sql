CREATE TABLE IF NOT EXISTS `mis-gempundit.Content_FMS.Users` (
  user_id INT64 NOT NULL,
  username STRING NOT NULL,
  email STRING NOT NULL,
  password_hash STRING NOT NULL,
  role STRING NOT NULL,
  is_active BOOL NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);