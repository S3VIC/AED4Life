DELIMITER //
BEGIN NOT ATOMIC
    IF EXISTS (SELECT 1 FROM `AEDReports` WHERE `PhotoUrl` IS NULL OR `PhotoUrl` NOT REGEXP '[^[:space:]]') THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Provide a nonblank AEDReports.PhotoUrl for every existing report, then rerun initialization.';
    END IF;
END//
DELIMITER ;

ALTER TABLE `AEDReports`
    MODIFY COLUMN `PhotoUrl` LONGTEXT NOT NULL,
    DROP CONSTRAINT IF EXISTS `CK_AEDReports_PhotoUrl`,
    ADD CONSTRAINT `CK_AEDReports_PhotoUrl` CHECK (`PhotoUrl` REGEXP '[^[:space:]]');
