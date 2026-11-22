DELIMITER //
BEGIN NOT ATOMIC
    IF EXISTS (SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'AEDs' AND COLUMN_NAME = 'Rating') THEN
        IF EXISTS (SELECT 1 FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'AEDs' AND COLUMN_NAME = 'DataRating') THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'AEDs contains both Rating and DataRating. Resolve the conflicting columns before retrying initialization.';
        END IF;
        ALTER TABLE `AEDs` RENAME COLUMN `Rating` TO `DataRating`;
    END IF;
END//
DELIMITER ;

ALTER TABLE `AEDs`
    ADD COLUMN IF NOT EXISTS `DataRating` INT NULL,
    DROP CONSTRAINT IF EXISTS `CK_AEDs_Rating`,
    DROP CONSTRAINT IF EXISTS `CK_AEDs_DataRating`,
    ADD CONSTRAINT `CK_AEDs_DataRating` CHECK (`DataRating` IS NULL OR `DataRating` IN (0, 1));

UPDATE `TranslationProfileUnits`
SET `ToColumn` = 'AEDs.DataRating'
WHERE `ToColumn` = 'AEDs.Rating';
