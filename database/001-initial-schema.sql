CREATE TABLE IF NOT EXISTS `Cities` (
    `Id` BIGINT NOT NULL AUTO_INCREMENT,
    `Name` LONGTEXT NULL,
    CONSTRAINT `PK_Cities` PRIMARY KEY (`Id`)
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `Streets` (
    `Id` BIGINT NOT NULL AUTO_INCREMENT,
    `Name` LONGTEXT NULL,
    CONSTRAINT `PK_Streets` PRIMARY KEY (`Id`)
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `PostalCodes` (
    `Id` INT NOT NULL AUTO_INCREMENT,
    `Code` VARCHAR(6) NULL,
    CONSTRAINT `PK_PostalCodes` PRIMARY KEY (`Id`)
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `Addresses` (
    `Id` BIGINT NOT NULL AUTO_INCREMENT,
    `StreetId` BIGINT NULL,
    `CityId` BIGINT NULL,
    `PostalCodeId` INT NULL,
    `BuildingNumber` INT NULL,
    CONSTRAINT `PK_Addresses` PRIMARY KEY (`Id`),
    INDEX `IX_Addresses_StreetId` (`StreetId`),
    INDEX `IX_Addresses_CityId` (`CityId`),
    INDEX `IX_Addresses_PostalCodeId` (`PostalCodeId`),
    CONSTRAINT `FK_Address_Streets_StreetId` FOREIGN KEY (`StreetId`)
        REFERENCES `Streets` (`Id`) ON DELETE RESTRICT,
    CONSTRAINT `FK_Address_Cities_CityId` FOREIGN KEY (`CityId`)
        REFERENCES `Cities` (`Id`) ON DELETE RESTRICT,
    CONSTRAINT `FK_Address_PostalCodes_PostalCodeId` FOREIGN KEY (`PostalCodeId`)
        REFERENCES `PostalCodes` (`Id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `AEDs` (
    `Id` BIGINT NOT NULL AUTO_INCREMENT,
    `AddressId` BIGINT NULL,
    `Created` DATETIME(6) NOT NULL,
    `LastUpdated` DATETIME(6) NOT NULL,
    `SerialNumber` LONGTEXT NULL,
    `Latitude` DOUBLE NULL,
    `Longitude` DOUBLE NULL,
    `Access` INT NULL,
    `AvailabilityStartHour` INT NULL,
    `AvailabilityEndHour` INT NULL,
    `Rating` INT NULL,
    CONSTRAINT `PK_AEDs` PRIMARY KEY (`Id`),
    CONSTRAINT `CK_AEDs_Access` CHECK (`Access` IS NULL OR `Access` IN (0, 1, 2)),
    CONSTRAINT `CK_AEDs_Rating` CHECK (`Rating` IS NULL OR `Rating` IN (0, 1)),
    CONSTRAINT `CK_AEDs_Latitude` CHECK (`Latitude` IS NULL OR `Latitude` BETWEEN -90 AND 90),
    CONSTRAINT `CK_AEDs_Longitude` CHECK (`Longitude` IS NULL OR `Longitude` BETWEEN -180 AND 180),
    CONSTRAINT `CK_AEDs_AvailabilityHours` CHECK (
        (`AvailabilityStartHour` IS NULL OR `AvailabilityStartHour` BETWEEN 0 AND 23)
        AND (`AvailabilityEndHour` IS NULL OR `AvailabilityEndHour` BETWEEN 0 AND 24)
        AND (`AvailabilityStartHour` IS NULL OR `AvailabilityEndHour` IS NULL
            OR `AvailabilityStartHour` <> `AvailabilityEndHour`)
    ),
    INDEX `IX_AEDs_AddressId` (`AddressId`),
    CONSTRAINT `FK_AEDs_Address_AddressId` FOREIGN KEY (`AddressId`)
        REFERENCES `Addresses` (`Id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `AEDOwners` (
    `Id` BIGINT NOT NULL AUTO_INCREMENT,
    `RegonNumber` VARCHAR(14) NULL,
    `IsPublic` TINYINT(1) NULL,
    `Name` LONGTEXT NULL,
    `CityId` BIGINT NULL,
    `StreetId` BIGINT NULL,
    CONSTRAINT `PK_AEDOwners` PRIMARY KEY (`Id`),
    UNIQUE INDEX `IX_AEDOwners_RegonNumber` (`RegonNumber`),
    INDEX `IX_AEDOwners_CityId` (`CityId`),
    INDEX `IX_AEDOwners_StreetId` (`StreetId`),
    CONSTRAINT `FK_AEDOwners_Cities_CityId` FOREIGN KEY (`CityId`)
        REFERENCES `Cities` (`Id`) ON DELETE RESTRICT,
    CONSTRAINT `FK_AEDOwners_Streets_StreetId` FOREIGN KEY (`StreetId`)
        REFERENCES `Streets` (`Id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
