ALTER TABLE `AEDs`
    ADD COLUMN IF NOT EXISTS `Access` INT NULL,
    ADD COLUMN IF NOT EXISTS `AvailabilityStartHour` INT NULL,
    ADD COLUMN IF NOT EXISTS `AvailabilityEndHour` INT NULL,
    ADD COLUMN IF NOT EXISTS `DataRating` INT NULL,
    DROP CONSTRAINT IF EXISTS `CK_AEDs_Access`,
    DROP CONSTRAINT IF EXISTS `CK_AEDs_DataRating`,
    DROP CONSTRAINT IF EXISTS `CK_AEDs_AvailabilityHours`,
    ADD CONSTRAINT `CK_AEDs_Access` CHECK (`Access` IS NULL OR `Access` IN (0, 1, 2)),
    ADD CONSTRAINT `CK_AEDs_DataRating` CHECK (`DataRating` IS NULL OR `DataRating` IN (0, 1)),
    ADD CONSTRAINT `CK_AEDs_AvailabilityHours` CHECK (
        (`AvailabilityStartHour` IS NULL OR `AvailabilityStartHour` BETWEEN 0 AND 23)
        AND (`AvailabilityEndHour` IS NULL OR `AvailabilityEndHour` BETWEEN 0 AND 24)
        AND (`AvailabilityStartHour` IS NULL OR `AvailabilityEndHour` IS NULL
            OR `AvailabilityStartHour` <> `AvailabilityEndHour`)
    );
