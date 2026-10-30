::ILANG
[TYPE:agent-guide][PROJECT:vps-deals][LANG:zh]
::STATE{@PROJECT, kind:public static comparison site, data_source:.ilang/site.ilang}
::MODULE{PURPOSE|title:目标}
定期审阅官方主机价格页面，生成可追溯的静态价格信息和服务商目录。
::MODULE{PERMISSIONS|title:允许的修改}
修复爬虫、增加验证测试、改模板、添加官方数据源、修复无效链接。
::BOUNDARY{never:发明价格 优惠 佣金 到期日期 伪造评价 绕过反爬 抓登录数据 静默替换官网链接|scope:permanent}
::RULE{scraper.py build.py 都必须读取 .ilang/site.ilang}
::RULE{不确定的价格不显示；官方链接不能证明促销时按公开价格而非折扣展示}
::RULE{不得向 GitHub 或网站提交秘密}