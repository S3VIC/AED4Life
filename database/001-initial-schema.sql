CREATE TABLE IF NOT EXISTS `Cities` (
    `Id` BIGINT NOT NULL AUTO_INCREMENT,
    `Name` LONGTEXT NOT NULL,
    `PostalCode` LONGTEXT NOT NULL,
    CONSTRAINT `PK_Cities` PRIMARY KEY (`Id`)
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `Streets` (
    `Id` BIGINT NOT NULL AUTO_INCREMENT,
    `Name` LONGTEXT NOT NULL,
    CONSTRAINT `PK_Streets` PRIMARY KEY (`Id`)
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `AEDs` (
    `Id` BIGINT NOT NULL AUTO_INCREMENT,
    `CityId` BIGINT NOT NULL,
    `StreetId` BIGINT NOT NULL,
    `HouseNumber` INT NOT NULL,
    `Created` DATETIME(6) NOT NULL,
    `LastUpdated` DATETIME(6) NOT NULL,
    `SerialNumber` LONGTEXT NOT NULL,
    `Access` INT NULL,
    `AvailabilityStartHour` INT NULL,
    `AvailabilityEndHour` INT NULL,
    `Rating` INT NOT NULL DEFAULT 0,
    CONSTRAINT `PK_AEDs` PRIMARY KEY (`Id`),
    CONSTRAINT `CK_AEDs_Access` CHECK (`Access` IS NULL OR `Access` IN (0, 1, 2)),
    CONSTRAINT `CK_AEDs_Rating` CHECK (`Rating` IN (0, 1)),
    CONSTRAINT `CK_AEDs_AvailabilityHours` CHECK (
        (`AvailabilityStartHour` IS NULL AND `AvailabilityEndHour` IS NULL)
        OR (`AvailabilityStartHour` IS NOT NULL AND `AvailabilityEndHour` IS NOT NULL
            AND `AvailabilityStartHour` BETWEEN 0 AND 23
            AND `AvailabilityEndHour` BETWEEN 0 AND 24
            AND `AvailabilityStartHour` <> `AvailabilityEndHour`)
    ),
    INDEX `IX_AEDs_CityId` (`CityId`),
    INDEX `IX_AEDs_StreetId` (`StreetId`),
    CONSTRAINT `FK_AEDs_Cities_CityId` FOREIGN KEY (`CityId`)
        REFERENCES `Cities` (`Id`) ON DELETE RESTRICT,
    CONSTRAINT `FK_AEDs_Streets_StreetId` FOREIGN KEY (`StreetId`)
        REFERENCES `Streets` (`Id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `AEDOwners` (
    `Id` BIGINT NOT NULL AUTO_INCREMENT,
    `RegonNumber` VARCHAR(14) NOT NULL,
    `IsPublic` TINYINT(1) NOT NULL,
    `Name` LONGTEXT NOT NULL,
    `CityId` BIGINT NOT NULL,
    `StreetId` BIGINT NOT NULL,
    CONSTRAINT `PK_AEDOwners` PRIMARY KEY (`Id`),
    UNIQUE INDEX `IX_AEDOwners_RegonNumber` (`RegonNumber`),
    INDEX `IX_AEDOwners_CityId` (`CityId`),
    INDEX `IX_AEDOwners_StreetId` (`StreetId`),
    CONSTRAINT `FK_AEDOwners_Cities_CityId` FOREIGN KEY (`CityId`)
        REFERENCES `Cities` (`Id`) ON DELETE RESTRICT,
    CONSTRAINT `FK_AEDOwners_Streets_StreetId` FOREIGN KEY (`StreetId`)
        REFERENCES `Streets` (`Id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `PostalCodes` (
    `Id` INT NOT NULL AUTO_INCREMENT,
    `PostalCode` TEXT(6) NOT NULL,
    CONSTRAINT `PK_PostalCodes` PRIMARY KEY (`Id`)
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_unicode_ci;