// CODEX_PUBLIC_WHITELIST_SYNC_BEGIN
// Append this WHOLE block AFTER the existing subscription extension script.
// Existing main(), proxy nodes, proxy groups and final MATCH are preserved.
;(function () {
  if (typeof main !== "function") {
    throw new Error("请保留原来的 main 函数，将公网白名单补丁追加到整个原脚本末尾。");
  }
  const previousMain = main;
  const setName = "公网直连域名";
  const publicRules = [
    "DOMAIN-KEYWORD,weixin",
    "DOMAIN-SUFFIX,qpic.cn",
    "DOMAIN-SUFFIX,qlogo.cn",
    "DOMAIN-SUFFIX,crashlytics.com",
    "DOMAIN-SUFFIX,4yailab.com",
    "DOMAIN-SUFFIX,mail.com",
    "DOMAIN,lanhuapp.com",
    "DOMAIN-WILDCARD,*.feishu.*",
    "DOMAIN-SUFFIX,163.com",
    "DOMAIN-SUFFIX,alipay.com",
    "DOMAIN-SUFFIX,gov.hk",
    "DOMAIN-SUFFIX,italent.cn",
    "DOMAIN-SUFFIX,kubesphere.com.cn",
    "DOMAIN-SUFFIX,codebuddy.cn",
    "DOMAIN-SUFFIX,jpage.cn",
    "DOMAIN-SUFFIX,coze.cn",
    "DOMAIN-SUFFIX,modelscope.cn",
    "DOMAIN-SUFFIX,ldxp.cn",
    "DOMAIN-WILDCARD,*.usr.*",
    "DOMAIN,zpayz.cn",
    "DOMAIN-WILDCARD,*.pay.*",
    "DOMAIN,api.z-pay.cn",
    "DOMAIN,www.model-family.com",
    "DOMAIN,apiopencc.com",
    "DOMAIN,api.models-family.com",
    "DOMAIN,www.codewing.link",
    "DOMAIN,hero-sms.com",
    "DOMAIN-WILDCARD,*.decodo.*",
    "DOMAIN,www.cleverbridge.com",
    "DOMAIN-SUFFIX,feishu.cn",
    "DOMAIN-SUFFIX,feishucdn.com",
    "DOMAIN-SUFFIX,feishu.net",
    "DOMAIN-SUFFIX,feishupkg.com",
    "DOMAIN-SUFFIX,bstatics.com",
    "DOMAIN,pay.kbfu.cn",
    "DOMAIN,xxxyan.cc",
    "DOMAIN,dashboard.decodo.com",
    "DOMAIN,api.xunhupay.com",
    "DOMAIN-SUFFIX,aizlx.com",
    "DOMAIN,signup.live.com",
    "DOMAIN,login.live.com",
    "DOMAIN,login.microsoftonline.com",
    "DOMAIN,admin.xunhupay.com",
    "DOMAIN-SUFFIX,aliyuncs.com",
    "DOMAIN,web.ddnsto.com",
    "DOMAIN-SUFFIX,volces.com",
    "DOMAIN-SUFFIX,deepseek.com",
    "DOMAIN,console.volcengine.com",
    "DOMAIN-SUFFIX,meeting.tencent.com",
    "DOMAIN-SUFFIX,igtm-meeting-tencent.com",
    "DOMAIN,docs.apifox.com"
  ];
  const appRules = [
    "PROCESS-PATH-REGEX,^/Applications/TencentMeeting[.]app/.*,DIRECT",
    "PROCESS-NAME,WeChat,DIRECT"
  ];

  function applyWhitelist(config) {
    if (!config || typeof config !== "object" || !Array.isArray(config.rules)) {
      throw new Error("原脚本没有返回包含 rules 的配置，请先导入并启用有效订阅。");
    }
    config["rule-providers"] = {
      ...(config["rule-providers"] || {}),
      [setName]: {
        type: "inline",
        behavior: "classical",
        payload: publicRules.slice()
      }
    };
    const additions = appRules.concat(["RULE-SET," + setName + ",DIRECT"]);
    const rules = config.rules.filter(rule => !additions.includes(rule));
    const insertAt = rules.findIndex(rule =>
      typeof rule === "string" && (
        /^MATCH,/i.test(rule) ||
        /^NETWORK,UDP,REJECT(?:-DROP)?(?:,|$)/i.test(rule)
      )
    );
    rules.splice(insertAt < 0 ? rules.length : insertAt, 0, ...additions);
    config.rules = rules;

    config.dns = config.dns || {};
    config.dns["nameserver-policy"] = {
      ...(config.dns["nameserver-policy"] || {}),
      ["rule-set:" + setName]: [
        "https://dns.alidns.com/dns-query#DIRECT",
        "https://doh.pub/dns-query#DIRECT"
      ]
    };
    // Keep non-default fake-IP filter formats intact.
    const filterMode = config.dns["fake-ip-filter-mode"] || "blacklist";
    if (filterMode === "blacklist") {
      config.dns["fake-ip-filter"] = Array.from(new Set([
        ...(config.dns["fake-ip-filter"] || []),
        "rule-set:" + setName
      ]));
    }
    return config;
  }

  main = function (config, profileName) {
    return applyWhitelist(previousMain(config, profileName));
  };
})();
// CODEX_PUBLIC_WHITELIST_SYNC_END
