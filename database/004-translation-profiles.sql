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
