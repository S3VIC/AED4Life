ALTER TABLE `Cities` MODIFY COLUMN `Name` LONGTEXT NULL;
ALTER TABLE `Streets` MODIFY COLUMN `Name` LONGTEXT NULL;
ALTER TABLE `PostalCodes` MODIFY COLUMN `Code` VARCHAR(6) NULL;

ALTER TABLE `Addresses`
    MODIFY COLUMN `StreetId` BIGINT NULL,
    MODIFY COLUMN `CityId` BIGINT NULL,
    MODIFY COLUMN `PostalCodeId` INT NULL,
    MODIFY COLUMN `BuildingNumber` INT NULL;

ALTER TABLE `AEDOwners`
    MODIFY COLUMN `RegonNumber` VARCHAR(14) NULL,
    MODIFY COLUMN `IsPublic` TINYINT(1) NULL,
    MODIFY COLUMN `Name` LONGTEXT NULL,
    MODIFY COLUMN `CityId` BIGINT NULL,
    MODIFY COLUMN `StreetId` BIGINT NULL;

ALTER TABLE `AEDs`
    MODIFY COLUMN `AddressId` BIGINT NULL,
    MODIFY COLUMN `SerialNumber` LONGTEXT NULL,
    MODIFY COLUMN `Rating` INT NULL,
    DROP CONSTRAINT IF EXISTS `CK_AEDs_Rating`,
    DROP CONSTRAINT IF EXISTS `CK_AEDs_AvailabilityHours`,
    ADD CONSTRAINT `CK_AEDs_Rating` CHECK (`Rating` IS NULL OR `Rating` IN (0, 1)),
    ADD CONSTRAINT `CK_AEDs_AvailabilityHours` CHECK (
        (`AvailabilityStartHour` IS NULL OR `AvailabilityStartHour` BETWEEN 0 AND 23)
        AND (`AvailabilityEndHour` IS NULL OR `AvailabilityEndHour` BETWEEN 0 AND 24)
        AND (`AvailabilityStartHour` IS NULL OR `AvailabilityEndHour` IS NULL
            OR `AvailabilityStartHour` <> `AvailabilityEndHour`)
    );
