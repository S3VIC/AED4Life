SET NAMES utf8mb4;
START TRANSACTION;

INSERT INTO `Cities` (`Name`, `PostalCode`)
SELECT sample.Name, sample.PostalCode
FROM (
    SELECT 'Warszawa' AS Name, '01-357' AS PostalCode
    UNION ALL SELECT 'Bydgoszcz', '85-708'
    UNION ALL SELECT 'Glinik', '11-123'
    UNION ALL SELECT 'Rzeszów', '12-122'
    UNION ALL SELECT 'Monza', '13-234'
    UNION ALL SELECT 'Berlin', '12-478'
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

INSERT INTO `AEDs` (`CityId`, `StreetId`, `HouseNumber`, `Created`, `LastUpdated`, `SerialNumber`,
    `Access`, `AvailabilityStartHour`, `AvailabilityEndHour`, `Rating`)
WITH CitySlots AS (
    SELECT Id, ROW_NUMBER() OVER (ORDER BY Id) AS Slot, COUNT(*) OVER () AS SlotCount
    FROM `Cities`
), StreetSlots AS (
    SELECT Id, ROW_NUMBER() OVER (ORDER BY Id) AS Slot, COUNT(*) OVER () AS SlotCount
    FROM `Streets`
)
SELECT city.Id, street.Id, sample.HouseNumber, CURRENT_TIMESTAMP(6), CURRENT_TIMESTAMP(6), sample.SerialNumber,
    sample.Access, sample.AvailabilityStartHour, sample.AvailabilityEndHour, sample.Rating
FROM (
    SELECT 1 AS CitySlot, 1 AS StreetSlot, 225 AS HouseNumber, 'AED-7F3A9C21' AS SerialNumber,
        0 AS Access, 0 AS AvailabilityStartHour, 24 AS AvailabilityEndHour, 1 AS Rating
    UNION ALL SELECT 2, 2, 18, 'AED-B82D4E60', 1, 8, 20, 1
    UNION ALL SELECT 3, 3, 7, 'AED-19C6F4A8', 2, 9, 17, 0
    UNION ALL SELECT 4, 4, 43, 'AED-E5A207D3', 0, 22, 6, 1
    UNION ALL SELECT 5, 2, 112, 'AED-6C91B0F7', 1, NULL, NULL, 0
    UNION ALL SELECT 6, 1, 56, 'AED-A4308E2B', NULL, NULL, NULL, 0
) AS sample
JOIN CitySlots AS city ON city.Slot = MOD(sample.CitySlot - 1, city.SlotCount) + 1
JOIN StreetSlots AS street ON street.Slot = MOD(sample.StreetSlot - 1, street.SlotCount) + 1
WHERE NOT EXISTS (SELECT 1 FROM `AEDs`);

COMMIT;

SELECT 'Cities' AS TableName, COUNT(*) AS RowCount FROM `Cities`
UNION ALL SELECT 'Streets', COUNT(*) FROM `Streets`
UNION ALL SELECT 'AEDOwners', COUNT(*) FROM `AEDOwners`
UNION ALL SELECT 'AEDs', COUNT(*) FROM `AEDs`;