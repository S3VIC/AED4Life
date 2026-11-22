ALTER TABLE `Users`
    ADD COLUMN IF NOT EXISTS `PasswordHash` VARCHAR(512) NULL AFTER `Username`;

DELIMITER //
BEGIN NOT ATOMIC
    IF EXISTS (SELECT 1 FROM `Users` WHERE `PasswordHash` IS NULL OR CHAR_LENGTH(TRIM(`PasswordHash`)) = 0) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Provision Users.PasswordHash for every existing user with the application password hasher, then rerun initialization.';
    END IF;
END//
DELIMITER ;

ALTER TABLE `Users`
    MODIFY COLUMN `PasswordHash` VARCHAR(512) NOT NULL,
    DROP CONSTRAINT IF EXISTS `CK_Users_PasswordHash`,
    ADD CONSTRAINT `CK_Users_PasswordHash` CHECK (CHAR_LENGTH(TRIM(`PasswordHash`)) > 0);
