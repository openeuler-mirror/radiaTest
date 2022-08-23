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
-- NEW VERSION OF CASBIN_MODEL OF RADIATEST HAS DOMAIN FOR EACH RULE
-- E.G. [p, admin@group_1, /api/v1/test/1/next/2, GET, allow] 
--      => [p, admin@group_1, /api/v1/test/1/next/2, GET, allow, test] 

UPDATE casbin_rule
SET v4 = regexp_substr(v1, '(?<=/api/v1/)[^/]+')
WHERE ptype = 'p';