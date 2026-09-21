import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

function applyResultStyle(widget) {
    if (!widget?.inputEl) return;
    widget.inputEl.readOnly = true;
    widget.inputEl.style.opacity = "0.9";
    widget.inputEl.style.backgroundColor = "rgba(0, 0, 0, 0.35)";
    widget.inputEl.style.color = "#4DEEEA"; // 极客青光蓝，清爽醒目
    widget.inputEl.style.fontSize = "12px";
    widget.inputEl.style.fontFamily = "Consolas, Monaco, monospace";
    widget.inputEl.style.fontWeight = "bold";
    widget.inputEl.style.borderRadius = "6px";
    widget.inputEl.style.border = "1px solid rgba(77, 238, 234, 0.3)";
    widget.inputEl.style.boxSizing = "border-box";
    widget.inputEl.style.width = "100%";
    widget.inputEl.style.wordBreak = "break-all";      // 保证不超出左右边界
    widget.inputEl.style.overflowWrap = "anywhere";   // 超长文本任意位置可折行
    widget.inputEl.style.whiteSpace = "pre-wrap";     // 自动换行，支持两行及多行
    widget.inputEl.style.lineHeight = "1.5";
    widget.inputEl.style.padding = "6px 8px";
}

app.registerExtension({
    name: "Trucy.TextToNumber.UI",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "TrucyTextToNumber") {
            const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function (message) {
                onExecuted?.apply(this, arguments);

                if (message?.text) {
                    let widget = this.widgets?.find((w) => w.name === "result_info");

                    // 第一次运行时动态生成多行自适应文本框
                    if (!widget) {
                        widget = ComfyWidgets["STRING"](
                            this,
                            "result_info",
                            ["STRING", { multiline: true }],
                            app
                        ).widget;
                        applyResultStyle(widget);
                    }

                    // 填入后端传来的结果并重新应用样式
                    widget.value = message.text.join("\n");
                    applyResultStyle(widget);

                    // 自动根据行数调整节点高度并重绘画布
                    this.onResize?.(this.computeSize());
                    this.setDirtyCanvas(true, true);
                }
            };
        }
    },
});