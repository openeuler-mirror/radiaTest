#                                  登录重构后数据库变更方法

背景:因radiaTest平台与码云oauth2鉴权解耦后,登录鉴权方式多样化,导致user表中gitee_id,gitee_name,gitee_login字段变更为user_id,user_name,user_login,与user表绑定外键关系的表需要作出变更,由于migrate升级数据库能力有限,采用手动升级,保障数据平迁。

## step 1

执行get_sqls_for_remove_old_foreign_keys.sql,sql说明:本步骤主要是关闭外键,重命名表字段以及变更字段类型。

注: migrate是无法识别表字段重命名场景,且在原始字段移除后,引入外键不存在问题。

## step 2

执行change_to_user_id.sql, sql说明:查出radiatest对应的schema下跟user表有关联的外键详情,并执行查询结果,删除所有与user表有关的外键信息。

## step 3

执行modify_columns_type.sql,sql说明:变更与user表user_id字段外键关联的表字段类型。

## step 4

清空migrate目录,分别执行:

​      python3 manage.py db init 

​      python3 manage.py db migrate

​      python3 manage.py db upgrade

执行第三句后,会出现组织表新增字段缺乏默认值,执行step 5.

## step 5

执行add_default_value_for_org.sql,sql说明:为历史数据新增的字段添加默认值.

step 5执行后,可以再次执行step 4.

注:升级过程中,遇到问题,清理问题后,step 2 step3 step4可反复执行.



