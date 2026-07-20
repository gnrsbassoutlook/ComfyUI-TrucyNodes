import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

app.registerExtension({
    name: "ComfyUI.AudioDetector.UI",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        // 绑定到我们在 Python 中定义的类名
        if (nodeData.name === "AudioLengthDetector") {
            const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function(message) {
                onExecuted?.apply(this, arguments);
                
                // 监听Python传回的 "text"
                if (message.text) {
                    // 查找是否已经创建了信息展示框
                    let widget = this.widgets?.find(w => w.name === "result_info");
                    
                    // 如果没有，就新建一个多行字符串控件
                    if (!widget) {
                        widget = ComfyWidgets["STRING"](this, "result_info", ["STRING", { multiline: true }], app).widget;
                        // 设置为只读并略微变灰，以作为纯数据显示用
                        widget.inputEl.readOnly = true;
                        widget.inputEl.style.opacity = 0.7;
                        widget.inputEl.style.backgroundColor = "transparent";
                    }
                    
                    // 将计算好的文字展示上去
                    widget.value = message.text.join("");
                    
                    // 自动调整节点尺寸以适应文字高度
                    this.onResize?.(this.computeSize());
                }
            };
        }
    }
});