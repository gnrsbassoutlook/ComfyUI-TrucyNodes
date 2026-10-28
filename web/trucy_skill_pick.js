// Skill Loader Trucy —— 在节点上直接挑本地 .md/.txt 载入（临时 skill）
//
// 后端机制（trucy_skills.规范化内联文件）：整份文本塞进「加载文件内容」这只字符串控件，
// 就变成一次性的 inline skill。所以这里不需要额外交互接口，纯前端 FileReader 即可。
// 参考了 comfyUI-llama-TE 的 skill_loader_path.js，额外支持多选：
//   第一个选中的文件当 skill 正文，其余按「===== 文件名 =====」分块追加在后面，
//   这样「SKILL.md + references/*.md」可以一次挑进来，模型照样能读到附录。

import { app } from "../../scripts/app.js";

const 节点类型 = "TrucySkillLoader";
const 正文控件 = "加载文件名";
const 内容控件 = "加载文件内容";
const 自动选择 = "自动选择";
const 单次上限 = 3.2 * 1024 * 1024; // 后端硬上限 4 MB，留出分块头的余量

function 建元素(标签, 文本) {
  const el = document.createElement(标签);
  if (文本) el.textContent = 文本;
  return el;
}

app.registerExtension({
  name: "TrucyNodes.SkillPick",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== 节点类型) return;

    const 原onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      原onNodeCreated?.apply(this, arguments);
      if (typeof this.addDOMWidget !== "function") return;
      if (this.__trucySkillPick) return;

      const node = this;
      const 取控件 = (名) => node.widgets?.find((w) => w?.name === 名);
      const 写控件 = (名, 值) => {
        const w = 取控件(名);
        if (!w) return false;
        w.value = 值;
        try {
          w.callback?.(值);
        } catch (错误) {
          console.warn("[TrucyNodes] 写入 Skill 控件失败", 错误);
        }
        const 序 = node.widgets.indexOf(w);
        if (序 >= 0) {
          node.widgets_values ??= [];
          node.widgets_values[序] = 值;
        }
        return true;
      };
      // 这两个控件对用户没意义（一整段 skill 正文塞在面板里），藏掉只留按钮
      const 藏控件 = (w) => {
        if (!w || w.__trucySkillHidden) return;
        w.__trucySkillHidden = true;
        w.hidden = true;
        w.computeSize = () => [0, -4];
        w.draw = () => {};
        w.mouse = () => false;
        for (const el of [w.element, w.domElement, w.el, w.container]) {
          if (!el?.style) continue;
          el.style.display = "none";
          el.style.visibility = "hidden";
          el.style.width = "0";
          el.style.height = "0";
          el.style.margin = "0";
          el.style.padding = "0";
        }
      };
      藏控件(取控件(正文控件));
      藏控件(取控件(内容控件));

      const root = 建元素("div");
      const 提示 = 建元素("div", "临时 skill：只在本次会话生效，长期用请放进本插件 skills/ 目录");
      const 操作行 = 建元素("div");
      const 选择钮 = 建元素("button", "选择 .md 文件");
      const 清除钮 = 建元素("button", "清除");
      const 状态 = 建元素("div", "未加载临时文件");

      选择钮.type = "button";
      清除钮.type = "button";
      操作行.append(选择钮, 清除钮);
      root.append(提示, 操作行, 状态);

      Object.assign(root.style, {
        boxSizing: "border-box",
        width: "100%",
        padding: "4px 6px",
        border: "1px solid rgba(255,255,255,0.12)",
        borderRadius: "4px",
        background: "rgba(0,0,0,0.16)",
        color: "#cfd5dc",
        fontSize: "10px",
        lineHeight: "13px",
        whiteSpace: "normal",
        overflowWrap: "anywhere",
      });
      Object.assign(操作行.style, { display: "flex", gap: "4px", marginTop: "4px" });
      选择钮.style.flex = "1 1 auto";
      清除钮.style.flex = "0 0 auto";
      for (const 钮 of [选择钮, 清除钮]) {
        Object.assign(钮.style, {
          minHeight: "24px",
          padding: "2px 7px",
          border: "1px solid rgba(255,255,255,0.16)",
          borderRadius: "3px",
          background: "rgba(255,255,255,0.08)",
          color: "inherit",
          font: "inherit",
          cursor: "pointer",
        });
      }
      Object.assign(状态.style, { color: "#9da8b5", marginTop: "3px" });
      提示.style.color = "#8b95a1";

      const 刷新状态 = () => {
        const 名 = String(取控件(正文控件)?.value || "").trim();
        const 正文 = String(取控件(内容控件)?.value || "");
        const 附录数 = (正文.match(/^===== .+ =====$/gm) || []).length;
        if (名 && 正文.trim()) {
          状态.textContent = 附录数 ? `已加载：${名}（另含 ${附录数} 份附录）` : `已加载：${名}`;
        } else {
          状态.textContent = "未加载临时文件";
        }
        const 空 = !(名 && 正文.trim());
        清除钮.disabled = 空;
        清除钮.style.opacity = 空 ? "0.5" : "1";
        node.graph?.setDirtyCanvas?.(true, true);
      };

      const 读文件 = (file) =>
        new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onerror = () => reject(new Error(`读取 ${file.name} 失败`));
          reader.onload = () => resolve(String(reader.result || ""));
          reader.readAsText(file, "UTF-8");
        });

      选择钮.onclick = (事件) => {
        事件.preventDefault();
        事件.stopPropagation();
        const input = 建元素("input");
        input.type = "file";
        input.accept = ".md,.txt,text/markdown,text/plain";
        input.multiple = true;
        input.onchange = async () => {
          const 文件们 = Array.from(input.files || []);
          if (!文件们.length) return;
          // .md/.txt 才要；其它一律挡掉（后端也只认这两种）
          const 合格 = 文件们.filter((f) => /\.(md|txt)$/i.test(f.name));
          if (!合格.length) {
            状态.textContent = "只支持 .md / .txt 文件";
            return;
          }
          try {
            const 正文们 = await Promise.all(合格.map(读文件));
            // SKILL.md 优先当正文，否则用第一个
            let 主 = 合格.findIndex((f) => f.name.toLowerCase() === "skill.md");
            if (主 < 0) 主 = 0;
            const 名 = 合格[主].name;
            let 内容 = 正文们[主];
            const 附 = 合格
              .filter((_, i) => i !== 主)
              .map((f, i) => `\n\n===== ${f.name} =====\n${正文们[合格.indexOf(f)]}`);
            内容 = 内容 + 附.join("");
            if (内容.length > 单次上限) {
              状态.textContent = `合计超过 ${(单次上限 / 1024 / 1024).toFixed(1)} MB，请少选几份`;
              return;
            }
            写控件(正文控件, 名);
            写控件(内容控件, 内容);
            写控件("skill", 自动选择); // 临时文件优先，下拉不必再指定
            刷新状态();
          } catch (错误) {
            状态.textContent = String(错误?.message || 错误);
          }
        };
        input.click();
      };

      清除钮.onclick = (事件) => {
        事件.preventDefault();
        事件.stopPropagation();
        写控件(正文控件, "");
        写控件(内容控件, "");
        刷新状态();
      };

      const 原onConfigure = node.onConfigure;
      node.onConfigure = function () {
        const 结果 = 原onConfigure?.apply(this, arguments);
        setTimeout(刷新状态, 0);
        return 结果;
      };

      const 控件 = this.addDOMWidget("trucy_skill_pick", "trucy_skill_pick", root, {
        hideOnZoom: false,
        serialize: false,
        getMinHeight: () => 62,
      });
      控件.computeSize = (宽) => [宽, 62];
      this.__trucySkillPick = 控件;
      刷新状态();
      node.graph?.setDirtyCanvas?.(true, true);
    };
  },
});
