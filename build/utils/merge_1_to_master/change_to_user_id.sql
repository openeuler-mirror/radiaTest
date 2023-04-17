set FOREIGN_KEY_CHECKS = 0;
alter table user modify gitee_id varchar(512);
alter table user change gitee_id user_id varchar(512);
alter table user change gitee_login user_login varchar(50);
alter table user change gitee_name user_name varchar(50);
alter table re_user_organization modify user_gitee_id varchar(512);
alter table re_user_organization change user_gitee_id user_id varchar(512);
alter table re_user_group modify user_gitee_id varchar(512);
alter table re_user_group change user_gitee_id user_id varchar(512);