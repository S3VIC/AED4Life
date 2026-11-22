ALTER TABLE `AEDReports`
    ADD COLUMN IF NOT EXISTS `Description` LONGTEXT NULL,
    ADD COLUMN IF NOT EXISTS `AvailabilityStartHour` INT NULL,
    ADD COLUMN IF NOT EXISTS `AvailabilityEndHour` INT NULL,
    ADD COLUMN IF NOT EXISTS `IsPubliclyAccessible` TINYINT(1) NULL;

UPDATE `AEDReports`
SET `Description` = 'Legacy report: device placement description was not provided.'
WHERE `Description` IS NULL OR `Description` NOT REGEXP '[^[:space:]]';

ALTER TABLE `AEDReports`
    MODIFY COLUMN `Description` LONGTEXT NOT NULL,
    DROP CONSTRAINT IF EXISTS `CK_AEDReports_Description`,
    DROP CONSTRAINT IF EXISTS `CK_AEDReports_IsPubliclyAccessible`,
    DROP CONSTRAINT IF EXISTS `CK_AEDReports_AvailabilityHours`,
    ADD CONSTRAINT `CK_AEDReports_Description` CHECK (`Description` REGEXP '[^[:space:]]'),
    ADD CONSTRAINT `CK_AEDReports_IsPubliclyAccessible` CHECK (`IsPubliclyAccessible` IS NULL OR `IsPubliclyAccessible` IN (0, 1)),
    ADD CONSTRAINT `CK_AEDReports_AvailabilityHours` CHECK (
        (`AvailabilityStartHour` IS NULL OR `AvailabilityStartHour` BETWEEN 0 AND 23)
        AND (`AvailabilityEndHour` IS NULL OR `AvailabilityEndHour` BETWEEN 0 AND 24)
        AND (`AvailabilityStartHour` IS NULL OR `AvailabilityEndHour` IS NULL
            OR `AvailabilityStartHour` <> `AvailabilityEndHour`)
    );
