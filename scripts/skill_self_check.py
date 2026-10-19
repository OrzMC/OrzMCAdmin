#!/usr/bin/env python3
"""orzmc 技能自检：结构一致性 / 死链 / 孤儿 / 私有信息残留

用法:
    python3 scripts/skill_self_check.py

私有信息检查（可选）: 通过环境变量传入关键词，脚本本身**不含任何真实值**：
    ORZMC_PRIV_KEYS="关键词1,关键词2" python3 scripts/skill_self_check.py
未设置时跳过该项。
"""
import glob
import os
import re
import sys

import yaml

os.chdir(os.path.expanduser("~/.hermes/skills/gaming/orzmc"))
txt = open("SKILL.md", encoding="utf-8").read()
refs = {os.path.basename(p) for p in glob.glob("references/*.md")}
scripts = {os.path.basename(p) for p in glob.glob("scripts/*")}
mentioned = set(re.findall(r"references/([A-Za-z0-9_\-\.]+\.md)", txt))

ok = True
print("① frontmatter")
m = re.match(r"---\n(.*?)\n---\n", txt, re.S)
d = yaml.safe_load(m.group(1))
print(f"   name={d['name']} version={d['version']} desc={len(d['description'])}字符")
if not d.get("version"):
    ok = False

print("② 参考文档")
dead = sorted(x for x in mentioned if x not in refs)
orph = sorted(refs - mentioned)
print(f"   共 {len(refs)} 篇 / SKILL.md 引用 {len(mentioned)} 篇")
print(f"   死链: {dead or '无'}   孤儿: {orph or '无'}")
ok = ok and not dead and not orph

print("③ 技能内脚本")
ms = set(re.findall(r"`scripts/([A-Za-z0-9_\-\.]+\.(?:py|sh|js|ps1))`", txt))
mdead = sorted(s for s in ms if s not in scripts)
print(f"   技能内脚本 {len(scripts)} 个；SKILL.md 以 `scripts/x` 引用 {len(ms)} 个")
print(f"   引用但不在技能内（应有「脚本位置约定」说明）: {mdead or '无'}")

print("④ 可读性")
lines = txt.splitlines()
long = [(i + 1, len(x)) for i, x in enumerate(lines) if len(x) > 1200]
print(f"   SKILL.md {len(txt)} 字符 / {len(lines)} 行；超长行(>1200)：{long or '无'}")

print("⑤ 私有信息残留（关键词由 ORZMC_PRIV_KEYS 传入，脚本本身不含真实值）")
keys = [k for k in os.environ.get("ORZMC_PRIV_KEYS", "").split(",") if k.strip()]
if not keys:
    print("   （未设置 ORZMC_PRIV_KEYS，跳过）")
else:
    for kw in keys:
        n = txt.count(kw)
        if n:
            print(f"   {kw[:6]}***: {n} 处（导出时由 bisync 占位化）")
        else:
            print(f"   {kw[:6]}***: 0")

print("⑥ 章节结构")
for x in lines:
    if x.startswith("## "):
        print("   ", x)
print()
print("结果:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
