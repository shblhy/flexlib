# Flexlib

python开发的一个扩展库，包含网站及日常开发的一些实用工具，和python常用库(mongoengine/flask_restplus)的一些扩展。

利用多个开源库，共同构成了一套可按需组装、自由拓展的网站开发框架。


## 如何使用


期望安装方式：pip install flexlib

当前实际安装：用git子仓库的方式进行引用

    git submodule add https://gitee.com/wow_1/exlib exlib
    git submodule init
    git submodule update

具体到代码层面，方法直接调用，提供的类，多数可直接使用，如需改造，一般有两种使用方式：

    1、继承重写，即类功能重写的常规方式
    2、定义配置类，适用于当前类已经被库中其它类引用的情况

## 功能
    
### 日常工具 widgets


方法计时器   func_timer
缓存属性    cached_property
类属性     classproperty



### 网站工具
    
### 常见库扩展


#### mongoengine

以下罗列了常用功能列表，更多细节，请参见模块init文件的注释。
    
##### DocumentMixin:提供了Document对象使用的一些常用方法
    
     create_with   以字典直接创建对象（支持嵌套）
     update_with   以字典直接更新对象（支持嵌套）
     db_dict    获取数据库字典
     to_dict    转为字典

推荐用法：
    自定义Document，在引用mongoengine前加一层封装，在这个层次加入自己需要的业务公共属性，并继承DocumentMixin


##### HistoryMixin:为Document提供保存历史记录功能

##### SearchMixin:为Document提供保存历史记录功能

##### ConditionValidatorMixin:为Document提供条件校验功能


#### peewee




#### flask_restplus


#### elasticsearch_dsl


### 组合工具

#### rest

##### ListResponse/SingleResponse



## 基于Flexlib进行网站开发

### 整体描述

Flexlib 已整理了全套web开发过程，可提供以下问题情境解决范例：

1. 数据库支持 mysql(基于peewee) mongo(基于Mongoengine)
2. 自动化api文档（基于flask_restplus和swagger）
3. 登录、
4. 跨域 （flask_cors）
5. 角色、权限 casbin
6. 定时/异步任务 celery/apscheduler
7. 命令行操作 click flask cmd
8. 


实际使用时，按需组装。具体用法可参看样例网站 万象 wx

### 代码规范

### 案例


