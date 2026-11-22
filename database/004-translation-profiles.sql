CREATE TABLE IF NOT EXISTS `TranslationProfiles` (
    `Id` BIGINT NOT NULL AUTO_INCREMENT,
    `Name` VARCHAR(255) NOT NULL,
    CONSTRAINT `PK_TranslationProfiles` PRIMARY KEY (`Id`),
    UNIQUE INDEX `IX_TranslationProfiles_Name` (`Name`)
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `TranslationProfileUnits` (
    `Id` BIGINT NOT NULL AUTO_INCREMENT,
    `TranslationProfileId` BIGINT NOT NULL,
    `Position` INT NOT NULL,
    `FromColumn` LONGTEXT NOT NULL,
    `FromType` INT NOT NULL,
    `ToColumn` LONGTEXT NOT NULL,
    `ToType` INT NOT NULL,
    CONSTRAINT `PK_TranslationProfileUnits` PRIMARY KEY (`Id`),
    UNIQUE INDEX `IX_TranslationProfileUnits_TranslationProfileId_Position` (`TranslationProfileId`, `Position`),
    CONSTRAINT `FK_TranslationProfileUnits_Profile` FOREIGN KEY (`TranslationProfileId`)
        REFERENCES `TranslationProfiles` (`Id`) ON DELETE CASCADE,
    CONSTRAINT `CK_TranslationProfileUnits_Position` CHECK (`Position` >= 0),
    CONSTRAINT `CK_TranslationProfileUnits_FromType` CHECK (`FromType` IN (0, 1, 2, 3)),
    CONSTRAINT `CK_TranslationProfileUnits_ToType` CHECK (`ToType` IN (0, 1, 2, 3))
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

START TRANSACTION;

SET @SeedTranslationProfiles = NOT EXISTS (SELECT 1 FROM `TranslationProfiles`);

INSERT INTO `TranslationProfiles` (`Name`)
SELECT sample.Name
FROM (
    SELECT 'Sample owner import' AS Name
    UNION ALL SELECT 'Sample address import'
) AS sample
WHERE @SeedTranslationProfiles;

INSERT INTO `TranslationProfileUnits`
    (`TranslationProfileId`, `Position`, `FromColumn`, `FromType`, `ToColumn`, `ToType`)
SELECT profile.Id, sample.Position, sample.FromColumn, sample.FromType, sample.ToColumn, sample.ToType
FROM (
    SELECT 'Sample owner import' AS ProfileName, 0 AS Position,
        'owner_name' AS FromColumn, 2 AS FromType, 'AEDOwners.Name' AS ToColumn, 2 AS ToType
    UNION ALL SELECT 'Sample owner import', 1, 'regon', 2, 'AEDOwners.RegonNumber', 2
    UNION ALL SELECT 'Sample owner import', 2, 'is_public', 3, 'AEDOwners.IsPublic', 3
    UNION ALL SELECT 'Sample owner import', 3, 'city_id', 0, 'AEDOwners.CityId', 0
    UNION ALL SELECT 'Sample owner import', 4, 'street_id', 0, 'AEDOwners.StreetId', 0
    UNION ALL SELECT 'Sample address import', 0, 'city_id', 0, 'Addresses.CityId', 0
    UNION ALL SELECT 'Sample address import', 1, 'street_id', 0, 'Addresses.StreetId', 0
    UNION ALL SELECT 'Sample address import', 2, 'postal_code_id', 0, 'Addresses.PostalCodeId', 0
    UNION ALL SELECT 'Sample address import', 3, 'building_number', 0, 'Addresses.BuildingNumber', 0
) AS sample
JOIN `TranslationProfiles` AS profile ON profile.Name = sample.ProfileName
WHERE @SeedTranslationProfiles;

COMMIT;
