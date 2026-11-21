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
    CONSTRAINT `PK_AEDs` PRIMARY KEY (`Id`),
    INDEX `IX_AEDs_CityId` (`CityId`),
    INDEX `IX_AEDs_StreetId` (`StreetId`),
    CONSTRAINT `FK_AEDs_Cities_CityId` FOREIGN KEY (`CityId`)
        REFERENCES `Cities` (`Id`) ON DELETE RESTRICT,
    CONSTRAINT `FK_AEDs_Streets_StreetId` FOREIGN KEY (`StreetId`)
        REFERENCES `Streets` (`Id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `AEDOwners` (
    `RegonNumber` BIGINT NOT NULL,
    `IsPublic` TINYINT(1) NOT NULL,
    `Name` LONGTEXT NOT NULL,
    `CityId` BIGINT NOT NULL,
    `StreetId` BIGINT NOT NULL,
    CONSTRAINT `PK_AEDOwners` PRIMARY KEY (`RegonNumber`),
    INDEX `IX_AEDOwners_CityId` (`CityId`),
    INDEX `IX_AEDOwners_StreetId` (`StreetId`),
    CONSTRAINT `FK_AEDOwners_Cities_CityId` FOREIGN KEY (`CityId`)
        REFERENCES `Cities` (`Id`) ON DELETE RESTRICT,
    CONSTRAINT `FK_AEDOwners_Streets_StreetId` FOREIGN KEY (`StreetId`)
        REFERENCES `Streets` (`Id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
