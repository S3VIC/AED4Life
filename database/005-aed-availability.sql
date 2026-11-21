ALTER TABLE `AEDs`
    ADD COLUMN IF NOT EXISTS `Access` INT NULL,
    ADD COLUMN IF NOT EXISTS `AvailabilityStartHour` INT NULL,
    ADD COLUMN IF NOT EXISTS `AvailabilityEndHour` INT NULL,
    ADD COLUMN IF NOT EXISTS `Rating` INT NOT NULL DEFAULT 0,
    DROP CONSTRAINT IF EXISTS `CK_AEDs_Access`,
    DROP CONSTRAINT IF EXISTS `CK_AEDs_Rating`,
    DROP CONSTRAINT IF EXISTS `CK_AEDs_AvailabilityHours`,
    ADD CONSTRAINT `CK_AEDs_Access` CHECK (`Access` IS NULL OR `Access` IN (0, 1, 2)),
    ADD CONSTRAINT `CK_AEDs_Rating` CHECK (`Rating` IN (0, 1)),
    ADD CONSTRAINT `CK_AEDs_AvailabilityHours` CHECK (
        (`AvailabilityStartHour` IS NULL AND `AvailabilityEndHour` IS NULL)
        OR (`AvailabilityStartHour` IS NOT NULL AND `AvailabilityEndHour` IS NOT NULL
            AND `AvailabilityStartHour` BETWEEN 0 AND 23
            AND `AvailabilityEndHour` BETWEEN 0 AND 24
            AND `AvailabilityStartHour` <> `AvailabilityEndHour`)
    );
