import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

app.registerExtension({
    name: "ComfyUI.AudioDetector.UI",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        // 精准绑定到音频检测网关节点
        if (nodeData.name === "AudioLengthDetector") {
            const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function(message) {
                onExecuted?.apply(this, arguments);
                
                // 监听 Python 后端传回的 ui.text
                if (message?.text) {
                    let widget = this.widgets?.find(w => w.name === "result_info");
                    
                    // 第一次运行时动态创建展示框
                    if (!widget) {
                        widget = ComfyWidgets["STRING"](this, "result_info", ["STRING", { multiline: true }], app).widget;
                        widget.inputEl.readOnly = true;
                        widget.inputEl.style.opacity = "0.85";
                        widget.inputEl.style.backgroundColor = "rgba(0, 0, 0, 0.25)";
                        widget.inputEl.style.color = "#00FF99"; // 科技绿荧光文字，视觉更清晰
                        widget.inputEl.style.fontWeight = "bold";
                    }
                    
                    // 填入计算结果文字
                    widget.value = message.text.join("\n");
                    
                    // 自动适应尺寸并强制重绘画布（避免节点变白或不刷新）
                    this.onResize?.(this.computeSize());
                    this.setDirtyCanvas(true, true);
                }
            };
        }
    }
});