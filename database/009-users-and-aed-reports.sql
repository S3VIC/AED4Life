CREATE TABLE IF NOT EXISTS `Users` (
    `Id` BIGINT NOT NULL AUTO_INCREMENT,
    `Username` VARCHAR(255) NOT NULL,
    `PasswordHash` VARCHAR(512) NOT NULL,
    `FirstName` LONGTEXT NOT NULL,
    `LastName` LONGTEXT NOT NULL,
    `BirthDate` DATE NOT NULL,
    `AddressId` BIGINT NOT NULL,
    `Type` INT NOT NULL,
    CONSTRAINT `PK_Users` PRIMARY KEY (`Id`),
    CONSTRAINT `CK_Users_Type` CHECK (`Type` IN (0, 1, 2, 3)),
    CONSTRAINT `CK_Users_PasswordHash` CHECK (CHAR_LENGTH(TRIM(`PasswordHash`)) > 0),
    UNIQUE INDEX `IX_Users_Username` (`Username`),
    INDEX `IX_Users_AddressId` (`AddressId`),
    CONSTRAINT `FK_Users_Addresses_AddressId` FOREIGN KEY (`AddressId`)
        REFERENCES `Addresses` (`Id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `AEDReports` (
    `Id` BIGINT NOT NULL AUTO_INCREMENT,
    `UserId` BIGINT NOT NULL,
    `AEDId` BIGINT NULL,
    `PhotoUrl` LONGTEXT NOT NULL,
    `Description` LONGTEXT NOT NULL,
    `AvailabilityStartHour` INT NULL,
    `AvailabilityEndHour` INT NULL,
    `IsPubliclyAccessible` TINYINT(1) NULL,
    `Rating` INT NULL,
    `Created` DATETIME(6) NOT NULL,
    `LastUpdated` DATETIME(6) NOT NULL,
    `Status` INT NOT NULL,
    `ReporterLatitude` DOUBLE NULL,
    `ReporterLongitude` DOUBLE NULL,
    `Latitude` DOUBLE NULL,
    `Longitude` DOUBLE NULL,
    `CityName` LONGTEXT NULL,
    `StreetName` LONGTEXT NULL,
    `PostalCode` VARCHAR(6) NULL,
    `BuildingNumber` INT NULL,
    CONSTRAINT `PK_AEDReports` PRIMARY KEY (`Id`),
    CONSTRAINT `CK_AEDReports_Status` CHECK (`Status` IN (0, 1, 2, 3)),
    CONSTRAINT `CK_AEDReports_PhotoUrl` CHECK (`PhotoUrl` REGEXP '[^[:space:]]'),
    CONSTRAINT `CK_AEDReports_Description` CHECK (`Description` REGEXP '[^[:space:]]'),
    CONSTRAINT `CK_AEDReports_IsPubliclyAccessible` CHECK (`IsPubliclyAccessible` IS NULL OR `IsPubliclyAccessible` IN (0, 1)),
    CONSTRAINT `CK_AEDReports_Rating` CHECK (`Rating` IS NULL OR `Rating` BETWEEN 0 AND 100),
    CONSTRAINT `CK_AEDReports_ReporterLatitude` CHECK (`ReporterLatitude` IS NULL OR `ReporterLatitude` BETWEEN -90 AND 90),
    CONSTRAINT `CK_AEDReports_ReporterLongitude` CHECK (`ReporterLongitude` IS NULL OR `ReporterLongitude` BETWEEN -180 AND 180),
    CONSTRAINT `CK_AEDReports_ReporterCoordinates` CHECK ((`ReporterLatitude` IS NULL) = (`ReporterLongitude` IS NULL)),
    CONSTRAINT `CK_AEDReports_Latitude` CHECK (`Latitude` IS NULL OR `Latitude` BETWEEN -90 AND 90),
    CONSTRAINT `CK_AEDReports_Longitude` CHECK (`Longitude` IS NULL OR `Longitude` BETWEEN -180 AND 180),
    CONSTRAINT `CK_AEDReports_AvailabilityHours` CHECK (
        (`AvailabilityStartHour` IS NULL OR `AvailabilityStartHour` BETWEEN 0 AND 23)
        AND (`AvailabilityEndHour` IS NULL OR `AvailabilityEndHour` BETWEEN 0 AND 24)
        AND (`AvailabilityStartHour` IS NULL OR `AvailabilityEndHour` IS NULL
            OR `AvailabilityStartHour` <> `AvailabilityEndHour`)
    ),
    INDEX `IX_AEDReports_UserId` (`UserId`),
    INDEX `IX_AEDReports_AEDId` (`AEDId`),
    CONSTRAINT `FK_AEDReports_Users_UserId` FOREIGN KEY (`UserId`)
        REFERENCES `Users` (`Id`) ON DELETE RESTRICT,
    CONSTRAINT `FK_AEDReports_AEDs_AEDId` FOREIGN KEY (`AEDId`)
        REFERENCES `AEDs` (`Id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
