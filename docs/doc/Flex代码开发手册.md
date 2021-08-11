# Flexlib 开发手册

0、安装于基本使用
    
    pip install Flexlib 即可获得Flexlib最新版
    github地址 https://github.com/shblhy/flexlib 码云地址 
    tags中保存了发布的

1、Flexlib将代码分为环境代码和业务代码，实现代码由环境代码和业务代码的子类重写而得。开发者必须先提供基础的环境代码，在此基础上再进行业务开发。

    我们将代码分为业务代码/环境代码/实现代码三类。实现代码 = 环境代码 + 业务代码
    业务代码指通用业务逻辑，描述的是行业的业务经验。
    环境代码指为实现系统功能，必须提供各类环境支持，如数据库，缓存，py基础库，等等。不同系统会有所不同。
    实现代码，顾名思义是业务逻辑放到具体环境中做出的实际实现。
    三类代码都实现为类，实现代码多重继承于业务代码和环境代码，依据实际需要对父类提供的方法或属性进行重写。


2、对代码进行分层，一种典型的分层结构如下：

    app
        模块
            models
            serializers
            schemas
            views
            tests
    doc
    utils
    scripts
    deploy
    
明确各层代码的职责。参考 6.1、代码分层。
    
3、提供环境代码及相关使用说明。（复制Flex提供的环境类模板，按需改写，对改写部分，应额外提供说明）。
所谓环境代码，主要是描述了系统运行的环境，使用的类库等。它和配套使用说明或开发规范，应在实际进行业务开发前提供到位。
eg.
    
    wow 基于Flexlib的开发手册
    models: 数据分为资源数据、业务数据、混合数据，对应model基类：Document/DataDocument/MixDocument
    views层代码继承于SkvView，
    se
    

4、DocumentMixin 功能介绍：

5、



    