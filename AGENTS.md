::ILANG
[TYPE:agent-guide][PROJECT:vps-deals][LANG:zh]
::STATE{@PROJECT, kind:public static comparison site, data_source:.ilang/site.ilang}
::MODULE{PURPOSE|title:目标}
以官方同页标示的常规价和真实促销价差为唯一 deal 准入条件；生成可追溯优惠页、厂商目录、对比页。
::MODULE{PERMISSIONS|title:允许的修改}
修复爬虫、增加验证测试、改模板、添加官方数据源、修复无效链接。
::BOUNDARY{never:发明价格 优惠 佣金 到期日期 伪造评价 绕过反爬 抓登录数据 静默替换官网链接|scope:permanent}
::RULE{scraper.py build.py 都必须读取 .ilang/site.ilang}
::RULE{找不到同一型号官方常规原价+促销价+条件 => 0条deal,仅保留厂商页}
::RULE{标准公开标价绝不进入deal,不能替换为普通价格页}
::RULE{相同厂商+型号+货币去重,没有确切日期不输出截止时间}
::RULE{站点实际域名vps.madebyyong.com,不要回退到pages.dev canonical}
::RULE{templates文件负责HTML,构建不依赖任何AI或收费API}
::RULE{多语言须有真实地区价格+本币+官方来源+hreflang,否则不得启用}
::RULE{联盟申请批准后才能加affiliate,不自买自推不注入Cookie不竞价品牌词}
::RULE{代码变更需运行所有 unittest,确认sitemap = 2+配置厂商数+严格核实的deal数}
::RULE{未实现专用解析器的厂商只能标记parser_not_implemented,不能声称官网没有优惠}
::RULE{每家来源必须检查robots.txt和HTTPS；第三方错误、403、超时不得绕过反爬}
::RULE{不得向 GitHub 或网站提交秘密}