-- Waycrystals a character has attuned to (see src/custom_waystones.cpp)
CREATE TABLE IF NOT EXISTS `character_waystone` (
  `guid` INT UNSIGNED NOT NULL,
  `waystone` INT UNSIGNED NOT NULL,
  PRIMARY KEY (`guid`, `waystone`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Attuned Kirin Tor waycrystals';
