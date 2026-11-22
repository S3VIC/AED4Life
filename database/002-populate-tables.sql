SET NAMES utf8mb4;
START TRANSACTION;

INSERT INTO `Cities` (`Name`)
SELECT sample.Name
FROM (
    SELECT 'Warszawa' AS Name
    UNION ALL SELECT 'Bydgoszcz'
    UNION ALL SELECT 'Glinik'
    UNION ALL SELECT 'Rzeszów'
    UNION ALL SELECT 'Monza'
    UNION ALL SELECT 'Berlin'
) AS sample
WHERE NOT EXISTS (SELECT 1 FROM `Cities`);

INSERT INTO `Streets` (`Name`)
SELECT sample.Name
FROM (
    SELECT 'Aleja Niepodległości' AS Name
    UNION ALL SELECT 'Miła'
    UNION ALL SELECT 'Wiejska'
    UNION ALL SELECT 'Klaudiuszowa'
) AS sample
WHERE NOT EXISTS (SELECT 1 FROM `Streets`);

INSERT INTO `PostalCodes` (`Code`)
SELECT sample.Code
FROM (
    SELECT '01-357' AS Code
    UNION ALL SELECT '85-708'
    UNION ALL SELECT '11-123'
    UNION ALL SELECT '12-122'
    UNION ALL SELECT '13-234'
    UNION ALL SELECT '12-478'
) AS sample
WHERE NOT EXISTS (SELECT 1 FROM `PostalCodes`);

INSERT INTO `Addresses` (`CityId`, `StreetId`, `PostalCodeId`, `BuildingNumber`)
WITH CitySlots AS (
    SELECT Id, ROW_NUMBER() OVER (ORDER BY Id) AS Slot, COUNT(*) OVER () AS SlotCount
    FROM `Cities`
), StreetSlots AS (
    SELECT Id, ROW_NUMBER() OVER (ORDER BY Id) AS Slot, COUNT(*) OVER () AS SlotCount
    FROM `Streets`
), PostalCodeSlots AS (
    SELECT Id, ROW_NUMBER() OVER (ORDER BY Id) AS Slot, COUNT(*) OVER () AS SlotCount
    FROM `PostalCodes`
)
SELECT city.Id, street.Id, postalCode.Id, sample.BuildingNumber
FROM (
    SELECT 1 AS CitySlot, 1 AS StreetSlot, 1 AS PostalCodeSlot, 225 AS BuildingNumber
    UNION ALL SELECT 2, 2, 2, 18
    UNION ALL SELECT 3, 3, 3, 7
    UNION ALL SELECT 4, 4, 4, 43
    UNION ALL SELECT 5, 2, 5, 112
    UNION ALL SELECT 6, 1, 6, 56
) AS sample
JOIN CitySlots AS city ON city.Slot = MOD(sample.CitySlot - 1, city.SlotCount) + 1
JOIN StreetSlots AS street ON street.Slot = MOD(sample.StreetSlot - 1, street.SlotCount) + 1
JOIN PostalCodeSlots AS postalCode ON postalCode.Slot = MOD(sample.PostalCodeSlot - 1, postalCode.SlotCount) + 1
WHERE NOT EXISTS (SELECT 1 FROM `Addresses`);

-- Location slots use actual IDs and cycle through any existing lookup rows.
INSERT INTO `AEDOwners` (`RegonNumber`, `IsPublic`, `Name`, `CityId`, `StreetId`)
WITH CitySlots AS (
    SELECT Id, ROW_NUMBER() OVER (ORDER BY Id) AS Slot, COUNT(*) OVER () AS SlotCount
    FROM `Cities`
), StreetSlots AS (
    SELECT Id, ROW_NUMBER() OVER (ORDER BY Id) AS Slot, COUNT(*) OVER () AS SlotCount
    FROM `Streets`
)
SELECT sample.RegonNumber, sample.IsPublic, sample.Name, city.Id, street.Id
FROM (
    SELECT '123456789' AS RegonNumber, 1 AS IsPublic,
        'Szkoła Podstawowa nr. 1 w Warszawie' AS Name, 1 AS CitySlot, 1 AS StreetSlot
    UNION ALL SELECT '987654321', 1, 'Szkoła Podstawowa nr. 2 w Warszawie', 2, 1
    UNION ALL SELECT '123123456', 1, 'Liceum Ogólnokształcace nr. 4 w Warszawie', 3, 1
    UNION ALL SELECT '345345123', 1, 'JRG nr. 3 w Warszawie', 1, 2
    UNION ALL SELECT '123789678', 1, 'OSP Śródmieście', 1, 3
) AS sample
JOIN CitySlots AS city ON city.Slot = MOD(sample.CitySlot - 1, city.SlotCount) + 1
JOIN StreetSlots AS street ON street.Slot = MOD(sample.StreetSlot - 1, street.SlotCount) + 1
WHERE NOT EXISTS (SELECT 1 FROM `AEDOwners`);

INSERT INTO `AEDs` (`AddressId`, `Created`, `LastUpdated`, `SerialNumber`,
    `Access`, `AvailabilityStartHour`, `AvailabilityEndHour`, `Rating`)
WITH AddressSlots AS (
    SELECT Id, ROW_NUMBER() OVER (ORDER BY Id) AS Slot, COUNT(*) OVER () AS SlotCount
    FROM `Addresses`
)
SELECT address.Id, CURRENT_TIMESTAMP(6), CURRENT_TIMESTAMP(6), sample.SerialNumber,
    sample.Access, sample.AvailabilityStartHour, sample.AvailabilityEndHour, sample.Rating
FROM (
    SELECT 1 AS AddressSlot, 'AED-7F3A9C21' AS SerialNumber,
        0 AS Access, 0 AS AvailabilityStartHour, 24 AS AvailabilityEndHour, 1 AS Rating
    UNION ALL SELECT 2, 'AED-B82D4E60', 1, 8, 20, 1
    UNION ALL SELECT 3, 'AED-19C6F4A8', 2, 9, 17, 0
    UNION ALL SELECT 4, 'AED-E5A207D3', 0, 22, 6, 1
    UNION ALL SELECT 5, 'AED-6C91B0F7', 1, NULL, NULL, 0
    UNION ALL SELECT 6, 'AED-A4308E2B', NULL, NULL, NULL, 0
) AS sample
JOIN AddressSlots AS address ON address.Slot = MOD(sample.AddressSlot - 1, address.SlotCount) + 1
WHERE NOT EXISTS (SELECT 1 FROM `AEDs`);

COMMIT;

SELECT 'Cities' AS TableName, COUNT(*) AS RowCount FROM `Cities`
UNION ALL SELECT 'Streets', COUNT(*) FROM `Streets`
UNION ALL SELECT 'PostalCodes', COUNT(*) FROM `PostalCodes`
UNION ALL SELECT 'Addresses', COUNT(*) FROM `Addresses`
UNION ALL SELECT 'AEDOwners', COUNT(*) FROM `AEDOwners`
UNION ALL SELECT 'AEDs', COUNT(*) FROM `AEDs`;