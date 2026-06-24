/**
 * 前端输入安全工具
 *
 * 提供输入清理和敏感内容检测，在请求发送到后端之前进行本地拦截。
 */

// ==================== XSS 防护 ====================

/**
 * 清理用户输入中的潜在恶意内容
 * - 剥离 HTML 标签和事件处理器
 * - 移除危险协议
 * - 保留正常文本内容
 */
export function sanitizeInput(input) {
  if (!input || typeof input !== 'string') return ''

  let cleaned = input

  // 移除 HTML 标签
  cleaned = cleaned.replace(/<[^>]*>/g, '')

  // 移除事件处理器属性（在标签已被剥离的情况下做二层防护）
  cleaned = cleaned.replace(/on\w+\s*=\s*["'][^"']*["']/gi, '')
  cleaned = cleaned.replace(/on\w+\s*=\s*[^\s>]*/gi, '')

  // 移除 javascript: 协议
  cleaned = cleaned.replace(/javascript\s*:/gi, '')

  // 移除 data: URI（防止 data:html 注入）
  cleaned = cleaned.replace(/data\s*:\s*text\/html[^)]*/gi, '')

  // 移除 CSS expression() 注入
  cleaned = cleaned.replace(/expression\s*\(/gi, '')

  // 移除 HTML 实体编码的标签（&#60; 等）
  cleaned = cleaned.replace(/&#x?[0-9a-f]+;?/gi, '')

  return cleaned.trim()
}

// ==================== 敏感词检测 ====================

/**
 * 敏感词/危险模式列表
 * 硬编码，构建时打包，无需后端请求
 */
const SENSITIVE_PATTERNS = [
  // SQL 注入
  { pattern: /\b(?:drop|truncate|alter)\s+(?:table|database|index)\b/gi, label: 'SQL DDL 操作' },
  { pattern: /\bdelete\s+from\b/gi, label: 'SQL 删除操作' },
  { pattern: /\binsert\s+into\b/gi, label: 'SQL 插入操作' },
  { pattern: /\bupdate\s+\w+\s+set\b/gi, label: 'SQL 更新操作' },
  { pattern: /\bselect\s+.*\bfrom\b/gi, label: 'SQL 查询操作' },
  { pattern: /'\s*;\s*(?:--|#|\/\*)/gi, label: 'SQL 注释注入' },

  // 命令注入
  { pattern: /\bexec\s*\(/gi, label: '命令执行函数' },
  { pattern: /\bsystem\s*\(/gi, label: '系统调用函数' },
  { pattern: /\beval\s*\(/gi, label: '代码执行函数' },
  { pattern: /\b(?:os|subprocess|child_process)\./gi, label: '系统模块调用' },
  { pattern: />\s*\/dev\/null/gi, label: 'Shell 重定向' },

  // Prompt 注入（中英文）
  { pattern: /ignore\s+(?:all\s+)?(?:previous|above)\s+instructions?/gi, label: 'Prompt 注入（忽略指令）' },
  { pattern: /忽略(?:所有)?(?:之前|上面)的?指令/gi, label: 'Prompt 注入（忽略指令-中文）' },
  { pattern: /system\s*prompt/gi, label: 'Prompt 注入（系统提示）' },
  { pattern: /you\s+are\s+(?:now|going\s+to)\s+(?:act|pretend|roleplay)/gi, label: 'Prompt 注入（角色扮演）' },
  { pattern: /忘记.*(?:设定|规则|限制)/gi, label: 'Prompt 注入（忘记规则-中文）' },
  { pattern: /DAN\s+(?:mode|prompt|jailbreak)/gi, label: 'Prompt 越狱' },

  // XSS 脚本注入
  { pattern: /<script\b/gi, label: '脚本标签注入' },
  { pattern: /<iframe\b/gi, label: 'iframe 注入' },
  { pattern: /<embed\b/gi, label: 'embed 注入' },
  { pattern: /<object\b/gi, label: 'object 注入' },

  // 路径遍历
  { pattern: /\.\.\/\.\.\//g, label: '路径遍历攻击' },
  { pattern: /(?:etc\/passwd|etc\/shadow|boot\.ini)/gi, label: '系统文件访问' },

  // ========== 辱骂与不文明用语 ==========
  // 中文辱骂（常见脏话关键词）
  { pattern: /傻[逼比屄叉]|[我你他她它]妈[逼比的]|草[泥你尼拟]马|操[你尼拟]|[日肏操艹](?:[你您]|他妈的)|狗[日肏]|[他她它]奶[奶的]|[去滚]你[妈吗]|[脑恼]残|弱智|白痴|智障|煞笔|沙雕/g, label: '不文明用语（中文）' },
  // 英文辱骂
  { pattern: /\b(?:fuck|shit|damn|asshole|bastard|bitch|dick|cunt|piss)\b/gi, label: '不文明用语（英文）' },
  // 人身攻击类
  { pattern: /(?:死全家|全家死|断子绝孙|不得好死|出门被车撞)/g, label: '人身攻击用语' },
  // 歧视性言论
  { pattern: /(?:支那|东亚病夫|蝗虫|黑鬼|白皮猪|阿三)/g, label: '歧视性用语' },

  // ========== 政治敏感 ==========
  // 注意：基础关键词过滤，仅作为前端辅助拦截，完整审核需后端内容安全服务
  { pattern: /(?:[六6][四4](?:事件|运动|屠杀)|天安门(?:事件|屠杀|镇压|学运|广场))/g, label: '政治敏感内容' },
  { pattern: /(?:[法法][轮车仑][功工]|falun\s*(?:gong|dafa))/gi, label: '政治敏感内容' },
  { pattern: /(?:台[独毒]|藏[独毒]|疆[独毒]|港[独毒]|两个中国|一中一台)/g, label: '政治敏感内容' },
  { pattern: /(?:习近平|习大大|李克强)(?:\s*(?:下台|下野|独裁|暴君|皇帝|包子|维尼))/g, label: '政治敏感内容' },
  { pattern: /(?:共产党|中共|CCP)(?:\s*(?:下台|灭亡|毁灭|独裁|暴政|邪恶))/g, label: '政治敏感内容' },
]

/**
 * 检测输入中的敏感/危险内容
 * @returns {{ clean: boolean, matches: { label: string, text: string }[] }}
 */
export function filterSensitive(input) {
  if (!input || typeof input !== 'string') {
    return { clean: true, matches: [] }
  }

  const matches = []

  for (const { pattern, label } of SENSITIVE_PATTERNS) {
    // 重置正则 lastIndex（全局正则需要）
    pattern.lastIndex = 0
    const match = pattern.exec(input)
    if (match) {
      matches.push({
        label,
        text: match[0].substring(0, 40)
      })
    }
  }

  return {
    clean: matches.length === 0,
    matches
  }
}

// ==================== 综合验证 ====================

/**
 * 综合验证：先清理 XSS，再检测敏感词
 * @returns {{ sanitized: string, isClean: boolean, matches: { label: string, text: string }[] }}
 */
export function validateInput(input) {
  const sanitized = sanitizeInput(input)
  const { clean, matches } = filterSensitive(sanitized)
  return { sanitized, isClean: clean, matches }
}
