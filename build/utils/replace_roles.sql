-- Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
-- This program is licensed under Mulan PSL v2.
-- You can use it according to the terms and conditions of the Mulan PSL v2.
--          http://license.coscl.org.cn/MulanPSL2
-- THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
-- EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
-- MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
-- See the Mulan PSL v2 for more details.
-- ##################################
-- @Author  : Ethan-Zhang
-- @email   : ethanzhang55@outlook.com
-- @Date    : 2022/08/23 21:51:00
-- @License : Mulan PSL v2
-- ####################################
-- THIS SQL SCRIPT IS FOR MIGRATION FROM OLD VERSION CASBIN_MODEL TO THE NEW
-- NEW VERSION OF CASBIN_MODEL OF RADIATEST USE GROUP_ID/ORG_ID TO REPLACE GROUP_NAME/ORG_NAME FOR EACH RULE
-- E.G. [g, admin@group_test, default@group_test ]
--      => [g, admin@group_1, default@group_1]

DELIMITER $$
DROP PROCEDURE IF EXISTS Replace_Roles$$
CREATE PROCEDURE Replace_Roles(in group_pattern VARCHAR(50), in org_pattern VARCHAR(50))
BEGIN
	DECLARE rule_id INT;
	DECLARE group_id INT;
	DECLARE org_id INT;
	
	DECLARE rule CURSOR FOR 
	SELECT id FROM casbin_rule;
					
	OPEN rule;
	LOOP
		FETCH rule INTO rule_id;
		
		UPDATE casbin_rule
		SET v0 = regexp_replace(
			v0,
			group_pattern,
			IFNULL(
				(
					SELECT group.id
					FROM `group`, (
						SELECT regexp_substr(
							v0,
							group_pattern
						) AS name
						FROM casbin_rule
						WHERE casbin_rule.id = rule_id
					) AS t
					WHERE group.name = t.name
				), 
				''
			)
		), v1 = regexp_replace(
			v1,
			group_pattern,
			IFNULL(
				(
					SELECT group.id
					FROM `group`, (
						SELECT regexp_substr(
							v1,
							group_pattern
						) AS name
						FROM casbin_rule
						WHERE casbin_rule.id = rule_id
					) AS t
					WHERE group.name = t.name
				), 
				''
			)
		)
		WHERE casbin_rule.id = rule_id;
		
		UPDATE casbin_rule
		SET v0 = regexp_replace(
			v0,
			org_pattern,
			IFNULL(
				(
					SELECT organization.id
					FROM `organization`, (
						SELECT regexp_substr(
							v0,
							org_pattern
						) AS name
						FROM casbin_rule
						WHERE casbin_rule.id = rule_id
					) AS t
					WHERE organization.name = t.name
				), 
				''
			)
		), v1 = regexp_replace(
			v1,
			org_pattern,
			IFNULL(
				(
					SELECT organization.id
					FROM `organization`, (
						SELECT regexp_substr(
							v1,
							org_pattern
						) AS name
						FROM casbin_rule
						WHERE casbin_rule.id = rule_id
					) AS t
					WHERE organization.name = t.name
				), 
				''
			)
		)
		WHERE casbin_rule.id = rule_id;
	END LOOP;
	CLOSE rule;
END$$

DELIMITER ;
CALL Replace_Roles('(?<=@group_)[^0-9]+', '(?<=@org_)[^0-9]+');